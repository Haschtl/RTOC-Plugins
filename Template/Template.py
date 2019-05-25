# This template shows, how to implement plugins in RTOC
# RTOC version 2.0

# A plugin needs to import RTOC.LoggerPlugin to be recognized by RTOC.
try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import sys
import time
from PyQt5 import uic
from PyQt5 import QtWidgets
import numpy as np

DEVICENAME = "Template"  # Define the name of this Device

AUTORUN = True  # If true, the thread to collect data will run right after initializing this plugin
SAMPLERATE = 1  # The thread,which is supposed to collect data will be executed with 1 Hz


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None):
        # Plugin configuration
        # Call this to initialize RTOC.LoggerPlugin
        super(Plugin, self).__init__(stream, plot, event)
        # Set a devicename.
        # This will be used for all signals sent by this plugin as default
        self.setDeviceName(DEVICENAME)

        # GUI configuration
        self.smallGUI = True  # Only cares, if your Plugin has a GUI

        # Initialize some Data-logger thread
        self._firstrun = True
        self.setPerpetualTimer(self._updateT, samplerate=SAMPLERATE)
        if AUTORUN:
            self.start()

    # This function is being called in a thread.
    def _updateT(self):
        # Do something, collect data ,...
        # for example:
        y1 = np.sin(time.time())
        y2 = np.cos(time.time())

        # Then send your data
        self.stream([y1, y2], snames=['Sinus', 'Cosinus'],
                    unit=["kg", "m"])  # send data to RTOC

        # You can also plot data like this:
        self.plot([-10, 0], [2, 1], sname='Plot', unit='Wow')

        # Or send an event with self.event(text='',sname='')
        # (but use with caution, it can spam your RTOC plots):
        if self._firstrun:
            self.event('Test event', sname='Plot', id='testID')
            self._firstrun = False

    # This function is used to initialize a own Plugin-GUI,
    # which will be available in RTOC.
    # Remove it, if you don't want a GUI for your plugin.
    def loadGUI(self):
        self.widget = QtWidgets.QWidget()  # Create an empty QWidget
        packagedir = self.getDir(__file__)  # Get filepath of this file
        # Load a GUI designed with QDesigner
        uic.loadUi(packagedir+"/Template/template.ui", self.widget)
        return self.widget  # This function needs to return a QWidget


# Sometimes you want to use plugins standalone also. Very useful for testing.
hasGUI = True  # If your plugin has a widget do this

if __name__ == "__main__":
    if hasGUI:
        app = QtWidgets.QApplication(sys.argv)
        myapp = QtWidgets.QMainWindow()

    widget = Plugin()

    if hasGUI:
        widget.loadGUI()
        myapp.setCentralWidget(widget.widget)

        myapp.show()
        app.exec_()

    widget.run = False

    sys.exit()
