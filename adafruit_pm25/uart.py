# SPDX-FileCopyrightText: 2020 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_pm25.uart`
================================================================================

UART module for CircuitPython library for PM2.5 Air Quality Sensors


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

Works with most (any?) Plantower UART or I2C interfaced PM2.5 sensor.

* `PM2.5 Air Quality Sensor and Breadboard Adapter Kit - PMS5003
  <https://www.adafruit.com/product/3686>`_


**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

import time
from digitalio import Direction, DigitalInOut
from . import PM25

try:
    # Used only for typing
    import typing  # pylint: disable=unused-import
    from busio import UART
except ImportError:
    pass


class PM25_UART(PM25):
    """
    A driver for the PM2.5 Air quality sensor over UART

    :param ~busio.UART uart: The `busio.UART` object to use.
    :param ~microcontroller.Pin reset_pin: Pin use to reset the sensor.
     Defaults to `None`


    **Quickstart: Importing and using the PMS5003 Air quality sensor**

        Here is one way of importing the `PM25_UART` class so you
        can use it with the name ``pm25``.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import busio
            from adafruit_pm25.uart import PM25_UART

        Once this is done you can define your `busio.UART` object and define
        your sensor object

        .. code-block:: python

            uart = busio.UART(board.TX, board.RX, baudrate=9600)
            reset_pin = None
            pm25 = PM25_UART(uart, reset_pin)

        Now you have access to the air quality data using the class function
        `adafruit_pm25.PM25.read`

        .. code-block:: python

            aqdata = pm25.read()

    """

    def __init__(self, uart: UART, reset_pin: DigitalInOut = None):
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

    def _read_into_buffer(self) -> None:
        while True:
            b = self._uart.read(1)
            if not b:
                raise RuntimeError("Unable to read from PM2.5 (no start of frame)")
            if b[0] == 0x42:
                break
        self._buffer[0] = b[0]  # first byte and start of frame

        remain = self._uart.read(31)
        if not remain or len(remain) != 31:
            raise RuntimeError("Unable to read from PM2.5 (incomplete frame)")
        self._buffer[1:] = remain
