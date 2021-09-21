import json
import cv2
import base64
import threading
import time
from datetime import datetime
from websocket_server import WebsocketServer
import logging

from interfaces.pose3d import ListenerPose3d
from interfaces.laser import ListenerLaser

from map import Map

# Graphical User Interface Class


class GUI:
    map = None

    # Initialization function
    # The actual initialization
    def __init__(self, host, hal):
        t = threading.Thread(target=self.run_server)

        self.payload = {'map': ''}
        self.server = None
        self.client = None

        self.host = host

        self.acknowledge = False
        self.acknowledge_lock = threading.Lock()

        # Take the console object to set the same websocket and client
        self.hal = hal
        t.start()

        # Create the map object
        laser_object_f = ListenerLaser("/F1ROS/laser_f/scan")
        laser_object_r = ListenerLaser("/F1ROS/laser_r/scan")
        laser_object_b = ListenerLaser("/F1ROS/laser_b/scan")
        pose3d_object = ListenerPose3d("/F1ROS/odom")
        self.map = Map(laser_object_f, laser_object_r, laser_object_b, pose3d_object)

    # Explicit initialization function
    # Class method, so user can call it without instantiation
    @classmethod
    def initGUI(self):
        # self.payload = {'image': '', 'shape': []}
        pass

    # Function to get the client
    # Called when a new client is received
    def get_client(self, client, server):
        self.client = client

    # Function to get value of Acknowledge
    def get_acknowledge(self):
        self.acknowledge_lock.acquire()
        acknowledge = self.acknowledge
        self.acknowledge_lock.release()

        return acknowledge

    # Function to get value of Acknowledge
    def set_acknowledge(self, value):
        self.acknowledge_lock.acquire()
        self.acknowledge = value
        self.acknowledge_lock.release()

    # Update the gui
    def update_gui(self):
        # Payload Map Message
        map_message = self.map.get_json_data()
        self.payload["map"] = map_message

        message = "#gui" + json.dumps(self.payload)
        self.server.send_message(self.client, message)

    # Function to read the message from websocket
    # Gets called when there is an incoming message from the client
    def get_message(self, client, server, message):
        # Acknowledge Message for GUI Thread
        if(message[:4] == "#ack"):
            self.set_acknowledge(True)

    # Activate the server
    def run_server(self):
        self.server = WebsocketServer(port=2303, host=self.host)
        self.server.set_fn_new_client(self.get_client)
        self.server.set_fn_message_received(self.get_message)
        self.server.run_forever()

    # Function to reset
    def reset_gui(self):
        self.map.reset()


# This class decouples the user thread
# and the GUI update thread
class ThreadGUI:
    def __init__(self, gui):
        self.gui = gui

        # Time variables
        self.time_cycle = 80
        self.ideal_cycle = 80
        self.iteration_counter = 0

    # Function to start the execution of threads
    def start(self):
        self.measure_thread = threading.Thread(target=self.measure_thread)
        self.thread = threading.Thread(target=self.run)

        self.measure_thread.start()
        self.thread.start()

        print("GUI Thread Started!")

    # The measuring thread to measure frequency
    def measure_thread(self):
        while(self.gui.client == None):
            pass

        previous_time = datetime.now()
        while(True):
            # Sleep for 2 seconds
            time.sleep(2)

            # Measure the current time and subtract from previous time to get real time interval
            current_time = datetime.now()
            dt = current_time - previous_time
            ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
            previous_time = current_time

            # Get the time period
            try:
                # Division by zero
                self.ideal_cycle = ms / self.iteration_counter
            except:
                self.ideal_cycle = 0

            # Reset the counter
            self.iteration_counter = 0

    # The main thread of execution
    def run(self):
        while(self.gui.client == None):
            pass

        while(True):
            start_time = datetime.now()
            self.gui.update_gui()
            acknowledge_message = self.gui.get_acknowledge()

            while(acknowledge_message == False):
                acknowledge_message = self.gui.get_acknowledge()

            self.gui.set_acknowledge(False)

            finish_time = datetime.now()
            self.iteration_counter = self.iteration_counter + 1

            dt = finish_time - start_time
            ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
            if(ms < self.time_cycle):
                time.sleep((self.time_cycle-ms) / 1000.0)
