### jack_display: screen presentation module for
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

import termios
import sys
import os
import signal

import jack_ripstuff
import jack_term
import jack_children
import jack_freedb
import jack_functions
import jack_globals
import jack_tag

from jack_globals import *

global_total = None
options_string = None
special_line = None
bottom_line = None
discname = None

# terminal attributes
old_tc = None

smile = " :-)"

def init():
    global global_total
    global options_string
    global discname
    global old_tc

    global_total = jack_functions.tracksize(jack_ripstuff.all_tracks_todo_sorted)[jack_functions.BLOCKS]

    options_string = "Options:" \
        + (" bitrate=%i" % cf['_bitrate']) * (not cf['_vbr']) + " vbr" * cf['_vbr'] \
        + " reorder" * cf['_reorder'] \
        + " read-ahead=" + `cf['_read_ahead']` \
        + " keep-wavs" * cf['_keep_wavs'] \
        + " id=" + jack_freedb.freedb_id(jack_ripstuff.all_tracks) \
        + (" len=%02i:%02i" % (global_total / jack_globals.CDDA_BLOCKS_PER_SECOND \
            / 60, global_total / jack_globals.CDDA_BLOCKS_PER_SECOND % 60)) \
        + " | press Q to quit"
    jack_term.tmod.extra_lines = 2
    if jack_freedb.names_available:
        jack_term.tmod.extra_lines = jack_term.tmod.extra_lines + 1
        if jack_term.term_type == "curses":
            discname = jack_tag.track_names[0][0] + " - " + jack_tag.track_names[0][1]
        else:
            options_string = center_line(jack_tag.track_names[0][0] + " - " + jack_tag.track_names[0][1], fill = "- ", fill_r = " -", width = jack_term.size_x) + "\n" + center_line(options_string, fill = " ", fill_r = " ", width = jack_term.size_x)

def sig_handler(sig, frame):
    "signal handler and general cleanup procedure"
    if frame < 0:
        exit_code = frame
    else:
        exit_code = 0

    jack_term.disable()

    if sig:
        exit_code = 2
        info("signal %d caught, exiting." % sig)

    for i in jack_children.children:
        exit_code = 1
        if not cf['_silent_mode']:
            info("killing %s (pid %d)" % (i['type'], i['pid']))
        os.kill(i['pid'], signal.SIGTERM)
        i['file'].close()

    if exit_code and cf['_silent_mode']:
        progress("all", "err", "abnormal exit (code %i), check %s and %s" % (exit_code, err_file, out_file))

    if cf['_wait_on_quit']:
        raw_input("press ENTER to exit")

    sys.exit(exit_code)

#/ end of sig_handler /#

def center_line(str, fill = " ", fill_sep = " ", fill_r = "", width = 80):
    "return str centered, filled with fill chars"
    width = jack_term.size_x
    free = width - len(str)
    if free >= 2:
        if not fill_r:
            fill_r = fill
        length = len(fill)
        left = free / 2
        right = free / 2 + (free % 2)
        left_c = fill * (left / length) + fill_sep * (left % length)
        right_c = fill_sep * (right % length) + fill_r * (right / length)
        return left_c + str + right_c
    else:
        return str

def exit(why = 0):
    "call my own cleanum fkt. and exit"
    if why:
        why = 0 - why
    sig_handler(0, why)

