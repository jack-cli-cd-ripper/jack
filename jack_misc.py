# jack_misc - misc stuff for
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
import sys
import os

import jack_globals


def id(x):
    return x


def multi_replace(s, rules, where, filter=id, warn=0):
    "like string.replace but take list (('from0', 'to0'), ('from1', 'to1'))..."

    if warn == 2:
        do_warn = jack_globals.error
    else:
        do_warn = jack_globals.warning

    # get a list of characters we need to replace (i.e. the x from %x)
    # currently all from must be like %x (a percent sign follow by single
    # char).
    pattern = [x[0] for x in s[s.find("%"):].split("%") if x]
    for p in pattern:
        if not rules.has_key(p):
            warn and do_warn(
                "Unknown pattern %%%c is used in %s." % (p, where))
        else:
            if not rules[p]:
                warn and do_warn(
                    "%%%c is not set but used in %s." % (p, where))
            else:
                s = s.replace("%%%c" % p, filter(rules[p]))
    return s


def safe_int(number, message):
    try:
        return int(number)
    except ValueError:
        print message
        sys.exit(1)


class dict2(dict):

    def rupdate(self, d2, where):
        for i in d2.keys():
            if self.__contains__(i):
                new = self.__getitem__(i)
                if new['val'] != d2[i]['val']:
                    new.update(d2[i])
                    new['history'].append([where, new['val']])
                    dict.__setitem__(self, i, new)

    def __getitem__(self, y):
        if type(y) == types.StringType and y and y[0] == "_":
            return dict.__getitem__(self, y[1:])['val']
        else:
            return dict.__getitem__(self, y)

    def __setitem__(self, y, x):
        if type(y) == types.StringType and y and y[0] == "_":
            self[y[1:]]['val'] = x
            # return dict.__setitem__(self, y[1:])['val']
        else:
            return dict.__setitem__(self, y, x)


def loadavg():
    "extract sysload from /proc/loadavg, linux only (?)"
    try:
        f = open("/proc/loadavg", "r")
        load = float(string.split(f.readline())[0])
        return load
    except:
        return -1
