# The MIT License (MIT)
#
# Copyright (c) 2020 ladyada for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_pm25`
================================================================================

CircuitPython library for PM2.5 Air Quality Sensors


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

Works with most (any?) Plantower UART or I2C interfaced PM2.5 sensor.

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

# imports
import time
import struct
from digitalio import Direction

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_PM25.git"


class PM25:
    """Super-class for generic PM2.5 sensors. Subclasses must implement
    _read_into_buffer to fill self._buffer with a packet of data"""

    def __init__(self):
        # rad, ok make our internal buffer!
        self._buffer = bytearray(32)
        self.aqi_reading = {
            "pm10 standard": None,
            "pm25 standard": None,
            "pm100 standard": None,
            "pm10 env": None,
            "pm25 env": None,
            "pm100 env": None,
            "particles 03um": None,
            "particles 05um": None,
            "particles 10um": None,
            "particles 25um": None,
            "particles 50um": None,
            "particles 100um": None,
        }

    def _read_into_buffer(self):
        """Low level buffer filling function, to be overridden"""
        raise NotImplementedError()

    def read(self):
        """Read any available data from the air quality sensor and
        return a dictionary with available particulate/quality data"""
        self._read_into_buffer()
        # print([hex(i) for i in self._buffer])

        # check packet header
        if (self._buffer[0] != 0x42) or (self._buffer[1] != 0x4D):
            raise RuntimeError("Invalid PM2.5 header")

        # check frame length
        frame_len = struct.unpack(">H", self._buffer[2:4])[0]
        if frame_len != 28:
            raise RuntimeError("Invalid PM2.5 frame length")

        checksum = struct.unpack(">H", self._buffer[30:32])[0]
        check = sum(self._buffer[0:30])
        if check != checksum:
            raise RuntimeError("Invalid PM2.5 checksum")

        # unpack data
        frame = struct.unpack(">HHHHHHHHHHHH", self._buffer[4:28])
        (
            self.aqi_reading["pm10 standard"],
            self.aqi_reading["pm25 standard"],
            self.aqi_reading["pm100 standard"],
            self.aqi_reading["pm10 env"],
            self.aqi_reading["pm25 env"],
            self.aqi_reading["pm100 env"],
            self.aqi_reading["particles 03um"],
            self.aqi_reading["particles 05um"],
            self.aqi_reading["particles 10um"],
            self.aqi_reading["particles 25um"],
            self.aqi_reading["particles 50um"],
            self.aqi_reading["particles 100um"],
        ) = frame

        return self.aqi_reading


class PM25_I2C(PM25):
    """
    A driver for the PM2.5 Air quality sensor over I2C
    """
from adafruit_bus_device.i2c_device import I2CDevice

    def __init__(self, i2c_bus, reset_pin=None, address=0x12):
        if reset_pin:
            # Reset device
            reset_pin.direction = Direction.OUTPUT
            reset_pin.value = False
            time.sleep(0.01)
            reset_pin.value = True
            # it takes at least a second to start up
            time.sleep(1)

        for _ in range(5):  # try a few times, it can be sluggish
            try:
                self.i2c_device = I2CDevice(i2c_bus, address)
                break
            except ValueError:
                time.sleep(1)
                continue
        else:
            raise RuntimeError("Unable to find PM2.5 device")
        super().__init__()

    def _read_into_buffer(self):
        with self.i2c_device as i2c:
            try:
                i2c.readinto(self._buffer)
            except OSError:
                raise RuntimeError("Unable to read from PM2.5 over I2C")


class PM25_UART(PM25):
    """
    A driver for the PM2.5 Air quality sensor over UART
    """

    def __init__(self, uart, reset_pin=None):
        if reset_pin:
            # Reset device
            reset_pin.direction = Direction.OUTPUT
            reset_pin.value = False
            time.sleep(0.01)
            reset_pin.value = True
            # it takes at least a second to start up
            time.sleep(1)

        self._uart = uart
        super().__init__()

    def _read_into_buffer(self):
        b = self._uart.read(1)
        if not b:
            raise RuntimeError("Unable to read from PM2.5 UART")
        b = b[0]
        if b != 0x42:
            raise RuntimeError("Unable to read from PM2.5 UART")
        self._buffer[0] = b  # read one byte

        remain = self._uart.read(31)
        if not remain or len(remain) != 31:
            raise RuntimeError("Unable to read from PM2.5 UART")
        for i in range(31):
            self._buffer[i + 1] = remain[i]
        # print([hex(i) for i in self._buffer])
