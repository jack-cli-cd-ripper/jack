# -*- coding: iso-8859-15 -*-
### jack_globals: Global storage space for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2003  Arne Zellentin <zarne@users.sf.net>

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

from jack_config import cf
from jack_constants import *
from jack_generic import debug, error, expand, info, warning
from jack_init import eyed3

#import jack_generic
#error = jack_generic.error

dummy="""
def error(x):
    jack_generic.error(x)

def debug(x):
    jack_generic.debug(x)

def info(x):
    jack_generic.info(x)

def debug(x):
    jack_generic.warning(x)
"""

# globals
revision = 0                        # initial revision of freedb data
is_submittable = 0                  # well-formed freedb-file?

id3genres = eyed3.id3.ID3_GENRES
