# jack_CDTime - various converters between data representation - part of
# jack - extract audio from a CD and MP3ify it using 3rd party software
# Copyright (C) 1999,2000  Arne Zellentin <zarne@users.sf.net>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import string
import types

CDDA_BLOCKS_PER_SECOND = 75


def strtoblocks(str):
    "convert mm:ss:ff to blocks"
    str = string.split(str, ":")
    blocks = string.atoi(str[2])
    blocks = blocks + string.atoi(str[1]) * CDDA_BLOCKS_PER_SECOND
    blocks = blocks + string.atoi(str[0]) * 60 * CDDA_BLOCKS_PER_SECOND
    return blocks


def blockstomsf(blocks):
    "convert blocks to mm, ss, ff"
    mm = blocks / 60 / CDDA_BLOCKS_PER_SECOND
    blocks = blocks - mm * 60 * CDDA_BLOCKS_PER_SECOND
    ss = blocks / CDDA_BLOCKS_PER_SECOND
    ff = blocks % CDDA_BLOCKS_PER_SECOND
    return mm, ss, ff, blocks

B_MM, B_SS, B_FF = 0, 1, 2


def msftostr(msf):
    "convert msf format to readable string"
    return "%02i" % msf[B_MM] + ":" + "%02i" % msf[B_SS] + ":" + "%02i" % msf[B_FF]


class CDTime:

    def __init__(self, any=None):
        self.__dict__['blocks'] = 0
        self.__dict__['mm'] = 0
        self.__dict__['ss'] = 0
        self.__dict__['ff'] = 0
        self.__dict__['string'] = "00:00:00"
        if any:
            self.any = any

    def __str__(self):
        return self.string

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if name == 'string' or name == 'any':
            new_val = self.__dict__[name]
            if type(new_val) == types.StringType and len(new_val) >= 2:
                if new_val[0] == new_val[-1]:
                    if new_val[0] in ('"', "'"):
                        new_val = new_val[1:-1]
            try:
                blocks = string.atoi(new_val)
            except:
                if type(new_val) == types.StringType:
                    blocks = strtoblocks(new_val)
                elif type(new_val) == types.IntType:
                    blocks = new_val
                else:
                    raise ValueError
            self.ff = blocks
        elif name == 'blocks':
            self.__dict__['mm'] = 0
            self.__dict__['ss'] = 0
            self.ff == self.blocks
        elif name == 'ff':
            if self.ff >= CDDA_BLOCKS_PER_SECOND:
                self.ss = self.ss + self.ff / CDDA_BLOCKS_PER_SECOND
                self.__dict__['ff'] = self.ff % CDDA_BLOCKS_PER_SECOND
        elif name == 'ss':
            if self.ss >= 60:
                self.mm = self.mm + self.ss / 60
                self.__dict__['ss'] = self.ss % 60
        self.__dict__['string'] = msftostr((self.mm, self.ss, self.ff,))
        self.__dict__['blocks'] = strtoblocks(self.string)
        self.__dict__['any'] = None
