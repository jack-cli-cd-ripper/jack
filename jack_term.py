### jack_term: terminal specific stuff for
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

# terminal is one of dumb, curses

import array
import traceback
import fcntl
import sys

import jack_ripstuff
import jack_freedb

from jack_globals import *

# exported functions:
#init
#enable
#disable

# expected functions in tmod:
#update
#getkey
#sig_winch_handler

# exported variables:
enabled = None
initialized = None
size_x, size_y = None, None
orig_size_x, orig_size_y = None, None
term_type = None

# variables
xtermset = None
can_getsize = None
xtermset = None
geom_changed = None

def init(arg_type="auto", arg_xtermset = 0):
    global initialized
    global geom_changed
    global tmod
    global xtermset
    global term_type
    global size_x, size_y
    global orig_size_x, orig_size_y
    size_x, size_y = None, None
    
    if initialized:
        return

    # import the terminal specific module
    if arg_type == "auto":
        try:
            import jack_t_curses as tmod
            term_type = "curses"
        except:
            import jack_t_dumb as tmod
            term_type = "dump"
    elif arg_type == "dumb":
        import jack_t_dumb as tmod
        term_type = "dump"
    elif arg_type == "curses":
        import jack_t_curses as tmod
        term_type = "curses"

    if not tmod:
        error("invalid terminal type `%s'" % type)

    xtermset = arg_xtermset

    initialized = 1
    geom_changed = 0
    size_x, size_y = 80, 24     # fallback value

    oldsize_x, ldsize_y = None, None
    oldsize = getsize()
    if oldsize:
        orig_size_x, orig_size_y = oldsize
        size_x, size_y = oldsize
    del oldsize

def getsize():
    global can_getsize
    if can_getsize == 0:
        return None

    if can_getsize == None:
        try:
            from IOCTLS import TIOCGWINSZ
        except ImportError:
            try:
                from termios import TIOCGWINSZ
            except ImportError:
                # TIOCGWINSZ = 0x5413 # linux, ix86. Anyone else?
                can_getsize = 0
                warning("""could not find a module which exports
TIOCGWINSZ.  This means I can't determine your terminal's geometry, so please
don't resize it. Use Tools/scripts/h2py.py from the Python source distribution
to convert /usr/include/asm/ioctls.h to IOCTLS.py and install it.""")
                return None
    try:
        # to get the size, we will have to do an ioctl which will return a
        # struct winsize {
        #         unsigned short ws_row;
        #         unsigned short ws_col;
        #         unsigned short ws_xpixel;
        #         unsigned short ws_ypixel;
        # };
        # (according to _I386_TERMIOS_H, /usr/include/asm/termios.h)

        winsize = array.array("H")
        data = " " * (winsize.itemsize * 4)
        data = fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, data)
        # unpack the data, I hope this is portable:
        winsize.fromstring(data)
        new_y, new_x, xpixel, ypixel = winsize.tolist()
    except:
        can_getsize = 0
        return None
    return new_x, new_y

def enable(want_x = None, want_y = None):
    global xtermset
    global geom_changed
    global enabled

    if enabled:
        return

    if xtermset:
        import os
        if want_x == None and want_y == None:
            want_x = 80 - len("track_00") + jack_ripstuff.max_name_len
            want_y = len(jack_ripstuff.all_tracks_todo_sorted) + 3
        if type == "curses":
            want_y = want_y - 1
        if jack_freedb.names_available:
            want_y = want_y + 1
        if (self.size_x, self.size_y) != (want_x, want_y):
            try:
                os.system("xtermset -geom %dx%d" % (want_x, want_y))
                geom_changed = 1
            except:
                warning("failed to call xtermset, is it really installed?")
                xtermset = 0
    enabled = 1
    tmod.enable()

def disable():
    global enabled
    import os

    if not enabled:
        return
    tmod.disable()
    if geom_changed:
        os.system("xtermset -restore -geom %dx%d" % (oldsize_x, oldsize_y))

