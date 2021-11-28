# jack.utils: utility functions for
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
import signal
import types
import os
import stat
import re

import jack.functions
import jack.globals
import jack.misc
import jack.term
import jack.config

from jack.globals import *


def all_paths(p):
    "return all path leading to and including p"
    if type(p) == str:
        p = split_dirname(p)
    all = []
    x = ""
    for i in p:
        x = os.path.join(x, i)
        all.append(x)
    return all


def check_path(p1, p2):
    "check if p1 and p2 are equal or sub/supersets"
    if type(p1) == str:
        p1 = split_dirname(p1)
    if type(p2) == str:
        p2 = split_dirname(p2)
    for i in p1, p2:
        if type(i) != list:
            error("invalid type for check_path" + repr(i))
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
    print(cwd)
    cwds = split_dirname(cwd)
    if type(old) == str:
        old = split_dirname(old)
    if type(new) == str:
        new = split_dirname(new)
    for i in old, new, cwds:
        if type(i) != list:
            error("invalid type for rename_path: " + repr(i))

    # weed out empty dirs (which are technically illegal on metadata but exist)
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
            try:
                os.mkdir(i)
            except OSError:
                error('Cannot create directory "%s" (Filename is too long or has unusable characters)' % i)
        if os.path.isdir(i):
            os.chdir(i)
        else:
            error("could not create or change to " + i + " from " + os.getcwd())

    last_of_new = new[-1]
    if os.path.exists(last_of_new):
        error("destination directory already exists: " + os.path.join(*[cf['_base_dir']] + new))
    try:
        os.rename(cwd, last_of_new)
    except OSError:
        error('Cannot rename "%s" to "%s" (Filename is too long or has unusable characters)' % (cwd, last_of_new))
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
    if x > y:
        return 1
    elif x == y:
        return 0
    elif x < y:
        return -1


NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME = list(range(9))


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
    if 'save' in what and what['save'] == 0:
        return ""

    if what['type'] == 'toggle':
        if what['val']:
            s = "yes"
        else:
            s = "no"
    elif what['type'] == str:
        s = "'%s'" % what['val']
    else:
        s = str(what['val'])

    s = " [%s]" % s
    if what['history'][-1][0] == "global_rc":
        s = s + "*"
    if 'doc' in what:
        s = s + " +"
    return s


def safe_float(number, message):
    try:
        return float(number)
    except ValueError:
        print(message)
        sys.exit(1)


def unusable_charmap(x):
    for i in range(len(cf['_unusable_chars'])):
        uc = cf['_unusable_chars'][i]
        rc = cf['_replacement_chars'][i]
        if len(uc) > 1 and uc.startswith('/') and uc.endswith('/'):
            x = re.sub(uc[1:-1], rc, x)
        else:
            x = x.replace(uc, rc)
    return x


def mkdirname(names, template):
    "generate mkdir-able directory name(s)"
    year = genre = None
    if cf['_year']:
        year = repr(cf['_year'])
    if cf['_genre']:
        genre = cf['_genre']
    medium_position = None
    medium_count = None
    medium_title = None

    artist = names[0][0]
    album_title = names[0][1]
    if len(names[0]) >= 7:
        medium_position = names[0][4]
        medium_count = names[0][5]
        medium_title = names[0][6]

    replacelist = {" ": " ",
                   "a": artist,
                   "l": album_title,
                   "y": year,
                   "g": genre,
                   "d": str(medium_position),
                   "D": str(medium_count),
                   "t": medium_title}

    if medium_count and medium_count != 1:
        if int(medium_count) > 1:
            if medium_title and medium_title != album_title:
                template = cf['_dir_titled_cd_template']
            else:
                template = cf['_dir_multi_cd_template']
        else:
            if medium_title and medium_title != album_title:
                template = cf['_dir_titled_cd_unknown_number_template']
            else:
                template = cf['_dir_multi_cd_unknown_number_template']

    cf['_dir_template'] = template

    # Process substitution patterns from dir_template
    subst = template.split(os.path.sep)
    dirs = []
    for i in subst:
        x = jack.misc.multi_replace(i, replacelist, "dir_template", unusable_charmap, warn=2)
        exec("x = x" + cf['_char_filter'])
        dirs.append(x)
    if cf['_append_year'] and year:
        dirs[-1] += jack.misc.multi_replace(cf['_append_year'], replacelist, "append-year", warn=1)
    return dirs, os.path.join(*dirs)


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


def in_path(file):
    "check if a file is an executable in PATH"
    for path in os.environ.get("PATH", "").split(os.path.pathsep):
        p = os.path.join(path, file)
        if (os.path.isfile(p) and os.access(p, os.X_OK)):
            return True
    return False


def ex_edit(file):
    editor = "/usr/bin/sensible-editor"
    if "EDITOR" in os.environ:
        editor = os.environ['EDITOR']
    print("invoking your editor,", editor, "...")
    os.system(((editor)[0] + " " + file).split())


def has_track(l, num):
    for i in range(len(l)):
        if l[i][NUM] == num:
            return i
    return -1.5
