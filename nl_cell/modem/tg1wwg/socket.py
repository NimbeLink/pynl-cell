"""
A Skywire socket factory

(C) NimbeLink Corp. 2021

All rights reserved except as explicitly granted in the license agreement
between NimbeLink Corp. and the designated licensee. No other use or disclosure
of this software is permitted. Portions of this software may be subject to third
party license terms as specified in this software, and such portions are
excluded from the preceding copyright notice of NimbeLink Corp.
"""

import re
import socket
import typing

import nimbelink.cell.modem as modem
import nimbelink.cell.modem.skywire as skywire

class Socket(skywire.Socket):
    """A NL-SW-LTE-TG1WWG socket factory
    """

    class Instance(skywire.Socket.Instance):
        """A usable socket object
        """

        def __init__(self, factory: "Socket") -> None:
            """Creates a new socket instance

            :param self:
                Self
            :param factory:
                The socket factory to use

            :return none:
            """

            self.factory: "Socket" = factory

            # If there is a connection ID available, grab it
            if len(self.factory.availableConnIds) > 0:
                self.connId = self.factory.availableConnIds.pop()

            else:
                self.connId: int = None

            self.isOpen: bool = False

        def __del__(self):
            """Destructs the socket instance

            :param self:
                Self

            :return none:
            """

            self.close()

        def create(
            self,
            family: int = socket.AF_INET,
            type: int = socket.SOCK_STREAM,
            proto: int = 0,
            fileno: int = None
        ) -> None:
            """Creates a new socket

            :param self:
                Self
            :param family:
                The socket family
            :param type:
                The socket type
            :param proto:
                The socket protocol
            :param *args:
                Additional positional arguments
            :param **kwargs:
                Additional keyword arguments

            :raise OSError:
                Failed to create new socket on modem
            :raise OSError:
                Failed to find file descriptor

            :return none:
            """

            # Since the sockets already seem preconfigured with default values,
            # don't do anything yet since we don't want to write to NVM too
            # much.

            return None

        def close(self) -> None:
            """Closes the socket

            :param self:
                Self

            :return none:
            """

            if self.connId is None:
                return

            # Request that the modem shuts down the socket
            result = self.factory.modem.at.sendCommand(f"AT#SH={self.connId}")

            # Make sure we got a successful socket shutdown
            if not result:
                raise modem.AtError(
                    result, f"Modem failed to shutdown socket {self.connId}"
                )

            # Add the connection ID back to the list of available sockets
            self.factory.availableConnIds.append(self.connId)

            # Nullify the current ID
            self.connId = None

        def connect(self, address: typing.Tuple[str, int]) -> None:
            """Connects to an address

            :param self:
                Self
            :param address:
                A tuple of the host string and port number

            :raise OSError:
                Failed to connect socket

            :return none:
            """

            # Ensure socket has a connection
            if self.connId is None:
                raise OSError(
                    "Socket was not initialized properly before connection"
                )

            # Initiate the socket dial to the specified address, but leave the
            # modem in command mode
            #
            # This simplifies the code since we don't have to pause and unpause
            # a data stream between methods.
            result = self.factory.modem.at.sendCommand(
                f'AT#SD={self.connId},0,{address[1]},"{address[0]}",0,0,1'
            )

            # Check that opening the socket was successful
            if not result:
                raise OSError(f"Socket failed to connect to {address}")

            # Set the isOpen flag
            self.isOpen = True

        def send(self, bytes: bytearray) -> int:
            """Sends data to the socket

            :param self:
                Self
            :param bytes:
                The data to send

            :return Integer:
                The number of bytes sent
            """

            # Ensure socket has been initialized
            if self.connId is None:
                raise OSError(
                    "Connection has to be initialized before sending data"
                )

            # Ensure socket is open
            if not self.isOpen:
                raise OSError("Connection must be open in order to send data")

            # Write the command to request to send data to the modem
            self.factory.modem.at._writeRaw(
                f"AT#SSENDEXT={self.connId},{len(bytes)}\r\n".encode()
            )

            # Wait for the prompt to appear
            if not self.factory.modem.at.waitForPattern(re.compile("> "), 5):
                raise modem.AtError("Failed to get prompt for sending")

            # Write the raw bytes into the socket
            self.factory.modem.at._writeRaw(bytes)

            # Modem will automatically return to command mode

            # Return the bytes we wrote
            return len(bytes)

        def recv(self, bufsize: int) -> bytearray:
            """Receives data from the socket.

            :param self:
                Self
            :param bufsize:
                The amount of data to receive.
                Range: 1-1500 bytes

            :return bytearray:
                The received data
            """

            # Ensure the buffer size is within range
            if (bufsize < 1) or (bufsize > 1500):
                raise ValueError("bufsize must be between 1 and 1500 bytes")

            # Request that the modem send us up to bufsize bytes
            self.factory.modem.at._writeRaw(
                f"AT#SRECV={self.connId},{bufsize}\r\n".encode()
            )

            # The size of data being returned
            size: int = 0

            # Parse how many bytes the modem is giving to us
            for line in self.factory.modem.at._getLines(5):
                if "#SRECV: " in line:
                    size = int(line.split(",")[1].strip())
                    break

            # Read the data from the modem
            data: bytes = self.factory.modem.at._readRaw(size)

            # Make sure we get the OK result from the modem
            if not self.factory.modem.at.waitForPattern(re.compile("OK\r\n")):
                raise OSError("Failed to seek to OK after socket recv()")

            # Cast the data to a mutable bytearray to match return types
            return bytearray(data)

    def __init__(self, tg1wwg: "modem.tg1wwg.TG1WWG") -> None:
        """Creates a new socket factory

        :param self:
            Self
        :param tg1wwg:
            Our modem

        :return none:
        """

        super().__init__()

        # The available connection IDs that the modem can use
        self.availableConnIds: typing.List[int] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        self.modem: "modem.tg1wwg.TG1WWG" = tg1wwg

    def _activeContexts(self) -> int:
        """Checks how many contexts are active on the modem

        :param self:
            Self

        :return int:
            The number of active contexts on the modem
        """

        # Check the SGACT status
        response = self.modem.at.sendCommand("AT#SGACT?", 5)

        if not response:
            raise modem.AtError("Failed to query SGACT status")

        activeContexts: int = 0

        # Count the number of active PDP contexts
        for line in response.lines:
            # Only process lines that are reporting a context state
            if "#SGACT: " not in line:
                continue

            splitLine = line.split(",")

            state: int = int(splitLine[1].strip())

            # Count the active contexts
            if state == 1:
                activeContexts += 1

        # Return the number of active PDP contexts
        return activeContexts

    def _activateContexts(self):
        """Tries to activate PDP contexts if not already active

        An active PDP context is required for sockets to communicate.

        :param self:
            Self

        :return none:
        """

        # If we already have an active context, skip trying to activate others
        if self._activeContexts() > 0:
            return

        # Try activating the first context for AT&T APNs
        if self.modem.at.sendCommand("AT#SGACT=1,1"):
            return

        # Try activating the third context for Verizon APNs
        if self.modem.at.sendCommand("AT#SGACT=3,1"):
            return

        # Raise an error if none were activated
        raise OSError("Failed to activate PDP context")

    def __call__(self, *args, **kwargs) -> "Socket.Instance":
        """Creates a new socket

        :param self:
            Self
        :param *args:
            Positional arguments
        :param **kwargs:
            Keyword arguments

        :raise OSError:
            Failed to create new socket

        :return None:
            Failed to create socket
        :return Socket:
            The socket
        """

        # Make sure we have active PDP contexts
        self._activateContexts()

        # Get an instance of the socket
        instance: Socket.Instance = Socket.Instance(self)

        # Create it with the proper arguments
        instance.create(*args, **kwargs)

        # Check that we were able to create a socket and return None if we
        # weren't able to create the socket
        if instance.connId is None:
            return None

        # Return it from the factory
        return instance
