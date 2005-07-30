### jack_utils: utility functions for
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

import sys
import signal
import types
import os
import stat
import string

import jack_functions
import jack_globals
import jack_misc
import jack_term

from jack_globals import *

def all_paths(p):
    "return all path leading to and including p"
    if type(p) == types.StringType:
        p = split_dirname(p)
    all = []
    x = ""
    for i in p:
        x = os.path.join(x, i)
        all.append(x)
    return all

def check_path(p1, p2):
    "check if p1 and p2 are equal or sub/supersets"
    if type(p1) == types.StringType:
        p1 = split_dirname(p1)
    if type(p2) == types.StringType:
        p2 = split_dirname(p2)
    for i in p1, p2:
        if type(i) != types.ListType:
            error("invalid type for check_path" + `i`)
    if len(p1) > len(p2):   # make sure p1 is shorter or as long as p2
        p1, p2 = p2, p1
    ok = 1
    for i in range(1, len(p1) + 1):
        if p1[-i] != p2[-i]:
            ok = 0
    return ok

def rename_path(old, new):
    "this is complicated."
    cwd = os.getcwd()
    print cwd
    cwds = split_dirname(cwd)
    if type(old) == types.StringType:
        old = split_dirname(old)
    if type(new) == types.StringType:
        new = split_dirname(new)
    for i in old, new, cwds:
        if type(i) != types.ListType:
            error("invalid type for rename_path: " + `i`)

    # weed out empty dirs (which are technically illegal on freedb but exist)
    tmp = []
    for i in new:
        if i:
            tmp.append(i)
    new = tmp
    del tmp

    for i in old:
        os.chdir(os.pardir)
    for i in new[:-1]:
        if not os.path.exists(i):
            os.mkdir(i)
        if os.path.isdir(i):
            os.chdir(i)
        else:
            error("could not create or change to " + i + " from " + os.getcwd())

    last_of_new = new[-1]
    if os.path.exists(last_of_new):
        error("destination directory already exists: " + last_of_new)
    os.rename(cwd, last_of_new)
    os.chdir(last_of_new)
                                               # now remove empty "orphan" dirs

    old_dirs = all_paths(cwds)
    old_dirs.reverse()
    for i in old_dirs[:len(old)][1:]:
        try:
            os.rmdir(i)
        except OSError:
            pass

def cmp_toc(x, y):
    "compare two track's length"
    x, y = x[LEN], y[LEN]
    if x > y: return 1
    elif x == y: return 0
    elif x < y: return -1

NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME = range(9)
def cmp_toc_cd(x, y, what=(NUM, LEN, START)):
    "compare the relevant parts of two TOCs"
    if len(x) == len(y):
        for i in range(len(x)):
            for j in what:
                if x[i][j] != y[i][j]:
                    return 0
    else:
        return 0
    return 1

def filesize(name):
    return os.stat(name)[stat.ST_SIZE]

def yes(what):
    if what.has_key('save') and what['save'] == 0:
        return ""

    if what['type'] == 'toggle':
        if what['val']:
            s = "yes"
        else:
            s = "no"
    elif what['type'] == types.StringType:
        s = "'%s'" % what['val']
    else:
        s = str(what['val'])

    s = " [%s]" % s
    if what['history'][-1][0] == "global_rc":
        s = s + "*"
    if what.has_key('doc'):
        s = s + " +"
    return s

def safe_float(number, message):
    try:
        return float(number)
    except ValueError:
        print message
        sys.exit(1)

def unusable_charmap(x):
    for i in range(len(cf['_unusable_chars'])):
        x = string.replace(x, cf['_unusable_chars'][i], cf['_replacement_chars'][i])
    return x
    
def mkdirname(names, template):
    "generate mkdir-able directory name(s)"
    dirs = template.split(os.path.sep)
        
    dirs2 = []
    for i in dirs:
        replace_list = (("%a", names[0][0].encode(cf['_charset'], "replace")),
                        ("%l", names[0][1].encode(cf['_charset'], "replace")),
                        ("%y", `cf['_id3_year']`), ("%g", cf['_id3_genre_txt']))
        x = jack_misc.multi_replace(i, replace_list, unusable_charmap)
        exec("x = x" + cf['_char_filter'])
        dirs2.append(x)
    if cf['_append_year'] and len(`cf['_id3_year']`) == 4:  # Y10K bug!
        dirs2[-1] = dirs2[-1] + jack_misc.multi_replace(cf['_append_year'], replace_list)
    name = ""
    for i in dirs2:
        name = os.path.join(name, i)
    return dirs2, name

def split_dirname(name):
    "split path in components"
    names = []
    while 1:
        base, sub = os.path.split(name)
        if not base or base == os.sep:
            names.append(os.path.join(base, sub))
            break
        names.append(sub)
        name = base
    names.reverse()
    return names

def split_path(path, num):
    "split given path in num parts"
    new_path = []
    for i in range(1, num):
        base, end = os.path.split(path)
        path = base
        new_path.append(end)
    new_path.append(base)
    new_path.reverse()

def ex_edit(file):
    editor = "/usr/bin/sensible-editor"
    if os.environ.has_key("EDITOR"):
        editor = os.environ['EDITOR']
    print "invoking your editor,", editor, "..."
    os.system(string.split(editor)[0] + " " + file)

def has_track(l, num):
    for i in range(len(l)):
        if l[i][NUM] == num:
            return i
    return -1.5

