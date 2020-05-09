# -*- coding: utf-8 -*-
# jack.globals: Global storage space for
# jack - extract audio from a CD and encode it using 3rd party software
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

from jack.config import cf
from jack.constants import *
from jack.generic import debug, error, expand, info, warning

# import jack.generic
# error = jack.generic.error

dummy = """
def error(x):
    jack.generic.error(x)

def debug(x):
    jack.generic.debug(x)

def info(x):
    jack.generic.info(x)

def debug(x):
    jack.generic.warning(x)
"""

# globals
revision = 0                        # initial revision of freedb data
is_submittable = 0                  # well-formed freedb-file?
