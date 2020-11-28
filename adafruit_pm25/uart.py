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
`adafruit_pm25.uart`
================================================================================

UART module for CircuitPython library for PM2.5 Air Quality Sensors


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

Works with most (any?) Plantower UART interfaced PM2.5 sensor.

Tested with:

* PMS5003 on QT Py M0
  * On power on, this device defaults to 'active' mode unless a mode reset command is received

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

import time
from digitalio import Direction
from . import PM25

PLANTOWER_HEADER = b"\x42\x4D"

PLANTOWER_CMD_MODE_PASSIVE = b"\xE1\x00\x00"
PLANTOWER_CMD_MODE_ACTIVE = b"\xE1\x00\x01"
PLANTOWER_CMD_READ = b"\xE2\x00\x00"
PLANTOWER_CMD_SLEEP = b"\xE4\x00\x00"
PLANTOWER_CMD_WAKEUP = b"\xE4\x00\x01"

UART_RETRY_COUNT = 3
MAX_FRAME_SIZE = 32


class PM25_UART(PM25):
    """
    A driver for the PM2.5 Air quality sensor over UART
    """

    def __init__(self, uart, reset_pin=None, set_pin=None, mode="passive"):
        self._uart = uart
        self._reset_pin = reset_pin
        self._set_pin = set_pin
        self._mode = mode

        if reset_pin:
            # Reset device on init, for good measure
            self._reset_pin.direction = Direction.OUTPUT
            self._pin_reset()

        if set_pin:
            # Pull set pin high to 'working' status (pulling low puts device to sleep)
            self._set_pin.direction = Direction.OUTPUT
            self._set_pin.value = True

        if self._mode == "passive":
            self._cmd_mode_passive()
        elif self._mode == "active":
            self._cmd_mode_active()
        else:
            raise RuntimeError("Invalid mode")

        super().__init__()

    def _read_into_buffer(self):
        if self._mode == "passive":
            read_buffer = self._cmd_passive_read()
        self._buffer = self._read_uart()

    def _cmd_mode_passive(self):
        """
        Sends command to device to enable 'passive' mode, where data frames are only sent after a read command
        """
        self._uart.reset_input_buffer()
        self._uart.write(self._build_cmd_frame(PLANTOWER_CMD_MODE_PASSIVE))
        cmd_response = self._read_uart()
        self._mode = "passive"
        time.sleep(1)
        return cmd_response

    def _cmd_mode_active(self):
        """
        Sends command to device to enable 'active' mode, where data frames are sent repeatedly every second
        """
        self._uart.reset_input_buffer()
        self._uart.write(self._build_cmd_frame(PLANTOWER_CMD_MODE_ACTIVE))
        cmd_response = self._read_uart()
        self._mode = "active"
        time.sleep(1)
        return cmd_response

    def _cmd_sleep(self):
        """
        Sends command to put device into low-power sleep mode via UART
        """
        self._uart.reset_input_buffer()
        self._uart.write(self._build_cmd_frame(PLANTOWER_CMD_SLEEP))
        cmd_response = self._read_uart()
        time.sleep(1)
        return cmd_response

    def _cmd_wakeup(self):
        """
        Sends command to wake device from low-power sleep mode via UART

        Wakeup from sleep via command requires about 3 seconds before the device becomes available

        Additionally, this command does not trigger a response and behaves more like a reset or pin awake. On command reciept the device pulls TX low until about a second later as it initializes.
        """
        self._uart.reset_input_buffer()
        self._uart.write(self._build_cmd_frame(PLANTOWER_CMD_WAKEUP))
        time.sleep(3)

    def _cmd_passive_read(self):
        """
        Sends command to request a data frame whlie in 'passive' mode and immediately reads in frame
        """
        self._uart.reset_input_buffer()
        self._uart.write(self._build_cmd_frame(PLANTOWER_CMD_READ))

    def _pin_reset(self):
        """
        Resets device via RESET pin, but only if pin has been assigned

        Reset via pin requires about 3 seconds before the device becomes available
        """
        if self._reset_pin is not None:
            self._reset_pin.value = False
            time.sleep(0.01)
            self._reset_pin.value = True
            time.sleep(3)

    def _pin_sleep(self):
        """
        Sleeps device via SET pin, but only if pin has been assigned
        """
        if self._set_pin is not None and self._set_pin.value == True:
            self._set_pin.value = False

    def _pin_wakeup(self):
        """
        Wakes device via SET pin, but only if pin has been assigned

        Wakeup from sleep via pin takes about 3 seconds before device is available
        """
        if self._set_pin is not None and self._set_pin.value == False:
            self._set_pin.value = True
            time.sleep(3)

    def _build_cmd_frame(self, cmd_bytes):
        """
        Builds a valid command frame byte array with checksum for given command bytes
        """
        if len(cmd_bytes) != 3:
            raise RuntimeError("Malformed command frame")
        cmd_frame = bytearray()
        cmd_frame.extend(PLANTOWER_HEADER)
        cmd_frame.extend(cmd_bytes)
        cmd_frame.extend(sum(cmd_frame).to_bytes(2, "big"))
        return cmd_frame

    def _read_uart(self):
        """
        Reads a single frame via UART, ignoring bytes that are not frame headers to avoid reading in frames mid-stream
        """
        error_count = 0
        first_bytes_tried = 0
        while True:
            serial_data = bytearray()
            first_byte = self._uart.read(1)
            if first_byte is not None:
                if ord(first_byte) == PLANTOWER_HEADER[0]:
                    serial_data.append(ord(first_byte))
                    second_byte = self._uart.read(1)
                    if ord(second_byte) == PLANTOWER_HEADER[1]:
                        serial_data.append(ord(second_byte))
                        frame_length_bytes = self._uart.read(2)
                        frame_length = int.from_bytes(frame_length_bytes, "big")
                        if frame_length > 0 and frame_length <= (MAX_FRAME_SIZE - 4):
                            serial_data.extend(frame_length_bytes)
                            data_frame = self._uart.read(frame_length)
                            if len(data_frame) > 0:
                                serial_data.extend(data_frame)
                                frame_checksum = serial_data[-2:]
                                checksum = sum(serial_data[:-2]).to_bytes(2, "big")
                                if frame_checksum != checksum:
                                    # Invalid checksum, ignore the frame, increment count, and try again
                                    error_count += 1
                                else:
                                    return serial_data
                            else:
                                # Data frame empty, ignore the frame, increment error count, and try again
                                error_count += 1
                        else:
                            # Invalid frame length, ignore the frame, increment error count, and try again
                            error_count += 1
                    else:
                        # Invalid header low bit, ignore the frame, increment error count, and try again
                        error_count += 1
                else:
                    # First bit isn't a header high bit, ignore and retry until we get a header bit
                    first_bytes_tried += 1
            else:
                # If we didn't get a byte during our read, that's fine, just move on
                pass

            if error_count >= UART_RETRY_COUNT:
                raise RuntimeError("Frame error count exceded retry threshold")
            elif first_bytes_tried > MAX_FRAME_SIZE:
                # If we haven't found a frame header in more than MAX_FRAME_SIZE bytes then increment error count and try again
                error_count += 1
