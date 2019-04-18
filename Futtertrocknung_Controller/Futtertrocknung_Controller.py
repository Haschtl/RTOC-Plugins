try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import serial
from re import split
import time
import os
import sys
from threading import Thread
import traceback
# userpath = os.path.expanduser('~/heutrocknung/Lüftersteuerung/API')
# if not os.path.exists(userpath):
#     print('WRONG DIR TO IMPORT Controller API')
#     sys.exit(1)
# else:
#     try:
#         sys.path.insert(0, userpath)
#         from controller_api import controller
#     except ImportError:
#         print('Could not import Controller API from '+userpath)
#         sys.exit(1)

devicename = "Controller"
UART_TIMEOUT = 0.5

CONTROL_ENABLED	=	1
CONTROL_MANUAL_SELECTION	=	2
CONTROL_INPUT	=	3
SET_CONTROL_WITH_POTENTIOMETER	=	4
REMOTE_PANEL	=	5
CONTROLLER_NOT_SETTLED	=	6
CONTROLLER_TIMED_OUT	=	7
SET_VALUE_OUT_OF_RANGE	=	8
OVERTEMPERATURE	=	9
BMP_SENSOR_FAULT	=	10
HVAC_SENSOR_FAULT	=	11
FRONTPANEL_SELECTION_FAULT	=	12
RPM	=	13
AIR_PRESSURE	=	14
TEMPERATURE1	=	15
FLOW_RATE	=	16
TEMPERATURE2	=	17
POTENTIOMETER	=	18
RPM_SET	=	19
AIR_PRESSURE_SET	=	20
FLOW_RATE_SET	=	21
RPM_OFFSET	=	22
RPM_FACTOR	=	23
AIR_PRESSURE_OFFSET	=	24
AIR_PRESSURE_FACTOR	=	25
TEMPERATURE1_OFFSET	=	26
TEMPERATURE1_FACTOR	=	27
FLOW_RATE_OFFSET	=	28
FLOW_RATE_FACTOR	=	29
TEMPERATURE2_OFFSET	=	30
TEMPERATURE2_FACTOR	=	31
POTENTIOMETER_OFFSET	=	32
POTENTIOMETER_FACTOR	=	33
POTI_AIR_PRESSURE_SET_MIN	=	34
POTI_AIR_PRESSURE_SET_MAX	=	35
POTI_FLOW_RATE_SET_MIN	=	36
POTI_FLOW_RATE_SET_MAX	=	37
P_GAIN_AIR_PRESSURE_CONTROL	=	38
I_GAIN_AIR_PRESSURE_CONTROL	=	39
D_GAIN_AIR_PRESSURE_CONTROL	=	40
A_GAIN_AIR_PRESSURE_CONTROL	=	41
AIR_PRESSURE_CONTROL_SETTLE_TOLERANCE	=	42
P_GAIN_FLOW_RATE_CONTROL	=	43
I_GAIN_FLOW_RATE_CONTROL	=	44
D_GAIN_FLOW_RATE_CONTROL	=	45
A_GAIN_FLOW_RATE_CONTROL	=	46
FLOW_RATE_CONTROL_SETTLE_TOLERANCE	=	47
CONTROL_SETTLE_TIME	=	48
CONTROL_TIMEOUT	=	49
REMOTE_PANEL_TIMEOUT	=	50
POTENTIOMETER_NOISE	=	51
MAIN_LOOP_PERIOD	=	52
MAX_TEMPERATURE	=	53
CPU_LOAD	=	54
MILLIS	=	55
SECONDS	=	56



class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None):
        #super(Plugin, self).__init__(stream, plot, event)
        LoggerPlugin.__init__(self, stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = 1

        self._control_enabled = 0
        self._control_manual_selection = 0
        self._control_input = 0
        self._set_control_with_potentiometer = 0
        self._remote_panel = 0
        self._controller_not_settled = 0
        self._controller_timed_out = 0
        self._set_value_out_of_range = 0
        self._overtemperature = 0
        self._bmp_sensor_fault = 0
        self._hvac_sensor_fault = 0
        self._frontpanel_selection_fault = 0
        self._rpm = 0
        self._air_pressure = 0
        self._temperature1 = 0
        self._flow_rate = 0
        self._temperature2 = 0
        self._potentiometer = 0
        self._rpm_set = 0
        self._air_pressure_set = 0
        self._flow_rate_set = 0
        self._rpm_offset = 0
        self._rpm_factor = 0
        self._air_pressure_offset = 0
        self._air_pressure_factor = 0
        self._temperature1_offset = 0
        self._temperature1_factor = 0
        self._flow_rate_offset = 0
        self._flow_rate_factor = 0
        self._temperature2_offset = 0
        self._temperature2_factor = 0
        self._potentiometer_offset = 0
        self._potentiometer_factor = 0
        self._poti_air_pressure_set_min = 0
        self._poti_air_pressure_set_max = 0
        self._poti_flow_rate_set_min = 0
        self._poti_flow_rate_set_max = 0
        self._p_gain_air_pressure_control = 0
        self._i_gain_air_pressure_control = 0
        self._d_gain_air_pressure_control = 0
        self._a_gain_air_pressure_control = 0
        self._air_pressure_control_settle_tolerance = 0
        self._p_gain_flow_rate_control = 0
        self._i_gain_flow_rate_control = 0
        self._d_gain_flow_rate_control = 0
        self._a_gain_flow_rate_control = 0
        self._flow_rate_control_settle_tolerance = 0
        self._control_settle_time = 0
        self._control_timeout = 0
        self._remote_panel_timeout = 0
        self._potentiometer_noise = 0
        self._main_loop_period = 0
        self._max_temperature = 0
        self._cpu_load = 0
        self._millis = 0
        self._seconds = 0

        self.ser = serial.Serial(
            port='/dev/serial0',
            baudrate=19200,
            #  parity=serial.PARITY_NONE,
            #  stopbits=serial.STOPBITS_ONE,
            #  bytesize=serial.EIGHTBITS,
            timeout=1
        )

        self._thread = Thread(target=self._getControllerData)
        self._thread.start()
        print('FUTTERTROCKNUNG CONTROLLER GESTARTET')

    def _getControllerData(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()

            # Stream all measurements
            rpm = self.rpm
            pressure = self.air_pressure
            temp1 = self.temperature1
            temp2 = self.temperature2
            flow = self.flow_rate
            sensor_data = {
                'E': {'Drehzahl': [rpm, 'U/min'], 'Luftdruck': [pressure, 'bar'], 'Temperatur1': [temp1, '°C'], 'Temperatur2': [temp2, '°C'], 'Durchfluss': [flow, 'm³/s']}
            }
            #print(sensor_data)
            self.stream(list=sensor_data)
            diff = (time.time() - start_time)

        # def setActive(self, active=True):
        #     pass
        #
        # def setMode(self, mode=0):  # manuell, druck, durchfluss
        #     pass
        #
        # def setPID(self, mode, p, i, d):
        #     pass
        #
        # def setDesired(self, mode, value):
        #     pass

    def save_profile(self):
        self.ser.reset_input_buffer()
        cmd = "E:1;\n"
        self.ser.write(cmd.encode())

    def load_profile(self):
        self.ser.reset_input_buffer()
        cmd = "E:2;\n"
        self.ser.write(cmd.encode())

    def read_controller(self, id):
        self.ser.reset_input_buffer()
        cmd = "R:"+str(id)+";\n"
        self.ser.write(cmd.encode())
        received = ""

        start = time.time()
        while len(received) <= 0 and time.time()-start < UART_TIMEOUT:
            try:
                received = self.ser.readline().decode("utf-8")
            except:
                print(traceback.format_exc())
                print("\tCONTROLLER: UART-read-error")
            time.sleep(0.01)
        try:
            return float(split(':', received)[2].replace(' ', '').replace(';', '').replace('\n', ''))
        except:
            print(received)
            return 0

    def write_controller(self, id, value):
        self.ser.reset_input_buffer()
        cmd = "W:"+str(id)+":"+str(value)+";\n"
        self.ser.write(cmd.encode())

    @property
    def control_enabled(self):
        self._control_enabled = self.read_controller(CONTROL_ENABLED)
        return self._control_enabled

    @control_enabled.setter
    def control_enabled(self, value):
        self.write_controller(CONTROL_ENABLED, value)

    @property
    def control_manual_selection(self):
        self._control_manual_selection = self.read_controller(CONTROL_MANUAL_SELECTION)
        return self._control_manual_selection

    @control_manual_selection.setter
    def control_manual_selection(self, value):
        self.write_controller(CONTROL_MANUAL_SELECTION, value)

    @property
    def control_input(self):
        self._control_input = self.read_controller(CONTROL_INPUT)
        return self._control_input

    @control_input.setter
    def control_enabled(self, value):
        self.write_controller(CONTROL_INPUT, value)

    @property
    def set_control_with_potentiometer(self):
        self._set_control_with_potentiometer = self.read_controller(SET_CONTROL_WITH_POTENTIOMETER)
        return self._set_control_with_potentiometer

    @set_control_with_potentiometer.setter
    def set_control_with_potentiometer(self, value):
        self.write_controller(SET_CONTROL_WITH_POTENTIOMETER, value)

    @property
    def remote_panel(self):
        self._remote_panel = self.read_controller(REMOTE_PANEL)
        return self._remote_panel

    @remote_panel.setter
    def remote_panel(self, value):
        self.write_controller(REMOTE_PANEL, value)

    @property
    def controller_not_settled(self):
        self._controller_not_settled = self.read_controller(CONTROLLER_NOT_SETTLED)
        return self._controller_not_settled

    @controller_not_settled.setter
    def controller_not_settled(self, value):
        self.write_controller(CONTROLLER_NOT_SETTLED, value)

    @property
    def controller_timed_out(self):
        self._controller_timed_out = self.read_controller(CONTROLLER_TIMED_OUT)
        return self._controller_timed_out

    @controller_timed_out.setter
    def controller_timed_out(self, value):
        self.write_controller(CONTROLLER_TIMED_OUT, value)

    @property
    def set_value_out_of_range(self):
        self._set_value_out_of_range = self.read_controller(SET_VALUE_OUT_OF_RANGE)
        return self._set_value_out_of_range

    @set_value_out_of_range.setter
    def set_value_out_of_range(self, value):
        self.write_controller(SET_VALUE_OUT_OF_RANGE, value)

    @property
    def overtemperature(self):
        self._overtemperature = self.read_controller(OVERTEMPERATURE)
        return self._overtemperature

    @overtemperature.setter
    def overtemperature(self, value):
        self.write_controller(OVERTEMPERATURE, value)

    @property
    def bmp_sensor_fault(self):
        self._bmp_sensor_fault = self.read_controller(BMP_SENSOR_FAULT)
        return self._bmp_sensor_fault

    @bmp_sensor_fault.setter
    def bmp_sensor_fault(self, value):
        self.write_controller(BMP_SENSOR_FAULT, value)

    @property
    def hvac_sensor_fault(self):
        self._hvac_sensor_fault = self.read_controller(HVAC_SENSOR_FAULT)
        return self._hvac_sensor_fault

    @hvac_sensor_fault.setter
    def hvac_sensor_fault(self, value):
        self.write_controller(HVAC_SENSOR_FAULT, value)

    @property
    def frontpanel_selection_fault(self):
        self._frontpanel_selection_fault = self.read_controller(FRONTPANEL_SELECTION_FAULT)
        return self._frontpanel_selection_fault

    @frontpanel_selection_fault.setter
    def frontpanel_selection_fault(self, value):
        self.write_controller(FRONTPANEL_SELECTION_FAULT, value)

    @property
    def rpm(self):
        self._rpm = self.read_controller(RPM)
        return self._rpm

    @rpm.setter
    def rpm(self, value):
        self.write_controller(RPM, value)

    @property
    def air_pressure(self):
        self._air_pressure = self.read_controller(AIR_PRESSURE)
        return self._air_pressure

    @air_pressure.setter
    def air_pressure(self, value):
        self.write_controller(AIR_PRESSURE, value)

    @property
    def temperature1(self):
        self._temperature1 = self.read_controller(TEMPERATURE1)
        return self._temperature1

    @temperature1.setter
    def temperature1(self, value):
        self.write_controller(TEMPERATURE1, value)

    @property
    def flow_rate(self):
        self._flow_rate = self.read_controller(FLOW_RATE)
        return self._flow_rate

    @flow_rate.setter
    def flow_rate(self, value):
        self.write_controller(FLOW_RATE, value)

    @property
    def temperature2(self):
        self._temperature2 = self.read_controller(TEMPERATURE2)
        return self._temperature2

    @temperature2.setter
    def temperature2(self, value):
        self.write_controller(TEMPERATURE2, value)

    @property
    def potentiometer(self):
        self._potentiometer = self.read_controller(POTENTIOMETER)
        return self._potentiometer

    @potentiometer.setter
    def potentiometer(self, value):
        self.write_controller(POTENTIOMETER, value)

    @property
    def rpm_set(self):
        self._rpm_set = self.read_controller(RPM_SET)
        return self._rpm_set

    @rpm_set.setter
    def rpm_set(self, value):
        self.write_controller(RPM_SET, value)

    @property
    def air_pressure_set(self):
        self._air_pressure_set = self.read_controller(AIR_PRESSURE_SET)
        return self._air_pressure_set

    @air_pressure_set.setter
    def air_pressure_set(self, value):
        self.write_controller(AIR_PRESSURE_SET, value)

    @property
    def flow_rate_set(self):
        self._flow_rate_set = self.read_controller(FLOW_RATE_SET)
        return self._flow_rate_set

    @flow_rate_set.setter
    def flow_rate_set(self, value):
        self.write_controller(FLOW_RATE_SET, value)

    @property
    def rpm_offset(self):
        self._rpm_offset = self.read_controller(RPM_OFFSET)
        return self._rpm_offset

    @rpm_offset.setter
    def rpm_offset(self, value):
        self.write_controller(RPM_OFFSET, value)

    @property
    def rpm_factor(self):
        self._rpm_factor = self.read_controller(RPM_FACTOR)
        return self._rpm_factor

    @rpm_factor.setter
    def rpm_factor(self, value):
        self.write_controller(RPM_FACTOR, value)

    @property
    def air_pressure_offset(self):
        self._air_pressure_offset = self.read_controller(AIR_PRESSURE_OFFSET)
        return self._air_pressure_offset

    @air_pressure_offset.setter
    def air_pressure_offset(self, value):
        self.write_controller(AIR_PRESSURE_OFFSET, value)

    @property
    def air_pressure_factor(self):
        self._air_pressure_factor = self.read_controller(AIR_PRESSURE_FACTOR)
        return self._air_pressure_factor

    @air_pressure_factor.setter
    def air_pressure_factor(self, value):
        self.write_controller(AIR_PRESSURE_FACTOR, value)

    @property
    def temperature1_offset(self):
        self._temperature1_offset = self.read_controller(TEMPERATURE1_OFFSET)
        return self._temperature1_offset

    @temperature1_offset.setter
    def temperature1_offset(self, value):
        self.write_controller(TEMPERATURE1_OFFSET, value)

    @property
    def temperature1_factor(self):
        self._temperature1_factor = self.read_controller(TEMPERATURE1_FACTOR)
        return self._temperature1_factor

    @temperature1_factor.setter
    def temperature1_factor(self, value):
        self.write_controller(TEMPERATURE1_FACTOR, value)

    @property
    def flow_rate_offset(self):
        self._flow_rate_offset = self.read_controller(FLOW_RATE_OFFSET)
        return self._flow_rate_offset

    @flow_rate_offset.setter
    def flow_rate_offset(self, value):
        self.write_controller(FLOW_RATE_OFFSET, value)

    @property
    def flow_rate_factor(self):
        self._flow_rate_factor = self.read_controller(FLOW_RATE_FACTOR)
        return self._flow_rate_factor

    @flow_rate_factor.setter
    def flow_rate_factor(self, value):
        self.write_controller(FLOW_RATE_FACTOR, value)

    @property
    def temperature2_offset(self):
        self._temperature2_offset = self.read_controller(TEMPERATURE2_OFFSET)
        return self._temperature2_offset

    @temperature2_offset.setter
    def temperature2_offset(self, value):
        self.write_controller(TEMPERATURE2_OFFSET, value)

    @property
    def temperature2_factor(self):
        self._temperature2_factor = self.read_controller(TEMPERATURE2_FACTOR)
        return self._temperature2_factor

    @temperature2_factor.setter
    def temperature2_factor(self, value):
        self.write_controller(TEMPERATURE2_FACTOR, value)

    @property
    def potentiometer_offset(self):
        self._potentiometer_offset = self.read_controller(POTENTIOMETER_OFFSET)
        return self._potentiometer_offset

    @potentiometer_offset.setter
    def potentiometer_offset(self, value):
        self.write_controller(POTENTIOMETER_OFFSET, value)

    @property
    def potentiometer_factor(self):
        self._potentiometer_factor = self.read_controller(POTENTIOMETER_FACTOR)
        return self._potentiometer_factor

    @potentiometer_factor.setter
    def potentiometer_factor(self, value):
        self.write_controller(POTENTIOMETER_FACTOR, value)

    @property
    def poti_air_pressure_set_min(self):
        self._poti_air_pressure_set_min = self.read_controller(POTI_AIR_PRESSURE_SET_MIN)
        return self._poti_air_pressure_set_min

    @poti_air_pressure_set_min.setter
    def poti_air_pressure_set_min(self, value):
        self.write_controller(POTI_AIR_PRESSURE_SET_MIN, value)

    @property
    def poti_air_pressure_set_max(self):
        self._poti_air_pressure_set_max = self.read_controller(POTI_AIR_PRESSURE_SET_MAX)
        return self._poti_air_pressure_set_max

    @poti_air_pressure_set_max.setter
    def poti_air_pressure_set_max(self, value):
        self.write_controller(POTI_AIR_PRESSURE_SET_MAX, value)

    @property
    def poti_flow_rate_set_min(self):
        self._poti_flow_rate_set_min = self.read_controller(POTI_FLOW_RATE_SET_MIN)
        return self._poti_flow_rate_set_min

    @poti_flow_rate_set_min.setter
    def poti_flow_rate_set_min(self, value):
        self.write_controller(POTI_FLOW_RATE_SET_MIN, value)

    @property
    def poti_flow_rate_set_max(self):
        self._poti_flow_rate_set_max = self.read_controller(POTI_FLOW_RATE_SET_MAX)
        return self._poti_flow_rate_set_max

    @poti_flow_rate_set_max.setter
    def poti_flow_rate_set_max(self, value):
        self.write_controller(POTI_FLOW_RATE_SET_MAX, value)

    @property
    def p_gain_air_pressure_control(self):
        self._p_gain_air_pressure_control = self.read_controller(P_GAIN_AIR_PRESSURE_CONTROL)
        return self._p_gain_air_pressure_control

    @p_gain_air_pressure_control.setter
    def p_gain_air_pressure_control(self, value):
        self.write_controller(P_GAIN_AIR_PRESSURE_CONTROL, value)

    @property
    def i_gain_air_pressure_control(self):
        self._i_gain_air_pressure_control = self.read_controller(I_GAIN_AIR_PRESSURE_CONTROL)
        return self._i_gain_air_pressure_control

    @i_gain_air_pressure_control.setter
    def i_gain_air_pressure_control(self, value):
        self.write_controller(I_GAIN_AIR_PRESSURE_CONTROL, value)

    @property
    def d_gain_air_pressure_control(self):
        self._d_gain_air_pressure_control = self.read_controller(D_GAIN_AIR_PRESSURE_CONTROL)
        return self._d_gain_air_pressure_control

    @d_gain_air_pressure_control.setter
    def d_gain_air_pressure_control(self, value):
        self.write_controller(D_GAIN_AIR_PRESSURE_CONTROL, value)

    @property
    def a_gain_air_pressure_control(self):
        self._a_gain_air_pressure_control = self.read_controller(A_GAIN_AIR_PRESSURE_CONTROL)
        return self._a_gain_air_pressure_control

    @a_gain_air_pressure_control.setter
    def a_gain_air_pressure_control(self, value):
        self.write_controller(A_GAIN_AIR_PRESSURE_CONTROL, value)

    @property
    def air_pressure_control_settle_tolerance(self):
        self._air_pressure_control_settle_tolerance = self.read_controller(
            AIR_PRESSURE_CONTROL_SETTLE_TOLERANCE)
        return self._air_pressure_control_settle_tolerance

    @air_pressure_control_settle_tolerance.setter
    def air_pressure_control_settle_tolerance(self, value):
        self.write_controller(AIR_PRESSURE_CONTROL_SETTLE_TOLERANCE, value)

    @property
    def p_gain_flow_rate_control(self):
        self._p_gain_flow_rate_control = self.read_controller(P_GAIN_FLOW_RATE_CONTROL)
        return self._p_gain_flow_rate_control

    @p_gain_flow_rate_control.setter
    def p_gain_flow_rate_control(self, value):
        self.write_controller(P_GAIN_FLOW_RATE_CONTROL, value)

    @property
    def i_gain_flow_rate_control(self):
        self._i_gain_flow_rate_control = self.read_controller(I_GAIN_FLOW_RATE_CONTROL)
        return self._i_gain_flow_rate_control

    @i_gain_flow_rate_control.setter
    def i_gain_flow_rate_control(self, value):
        self.write_controller(I_GAIN_FLOW_RATE_CONTROL, value)

    @property
    def d_gain_flow_rate_control(self):
        self._d_gain_flow_rate_control = self.read_controller(D_GAIN_FLOW_RATE_CONTROL)
        return self._d_gain_flow_rate_control

    @d_gain_flow_rate_control.setter
    def d_gain_flow_rate_control(self, value):
        self.write_controller(D_GAIN_FLOW_RATE_CONTROL, value)

    @property
    def a_gain_flow_rate_control(self):
        self._a_gain_flow_rate_control = self.read_controller(A_GAIN_AIR_PRESSURE_CONTROL)
        return self._a_gain_flow_rate_control

    @a_gain_flow_rate_control.setter
    def a_gain_flow_rate_control(self, value):
        self.write_controller(A_GAIN_AIR_PRESSURE_CONTROL, value)

    @property
    def flow_rate_control_settle_tolerance(self):
        self._flow_rate_control_settle_tolerance = self.read_controller(
            FLOW_RATE_CONTROL_SETTLE_TOLERANCE)
        return self._flow_rate_control_settle_tolerance

    @flow_rate_control_settle_tolerance.setter
    def flow_rate_control_settle_tolerance(self, value):
        self.write_controller(FLOW_RATE_CONTROL_SETTLE_TOLERANCE, value)

    @property
    def control_settle_time(self):
        self._control_settle_time = self.read_controller(CONTROL_SETTLE_TIME)
        return self._control_settle_time

    @control_settle_time.setter
    def control_settle_time(self, value):
        self.write_controller(CONTROL_SETTLE_TIME, value)

    @property
    def control_timeout(self):
        self._control_timeout = self.read_controller(CONTROL_TIMEOUT)
        return self._control_timeout

    @control_timeout.setter
    def control_timeout(self, value):
        self.write_controller(CONTROL_TIMEOUT, value)

    @property
    def remote_panel_timeout(self):
        self._remote_panel_timeout = self.read_controller(REMOTE_PANEL_TIMEOUT)
        return self._remote_panel_timeout

    @remote_panel_timeout.setter
    def remote_panel_timeout(self, value):
        self.write_controller(REMOTE_PANEL_TIMEOUT, value)

    @property
    def potentiometer_noise(self):
        self._potentiometer_noise = self.read_controller(POTENTIOMETER_NOISE)
        return self._potentiometer_noise

    @potentiometer_noise.setter
    def potentiometer_noise(self, value):
        self.write_controller(POTENTIOMETER_NOISE, value)

    @property
    def main_loop_period(self):
        self._main_loop_period = self.read_controller(MAIN_LOOP_PERIOD)
        return self._main_loop_period

    @main_loop_period.setter
    def main_loop_period(self, value):
        self.write_controller(MAIN_LOOP_PERIOD, value)

    @property
    def max_temperature(self):
        self._max_temperature = self.read_controller(MAX_TEMPERATURE)
        return self._max_temperature

    @max_temperature.setter
    def max_temperature(self, value):
        self.write_controller(MAX_TEMPERATURE, value)

    @property
    def cpu_load(self):
        self._cpu_load = self.read_controller(CPU_LOAD)
        return self._cpu_load

    @cpu_load.setter
    def cpu_load(self, value):
        self.write_controller(CPU_LOAD, value)

    @property
    def millis(self):
        self._millis = self.read_controller(MILLIS)
        return self._millis

    @millis.setter
    def millis(self, value):
        self.write_controller(MILLIS, value)

    @property
    def seconds(self):
        self._seconds = self.read_controller(SECONDS)
        return self._seconds

    @seconds.setter
    def seconds(self, value):
        self.write_controller(SECONDS, value)
