### jack_misc - misc stuff for
### jack - extract audio from a CD and MP3ify it using 3rd party software
### Copyright (C) 1999,2000  Arne Zellentin <zarne@users.sf.net>

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

import string, types
import sys
import os

def multi_replace(s, rules):
    "like string.replace but take list (('from0', 'to0'), ('from1', 'to1'))..."
    # currently all from must be like %x (a percent sign follow by single char.
    res = ""
    maybe = 0
    for i in s:
        if maybe:
            maybe = 0
            found = 0
            for j in rules:
                if ("%" + i) == j[0]:
                    res = res[:-1] + j[1]
                    found = 1
            if found:
                continue
        maybe = 0
        if i == "%":
            maybe = 1
        res = res + i
    return res

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
            #return dict.__setitem__(self, y[1:])['val']
        else:
            return dict.__setitem__(self, y, x)

def loadavg():
    "extract sysload from /proc/loadavg, linux only (?)"
    if os.uname()[0] == "Linux":
        f = open("/proc/loadavg", "r")
        load = float(string.split(f.readline())[0])
        return load
    else:
        return -1
