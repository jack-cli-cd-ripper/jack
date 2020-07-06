# jack.t_curses: curses terminal functions for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2020  Arne Zellentin <zarne@users.sf.net>

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

import termios
import sys
import signal
import types

import jack.status
import jack.ripstuff
import jack.display
import jack.term
import jack.globals
import jack.version

from jack.globals import *

enabled = None

try:
    from curses import endwin, resizeterm, A_REVERSE, newwin, newpad, initscr, noecho, cbreak, echo, nocbreak, error
except ImportError:
    print("curses module not found or too old, please install it (see README)")


# screen objects
stdscr = status_pad = usage_win = None

# status pad geometry
pad_x = pad_y = pad_start_y = pad_start_x = pad_end_y = pad_end_x = None
pad_height = pad_width = None
pad_disp_start_y = pad_disp_start_x = 0

# usage win
usage_win_title = "* * * " + jack.version.name + " " + jack.version.version + " " + jack.version.copyright + " * * *"
usage_win_width = len(usage_win_title) + 4
usage_win_xoffset = max(2, (usage_win_width - 49) // 2)
usage_win_height = 7
usage_win_y = usage_win_x = 0

# reserve lines for the copyright/help box
splash_reserve = 0
if cf['_usage_win']:
    splash_reserve = usage_win_height

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
    extra_lines = 2  # top + bottom status lines
    if jack.display.discname:
        extra_lines = extra_lines + 1
    stdscr = initscr()
    enabled = 1
    jack.term.sig_winch_cache = signal.signal(signal.SIGWINCH, signal.SIG_IGN)
    # Turn off echoing of keys, and enter cbreak mode,
    # where no buffering is performed on keyboard input
    noecho()
    cbreak()

    # In keypad mode, escape sequences for special keys
    # (like the cursor keys) will be interpreted and
    # a special value like KEY_LEFT will be returned
    stdscr.keypad(1)
    stdscr.leaveok(0)

    # build the pad
    pad_height, pad_width = len(jack.ripstuff.all_tracks_todo_sorted), jack.ripstuff.max_name_len + 72
    status_pad = newpad(pad_height, pad_width)
    usage_win = newwin(usage_win_height, usage_win_width, 0, 0)
    map_track_num = {}
    for i in range(len(jack.ripstuff.all_tracks_todo_sorted)):
        map_track_num[jack.ripstuff.all_tracks_todo_sorted[i][NUM]] = i

    sig_winch_handler(None, None)


def disable():
    global enabled
    if enabled:
        # Set everything back to normal
        stdscr.keypad(0)
        echo()
        nocbreak()
        # Terminate curses, back to normal screen
        endwin()
        # re-install previous sighandler
        # signal.signal(signal.SIGWINCH, jack.term.sig_winch_cache)
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

    jack.term.resize()

    old_y, old_x = stdscr.getmaxyx()
    resizeterm(jack.term.size_y, jack.term.size_x)
    pad_y, pad_x = pad_disp_start_y, pad_disp_start_x
    pad_start_y, pad_start_x = extra_lines - 1, 0
    pad_end_y = min(extra_lines - 1 + pad_height, jack.term.size_y - 2 - splash_reserve)
    pad_end_x = min(jack.term.size_x, pad_width) - 1
    pad_missing_y = max(pad_height - (jack.term.size_y - extra_lines - splash_reserve), 0)
    pad_missing_x = max(pad_width - jack.term.size_x, 0)
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
    if extra_lines < jack.term.size_y:
        if jack.display.discname:
            stdscr.addstr(0, 0, (jack.display.center_line(jack.display.options_string + " [" + scroll_keys + "]", fill=" ", width=jack.term.size_x))[:jack.term.size_x], A_REVERSE)
            stdscr.addstr(1, 0, jack.display.center_line( jack.display.discname, fill="- ", fill_r=" -", width=jack.term.size_x)[:jack.term.size_x], A_REVERSE)
        else:
            stdscr.addstr(0, 0, (jack.display.options_string + " " * (jack.term.size_x - len(jack.display.options_string) - (0 + 4)) + scroll_keys)[:jack.term.size_x], A_REVERSE)

        if jack.display.special_line:
            spec_pos = 1
            if jack.display.discname:
                spec_pos = 2
            stdscr.addstr(spec_pos, 0, jack.display.center_line(jack.display.special_line, fill=" ", width=jack.term.size_x)[:jack.term.size_x], A_REVERSE)

        if jack.display.bottom_line:
            stdscr.addstr(jack.term.size_y - 1, 0, (jack.display.bottom_line + " " * (jack.term.size_x - len(jack.display.bottom_line) - 1))[:jack.term.size_x - 1], A_REVERSE)

        stdscr.refresh()

        usage_win_y, usage_win_x = jack.term.size_y - usage_win_height - 1, int ((jack.term.size_x - usage_win_width) // 2)
        if usage_win_y > extra_lines and usage_win_x > 0 and jack.term.size_y > extra_lines + 2 + usage_win_height and jack.term.size_x > usage_win_width:
            del usage_win
            usage_win = newwin(usage_win_height, usage_win_width, usage_win_y, usage_win_x)
            usage_win.box()
            usage_win.addstr(1, 2, usage_win_title)
            usage_win.addstr(2, usage_win_xoffset, "use cursor keys or hjkl to scroll status info")
            usage_win.addstr(3, usage_win_xoffset, "press P to disable/continue ripping,")
            usage_win.addstr(4, usage_win_xoffset, "      E to pause/continue all encoders or")
            usage_win.addstr(5, usage_win_xoffset, "      R to pause/continue all rippers.")
            usage_win.refresh()

        for i in jack.ripstuff.all_tracks_todo_sorted:
            dae_stat_upd(i[NUM], jack.status.dae_status[i[NUM]])
            enc_stat_upd(i[NUM], jack.status.enc_status[i[NUM]])

        if pad_start_y < pad_end_y:
            status_pad.refresh(pad_y, pad_x, pad_start_y, pad_start_x, pad_end_y, pad_end_x)
    signal.signal(signal.SIGWINCH, sig_winch_handler)
# / end of sig_winch_handler(sig, frame) /#


def move_pad(cmd):
    global pad_disp_start_y, pad_disp_start_x, splash_reserve
    if cmd in ("j", 'KEY_DOWN') and pad_disp_start_y < pad_height - 1:
        pad_disp_start_y = pad_disp_start_y + 1
    elif cmd in ("k", 'KEY_UP') and pad_disp_start_y > 0:
        pad_disp_start_y = pad_disp_start_y - 1
    elif cmd in ("l", 'KEY_RIGHT') and pad_disp_start_x < pad_width - 1:
        pad_disp_start_x = pad_disp_start_x + 1
    elif cmd in ("h", 'KEY_LEFT') and pad_disp_start_x > 0:
        pad_disp_start_x = pad_disp_start_x - 1
    elif cmd in ("?"):
        if splash_reserve:
            splash_reserve = 0
        else:
            splash_reserve = usage_win_height
    else:
         return False

    sig_winch_handler(None, None)
    return True


def disp_bottom_line(bottom_line):
    stdscr.addstr(jack.term.size_y - 1, 0, (bottom_line + " " * (jack.term.size_x - len(bottom_line)))[:jack.term.size_x - 1], A_REVERSE)
    if pad_start_y < pad_end_y:
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
    if 1 < jack.term.size_y:
        disp_bottom_line(bottom_line)


def enc_stat_upd(num, string):
    status_pad.addstr(map_track_num[num], jack.ripstuff.max_name_len + 40, " " + jack.status.enc_status[num])
    status_pad.clrtoeol()


def dae_stat_upd(num, string, reverse=-1):
    track = jack.ripstuff.all_tracks[num - 1]
    if reverse >= 0:
        split_point = int(6.5 + reverse / 100.0 * 32)
        front = jack.ripstuff.printable_names[num] + ": " + jack.status.dae_status[num][:6]
        middle = jack.status.dae_status[num][6:split_point]
        end = jack.status.dae_status[num][split_point:] + " " + jack.status.enc_status[num]
        try:
            status_pad.addstr(map_track_num[num], 0, front)
            status_pad.addstr(map_track_num[num], len(front), middle, A_REVERSE)
            status_pad.addstr(map_track_num[num], len(front + middle), end)
        except error:
            pass
    else:
        try:
            status_pad.addstr(map_track_num[num], 0, (jack.ripstuff.printable_names[num] + ": " + str(jack.status.dae_status[num]) + " " + str(jack.status.enc_status[num])))
        except error:
            pass

    dummy = """
    if ripper == "cdparanoia" and track in dae_tracks or (track in enc_queue and track not in mp3s_done):
        status_pad.addstr(map_track_num[num], 0, jack.ripstuff.printable_names[num] + ": " + jack.status.dae_status[num][:7])
        pos = find(jack.status.dae_status[num], ">")
        if pos < 7:
            pos = 37
        status_pad.addstr(jack.status.dae_status[num][7:pos], A_REVERSE)
        status_pad.addstr(jack.status.dae_status[num][pos:])
    else:
        status_pad.addstr(map_track_num[num], 0, jack.ripstuff.printable_names[num] + ": " + jack.status.dae_status[num] + " " + jack.status.enc_status[num])
"""

    status_pad.clrtoeol()
