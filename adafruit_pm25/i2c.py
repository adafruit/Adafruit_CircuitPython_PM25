# SPDX-FileCopyrightText: 2020 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_pm25.i2c`
================================================================================

I2C module for CircuitPython library for PM2.5 Air Quality Sensors


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* `PM2.5 Air Quality Sensor with I2C Interface - PMSA003I
  <https://www.adafruit.com/product/4505>`_

* `Adafruit PMSA003I Air Quality Breakout
  <https://www.adafruit.com/product/4632>`_


Works with most (any?) Plantower I2C interfaced PM2.5 sensor.

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

# imports
import time
from digitalio import Direction, DigitalInOut
from adafruit_bus_device.i2c_device import I2CDevice
from . import PM25

try:
    # Used only for typing
    import typing  # pylint: disable=unused-import
    from busio import I2C
except ImportError:
    pass


class PM25_I2C(PM25):
    """
    A module for using the PM2.5 Air quality sensor over I2C

    :param i2c_bus: The `busio.I2C` object to use.
    :param ~microcontroller.Pin reset_pin: Pin use to reset the sensor. Defaults to `None`
    :param int address: The I2C address of the device. Defaults to :const:`0x12`

    **Quickstart: Importing and using the PMSA003I Air quality sensor**

        Here is one way of importing the `PM25_I2C` class so you can use it with the name ``pm25``.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import busio
            from adafruit_pm25.i2c import PM25_I2C

        Once this is done you can define your `busio.I2C` object and define your sensor object

        .. code-block:: python

            i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
            reset_pin = None
            pm25 = PM25_I2C(i2c, reset_pin)


        Now you have access to the air quality data using the class function
        `adafruit_pm25.PM25.read`

        .. code-block:: python

            aqdata = pm25.read()

    """

    def __init__(
        self, i2c_bus: I2C, reset_pin: DigitalInOut = None, address: int = 0x12
    ) -> None:
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

    def _read_into_buffer(self) -> None:
        with self.i2c_device as i2c:
            try:
                i2c.readinto(self._buffer)
            except OSError as err:
                raise RuntimeError("Unable to read from PM2.5 over I2C") from err
