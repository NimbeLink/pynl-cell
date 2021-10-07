"""
Interfaces with a modem using its AT interface

(C) NimbeLink Corp. 2021

All rights reserved except as explicitly granted in the license agreement
between NimbeLink Corp. and the designated licensee. No other use or disclosure
of this software is permitted. Portions of this software may be subject to third
party license terms as specified in this software, and such portions are
excluded from the preceding copyright notice of NimbeLink Corp.
"""

import logging
import re
import serial
import time
import typing

from .response import Response

class Interface(object):
    """Python class for sending and receiving commands from embedded cellular
    modems
    """

    class CommError(Exception):
        """An error that occurs when AT communication with a device fails
        """

        pass

    DefaultTimeout: float = 5.0
    """A default timeout for interacting with a modem"""

    SendNewLine: str = "\r"
    """The line engins to use to send commands"""

    NewLine: str = Response.DefaultNewLine
    """The line endings to expect"""

    def __init__(self, *args, **kwargs):
        """Creates a new AT interface

        :param self:
            Self
        :param *args:
            Arguments to a serial port
        :param **kwargs:
            Keyword arguments to a serial port

        :return none:
        """

        self._logger = logging.getLogger(__name__)

        # Try to make the serial port with our default timeout
        try:
            self._device = serial.Serial(*args, **kwargs, timeout = Interface.DefaultTimeout)

        # If it appears the user specified their own timeout, just use that
        except SyntaxError:
            self._device = serial.Serial(*args, **kwargs)

        self._buffer = bytearray()

        self.writeTimeout: float = 0

        # Clear out device's buffers to begin with
        self._clear()

    @property
    def device(self) -> serial.Serial:
        """Gets our serial port

        :param self:
            Self

        :return:
            The serial device used in our interface
        :rtype: serial.Serial
        """

        return self._device

    def _clear(self) -> None:
        """Clears our device's input/output buffers

        :param self:
            Self

        :return none:
        """

        while True:
            self._device.reset_output_buffer()
            self._device.reset_input_buffer()

            if len(self._device.read_all()) < 1:
                break

    @property
    def readTimeout(self) -> float:
        """Gets our serial port's read timeout

        :param self:
            Self

        :return float:
            Our serial port's read timeout
        """

        return self._device.timeout

    @readTimeout.setter
    def readTimeout(self, timeout: float) -> None:
        """Sets our serial port's read timeout

        :param self:
            Self
        :param timeout:
            The timeout to set, in seconds

        :return none:
        """

        # Setting the serial port's timeout can cause issues with buffering of
        # input/output, so only set it if necessary
        if self._device.timeout != timeout:
            self._device.timeout = timeout

    @property
    def writeTimeout(self) -> float:
        """Gets our serial port's write timeout

        :param self:
            Self

        :return float:
            Our serial port's write timeout, in seconds
        """

        return self._device.write_timeout

    @writeTimeout.setter
    def writeTimeout(self, timeout: float) -> None:
        """Sets our serial port's write timeout

        :param self:
            Self
        :param timeout:
            The timeout to set, in seconds

        :return none:
        """

        # Setting the serial port's timeout can cause issues with buffering of
        # input/output, so only set it if necessary
        if self._device.write_timeout != timeout:
            self._device.write_timeout = timeout

    @property
    def baudRate(self) -> int:
        """Gets our serial port's baud rate

        :param self:
            Self

        :return Integer:
            Our serial port's read timeout
        """

        return self._device.baudrate

    @baudRate.setter
    def baudRate(self, baudRate: int):
        """Sets our serial port's baud rate

        :param self:
            Self
        :param baudRate:
            The baud rate to use

        :return none:
        """

        self._device.baudrate = baudRate

    @property
    def flowControl(self) -> bool:
        """Gets our serial port's flow control

        :param self:
            Self

        :return Bool:
            Whether or not RTS/CTS flow control is on
        """

        return self._device.baudrate

    @flowControl.setter
    def flowControl(self, flowControl: bool) -> None:
        """Sets our serial port's flow control

        :param self:
            Self
        :param flowControl:
            Whether or not to use RTS/CTS flow control

        :return none:
        """

        self._device.rtscts = flowControl

    def _getLines(self, timeout: float = None) -> typing.Generator[str, None, None]:
        """Gets lines from the device

        Because this function uses 'yield' to return lines, the provided timeout
        will be used for the *entire* handling of lines. In other words, if you
        are given a line while using this function and come back to receive
        another line, the timeout will continue to be relative to when the
        function was first entered, prior to the previous line being returned.

        :param self:
            Self
        :param timeout:
            How long to wait for lines

        :yield String:
            The next line of text

        :return none:
        """

        if timeout is None:
            timeout = Interface.DefaultTimeout

        self.readTimeout = timeout

        # Allow a zero-second timeout to still potentially read input
        startTime: float = None

        while True:
            now = time.time()

            # If this is our first time through, note when we started
            if startTime is None:
                startTime = now

            # If we've timed out, stop
            if (now - startTime) > timeout:
                break

            # Get another line of text
            self._buffer.extend(self._device.readline())

            # If the data doesn't actually contain a newline, keep waiting
            #
            # There appear to be issues with readline() that aren't strictly
            # documented, where it's ending and returning a non-empty buffer
            # that *doesn't* contain a newline in it.
            if self._buffer.rfind(b"\n") < 0:
                continue

            # We need to clear our buffer before yielding, as we can't guarantee
            # the caller will re-enter the function again
            buffer = self._buffer

            # We consumed a whole line, so start over
            self._buffer = bytearray()

            self._logger.debug(f"Read  {ascii(buffer.decode())}")

            # Got another line
            yield buffer.decode()

    def _writeRaw(self, data: typing.Union[bytes, bytearray]) -> None:
        """Writes raw data

        :param self:
            Self
        :param data:
            The data to write

        :raise CommError:
            Failed to write data

        :return none:
        """

        if self._device.write(data) != len(data):
            raise Interface.CommError(f"Failed to send {ascii(data.decode())}")

        self._logger.debug(f"Wrote {ascii(data.decode())}")

    def _readRaw(self, size: int, timeout: float = None) -> bytes:
        """Read raw bytes from the serial device connected to the modem

        Less data may be returned than desired.

        :param self:
            Self
        :param size:
            The amount of data to attempt to read from the serial port
        :param timeout:
            The longest we should wait for more data if we don't have enough

        :return bytes:
            The data that was read from the serial port
        """

        # If the user didn't specify a timeout, just use the default timeout
        if timeout is None:
            timeout = Interface.DefaultTimeout

        # Set the read timeout of the device to the desired length
        self.readTimeout = timeout

        # Attempt to read the desired number of bytes from the serial port
        data: bytes = self._device.read(size)

        self._logger.debug(f"Read {ascii(data.decode())}")

        # Return the bytes that were read, even if there are less than desired
        return data

    def _beginCommand(self, command: str) -> None:
        """Sends a command to the AT interface without expecting a response

        :param command:
            Command to send

        :raise CommError:
            Failed to send command

        :return none:
        """

        # First try to have locked control over the interface by sending the
        # 'AT'
        self._writeRaw("AT".encode())

        # Handle any buffered URCs, which -- since we entered the 'AT' -- we
        # expect to not show up anymore until we're done with the command's full
        # entry and response
        for line in self._getLines(timeout = 0):
            pass

        # Drop the command's 'AT', if any
        if command[:2].upper() == "AT":
            command = command[2:]

        # Add our sending line ending(s)
        command = command + self.SendNewLine

        # Write the command
        self._writeRaw(command.encode())

    def _waitForResponse(self, command, timeout: float = None) -> Response:
        """Waits for a certain response

        :param self:
            Self
        :param command:
            The command to wait for a response to
        :param timeout:
            How long to wait for the response

        :raise CommError:
            Timed out waiting for response

        :return Response:
            The response
        """

        data = ""

        for line in self._getLines(timeout = timeout):
            # Note the additional contents
            data += line

            # Try to get a response from that
            response = Response.makeFromString(
                string = data,
                command = command,
                newLine = self.NewLine
            )

            # If this is a final result, return it
            if response is not None:
                return response

        raise Interface.CommError("Timeout waiting for response")

    def waitForPattern(self, pattern: typing.Pattern, timeout: float = None) -> bool:
        """Waits until a desired string is seen in the output from the device

        This method reads characters one at a time from the serial port and
        checks whether or not a match for the regular expression pattern exists
        in the read data.

        :param self:
            Self
        :param pattern:
            The regular expression pattern to wait for
        :param timeout:
            How long to wait for a given pattern

        :return bool:
            Whether or not the desired pattern was produced in the given time
        """

        # Ensure timeout is set to default if unspecified
        if timeout is None:
            timeout = Interface.DefaultTimeout

        buffer: bytearray = bytearray()

        begin: float = time.time()

        # While we haven't ran out of time, search for the desired string in the
        # output
        while begin + timeout > time.time():
            # Check if the buffer has a match for the pattern anywhere
            #
            # If the buffer does, then we are done.
            if re.search(pattern, buffer.decode()):
                return True

            # Attempt to read a single byte from the serial port
            data: bytes = self._readRaw(1, timeout)

            # If we read a byte, append it to the data we previously read
            if data:
                buffer.append(data[0])

        # Ran out of time, so return failure
        return False

    def sendCommand(self, command: str, timeout: float = None) -> Response:
        """Sends a command to the AT interface

        :param self:
            Self
        :param command:
            Command to send
        :param timeout:
            How long to wait for the response, if any

        :raise CommError:
            Timed out sending command or waiting for response

        :return Response:
            The response
        """

        # Make sure the command is stripped of any provided line endings
        command = command.rstrip()

        # Send the command
        self._beginCommand(command = command)

        # Wait for a response
        return self._waitForResponse(command = command, timeout = timeout)

    def getUrc(self, pattern: str = None, timeout: float = None) -> str:
        """Waits for an asynchronous output

        The pattern string can be a regular expression used to filter out
        irrelevant URCs. It must be contained on a single line, as URCs are only
        single lines of text.

        URCs will have their line endings stripped prior to being returned.

        :param self:
            Self
        :param pattern:
            A pattern for filtering URCs
        :param timeout:
            How long to wait for a new URC

        :raise CommError:
            Timed out waiting for URC

        :return String:
            The URC, sans line endings
        """

        # Get another URC
        for line in self._getLines(timeout = timeout):
            # If a pattern was specified but the URC doesn't match, ignore this
            if (pattern is not None) and (re.match(pattern, line) is None):
                continue

            # Got a URC that's wanted
            return line.rstrip()

        # We didn't get the URC in time
        raise Interface.CommError(f"Failed to receive URC matching '{pattern}'")

    def getUrcs(self, pattern: str = None, timeout: float = None) -> typing.Generator[str, None, None]:
        """Waits for multiple asynchronous output

        If a timeout is specified, it will be used for each individual URC as if
        that were the first URC. That is, if a URC is returned and this function
        is re-entered from the yield, the timeout will be measured relative to
        when the function is entered again, *not* from when it was first
        entered.

        :param self:
            Self
        :param pattern:
            A pattern for filtering URCs
        :param timeout:
            How long to wait for a new URC

        :yield String:
            The URC, sans line endings

        :return none:
        """

        while True:
            # Get another URC
            try:
                urc = self.getUrc(pattern = pattern, timeout = timeout)

                yield urc

            # If that failed, we're done
            except Interface.CommError:
                break

    def startPrompt(self, *args, **kwargs) -> "Interface.Prompt":
        """Starts a prompt command

        :param self:
            Self
        :param *args:
            Positional arguments
        :param **kwargs:
            Keyword arguments

        :return Prompt:
            The prompt
        """

        return Interface.Prompt(self, *args, **kwargs)

    class Prompt:
        """A prompt for sending dynamic data in an AT command
        """

        def __init__(self, interface: "Interface", dynamic: bool):
            """Creates a new prompt

            :param self:
                Self
            :param interface:
                The AT interface this is on
            :param dynamic:
                Whether or not the incoming data will be dynamic

            :return none:
            """

            self._interface: "Interface" = interface
            self._dynamic: bool = dynamic

            self._command: str = None

        def __enter__(self):
            """Enters the prompt context

            :param self:
                Self

            :return Prompt:
                Us
            """

            return self

        def __exit__(self, type, value, traceback):
            """Exits the prompt context

            :param self:
                Self
            :param type:
                The type of exception, if any
            :param value:
                The value of the exception, if any
            :param traceback:
                The exception's traceback, if any

            :return none:
            """

            pass

        def startCommand(self, command: str) -> None:
            """Starts a dynamic command

            :param self:
                Self
            :param command:
                The command to send

            :raise CommError:

            :return none:
            """

            # Make sure the command is stripped of any provided line endings
            command = command.rstrip()

            # Note the command we're sending so we can try to filter it out of
            # our response later
            self._command = command

            # Send the command
            self._interface._beginCommand(command = command)

        def writeData(self, data: typing.Union[bytes, bytearray]) -> None:
            """Writes command data

            :param self:
                Self
            :param data:
                The data to write

            :raise CommError:
                Failed to write data

            :return none:
            """

            self._interface._writeRaw(data)

        def finish(self, timeout: float = None) -> Response:
            """Finishes the prompt

            :param self:
                Self
            :param timeout:
                How long to wait for the response

            :raise CommError:
                Failed to write data or get response

            :return Response:
                The response
            """

            # If we're a dynamic command, send the terminator
            if self._dynamic:
                self._interface._writeRaw("\x1A".encode())

            # Wait for a response
            return self._interface._waitForResponse(command = self._command, timeout = timeout)
