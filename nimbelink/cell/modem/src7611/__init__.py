"""
The Sierra Wireless 7611

(C) NimbeLink Corp. 2021

All rights reserved except as explicitly granted in the license agreement
between NimbeLink Corp. and the designated licensee. No other use or disclosure
of this software is permitted. Portions of this software may be subject to third
party license terms as specified in this software, and such portions are
excluded from the preceding copyright notice of NimbeLink Corp.
"""

from .modem import SRC7611

from .socket import Socket

__all__ = [
    "SRC7611",

    "Socket",
]
