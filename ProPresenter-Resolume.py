""" ProPresenter & Resolume Link - Send ProPresenter text to Resolume """

import os
import json
import time
from ProPresenterStageDisplayClientComms import ProPresenterStageDisplayClientComms
from pythonosc import osc_message_builder
from pythonosc import udp_client

__author__ = "Anthony Eden"
__copyright__ = "Copyright 2017, Anthony Eden / Media Realm"
__credits__ = ["Anthony Eden"]
__license__ = "GPL"
__version__ = "0.1"

class ProPResolume():

    # Store the threaded classes for ProPresenter and Resolume
    ProPresenter = None
    Resolume = None

    # Config data for ProPresenter
    ProP_IPAddress = None
    ProP_IPPort = None
    ProP_Password = None

    # Config data for Resolume
    Resolume_IPAddress = None
    Resolume_IPPort = None
    Resolume_TextBoxOSCPaths = []
    Resolume_TextMatches = []
    
    # Allow splitting the text at a certain delimiter
    splitLinesChar = None

    NextRelease = None

    # Do we need to attempt a reconnection?
    tryReconnect = False
    disconnectTime = 0

    def __init__(self):
        # Setup the application

        # Get the config from JSON
        try:
            ConfigData_Filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
            ConfigData_JSON = open(ConfigData_Filename).read()
            ConfigData = json.loads(ConfigData_JSON)

        except Exception as e:
            print()
            print("##############################################")
            print("EXCEPTION: Cannot load and parse Config.JSON File: ")
            print(e)
            print("##############################################")
            print()

            exit()

        try:
            self.ProP_IPAddress = ConfigData['ProP_IPAddress']
            self.ProP_IPPort = int(ConfigData['ProP_IPPort'])
            self.ProP_Password = ConfigData['ProP_Password']

            self.Resolume_IPAddress = ConfigData['Resolume_IPAddress']
            self.Resolume_IPPort = int(ConfigData['Resolume_IPPort'])
            self.Resolume_TextBoxOSCPaths = ConfigData['Resolume_TextBoxOSCPaths']

            if 'TextMatchTriggers' in ConfigData:
                self.Resolume_TextMatches = ConfigData['TextMatchTriggers']
            
            if "SplitLines" in ConfigData:
                self.splitLinesChar = ConfigData['SplitLines']

        except Exception as e:
            print()
            print("##############################################")
            print("EXCEPTION: Config file is missing a setting")
            print(e)
            print("##############################################")
            print()

            exit()

        self.connectProP()
        self.connectResolume()
        self.reconnect_tick()

    def connectProP(self):
        # Connect to ProPresenter and setup the necessary callbacks
        self.tryReconnect = False
        self.disconnectTime = 0

        self.ProPresenter = ProPresenterStageDisplayClientComms(self.ProP_IPAddress, self.ProP_IPPort, self.ProP_Password)
        self.ProPresenter.addSubscription("CurrentSlide", self.updateSlideTextCurrent)
        self.ProPresenter.addSubscription("Connected", self.connected)
        self.ProPresenter.addSubscription("ConnectionFailed", self.connectFailed)
        self.ProPresenter.addSubscription("Disconnected", self.disconnected)
        self.ProPresenter.start()
    
    def connectResolume(self):
        self.Resolume = udp_client.SimpleUDPClient(self.Resolume_IPAddress, self.Resolume_IPPort)

    def connected(self, data):
        print("ProPresenter Connected")

    def connectFailed(self, error):
        self.tryReconnect = True

        if self.disconnectTime == 0:
            self.disconnectTime = time.time()

        print("ProPresenter Connect Failed", error)

    def disconnected(self, error):
        self.tryReconnect = True

        if self.disconnectTime == 0:
            self.disconnectTime = time.time()

        print("ProPresenter Disconnected", error)

    def reconnect_tick(self):
        if self.tryReconnect and self.disconnectTime < time.time() - 5:
            print("Attempting to reconnect to ProPresenter")
            self.connectProP()

        #self.labelCurrent.after(2000, self.reconnect_tick)

    def updateSlideTextCurrent(self, data):
        # Update the text label for the current slide
        
        if self.splitLinesChar is not None and data['text'] is not None and self.splitLinesChar in data['text']:
            data['text'] = data['text'].split(self.splitLinesChar)
            data['text'] = data['text'][0]
        
        if data['text'] is not None:
            self.resolumeSendText(data['text'].encode('utf-8'))
        else:
            self.resolumeSendText("\n")

    def resolumeSendText(self, text):
        if type(text) is bytes:
            text = text.decode().strip(' \t\r\n\0')
        
        text = text.strip()
        text = text.replace('\x00', ' ')
        
        if text == "":
            text = " "

        for path in self.Resolume_TextBoxOSCPaths:
            try:
                print("Sending text:", text)
                self.Resolume.send_message(path, text)
            except Exception as e:
                print("EXCEPTION while sending text!", e)
        
        foundMatch = False

        for match in self.Resolume_TextMatches:
            if match['Text'] in text:
                print("Matched text", text)
                foundMatch = True
                for command in match['Commands']:

                    if len(command) > 1:
                        args = command[1:]
                    else:
                        args = [True]

                    print(command)

                    try:
                        self.Resolume.send_message(command[0], *args)
                    except Exception as e:
                        print("EXCEPTION while doing text triggers!", e)

                if 'CommandReleased' in match:
                    self.NextRelease = match['CommandReleased']
                
                break
        
        if foundMatch is False and self.NextRelease is not None:
            for command in self.NextRelease:
                if len(command) > 1:
                    args = command[1:]
                else:
                    args = [True]
                
                print(command)
                self.Resolume.send_message(command[0], *args)
            

    def close(self):
        # Terminate the application
        if self.ProPresenter is not None:
            self.ProPresenter.stop()

if __name__ == "__main__":
    ProPResolume()
