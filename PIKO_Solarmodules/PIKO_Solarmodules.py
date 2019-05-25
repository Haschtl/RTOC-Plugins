try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

from .PIKO.Piko import Piko
import traceback
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

devicename = "PIKO"

SAMPLERATE = 1

ADRESSES = ['192.168.178.26','192.168.178.27','192.168.178.24','192.168.178.25']
NAMES = ['wh5','wh10','stadel10','stadel4']


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self._pikoservers = []
        for a in ADRESSES:
            self._pikoservers.append(Piko(a))
        self.setPerpetualTimer(self._streamData, samplerate=SAMPLERATE)
        self.start()

    def _streamData(self):
        for idx, s in enumerate(self._pikoservers):
            try:
                data, datanames, dataunits = s.get_data()
                if data != False:
                    self.stream(data, datanames, devicename+'_'+NAMES[idx], dataunits)
            except Exception:
                logging.debug(traceback.format_exc())
                logging.error('Problem with getting data from '+ADRESSES[idx])
