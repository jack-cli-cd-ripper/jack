# jack.ripstuff: container module for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2004  Arne Zellentin <zarne@users.sf.net>

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

import jack.freedb

import locale
import unicodedata

from jack.globals import *

all_tracks_orig = []
all_tracks_todo_sorted = []
all_tracks = []

wavs_ready = None

printable_names = None              # these are displayed for the track names
max_name_len = None                 # max len of printable_names[]

raw_space = None                    # free diskspace

# There's currently no good way in Python to obtain the real width a string
# will take up on the screen since it may e.g. depend on how the terminal
# displays wide characters.  This function is a first attempt to at least
# get an approximate idea of the width of a string (assuming that wide
# characters take up two columns on the screen).  This is only to be used
# until there's a real solution in Python.


def width(s):
    w = 0
    for c in s:
        if unicodedata.east_asian_width(c) in ("W", "F"):
            w += 2
        else:
            w += 1
    return w


def gen_printable_names(track_names, todo):
    global printable_names
    global max_name_len

    printable_names = []
    for i in range(CDDA_MAXTRACKS):
        printable_names.append("")

    if jack.freedb.names_available and cf['_show_names']:
        if cf['_various']:
            max_name_len = max(
                [len(track_names[x[NUM]][0] + " - " + track_names[x[NUM]][1]) for x in todo])
        else:
            max_name_len = max(
                [len(track_names[x[NUM]][1]) for x in todo])
        max_name_len = len("01 ") + max_name_len
        if cf['_show_time']:
            max_name_len = max_name_len + 6
    else:
        max_name_len = len("01")
        if cf['_show_time']:
            max_name_len = max_name_len + len(" 01:23")

    for i in todo:
        if cf['_show_time']:
            len_tmp = i[LEN] // CDDA_BLOCKS_PER_SECOND
            len_tmp = ("%02i:%02i") % (len_tmp // 60, len_tmp % 60)

        if jack.freedb.names_available and cf['_show_names']:
            if cf['_show_time']:
                tmp = "%02i %5s " % (i[NUM], len_tmp)
            else:
                tmp = "%02i " % i[NUM]
            if cf['_various']:
                tmp = tmp + track_names[i[NUM]][
                    0] + " - " + track_names[i[NUM]][1]
            else:
                tmp = tmp + track_names[i[NUM]][1]
            p_tmp = tmp
            printable_names[i[NUM]] = p_tmp + "." * (
                max_name_len - width(p_tmp))
        else:
            if cf['_show_time']:
                printable_names[i[NUM]] = ("%02i " % i[NUM]) + len_tmp + "." * (
                    max_name_len - len(i[NAME]) - 6)
            else:
                printable_names[i[NUM]] = i[
                    NAME] + "." * (max_name_len - len(i[NAME]))
