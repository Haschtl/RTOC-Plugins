from __future__ import print_function
try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

from threading import Thread
from PyQt5 import uic
from PyQt5 import QtWidgets
import time
import logging

import platform
import os
import sys
import subprocess
import re
import cpuinfo
import psutil
import datetime
import traceback
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

devicename = "System"

class _toggleTable(QtWidgets.QWidget):
    def __init__(self, name, stream, updateDEF = None, staticDEF=None):
        super(_toggleTable, self).__init__()#
        self.updateDEF = updateDEF
        self.staticDEF = staticDEF
        self.run = None
        self.stream = stream
        self.checkBox = QtWidgets.QCheckBox(name)
        self.name = name
        self.checkBox.stateChanged.connect(self.toggleUpdate)
        self.checkBox.setTristate(True)
        lay = QtWidgets.QVBoxLayout()
        self.setLayout(lay)
        lay.addWidget(self.checkBox)
        self.table = QtWidgets.QTableWidget()
        #self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        lay.addWidget(self.table)
        if self.staticDEF:
            self.__dict2QTable(self.staticDEF())

    def update(self):
        if self.run is not None:
            if self.updateDEF:
                d = self.updateDEF()
                self.__dict2QTable(d)
                if self.run == True:
                    datas = []
                    snames = []
                    for idx, key in enumerate(d.keys()):
                        for idx2, key2 in enumerate(d[key].keys()):
                            try:
                                v = float(d[key][key2])
                                sname = key+"."+key2
                                datas.append(v)
                                snames.append(sname)
                            except Exception:
                                pass

                    if datas != []:
                        self.stream(datas, snames=snames, dname=self.name.replace(' ',''))
                    # plot

    def toggleUpdate(self, checkbox_state):
        if checkbox_state == 0:
            self.run = None
        elif checkbox_state == 1:
            self.run = False
        elif checkbox_state == 2:
            self.run = True

    def __dict2QTable(self, data):
        if data is not None:
            for r, key in enumerate(data.keys()):
                if self.table.rowCount()<=r:
                    self.table.insertRow(r)
                    self.table.setVerticalHeaderItem(r, QtWidgets.QTableWidgetItem(key))
                for c, item in enumerate(data[key].keys()):
                    if self.table.columnCount()<=c:
                        self.table.insertColumn(c)
                        self.table.setHorizontalHeaderItem(c, QtWidgets.QTableWidgetItem(item))
                    newitem = QtWidgets.QTableWidgetItem(str(data[key][item]))
                    self.table.setItem(r, c, newitem)

class Plugin(LoggerPlugin):
    """
Dieses Gerät zeichnet Systemgrößen auf. 
    """
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName(devicename)
        self.smallGUI = None

        self.samplerate = 1           # Function frequency in Hz (1/sec)

        # Data-logger thread
        self._tables = []
        self.run = True  # False -> stops thread
        self.__updater = Thread(target=self.__updateT)    # Actualize data
        self.__updater.start()

    def __updateT(self):
        diff = 0
        self.gen_start = time.time()
        while self.run:  # All should be inside of this while-loop, because self.run == False should stops this plugin
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            for t in self._tables:
                t.update()
            if self.widget.cpuStatCheck.isChecked():
                s = psutil.cpu_stats()
                self.widget.ctxswitches.setText(str(s.ctx_switches))
                self.widget.interrupts.setText(str(s.interrupts))
                self.widget.softinterrupts.setText(str(s.soft_interrupts))
                self.widget.syscalls.setText(str(s.syscalls))
            diff = (time.time() - start_time)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/System/system.ui", self.widget)
        #self.setCallbacks()
        self._tables = []
        self._tables.append(_toggleTable('Disk Partitions', self.stream, getDiskPartitions,None))
        self._tables.append(_toggleTable('Disk IO', self.stream, getDiskIO,None))
        self._tables.append(_toggleTable('Memory', self.stream, getMemory,None))
        self.widget.doubleSpinBox.valueChanged.connect(self.__changeSamplerate)

        self.widget.boottimeLabel.setText(datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"))
        self.widget.cpucount.setText(str(psutil.cpu_count(False))+' ('+str(psutil.cpu_count())+')')
        self.widget.memoryLayout.addWidget(self._tables[0])
        self.widget.memoryLayout.addWidget(self._tables[1])
        self.widget.memoryLayout.addWidget(self._tables[2])

        self._tables.append(_toggleTable('Battery', self.stream, getBatteryInfo, None))
        self._tables.append(_toggleTable('Temperature', self.stream, getTemperature, None))
        self._tables.append(_toggleTable('Fans', self.stream, getFans, None))
        self.widget.sensorsLayout.addWidget(self._tables[3])
        self.widget.sensorsLayout.addWidget(self._tables[4])
        self.widget.sensorsLayout.addWidget(self._tables[5])

        self._tables.append(_toggleTable('Network IO', self.stream, getNetworkIO, None))
        self.widget.networkLayout.addWidget(self._tables[6])
        self._tables.append(_toggleTable('Network Connections', self.stream, getNetworkConnections, None))
        self.widget.networkLayout.addWidget(self._tables[7])
        self._tables.append(_toggleTable('Network Adresses', self.stream, getNetworkInfo, None))
        self.widget.networkLayout.addWidget(self._tables[8])
        self._tables.append(_toggleTable('Network Stats', self.stream, getNetworkStats, None))
        self.widget.networkLayout.addWidget(self._tables[9])

        self._tables.append(_toggleTable('Network IO', self.stream, getUsers, None))
        self.widget.usersLayout.addWidget(self._tables[10])

        self._tables.append(_toggleTable('CPU', self.stream, getCpuTimes, None))
        self.widget.cpuLayout.addWidget(self._tables[11])

        self._tables.append(_toggleTable('CPU', self.stream, getProcessList, None))
        self.widget.processLayout.addWidget(self._tables[12])

        return self.widget

    def __changeSamplerate(self):
        self.samplerate = self.widget.doubleSpinBox.value()

    def __closeEvent(self, *args,**kwargs):
        self.run = False

def getDiskPartitions():
    """
Liest die Festplatten-Partitionierung aus
    """
    d = {}
    for e in psutil.disk_partitions(True):
        d[e.device] = {}
        u = getDiskUsage(e.device)
        total,unit = bytes2str(u.total)
        used,n = bytes2str(u.used)
        free,n = bytes2str(u.free)
        d[e.device]['Total'] = total
        d[e.device]['Used'] = used
        d[e.device]['Free'] = free
        d[e.device]['Unit'] = unit
        d[e.device]['Percent'] = u.percent
        d[e.device]['Mountpoint'] = e.mountpoint
        d[e.device]['Filesystem'] = e.fstype
        d[e.device]['Options'] = e.opts

    return d
    # [sdiskpart(device='/dev/sda3', mountpoint='/', fstype='ext4', opts='rw,errors=remount-ro'),
    # sdiskpart(device='/dev/sda7', mountpoint='/home', fstype='ext4', opts='rw')]

def getDiskIO():
    """
Liest die aktuelle Lese/Schreibe-Rate der Festplatten aus
    """
    d= {}
    io = psutil.disk_io_counters(perdisk=True)
    ioges = psutil.disk_io_counters()
    for e in io.keys():
        d[e]={}
        d[e]['ReadCount'] = io[e].read_count
        d[e]['WriteCount'] = io[e].write_count
        d[e]['ReadBytes'] = io[e].read_bytes
        d[e]['WriteBytes'] = io[e].write_bytes
        d[e]['ReadTime'] = io[e].read_time
        d[e]['WriteTime'] = io[e].write_time
    d["Sum"]= {}
    d["Sum"]['ReadCount'] = ioges.read_count
    d["Sum"]['WriteCount'] = ioges.write_count
    d["Sum"]['ReadBytes'] = ioges.read_bytes
    d["Sum"]['WriteBytes'] = ioges.write_bytes
    d["Sum"]['ReadTime'] = ioges.read_time
    d["Sum"]['WriteTime'] = ioges.write_time
    return d
    # sdiskio(read_count=8141, write_count=2431, read_bytes=290203, write_bytes=537676, read_time=5868, write_time=94922)
    # {'sda1': sdiskio(read_count=920, write_count=1, read_bytes=2933248, write_bytes=512, read_time=6016, write_time=4),
    #  'sda2': sdiskio(read_count=18707, write_count=8830, read_bytes=6060, write_bytes=3443, read_time=24585, write_time=1572),
    #  'sdb1': sdiskio(read_count=161, write_count=0, read_bytes=786432, write_bytes=0, read_time=44, write_time=0)}

def getMemory():
    """
Liest Arbeitsspeicher-Informationen aus
    """
    m = psutil.virtual_memory()
    s = psutil.swap_memory()
    ans = {}
    ans['Physical']={}
    ans['Swap']={}
    total,unit = bytes2str(m.total)
    available,n = bytes2str(m.available)
    used,n = bytes2str(m.used)
    free,unit = bytes2str(m.free)

    ans['Physical']['Total'] = total
    ans['Physical']['Available'] = available
    ans['Physical']['Used'] = used
    ans['Physical']['Free'] = free
    ans['Physical']['Unit'] = unit
    ans['Physical']['Percent'] = m.percent

    total,unit = bytes2str(s.total)
    used,n = bytes2str(s.used)
    free,n = bytes2str(s.free)
    ans['Swap']['Total'] = total
    ans['Swap']['Available'] = "n.A."
    ans['Swap']['Used'] = used
    ans['Swap']['Free'] = free
    ans['Swap']['Unit'] = unit
    ans['Swap']['Percent'] = s.percent
    ans['Swap']['SOut'] = s.sout
    ans['Swap']['SIn'] = s.sin

    return ans

# def get_processor_name():
#     if platform.system() == "Windows":
#         return platform.processor()
#     elif platform.system() == "Darwin":
#         os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
#         command ="sysctl -n machdep.cpu.brand_string"
#         return subprocess.check_output(command).strip()
#     elif platform.system() == "Linux":
#         command = "cat /proc/cpuinfo"
#         all_info = subprocess.check_output(command, shell=True).strip()
#         for line in all_info.split("\n"):
#             if "model name" in line:
#                 return re.sub( ".*model name.*:", "", line,1)
#     return ""

def getBatteryInfo():
    ans = {}
    d = psutil.sensors_battery()
    ans['Percent'] = d.percent
    ans['Left [s]'] = d.secsleft
    ans['Plugged'] = d.power_plugged
    b = {}
    b["Battery"] = ans

    return b
    # sbattery(percent=42, secsleft=3226, power_plugged=False)

def getTemperature():
    """
Gibt die CPU-Temperatur zurück
    """
    d = {}
    try:
        io = psutil.sensors_temperatures() # In Celsius
        for e in io.keys():
            d[e]={}
            d[e]['Label'] = io[e][0].label
            d[e]['Current'] = io[e][0].current
            d[e]['High'] = io[e][0].high
            d[e]['Critical'] = io[e][0].critical
    except Exception:
        d['only']={}
        d['only']['Fail']='Linux'

    return d
    # {'ACPI\\ThermalZone\\THM0_0': [shwtemp(label='', current=49.05000000000001, high=127.05000000000001, critical=127.05000000000001)]}

def getFans():
    """
Gibt den Zustand von Lüftern zurück
    """
    d = {}
    try:
        io = psutil.sensors_fans() # In Celsius
        for e in io.keys():
            d[e]={}
            d[e]['Label'] = io[e][0].label
            d[e]['Current'] = io[e][0].current
    except Exception:
        d['only']={}
        d['only']['Fail']='Linux'
    return d
    # {'asus': [sfan(label='cpu_fan', current=3200)]}

def getNetworkInfo():
    """
Gibt Netzwerkinformationen zurück.
    """
    ans = {}
    d = psutil.net_if_addrs()
    for n in d.keys():
        for addr in d[n]:
            m = n+':'+str(addr.family).replace('AddressFamily.','')
            ans[m]={}
            ans[m]['Address'] = addr.address
            ans[m]['Netmask'] = addr.netmask
            ans[m]['Broadcast'] = addr.broadcast
            ans[m]['PTP'] = addr.ptp

def getNetworkStats():
    """
Gibt den aktuellen Netzwerkzustand zurück.
    """
    ans = {}
    d = psutil.net_if_stats()
    for m in d.keys():
        addr = d[m]
        ans[m]={}
        ans[m]['ISUP'] = addr.isup
        ans[m]['Duplex'] = addr.duplex
        ans[m]['Speed'] = addr.speed
        ans[m]['MTU'] = addr.mtu
    return ans

def getNetworkConnections():
    """
Gibt verbundene Geräte zurück.
    """
    ans = {}
    d = psutil.net_connections()
    for n, addr in enumerate(d):
        m=str(n)
        ans[m]={}
        ans[m]['FD'] = addr.fd
        ans[m]['Family'] = addr.family
        ans[m]['Type'] = addr.type
        if addr.laddr != ():
            ans[m]['Local address'] = addr.laddr.ip
            ans[m]['Local port'] = addr.laddr.port
        else:
            ans[m]['Local address'] = None
            ans[m]['Local port'] = None

        if addr.raddr != ():
            ans[m]['Remote address'] = addr.raddr.ip
            ans[m]['Remote port'] = addr.raddr.port
        else:
            ans[m]['Remote address'] = None
            ans[m]['Remote port'] = None

        ans[m]['Status'] = addr.status
        ans[m]['PID'] = addr.pid
    return ans

lastCall = time.time()
lastSent = 0
lastRecv = 0

def getNetworkIO():
    """
Gibt den aktuellen Netzwerk-IO zurück.
    """
    global lastSent
    global lastRecv
    global lastCall

    ans = {}
    d = psutil.net_io_counters(True,True)
    for m in d.keys():
        addr = d[m]
        ans[m]={}
        newtime = time.time()
        if lastCall == newtime:
            lastCall = newtime-1000
        ans[m]['Upstream [kB/s]'] = (addr.bytes_sent-lastSent)/(1000 * (newtime-lastCall))
        ans[m]['Downstream [kB/s]'] = (addr.bytes_recv-lastRecv)/(1000 * (newtime-lastCall))
        lastSent = addr.bytes_sent
        lastRecv =addr.bytes_recv
        lastCall = newtime
        ans[m]['Bytes sent'] = addr.bytes_sent
        ans[m]['Bytes recv'] = addr.bytes_recv
        ans[m]['Packets sent'] = addr.packets_sent
        ans[m]['Packets recv'] = addr.packets_recv
        ans[m]['Error In'] = addr.errin
        ans[m]['Error Out'] = addr.errout
        ans[m]['Drop In'] = addr.dropin
        ans[m]['Drop Out'] = addr.dropout
    return ans

def getUsers():
    """
Gibt Nutzer Informationen zurück.
    """
    ans = {}
    d = psutil.users()
    for n, addr in enumerate(d):
        m=addr.name
        ans[m]={}
        ans[m]['Terminal'] = addr.terminal
        ans[m]['Host'] = addr.host
        ans[m]['Started'] = datetime.datetime.fromtimestamp(addr.started).strftime("%Y-%m-%d %H:%M:%S")
        ans[m]['PID'] = addr.pid
    return ans

def getCpuTimes():
    """
Gibt CPU-Informationen zurück.
    """
    ans = {}
    d = psutil.cpu_times(True)
    e = psutil.cpu_percent(None, True)
    f = psutil.cpu_freq(True)
    for n, addr in enumerate(d):
        m = "CPU"+str(n)
        ans[m]={}
        ans[m]['Percent'] = e[n]
        ans[m]['User'] = addr.user
        ans[m]['System'] = addr.system
        ans[m]['Idle'] = addr.idle
        try:
            ans[m]['Nice'] = addr.nice
            ans[m]['IOWait'] = addr.iowait
            ans[m]['IRQ'] = addr.irq
            ans[m]['SoftIRQ'] = addr.softirq
            ans[m]['Steal'] = addr.steal
            ans[m]['Guest'] = addr.guest
            ans[m]['GuestNice'] = addr.guest_nice
        except Exception:
            pass
        try:
            ans[m]['Current Freq'] = f[n].current
            ans[m]['Min Freq'] = f[n].min
            ans[m]['Max Freq'] = f[n].max
        except Exception:
            pass
        try:
            ans[m]['Interrupt'] = f[n].interrupt
            ans[m]['DPC'] = f[n].dpc
        except Exception:
            pass
    d = psutil.cpu_times(False)
    e = psutil.cpu_percent(None, False)
    f = psutil.cpu_freq(False)
    m = 'Sum'
    ans[m]={}
    ans[m]['Percent'] = e
    ans[m]['User'] = d.user
    ans[m]['System'] = d.system
    ans[m]['Idle'] = d.idle
    try:
        ans[m]['Nice'] = d.nice
        ans[m]['IOWait'] = d.iowait
        ans[m]['IRQ'] = d.irq
        ans[m]['SoftIRQ'] = d.softirq
        ans[m]['Steal'] = d.steal
        ans[m]['Guest'] = d.guest
        ans[m]['GuestNice'] = d.guest_nice
    except Exception:
        pass
    ans[m]['Current Freq'] = f.current
    ans[m]['Min Freq'] = f.min
    ans[m]['Max Freq'] = f.max
    try:
        ans[m]['Interrupt'] = f[m].interrupt
        ans[m]['DPC'] = f[m].dpc
    except Exception:
        pass
    return ans

def getCpuInfo():
    """
Gibt CPU-Informationen zurück
    """
    a = cpuinfo.get_cpu_info()
    a.pop("flags",None)
    return a
    # {'python_version': '3.6.3.final.0 (64 bit)', 'cpuinfo_version': (4, 0, 0), 'arch': 'X86_64', 'bits': 64, 'count': 4, 'raw_arch_string': 'AMD64', 'vendor_id': 'GenuineIntel', 'brand': 'Intel(R) Core(TM) i5-7200U CPU @ 2.50GHz', 'hz_advertised': '2.5000 GHz', 'hz_actual': '2.7010 GHz', 'hz_advertised_raw': (2500000000, 0), 'hz_actual_raw': (2701000000, 0), 'l2_cache_size': '512 KB', 'stepping': 9, 'model': 142, 'family': 6, 'l3_cache_size': '3072 KB', 'l2_cache_line_size': 6, 'l2_cache_associativity': '0x100', 'extended_model': 8}


def getProcessList():
    """
Gibt eine Liste mit allen Prozessen zurück
    """
    ans = {}
    att = ['cmdline', 'connections', 'cpu_affinity', 'cpu_percent', 'create_time', 'cwd', 'environ', 'exe', 'memory_percent', 'name', 'nice', 'num_ctx_switches', 'num_handles', 'num_threads', 'open_files', 'pid', 'ppid', 'status', 'threads', 'username']
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=att)
        except psutil.NoSuchProcess:
            pass
        else:
            ans[pinfo['name']] = pinfo
            ans[pinfo['name']].pop('name')
    return ans

def getProcess(id:int): # example: 9393
    """
Gibt einen Process zurück 
    """
    p = psutil.Process(9800)
    # Then, we can access all the information and statistics of the process:
    path = p.exe() # 'C:\\Windows\\System32\\dllhost.exe'
    perc = p.cpu_percent() # 0.0
    cwd = p.cwd() # 'C:\\WINDOWS\\system32'

    return path, cwd, perc




def bytes2str(bytes):
    if bytes>1000000000:
        return bytes/1000000000,"GB"
    elif bytes>1000000:
        return bytes/1000000,"MB"
    elif bytes>1000:
        return bytes/1000,"KB"

def setStyleSheet(app, myapp):
    try:
        import qtmodern.styles
        import qtmodern.windows
        qtmodern.styles.dark(app)
        #mw = qtmodern.windows.ModernWindow(myapp)
        mw = myapp
        return app, mw
    except Exception:
        tb = traceback.format_exc()
        logging.debug(tb)
        logging.warning("New Style not installed")
        with open("/data/ui/darkmode.html", 'r') as myfile:
            stylesheet = myfile.read().replace('\n', '')
        app.setStyleSheet(stylesheet)
        return app, myapp

def getMemoryUsage():
    return psutil.virtual_memory() #  physical memory usage
    # svmem(total=17039765504, available=10798948352, percent=36.6, used=6240817152, free=10798948352)

def getSwap():
    return psutil.swap_memory()
    # sswap(total=2097147904L, used=886620160L, free=1210527744L, percent=42.3, sin=1050411008, sout=1906720768)

def getDiskUsage(disk):
    return psutil.disk_usage(disk)
    # sdiskusage(total=127950385152L, used=116934914048L, free=11015471104L, percent=91.4)


if __name__ == '__main__':
    os.chdir('..')
    app = QtWidgets.QApplication(sys.argv)
    myapp = QtWidgets.QMainWindow()
    widget = Plugin()
    widget.loadGUI()
    myapp.setCentralWidget(widget.widget)

    app, myapp = setStyleSheet(app, myapp)

    myapp.show()
    app.exec_()
    widget.run = False
    sys.exit()
