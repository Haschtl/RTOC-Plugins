try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

from .PIKO.Piko import Piko
import time
from threading import Thread
import time
import traceback

devicename = "PIKO"

samplerate = 1

ADRESSES = ['wh5','wh10','stadel10','stadel4']

class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.run = True
        self.samplerate = samplerate            # frequency in Hz (1/sec)
        self.status = False

        self.pikoservers = []
        for a in ADRESSES:
            self.pikoservers.append(Piko(a))
        self.__updater = Thread(target=self.__updateT)    # Actualize data
        self.__updater.start()

    def __updateT(self):
        diff = 0
        self.gen_start = time.time()
        while self.run:  # All should be inside of this while-loop, because self.run == False should stops this plugin
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            self.streamData()
            diff = (time.time() - start_time)

    def streamData(self):
        for idx, s in enumerate(self.pikoservers):
            try:
                data, datanames, dataunits = s.get_data()
                if data != False:
                    self.stream(data, datanames, devicename+'_'+ADRESSES[idx], dataunits)
            except:
                print(traceback.format_exc())
                print('Problem with getting data from '+ADRESSES[idx])
