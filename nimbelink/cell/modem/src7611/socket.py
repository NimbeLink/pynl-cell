"""
A SRC7611 socket factory

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
    """A NL-SW-LTE-SRC7611 socket factory
    """

    EOFPattern: bytes = b"--EOF--Pattern--"
    """The default EOF pattern for AT+KPATTERN"""

    def __init__(self, src7611: "modem.src7611.SRC7611") -> None:
        """Creates a new socket sub-module

        :param self:
            Self
        :param src7611:
            The SRC7611 we're attached to

        :return none:
        """

        self.modem: "modem.src7611.SRC7611" = src7611

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
        :return Socket.Instance:
            The socket
        """

        instance = Socket.Instance(src7611 = self.modem)

        instance.create(*args, **kwargs)

        return instance

    class Instance(skywire.Socket.Instance):
        """A usable NL-SW-LTE-SRC7611 socket instance
        """

        def __init__(self, src7611: "modem.src7611.SRC7611") -> None:
            """Creates a new socket instance

            :param self:
                Self
            :param src7611:
                The NL-SW-LTE-SRC7611 we're attached to

            :return none:
            """

            self.modem: "modem.src7611.SRC7611" = src7611

            self.sessionId: int = None
            self.type = None

            self.recvTimeout = 60

        def delete(self) -> None:
            """Deletes the socket on the modem

            :param self:
                Self

            :return None:
            """

            # Guard against sockets that failed to open or were already deleted
            if self.sessionId is None:
                return None

            # Delete the socket on the modem
            result = self.modem.at.sendCommand(f"AT+KTCPDEL={self.sessionId}")

            # Check the result to ensure it didn't fail
            if not result:
                raise modem.AtError(
                    f"Failed to delete socket {self.sessionId}"
                )

        def create(
            self,
            family: int = socket.AF_INET,
            type: int = socket.SOCK_STREAM,
            proto: int = 0,
            fileno: int = None,
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

            :raise AtError:
                AT command failed
            :raise OSError:
                Failed to create new socket on modem
            :raise OSError:
                Failed to find file descriptor

            :return none:
            """

            # Verify that the GPRS configuration is set
            #
            # If KCNXCFG is not configured the modem does not know how to
            # connect to the internet.
            response = self.modem.at.sendCommand("AT+KCNXCFG?")

            # Check that the modem responds
            if not response:
                raise modem.AtError(response)

            # Ensure KCNXCFG has been set to a value
            if "+KCNXCFG:" not in response:
                raise modem.Error("AT+KCNXCFG must be configured")

        def close(self) -> None:
            """Closes the socket

            :param self:
                Self

            :return none:
            """

            if self.sessionId != None:
                self.modem.at.sendCommand(f"AT+KTCPCLOSE={self.sessionId}")

                # Delete the socket from the modem
                self.delete()

                self.sessionId = None

        def connect(self, address: typing.Tuple[str, int]) -> None:
            """Creates a new socket and connects to an address

            The SRC7611 needs to have an address to create a socket so this
            method creates and connects the socket.

            :param self:
                Self
            :param address:
                A tuple of the host string and port number

            :raise AtError:
                Failed to send AT command to open socket
            :raise OSError:
                Failed to connect socket

            :return none:
            """

            # Create a new socket on the modem that will connect to the
            # specified address
            response = self.modem.at.sendCommand(
                f'AT+KTCPCFG=1,0,"{address[0]}",{address[1]}'
            )

            # If that failed, raise an exception
            if not response:
                raise modem.AtError("Failed to create new socket on modem")

            # Set the session id from the modem's response
            for line in response.lines:
                if "+KTCPCFG: " in line:
                    self.sessionId = int(line.split(" ")[1])
                    break

            # If we couldn't find the socket session id, raise an exception
            if self.sessionId is None:
                raise modem.AtError(
                    response, "Failed to create new socket on modem"
                )

            # Connect the socket to the remote server
            response = self.modem.at.sendCommand(
                f"AT+KTCPCNX={self.sessionId}"
            )

            # If we couldn't start a connection, raise an exception
            if not response:
                raise modem.AtError(response, "Failed to initiate connection")

            # Wait for the modem to connect to the remote server for up to 10
            # seconds
            response = self.modem.at.getUrc(
                f"\\+KTCP_IND: {self.sessionId},1", 10
            )

            # Ensure we got a response
            if not response:
                raise modem.AtError(
                    "Socket failed to connect to remote server."
                )

        def send(self, bytes: bytes) -> int:
            """Sends data to the socket

            :param self:
                Self
            :param bytes:
                The data to send

            :return int:
                The number of bytes sent
            """

            # Start the sending process by starting the TCP send command
            self.modem.at._beginCommand(f"AT+KTCPSND={self.sessionId},{len(bytes)}")

            # Wait for the CONNECT prompt to be sent
            if not self.modem.at.waitForPattern(re.compile("CONNECT")):
                raise modem.AtError("Failed to get CONNECT string")

            # Send the payload to the modem
            self.modem.at._writeRaw(bytes)

            # Send the EOF pattern to the modem
            self.modem.at._writeRaw(Socket.EOFPattern)

            # Ensure we were successful in sending the bytes to the modem
            if not self.modem.at.waitForPattern(re.compile("OK\r\n")):
                raise modem.AtError("Failed to send bytes")

            # Return the number of bytes that were sent
            return len(bytes)

        def recv(self, bufsize: int) -> bytearray:
            """Receives data from the socket

            NOTE: The MTU for the modem is 1500 bytes, this may limit how much
            data is able to be read from the modem at once. The AT command
            manual specifies that practically any number can be read at once but
            in experience the SRC7611 only allows up to 1500 to be read at a
            time.

            :param self:
                Self
            :param bufsize:
                The amount of data to receive

            :return bytearray:
                The received data
            """

            # Send the TCP data receive command with the size of the buffer to
            # receive
            #
            # The modem will send the max of the buffer size or the number of
            # bytes it currently has.
            response = self.modem.at.sendCommand(
                f"AT+KTCPRCV={self.sessionId},{bufsize}",
                timeout = self.recvTimeout + 5,
            )

            # If we failed to get a response, something probably went wrong so
            # return an empty array
            if not response:
                return bytearray()

            # The modem will always send the data between a CONNECT string and a
            # string with a EOF pattern. This makes the output simple to parse
            # since we just have to find the positions of two strings.

            # Find the start of the data output
            start: int = response.output.find("CONNECT")

            # If we didn't find the start of the data, raise an exception
            if start < 0:
                raise modem.AtError(
                    "Unable to find starting CONNECT in output from socket receive operation"
                )

            # Find the end of the data output
            end: int = response.output.rfind(Socket.EOFPattern.decode())

            # If we didn't find the end of the data, raise an exception
            if end < 0:
                raise modem.AtError(
                    "Unable to find EOF pattern in output from socket receive operation"
                )

            # Increment the start past the starting CONNECT token
            start += 9

            # Return only the contents of the received data
            return bytearray(response.output[start:end].encode())
