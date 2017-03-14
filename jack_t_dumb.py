### jack_t_dumb: dumb terminal functions for
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

import jack_display
import jack_status
import jack_ripstuff
from jack_globals import NUM

old_tc = None

def init():
    pass

def enable():
    global old_tc
    # set terminal attributes
    new = termios.tcgetattr(sys.stdin.fileno())
    if old_tc == None:
        old_tc = new[:]
    new[3] = new[3] & ~termios.ECHO
    new[3] = new[3] & ~termios.ICANON
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, new)
    del new

def disable():
    if not old_tc:
        return
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_tc)

def move_pad(cmd):
    pass

def getkey():
    return sys.stdin.read(1)

def sig_winch_handler(sig, frame):
    pass

def update(special_line, bottom_line):
    print
    print
    if special_line:
        print jack_display.center_line(special_line, fill = "#")
    print jack_display.options_string
    for i in jack_ripstuff.all_tracks_todo_sorted:
        print jack_ripstuff.printable_names[i[NUM]] + ": " + jack_status.dae_status[i[NUM]], jack_status.enc_status[i[NUM]]
    print bottom_line

def enc_stat_upd(num, string):
    pass

def dae_stat_upd(num, string):
    pass
