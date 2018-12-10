# RTOC - PlugIns

This repository contains some plugins for RealTime OpenControl (RTOC).

You can download RTOC from its [repository](https://github.com/Haschtl/RealTimeOpenControl).

## How to use plugins

To add a plugin to RTOC you need to do the following steps:

1. Install RTOC (`pip3 install RTOC`)
   - You will need to run RTOC once
2. Copy the files of the plugin to your RTOC-Userpath: `~/Documents/RTOC/devices/`
3. Now restart RTOC (`python3 -m RTOC`)



If you want a plugin to start with RTOC, you can add it to the `autorun_devices` file.

```
echo 'YOUR_DEVICENAME' >> ~/Documents/RTOC/autorun_devices
```



## List of plugins

- DPS5020: Plugin for DPS powersupplies. It can monitor all data and you can set Voltage, Current and switch it on/off. Uses USB to read data.
- Funktionsgenerator: Default-plugin of RTOC. Generates common signals.
- holdPeak_VC820: Plugin for VC820 multimeters. It can monitor the measured values with correct units. Uses USB/Minimalmodbus to read data.
- INA219_Modul: Plugin for INA219 solar module. Monitors voltage, current, power and shunt_voltage
- Octotouch: Plugin for 3D-printer-software Octotouch. It can just monitor the temperatures. Uses HTTP/JSON to read data.
- System: Plugin to monitor system-information like CPU, Memory, ...
- ReflowOfen/ReflowPlatte: Plugin, which reads data from local network-devices HTTP-address.
- Heliotherm: Plugin, which reads data from Heliotherm heat pump using TCP/Modbus.
- Futtertrocknung: Embedded-Plugin. Plugin, which is used to run on a RaspberryPi. Monitors some sensor-data.



## Plugin descriptions

### DPS5020

**GUI**: Yes

**Files**: DPS5020.py, DPS5020/*

**Dependencies**: `pip3 install minimalmodbus`

**Target system**: Each OS (connected to DPS with USB)

**Info**:

- You can set a parameters in file DPS5020.py:
  - default_device = '/dev/ttyUSB0'
  - SERIAL_BAUDRATE = 9600
  - SERIAL_BYTESIZE = 8
  - SERIAL_TIMEOUT = 2
- You will need to run RTOC as root unless you set devices rules. See [this tutorial](http://ask.xmodulo.com/change-usb-device-permission-linux.html) for how to set device rules.

### Funktionsgenerator

**GUI**: Yes

**Files**: Generator2.py, Funktionsgenerator/*

**Dependencies**: -

**Target system**: Each OS

**Info**:



### holdPeak_VC820

**GUI**: Yes

**Files**: HoldPeak\ VC820.py, holdPeak_VC820/*

**Dependencies**: `pip3 install serial`

**Target system**: Each OS (connected to VC820 with USB)

**Info**:

- You can set a parameters in file HoldPeak\ VC820.py:
  - default_device = 'COM7'
  - SERIAL_BAUDRATE = 2400
  - SERIAL_BYTESIZE = 8
  - SERIAL_TIMEOUT = 1
- You will need to run RTOC as root unless you set devices rules. See [this tutorial](http://ask.xmodulo.com/change-usb-device-permission-linux.html) for how to set device rules.



### INA219_Modul

**GUI**: No

**Files**: INA219_Modul.py

**Dependencies**: `pip3 install ina219`

**Target system**: RaspberryPi (connected to INA219 via I2C)

**Info**:

- You can set a parameters in file INA219_Modul.py:

  - SHUNT_OHMS = 0.1
  - MAX_EXPECTED_AMPS = 0.2

  - SAMPLERATE = 1/60# frequency in Hz (1/sec)
  - I2C_ADDRESS = 0x41



### Octotouch

**GUI**: Yes

**Files**: OctoTouch.py, Octotouch/*

**Dependencies**: -

**Target system**: Each OS (In same network as Octotouch-server)

**Info**:

You can set a parameters in file OctoTouch.py:

- devicename = "Octotouch"
- apikey = ""
- SAMPLERATE = 1



### System

**GUI**: Yes

**Files**: System.py, System/*

**Dependencies**: -

**Target system**: Each OS

**Info**:



### ReflowOfen/ReflowPlatte

**GUI**: Yes

**Files**: ReflowOfen.py, ReflowPlatte.py, Reflow/*

**Dependencies**: -

**Target system**: Each OS (In same network as Reflow-*)

**Info**:



### Heliotherm

**GUI**: Yes

**Files**: Heliotherm.py, Heliotherm/*

**Dependencies**: `pip3 install ModbusClient`

**Target system**: Each OS (In same network as Heliotherm heat pump)

**Info**:



### Futtertrocknung

**GUI**: No

**Files**: Futtertrocknung.py

**Dependencies**: `pip3 install adafruit_CCS811 adafruit_DHT board busio`

**Target system**: RaspberryPi

**Info**:
