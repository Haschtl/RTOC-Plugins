## Hantek API from https://github.com/rpcope1/Hantek6022API/blob/master/PyHT6022/LibUsbScope.py

try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin
import time
from threading import Thread
import traceback
import requests
from PyQt5 import uic
from PyQt5 import QtWidgets
import socket
import threading
import os
import numpy as np

from struct import pack
from collections import deque

from PyHT6022.LibUsbScope import Oscilloscope

devicename = 'Hantek6022'


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = False

        #self.data = []
        #self.data_extend = self.data.append
        # Data-logger thread
        self.scope = None
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()
        self.blocksize = 6*1024      # should be divisible by 6*1024
        self.alternative = 1         # choose ISO 3072 bytes per 125 us
        self.last_time = time.time()
        self.samplerate = 1

    def close(self):
        if self.scope:
            self.scope.close_handle()

    # THIS IS YOUR THREAD
    def updateT(self):
        #self.data = []
        #start_time = time.time()
        #print("Clearing FIFO and starting data transfer...")
        self.last_time = time.time()
        shutdown_event = self.scope.read_async(self.extend_callback, self.blocksize, outstanding_transfers=10,raw=True)
        self.scope.start_capture()
        while self.run:
            self.scope.poll()
        # print("Stopping new transfers.")
        #scope.stop_capture()
        shutdown_event.set()
        #time.sleep(1)
        self.scope.stop_capture()
        self.scope.close_handle()

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Hantek6022/hantek.ui", self.widget)
        # self.setCallbacks()
        self.widget.reconnectButton.clicked.connect(self.__openConnectionCallback)
        self.widget.samplerateComboBox.currentTextChanged.connect(self.__changeSamplerate)
        #self.widget.recordLengthSpinBox.valueChanged.connect(self.)
        #self.widget.channel1CheckBox.valueChanged.connect(self.enableChannel1)
        self.widget.channel1CheckBox.setEnabled(False)
        #self.widget.channel1ACDCComboBox.valueChanged.connect(self.)
<<<<<<< HEAD
        self.widget.channel1VoltPDivComboBox.currentTextChanged.connect(self.__changeChannel1VoltPDiv)
        self.widget.channel2VoltPDivComboBox.currentTextChanged.connect(self.__changeChannel2VoltPDiv)
        #self.widget.channel2CheckBox.valueChanged.connect(self.enableChannel2)
=======
        self.widget.channel1VoltPDivComboBox.textChanged.connect(self.__changeChannel1VoltPDiv)
        self.widget.channel2VoltPDivComboBox.textChanged.connect(self.__changeChannel2VoltPDiv)
        self.widget.channel2CheckBox.valueChanged.connect(self.enableChannel2)
>>>>>>> 6639ef4368de6e2c0c04ab81df3edb79d43a3ecf
        #self.widget.channel2ACDCComboBox.valueChanged.connect(self.)
        #self.widget.pauseButton.clicked.connect(self.)

        #self.widget.triggerChannelComboBox.textChanged.connect(self.)
        #self.widget.triggerLevelSpinBox.valueChanged.connect(self.)
        #self.widget.enableTriggerButton.clicked.connect(self.)
        self.__openConnectionCallback()
        return self.widget

    def __openConnectionCallback(self):
        self.widget.reconnectButton.setEnabled(False)
        if self.run:
            self.run = False
            self.widget.reconnectButton.setText("Reconnect")
            self.__base_address = ""
            self.widget.reconnectButton.setEnabled(True)
        else:
            self.scope = Oscilloscope()
            self.scope.setup()
            self.scope.open_handle()
            if (not self.scope.is_device_firmware_present):
                self.scope.flash_firmware()
            else:
                self.scope.supports_single_channel = True;

            print("Setting up scope!")
            self.scope.set_interface(self.alternative);
            print("ISO" if self.scope.is_iso else "BULK", "packet size:", self.scope.packetsize)
            self.scope.set_num_channels(1)
            # set voltage range
            self.__changeChannel1VoltPDiv('1 V')
            self.__changeChannel2VoltPDiv('1 V')

            self.run = True
            self.__updater = Thread(target=self.updateT)
            self.__updater.start()
            self.widget.reconnectButton.setText("Stop")
            self.widget.reconnectButton.setEnabled(True)


    def set_sampling_rate(self, samplerate): # sample rate in MHz or in 10khz
        if self.scope:
            self.scope.set_sample_rate(samplerate)

    def calibrate(self):
        if self.scope:
            self.scope.setup_dso_cal_level()
            cal_level = self.scope.get_calibration_data()
            self.scope.set_dso_calibration(cal_level)

    def __changeSamplerate(self, strung):
        self.set_sampling_rate(self.str2SamplerateID(strung))

    def str2SamplerateID(self,strung):
        if 'MHz' in strung:
            strung = strung.replace(' MHz','')
            return int(strung)
        else:
            strung = strung.replace(' kHz','')
            return int(strung)/10

    def __changeChannel1VoltPDiv(self, strung):
        if self.scope:
            voltagerange = self.strVoltageToID(strung)
            self.scope.set_ch1_voltage_range(voltagerange)

    def __changeChannel2VoltPDiv(self, strung):
        if self.scope:
            voltagerange = self.strVoltageToID(strung)
            self.scope.set_ch2_voltage_range(voltagerange)
    def enableChannel2(self, value):
        if value:
            self.scope.

    def strVoltageToID(self, strung):
        voltagerange = 1
        if strung == '2.6 V':
            voltagerange = 2
        elif strung == '5 V':
            voltagerange = 5
        elif strung == '10 V':
            voltagerange = 10
        return voltagerange

    def extend_callback(self, ch1_data, _):
        voltage_data = self.scope.scale_read_data(ch1_data, self.strVoltageToID(self.widget.channel1VoltPDivComboBox.currentText()))
        #print(voltage_data)
        if len(voltage_data)>1:
            #timing_data = np.linspace(self.last_time, time.time(),len(voltage_data))
            self.last_time = time.time()
            timing_data, _ = self.scope.convert_sampling_rate_to_measurement_times(len(voltage_data), self.str2SamplerateID(self.widget.samplerateComboBox.currentText()))
            #self.data_extend(ch1_data)
            self.plot(timing_data,voltage_data, hold='on', unit='V')

    # def __getData(self):
    #     if self.scope:
    #         self.data = []
    #
    #
    #         start_time = time.time()
    #         #print("Clearing FIFO and starting data transfer...")
    #         shutdown_event = self.scope.read_async(self.extend_callback, self.blocksize, outstanding_transfers=10,raw=True)
    #         self.scope.start_capture()
    #         while time.time() - start_time < 0.1:
    #             self.scope.poll()
    #         # print("Stopping new transfers.")
    #         #scope.stop_capture()
    #         shutdown_event.set()
    #         #time.sleep(1)
    #         self.scope.stop_capture()
    #         #scope.close_handle()
    #         #x = np.linspace(start_time, time.time(),len(self.data))
    #         voltage_data = self.scope.scale_read_data(self.data, self.strVoltageToID(self.widget.channel1VoltPDivComboBox.currentText()))
    #         timing_data, _ = self.scope.convert_sampling_rate_to_measurement_times(len(voltage_data), self.str2SamplerateID(self.widget.samplerateComboBox.currentText()))
    #         return timing_data, voltage_data
    #     else:
    #         return [0],[0]


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
