# SPDX-FileCopyrightText: 2020 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_pm25`
================================================================================

CircuitPython library for PM2.5 Air Quality Sensors


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

Works with most (any?) Plantower UART or I2C interfaced PM2.5 sensor.

* `PM2.5 Air Quality Sensor and Breadboard Adapter Kit - PMS5003
  <https://www.adafruit.com/product/3686>`_

* `PM2.5 Air Quality Sensor with I2C Interface - PMSA003I
  <https://www.adafruit.com/product/4505>`_

* `Adafruit PMSA003I Air Quality Breakout
  <https://www.adafruit.com/product/4632>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

import struct

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_PM25.git"


class PM25:
    """
    Super-class for generic PM2.5 sensors.

    .. note::
        Subclasses must implement _read_into_buffer to fill self._buffer with a packet of data

    """

    def __init__(self) -> None:
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

    def _read_into_buffer(self) -> None:
        """Low level buffer filling function, to be overridden"""
        raise NotImplementedError()

    def read(self) -> dict:
        """Read any available data from the air quality sensor and
        return a dictionary with available particulate/quality data

        Note that "standard" concentrations are those when corrected to
        standard atmospheric conditions (288.15 K, 1013.25 hPa), and
        "environmental" concentrations are those measure in the current
        atmospheric conditions.
        """
        self._read_into_buffer()
        # print([hex(i) for i in self._buffer])

        # check packet header
        if not self._buffer[0:2] == b"BM":
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
        ) = struct.unpack(">HHHHHHHHHHHH", self._buffer[4:28])

        return self.aqi_reading
