# jack_rc: read/write config file, a module for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2004  Arne Zellentin <zarne@users.sf.net>

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

import os
import sys
import string
import types

import jack_argv
import jack_version

from jack_globals import *

# exported functions:
# load
# save


def read(file):
    read_rc = []
    try:
        f = open(file)
    except (IOError, OSError):
        return read_rc
    lineno = 0
    for x in f.readlines():
        lineno += 1
        x = x.strip()
        opt = val = com = None
        if not x:
            # also return empty lines so --save will honour them
            pass
        elif x.startswith("#"):
            com = x[1:]
        else:
            x = [i.strip() for i in x.split(":", 1)]
            if len(x) < 2:
                opt = x[0]
            else:
                opt, val = x
                # check if there's a comment ridden in val
                if "#" in val:
                    quoted = []
                    for i in range(len(val)):
                        c = val[i]
                        if c in ('"', "'") and (not i or val[i - 1] != "\\"):
                            if quoted and quoted[-1] == c:
                                quoted.pop()
                            else:
                                quoted.append(c)
                        elif c == "#" and not quoted:
                            val, com = val[:i].strip(), val[i + 1:]
                            print com
                            break
        read_rc.append([opt, val, com, lineno])
    version = get_version(read_rc)
    if not version:
        warning("config file %s doesn't define jackrc-version." % file)
    elif version != jack_version.prog_rcversion:
        warning("config file %s is of unknown version %s." % (file, `version`))
    return read_rc


def get_version(rc):
    if not rc:
        return None
    if len(rc[0]) != 4:
        return None
    opt, val, com, lineno = rc[0]
    if opt == None and val == None and lineno == 1:
        vers = com.strip().split(":", 1)
        if len(vers) != 2:
            return None
        if vers[0] != "jackrc-version":
            return None
        if vers[1].isdigit():
            return int(vers[1])
    return None


def load(cf, file):
    rc = read(expand(file))
    rc_cf = {}
    for i in rc:
        if i[0] != None:
            if cf.has_key(i[0]):
                ret, val = jack_argv.parse_option(
                    cf, i[0:2], 0, i[0], None, origin="rcfile")
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
            append.append(new[i][:2] + [None, ])
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


def write(file, rc, rcfile_exists=True):
    f = open(file, "w")
    if not rcfile_exists:
        f.write("# jackrc-version:%d\n" % jack_version.prog_rcversion)

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


def write_yes(x):
    if x:
        return "yes"
    else:
        return "no"


def convert(cf):
    rc = []
    for i in cf.keys():
        if cf[i]['type'] == types.StringType:
            rc.append([i, cf[i]['val'], None])
        elif cf[i]['type'] == types.FloatType:
            rc.append([i, `cf[i]['val']`, None])
        elif cf[i]['type'] == types.IntType:
            rc.append([i, `cf[i]['val']`, None])
        elif cf[i]['type'] == 'toggle':
            rc.append([i, write_yes(cf[i]['val']), 'toggle'])
        elif cf[i]['type'] == types.ListType:
            rc.append([i, `cf[i]['val']`, None])
        else:
            error("don't know how to handle " + `cf[i]['type']`)
    return rc


def save(file, cf):
    file = expand(file)
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
    rcfile_exists = os.path.exists(file)
    try:
        write(file + ".tmp", newrc, rcfile_exists)
    except:
        error("can't write config file")
    if os.path.exists(file):
        os.rename(file, file + "~")
    os.rename(file + ".tmp", file)
    return len(rc_cf)
