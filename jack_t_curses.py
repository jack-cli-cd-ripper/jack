### jack_t_curses: dumb terminal functions for
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
import signal
import types

import jack_status
import jack_ripstuff
import jack_display
import jack_term
import jack_globals
import jack_version

from jack_globals import *

had_special = None
enabled = None

try:
    from jack_curses import endwin, resizeterm, A_REVERSE, newwin, newpad, initscr, noecho, cbreak, echo, nocbreak
except ImportError:
    warning("jack_curses module not found, trying normal curses...")
    try:
        from curses import endwin, A_REVERSE, newwin, newpad, initscr, noecho, cbreak, echo, nocbreak
        def resizeterm(y, x):
            pass
    except ImportError:
        print "curses module not found or too old, please install it (see README)"


# screen objects
stdscr = status_pad = usage_win = None  # screen objects

# status pad geometry
pad_x = pad_y = pad_start_y = pad_start_x = pad_end_y = pad_end_x = None
pad_height = pad_width = None
pad_disp_start_y = pad_disp_start_x = 0

# usage win geometry
usage_win_y = usage_win_x = 0
usage_win_height, usage_win_width = 7, 49

curses_sighandler = None
map_track_num = None        # list track number -> line number
extra_lines = None
had_special = None

def enable():
    # Initialize curses
    global stdscr
    global status_pad
    global usage_win
    global curses_sighandler
    global map_track_num
    global enabled
    global pad_height, pad_width
    global had_special
    global extra_lines

    if enabled:
        return

    had_special = 0
    extra_lines = 2
    if jack_display.discname:
        extra_lines = extra_lines + 1
    stdscr = initscr()
    enabled = 1
    jack_term.sig_winch_cache = signal.signal(signal.SIGWINCH, signal.SIG_IGN)
    # Turn off echoing of keys, and enter cbreak mode,
    # where no buffering is performed on keyboard input
    noecho() ; cbreak()

    # In keypad mode, escape sequences for special keys
    # (like the cursor keys) will be interpreted and
    # a special value like KEY_LEFT will be returned
    stdscr.keypad(1)
    stdscr.leaveok(0)

    # build the pad
    pad_height, pad_width = len(jack_ripstuff.all_tracks_todo_sorted), jack_term.size_x
    status_pad = newpad(pad_height, pad_width)
    usage_win = newwin(usage_win_height, usage_win_width, 0, 0)
    map_track_num = {}
    for i in range(len(jack_ripstuff.all_tracks_todo_sorted)):
        map_track_num[jack_ripstuff.all_tracks_todo_sorted[i][NUM]] = i

    sig_winch_handler(None, None)

def disable():
    global enabled
    if enabled:
        # Set everything back to normal
        stdscr.keypad(0)
        echo() ; nocbreak()
        # Terminate curses, back to normal screen
        endwin()
        # re-install previous sighandler
        #signal.signal(signal.SIGWINCH, jack_term.sig_winch_cache)
        signal.signal(signal.SIGWINCH, signal.SIG_IGN)
        enabled = 0

def sig_winch_handler(sig, frame):
    global staus_pad, stdscr, usage_win
    global pad_y, pad_x, pad_start_y, pad_start_x, pad_end_y, pad_end_x
    global usage_win_y, usage_win_x

    if not enabled:
        return

    signal.signal(signal.SIGWINCH, signal.SIG_IGN)
    if type(curses_sighandler) == types.FunctionType:
        curses_sighandler(sig, frame)

    jack_term.resize()

    old_y, old_x = stdscr.getmaxyx()
    resizeterm(jack_term.size_y, jack_term.size_x)
    pad_y, pad_x = pad_disp_start_y, pad_disp_start_x
    pad_start_y, pad_start_x = extra_lines - 1, 0
    pad_end_y, pad_end_x = min(extra_lines - 1 + pad_height, jack_term.size_x - 2), min(jack_term.size_x, pad_width) - 1
    pad_missing_y = max(pad_height - (jack_term.size_y - extra_lines), 0)
    pad_missing_x = max(pad_width - jack_term.size_x, 0)
    if pad_missing_y >= pad_height:
        pad_start_y = 0
    stdscr.clear()
    status_pad.clear()
    scroll_keys = ""
    if pad_disp_start_x:
        scroll_keys = scroll_keys + "h"
    else:
        scroll_keys = scroll_keys + " "
    if pad_missing_y and not pad_disp_start_y > pad_missing_y - 1:
        scroll_keys = scroll_keys + "j"
    else:
        scroll_keys = scroll_keys + " "
    if pad_disp_start_y:
        scroll_keys = scroll_keys + "k"
    else:
        scroll_keys = scroll_keys + " "
    if pad_missing_x and not pad_disp_start_x > pad_missing_x - 1:
        scroll_keys = scroll_keys + "l"
    else:
        scroll_keys = scroll_keys + " "
    if extra_lines < jack_term.size_y:
        if jack_display.discname:
            stdscr.addstr(0, 0, (jack_display.center_line(jack_display.options_string + " [" + scroll_keys + "]", fill = " ", width = jack_term.size_x))[:jack_term.size_x], A_REVERSE)
            stdscr.addstr(1, 0, jack_display.center_line(jack_display.discname, fill = "- ", fill_r = " -", width = jack_term.size_x)[:jack_term.size_x], A_REVERSE)
        else:
            stdscr.addstr(0, 0, (jack_display.options_string + " " * (jack_term.size_x - len(jack_display.options_string) - (0 + 4)) + scroll_keys)[:jack_term.size_x], A_REVERSE)

        if jack_display.special_line:
            stdscr.addstr(2, 0, jack_display.center_line(jack_display.special_line, fill = " ", width = jack_term.size_x)[:jack_term.size_x], A_REVERSE)

        if jack_display.bottom_line:
            stdscr.addstr(jack_term.size_y - 1, 0, (jack_display.bottom_line + " " * (jack_term.size_x - len(jack_display.bottom_line) - 1 ))[:jack_term.size_x - 1], A_REVERSE)

        stdscr.refresh()

        usage_win_y, usage_win_x = jack_term.size_y - usage_win_height - 2, (jack_term.size_x - usage_win_width) / 2
        if usage_win_y > extra_lines and usage_win_x > 0 and jack_term.size_y > extra_lines + 2 + usage_win_height and jack_term.size_x > usage_win_width:
            del usage_win
            usage_win = newwin(usage_win_height, usage_win_width, usage_win_y, usage_win_x)
            usage_win.box()
            usage_win.addstr(1, 2, "* * * " + jack_version.prog_name + " " + jack_version.prog_version + " (C)2002 Arne Zellentin * * *")
            usage_win.addstr(2, 2, "use cursor keys or hjkl to scroll status info")
            usage_win.addstr(3, 2, "press P to disable/continue ripping,")
            usage_win.addstr(4, 2, "      E to pause/continue all encoders or")
            usage_win.addstr(5, 2, "      R to pause/continue all rippers.")
            usage_win.refresh()

        for i in jack_ripstuff.all_tracks_todo_sorted:
            dae_stat_upd(i[NUM], jack_status.dae_status[i[NUM]])
            enc_stat_upd(i[NUM], jack_status.enc_status[i[NUM]])

        status_pad.refresh(pad_y, pad_x, pad_start_y, pad_start_x, pad_end_y, pad_end_x)
    signal.signal(signal.SIGWINCH, sig_winch_handler)
#/ end of sig_winch_handler(sig, frame) /#

def move_pad(cmd):
    global pad_disp_start_y, pad_disp_start_x
    if cmd in ("j", 'KEY_DOWN') and pad_disp_start_y < pad_height - 1:
        pad_disp_start_y = pad_disp_start_y + 1
    elif cmd in ("k", 'KEY_UP') and pad_disp_start_y > 0:
        pad_disp_start_y = pad_disp_start_y - 1
    elif cmd in ("l", 'KEY_RIGHT') and pad_disp_start_x < pad_width - 1:
        pad_disp_start_x = pad_disp_start_x + 1
    elif cmd in ("h", 'KEY_LEFT') and pad_disp_start_x > 0:
        pad_disp_start_x = pad_disp_start_x - 1
    sig_winch_handler(None, None)

def disp_bottom_line(bottom_line):
    stdscr.addstr(jack_term.size_y - 1, 0, (bottom_line + " " * (jack_term.size_x - len(bottom_line)))[:jack_term.size_x - 1], A_REVERSE)
    status_pad.refresh(pad_y, pad_x, pad_start_y, pad_start_x, pad_end_y, pad_end_x)
    stdscr.refresh()

def getkey():
    return stdscr.getkey()

def update(special_line, bottom_line):
    global had_special
    global extra_lines

    if special_line and not had_special:
        had_special = 1
        extra_lines = extra_lines + 1
        sig_winch_handler(None, None)
    elif had_special and not special_line:
        had_special = 0
        extra_lines = extra_lines - 1
        sig_winch_handler(None, None)
    if 1 < jack_term.size_y:
        disp_bottom_line(bottom_line)

def enc_stat_upd(num, string):
    status_pad.addstr(map_track_num[num], jack_ripstuff.max_name_len + 40, " " + jack_status.enc_status[num])
    status_pad.clrtoeol()

def dae_stat_upd(num, string):
    track = jack_ripstuff.all_tracks[num-1]
    status_pad.addstr(map_track_num[num], 0, (jack_ripstuff.printable_names[num] + ": " + jack_status.dae_status[num] + " " + jack_status.enc_status[num])[:jack_term.size_x - 1])
    dummy = """
    if ripper == "cdparanoia" and track in dae_tracks or (track in enc_queue and track not in mp3s_done):
        status_pad.addstr(map_track_num[num], 0, jack_ripstuff.printable_names[num] + ": " + jack_status.dae_status[num][:7])
        pos = find(jack_status.dae_status[num], ">")
        if pos < 7:
            pos = 37
        status_pad.addstr(jack_status.dae_status[num][7:pos], A_REVERSE)
        status_pad.addstr(jack_status.dae_status[num][pos:])
    else:
        status_pad.addstr(map_track_num[num], 0, jack_ripstuff.printable_names[num] + ": " + jack_status.dae_status[num] + " " + jack_status.enc_status[num])
"""
    status_pad.clrtoeol()
