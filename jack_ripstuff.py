### jack_ripstuff: container module for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2002  Arne Zellentin <zarne@users.sf.net>

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; either version 2 of the License, or
### (at your option) any later version.

### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.

### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import jack_freedb

from jack_globals import *

all_tracks_orig = []
all_tracks_todo_sorted = []
all_tracks = []

wavs_ready = None

printable_names = None              # these are displayed for the track names
max_name_len = None                 # max len of printable_names[]

raw_space = None                    # free diskspace

def gen_printable_names(track_names, todo):
    global printable_names
    global max_name_len

    printable_names=[]
    for i in range(CDDA_MAXTRACKS):
        printable_names.append("")

    if jack_freedb.names_available and cf['_show_names']:
        if cf['_various']:
            max_name_len = max(map(lambda x: len(track_names[x[NUM]][0] + " - " + track_names[x[NUM]][1]), todo))
        else:
            max_name_len = max(map(lambda x: len(track_names[x[NUM]][1]), todo))
        max_name_len = len("01 ") + max_name_len
        if cf['_show_time']:
            max_name_len = max_name_len + 6
    else:
        max_name_len = max(map(lambda x: len(x[NAME]), todo))

    for i in todo:
        if cf['_show_time']:
            len_tmp = i[LEN] / CDDA_BLOCKS_PER_SECOND
            len_tmp = ("%02i:%02i") % (len_tmp / 60, len_tmp % 60)

        if jack_freedb.names_available and cf['_show_names']:
            if cf['_show_time']:
                tmp = "%02i %5s " % (i[NUM], len_tmp)
            else:
                tmp = "%02i " % i[NUM]
            if cf['_various']:
                tmp = tmp + track_names[i[NUM]][0] + " - " + track_names[i[NUM]][1]
            else:
                tmp = tmp + track_names[i[NUM]][1]
            printable_names[i[NUM]] = tmp + "." * (max_name_len - len(tmp))
        else:
            if cf['_show_time']:
                printable_names[i[NUM]] = ("%02i " % i[NUM]) + len_tmp + "." * (max_name_len - len(i[NAME]) - 6)
            else:
                printable_names[i[NUM]] = i[NAME] + "." * (max_name_len - len(i[NAME]))

