"""
A Sierra Wireless 7611 modem

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

from .socket import Socket

class SRC7611(skywire.Skywire):
    """A NL-SW-LTE-SRC7611 modem
    """

    def __init__(self, interface: at.Interface) -> None:
        """Creates a new NL-SW-LTE-SRC7611 modem

        :param self:
            Self
        :param interface:
            An AT interface to use

        :return none:
        """

        super().__init__(
            app = None,
            interface = interface,
            gpio = None,
            sim = None,
            socket = Socket(self),
        )
