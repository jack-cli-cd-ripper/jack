### jack_rc: read/write config file, a module for
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

import os
import sys
import string
import types

import jack_argv

from jack_globals import *

# exported functions:
# load
# save

def read(file):
    read_rc = []

    try:
        f = open(file)
    except:
        return read_rc

    lineno = 0
    while 1:
        x = f.readline()
        if not x:
            break
        opt = val = com = None
        lineno = lineno + 1

        x = string.strip(x)
        x = string.split(x, "#", 1)
        if len(x) > 1:
            opt, com = x
        else:
            opt = x[0]
        if opt and com:
            opt = string.strip(opt)
        if opt:
            x = string.split(opt, ":", 1)
            if len(x) > 1:
                opt, val = x
            else:
                opt = x[0]
        else:
            opt = None
        read_rc.append([opt, val, com, lineno])
    return read_rc

def load(cf, file):
    file = os.path.expandvars(file)
    file = os.path.expanduser(file)
    rc = read(file)
    rc_cf = {}
    for i in rc:
        if i[0] != None:
            if cf.has_key(i[0]):
                ret, val = jack_argv.parse_option(cf, i[0:2], 0, i[0])
                if ret != None:
                    rc_cf[i[0]] = {'val': val}
                else:
                    warning(file + ":%s: " % i[3] + val)
            else:
                warning(file + ":%s: unknown option `%s'" % (i[3], i[0]))
    return rc_cf

def merge(old, new):
    old = old[:]
    new = new[:]
    append = []
    remove = []
    old.reverse()
    for i in range(len(new)):
        found = 0
        for j in range(len(old)):
            if new[i][0] and new[i][0] == old[j][0]:
                old[j][:2] = new[i][:2]
                found = 1
                break
        if not found:
            append.append(new[i][:2] + [None,])
        else:
            if new[i][2] == 'toggle':
                remove.append(old[j])
    for i in remove:
        if i[2] != None:
            x = old.index(i)
            old[x] = [None, None, old[x][2]]
        else:
            old.remove(i)
    old.reverse()
    return old + append

def write(file, rc):
    f = open(file, "w")
    for i in rc:
        if i[0]:
            f.write(i[0])
        if i[1] != None:
            f.write(":" + i[1])
        if i[2] != None:
            if i[0] or i[1]:
                f.write(" ")
            f.write("#" + i[2])
        f.write("\n")

def convert(cf):
    rc = []
    for i in cf.keys():
        if cf[i]['type'] == types.StringType:
            rc.append([i, cf[i]['val'], None])
        elif cf[i]['type'] == types.IntType:
            rc.append([i, `cf[i]['val']`, None])
        elif cf[i]['type'] == 'toggle':
            rc.append([i, None, 'toggle'])
        else:
            error("don't know how to handle " + `cf[i]['type']`)
    return rc

def save(file, cf):
    file = os.path.expandvars(file)
    file = os.path.expanduser(file)
    rc_cf = {}
    for i in cf.keys():
        if cf[i].has_key('save') and not cf[i]['save']:
            continue
        opt = cf[i]
        if opt['history'][-1][0] == "argv":
            rc_cf[i] = opt
    oldrc = read(file)
    argvrc = convert(rc_cf)
    newrc = merge(oldrc, argvrc)
    try:
        write(file + ".tmp", newrc)
    except:
        error("can't write config file")
    if os.path.exists(file):
        os.rename(file, file + "~")
    os.rename(file + ".tmp", file)
    return len(rc_cf)
