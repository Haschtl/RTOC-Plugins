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
        #self.last_time = time.time()
        self.samplerate = 10

        self.recordLength = 5000
        self.blocksize = self.recordLength
        #self.xData = deque(maxlen=self.recordLength)
        self.yData1 = deque(maxlen=self.recordLength)
        self.yData2 = deque(maxlen=self.recordLength)

        self.yData1Triggered = deque(maxlen=self.recordLength)
        self.yData2Triggered = deque(maxlen=self.recordLength)
        self.singleTriggerFound = False

    # def close(self):
    #     self.run=False

        # if self.scope:
        #     self.scope.close_handle()

    # THIS IS YOUR THREAD
    def updateT(self):
        self.__capturer = Thread(target=self.__captureT)
        self.__capturer.start()
        diff = 0
        #self.data = []
        #start_time = time.time()
        #print("Clearing FIFO and starting data transfer...")
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            if not self.widget.pauseButton.isChecked():
                if self.widget.enableTriggerButton.isChecked():
                    yData1, yData2, stop = self.__trigger(list(self.yData1),list(self.yData2))
                else:
                    yData1 = self.yData1
                    yData2 = self.yData2
                    stop = False
                samplerate = self.str2Samplerate(self.widget.samplerateComboBox.currentText())
                xData = [i/samplerate for i in range(len(yData1))]
                if len(self.yData1)>1:
                    self.plot(xData, yData1, dname='Hantek', sname='CH1', unit='V')
                if self.widget.channel2CheckBox.isChecked():
                    self.plot(xData, yData2, dname='Hantek', sname='CH2', unit='V')
                if stop:
                    self.widget.pauseButton.setChecked(True)
            diff = (time.time() - start_time)

        self.__capturer.join()

    def __captureT(self):
        #self.last_time = time.time()
        shutdown_event = self.scope.read_async(self.extend_callback, self.blocksize, outstanding_transfers=10,raw=True)
        self.scope.start_capture()
        while self.run:
            self.scope.poll()
        # print("Stopping new transfers.")
        #scope.stop_capture()
        self.scope.stop_capture()
        shutdown_event.set()
        time.sleep(0.1)
        self.scope.close_handle()

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Hantek6022/hantek.ui", self.widget)
        # self.setCallbacks()
        self.widget.reconnectButton.clicked.connect(self.__openConnectionCallback)
        self.widget.samplerateComboBox.currentTextChanged.connect(self.updateScopeSettings)
        self.widget.recordLengthSpinBox.valueChanged.connect(self.changeLength)
        #self.widget.channel1CheckBox.valueChanged.connect(self.enableChannel1)
        self.widget.channel1CheckBox.setEnabled(False)
        self.widget.channel1ACDCComboBox.hide()#valueChanged.connect(self.)
        self.widget.channel1VoltPDivComboBox.currentTextChanged.connect(self.updateScopeSettings)
        self.widget.channel2VoltPDivComboBox.currentTextChanged.connect(self.updateScopeSettings)
        self.widget.channel2CheckBox.stateChanged.connect(self.updateScopeSettings)
        self.widget.channel2ACDCComboBox.hide()#valueChanged.connect(self.)
        #self.widget.pauseButton.clicked.connect(self.)

        #self.widget.triggerChannelComboBox.textChanged.connect(self.)
        #self.widget.triggerLevelSpinBox.valueChanged.connect(self.)
        #self.widget.enableTriggerButton.clicked.connect(self.)
        self.recordLength = self.widget.recordLengthSpinBox.value()
        self.xData = deque(maxlen=self.recordLength)
        self.yData1 = deque(maxlen=self.recordLength)
        self.yData2 = deque(maxlen=self.recordLength)
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
            self.updateScopeSettings()
            self.widget.reconnectButton.setText("Stop")
            self.widget.reconnectButton.setEnabled(True)

    def __trigger(self, data1, data2):
        if not self.singleTriggerFound:
            if self.widget.channel2CheckBox.isChecked() and self.widget.triggerChannelComboBox.currentText()=='CH2':
                triggerSignal = list(data2)
            else:
                triggerSignal = list(data1)

            flanke = self.widget.comboBox.currentText()
            triggerLevel = self.widget.triggerLevelSpinBox.value()
            cutoff = 0
            mean = self.widget.smoothSpinBox.value()
            # if mean >= len(triggerSignal):
            #     mean = 10

            # if flanke == 'Rising':
            #     for idx in range(len(triggerSignal)-2*mean):
            #         if np.mean(triggerSignal[idx+mean+1:idx+2*mean-1])>triggerLevel and np.mean(triggerSignal[idx:idx+mean])<=triggerLevel:
            #             cutoff = idx+mean
            #             break
            #         if idx>=len(triggerSignal)/10:
            #             break
            # else:
            #     for idx in range(len(triggerSignal)-2*mean):
            #         if np.mean(triggerSignal[idx+mean+1:idx+2*mean-1])<triggerLevel and np.mean(triggerSignal[idx:idx+mean])>=triggerLevel:
            #             cutoff = idx+mean
            #             break
            #         if idx>=len(triggerSignal)/10:
            #             break
            triggerPrepared = False

            if flanke == 'Rising':
                if max(triggerSignal)>triggerLevel:
                    for idx in range(len(triggerSignal)):
                        if triggerSignal[idx]>=triggerLevel-mean and triggerSignal[idx]<=triggerLevel:
                            triggerPrepared = True
                            print('Trigger prepared')
                        elif triggerSignal[idx]<triggerLevel-mean and triggerPrepared:
                            triggerPrepared = False
                            print(' ... unprepared')
                        elif triggerSignal[idx]>triggerLevel and triggerPrepared == True:
                            cutoff = idx
                            print('Triggered')
                            break
            else:
                if min(triggerSignal)<triggerLevel:
                    for idx in range(len(triggerSignal)):
                        if triggerSignal[idx]<=triggerLevel+mean and triggerSignal[idx]>=triggerLevel:
                            triggerPrepared = True
                            print('Trigger prepared')
                        elif triggerSignal[idx]>triggerLevel+mean  and triggerPrepared:
                            triggerPrepared = False
                            print(' ... unprepared')
                        elif triggerSignal[idx]<triggerLevel and triggerPrepared == True:
                            cutoff = idx
                            print('Triggered')
                            break
            stop = False


            if len(data2)>cutoff:
                data2 = list(data2)[cutoff:]
            if len(data1)>cutoff:
                data1 = list(data1)[cutoff:]

            if cutoff!=0 and self.widget.checkBox.isChecked() and not self.singleTriggerFound:
                self.singleTriggerFound = True
            else:
                self.singleTriggerFound = False
            if self.widget.checkBox.isChecked():
                self.yData1Triggered = deque(list(data1),maxlen=self.recordLength)
                self.yData2Triggered = deque(list(data2),maxlen=self.recordLength)
        else:
            if len(self.yData1Triggered)<self.recordLength:
                # self.yData1Triggered.extend(data1)
                # self.yData2Triggered.extend(data2)
                pass
            else:
                #self.yData1Triggered.extend(data1[0:self.recordLength-len(self.yData1Triggered)])
                #self.yData2Triggered.extend(data2[0:self.recordLength-len(self.yData1Triggered)])
                stop = True
                data1 = self.yData1Triggered
                data2 = self.yData2Triggered

        return data1, data2, stop

    def updateScopeSettings(self):
        if self.scope:
            self.run = False
            self.__updater.join()

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
        if self.widget.channel2CheckBox.isChecked():
            self.scope.set_num_channels(2)
        else:
            self.scope.set_num_channels(1)
        # set voltage range
        voltagerange1 = self.strVoltageToID(self.widget.channel1VoltPDivComboBox.currentText())
        voltagerange2 = self.strVoltageToID(self.widget.channel2VoltPDivComboBox.currentText())
        self.scope.set_ch1_voltage_range(voltagerange1)
        self.scope.set_ch2_voltage_range(voltagerange2)

        self.scope.set_sample_rate(self.str2SamplerateID(self.widget.samplerateComboBox.currentText()))

        self.blocksize = self.recordLength

        self.run = True
        self.__updater = Thread(target=self.updateT)
        self.__updater.start()
        #self.widget.reconnectButton.setText("Stop")
        #self.widget.reconnectButton.setEnabled(True)


    # def set_sampling_rate(self, samplerate): # sample rate in MHz or in 10khz
    #     # if self.scope:
    #     #     self.run = False
    #     #     self.__updater.join()
    #     #     self.scope.open_handle()
    #     #     self.scope.set_sample_rate(samplerate)
    #     #     self.__updater = Thread(target=self.updateT)
    #     #     self.__updater.start()
    #     self.updateScopeSettings()

    def calibrate(self):
        if self.scope:
            self.scope.setup_dso_cal_level()
            cal_level = self.scope.get_calibration_data()
            self.scope.set_dso_calibration(cal_level)

    # def __changeSamplerate(self, strung):
    #     #self.set_sampling_rate(self.str2SamplerateID(strung))
    #     self.updateScopeSettings()

    def str2SamplerateID(self,strung):
        if 'MHz' in strung:
            strung = strung.replace(' MHz','')
            return int(strung)
        else:
            strung = strung.replace(' kHz','')
            return int(int(strung)/10)

    def str2Samplerate(self,strung):
        if 'MHz' in strung:
            strung = strung.replace(' MHz','')
            return int(strung)*1000000
        else:
            strung = strung.replace(' kHz','')
            return int(strung)*1000

    # def __changeChannel1VoltPDiv(self, strung):
    #     if self.scope:
    #         voltagerange = self.strVoltageToID(strung)
    #         self.scope.set_ch1_voltage_range(voltagerange)
    #
    # def __changeChannel2VoltPDiv(self, strung):
    #     if self.scope:
    #         voltagerange = self.strVoltageToID(strung)
    #         self.scope.set_ch2_voltage_range(voltagerange)

    def enableChannel2(self, value):
        if value:
            self.scope.set_num_channels(2)
        else:
            self.scope.set_num_channels(1)

    def strVoltageToID(self, strung):
        voltagerange = 1
        if strung == '2.6 V':
            voltagerange = 2
        elif strung == '5 V':
            voltagerange = 5
        elif strung == '10 V':
            voltagerange = 10
        return voltagerange

    def extend_callback(self, ch1_data, ch2_data):
        voltage_data = self.scope.scale_read_data(ch1_data, self.strVoltageToID(self.widget.channel1VoltPDivComboBox.currentText()))
        if len(voltage_data)>1:
            self.yData1.extend(voltage_data)
            if len(self.yData1Triggered)<self.recordLength:
                if len(self.yData1Triggered)+len(voltage_data)<self.recordLength:
                     self.yData1Triggered.extend(voltage_data)
                else:
                    self.yData1Triggered.extend(voltage_data[0:self.recordLength-len(self.yData1Triggered)])

        if ch2_data != '':
            voltage_data = self.scope.scale_read_data(ch2_data, self.strVoltageToID(self.widget.channel1VoltPDivComboBox.currentText()))
            self.yData2.extend(voltage_data)
            if len(self.yData2Triggered)<self.recordLength:
                if len(self.yData2Triggered)+len(voltage_data)<self.recordLength:
                     self.yData2Triggered.extend(voltage_data)
                else:
                    self.yData2Triggered.extend(voltage_data[0:self.recordLength-len(self.yData2Triggered)])

    def changeLength(self, newlen=10000):
        self.recordLength = newlen
        self.yData1 = deque(maxlen=self.recordLength)
        self.yData2 = deque(maxlen=self.recordLength)
        self.yData1Triggered = deque(maxlen=self.recordLength)
        self.yData2Triggered = deque(maxlen=self.recordLength)
        self.updateScopeSettings()


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
