"""
A Skywire NL-SW-LTE-TG1WWG modem

(C) NimbeLink Corp. 2021

All rights reserved except as explicitly granted in the license agreement
between NimbeLink Corp. and the designated licensee. No other use or disclosure
of this software is permitted. Portions of this software may be subject to third
party license terms as specified in this software, and such portions are
excluded from the preceding copyright notice of NimbeLink Corp.
"""

import serial

import nimbelink.cell.at as at
import nimbelink.cell.modem as modem
import nimbelink.cell.modem.skywire as skywire
import nimbelink.debugger as debugger

from .socket import Socket

class TG1WWG(skywire.Skywire):
    """The class for interfacing with a NL-SW-LTE-TG1WWG modem
    """

    def __init__(
        self,
        interface: at.Interface,
        kernelLog: serial.Serial = None,
        tool: debugger.Tool = None,
    ) -> None:
        """Creates a new Skywire Nano modem

        :param self:
            Self
        :param interface:
            Our AT interface
        :param kernelLog:
            A serial port for our kernel logging output
        :param tool:
            A debug tool

        :return none:
        """

        super().__init__(
            app = None,
            interface = interface,
            gpio = None,
            sim = None,
            socket = Socket(self),
        )

    def reboot(self) -> None:
        """Gracefully reboot the modem

        :param self:
            Self

        :raise AtError:
            Failed to either send reboot command or get +RESET URC

        :return none:
        """

        # Tell the modem to reboot
        try:
            self.at.sendCommand("AT#ENHRST=1,0")
        except at.Interface.CommError:
            raise modem.AtError(None, "Failed to issue reboot command")

    def shutdown(self) -> None:
        """Gracefully shut down the modem

        :param self:
            Self

        :raise AtError:
            Failed to send shutdown command or get +SHUTDOWN URC

        :return none:
        """

        # Tell the modem to shutdown
        try:
            self.at.sendCommand("AT#SHDN")
        except at.Interface.CommError:
            raise modem.AtError(None, "Failed to issue shutdown command")
