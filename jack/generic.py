# jack.generic: generic functions used (here) for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2002  Arne Zellentin <zarne@users.sf.net>

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

import sys
import os
import jack.version
from jack.config import cf


def indent(pre, msg, at=80, indent=0):
    msg = msg.split()
    ret = pre
    if indent:
        if len(pre) < indent:
            ret += " " * (indent - len(pre))
        tab = indent
    else:
        tab = len(pre)
    x = len(ret)
    for i in msg:
        add = 1 + len(i)
        if x + add > at:
            ret += "\n" + (" " * (tab))
            x = tab
        ret += " " + i
        x += add
    return ret


def log_to_logfile(s):
    if not hasattr(log_to_logfile, "logfile"):
        log_to_logfile.logfile = open(jack.version.name + ".debug", "a")
    log_to_logfile.logfile.write(s + "\n")


def log(pre, msg, show=True, fatal=False):
    s = indent(" *" + pre + "*", msg)
    if cf['_debug_write']:
        log_to_logfile(s)
    if fatal:
        import jack.term
        jack.term.disable()
        print(s)
        import sys
        sys.exit(1)
    if show:
        print(s)


def error(msg):
    log("error", msg, fatal=True)


def warning(msg):
    log("warning", msg)


def info(msg):
    log("info", msg)


def debug(msg):
    log("debug", msg, show=cf['_debug'])


def expand(filespec):
    return os.path.expanduser(os.path.expandvars(filespec))
