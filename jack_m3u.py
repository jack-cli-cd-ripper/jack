# jack_m3u: generate a m3u playlist - a module for
# jack - tag audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2003  Arne Zellentin <zarne@users.sf.net>

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


from jack_globals import *

m3u = None
wavm3u = None


def init():
    global m3u, wavm3u
    m3u = []
    wavm3u = []


def add(file):
    m3u.append(file)


def add_wav(file):
    wavm3u.append(file)
    # fixeme - not written to a file yet


def write(file="jack.m3u"):
    if m3u and cf['_write_m3u']:
        f = open(file, "w")
        for i in m3u:
            f.write(i)
            f.write("\n")
        f.close()
