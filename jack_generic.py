### jack_generic: generic functions used (here) for
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

import string
import sys
from jack_config import cf

def indent(pre, msg):
    print pre,

    msg = string.split(msg)
    p = len(pre)
    y = p
    for i in msg:
        if len(i) + y > 78:
            print
            print " " * p,
            y = p
        print i,
        y = y + len(i) + 1
    print

def ewprint(pre, msg):
    pre = " *" + pre + "*"
    indent(pre, msg)

def error(msg):
    import jack_term
    import sys
    jack_term.disable()
    ewprint("error", msg)
    sys.exit(1)

def warning(msg):
    ewprint("warning", msg)

def info(msg):
    ewprint("info", msg)

def debug(msg):
    if cf['_debug']:
        ewprint("debug", msg)

