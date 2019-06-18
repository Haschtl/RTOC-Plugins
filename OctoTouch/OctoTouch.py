from RTOC.LoggerPlugin import LoggerPlugin

from PyQt5 import uic
from PyQt5 import QtWidgets

from .Octotouch.OctoprintApi import OctoprintAPI

devicename = "Octotouch"
apikey = ""
SAMPLERATE = 1


class Plugin(LoggerPlugin):
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self._dataY = [0, 0, 0, 0, 0, 0]
        self._datanames = ["Hotend0", "Hotend0Des", "Hotend1", "Hotend1Des", "Heatbed", "HeatbedDes"]
        self._dataunits = ["°C", "°C", "°C", "°C", "°C", "°C"]

        # Data-logger thread
        self.setPerpetualTimer(self._updateT, samplerate=SAMPLERATE)

    # THIS IS YOUR THREAD
    def _updateT(self):
        valid, values = self.__get_data()
        if valid:
            self._dataY = values
            self.widget.spinBox0.setValue(values[1])
            self.widget.spinBox1.setValue(values[3])
            self.widget.spinBoxB.setValue(values[5])
            self.stream(y=self._dataY,  snames=self._datanames, unit=self._dataunits)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Octotouch/octotouch.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openConnectionCallback)
        self.widget.spinBox0.valueChanged.connect(self.__setTempDes0)
        self.widget.spinBox1.valueChanged.connect(self.__setTempDes1)
        self.widget.spinBoxB.valueChanged.connect(self.__setTempDesB)
        self.widget.samplerateSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.comboBox.setCurrentText("kellerdrucker")
        self.__openConnectionCallback()
        return self.widget

    def __openConnection(self):
        self.__api = OctoprintAPI(self.widget.comboBox.currentText(), apikey)
        ok, test = self.__api.getStatus()
        return ok

    def __openConnectionCallback(self):
        if self.run:
            self.cancel()
            self.widget.pushButton.setText("Verbinden")
        else:
            if self.__openConnection():
                self.start()
                self.widget.pushButton.setText("Beenden")
            else:
                self.cancel()
                self.widget.pushButton.setText("Fehler")

    def __get_data(self):
        ok, data = self.__api.getStatus()
        hotend0 = float(data["temperature"]["tool0"]["actual"])
        hotend1 = float(data["temperature"]["tool1"]["actual"])
        bed = float(data["temperature"]["bed"]["actual"])

        hotend0des = float(data["temperature"]["tool0"]["target"])
        hotend1des = float(data["temperature"]["tool1"]["target"])
        bedDes = float(data["temperature"]["bed"]["target"])

        return ok, [hotend0, hotend0des, hotend1, hotend1des, bed, bedDes]

    def __changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()

    def __setTempDes0(self):
        if self._dataY[1] != self.widget.spinBox0.value():
            self.__api.setNozzleTemp(self.widget.spinBox0.value(), 0)

    def __setTempDes1(self):
        if self._dataY[3] != self.widget.spinBox1.value():
            self.__api.setNozzleTemp(self.widget.spinBox1.value(), 1)

    def __setTempDesB(self):
        if self._dataY[5] != self.widget.spinBoxB.value():
            self.__api.setBedTemp(self.widget.spinBoxB.value())


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
