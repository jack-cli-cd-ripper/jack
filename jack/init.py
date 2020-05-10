# jack.init sanity check and initialization of various modules for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 2002-2003  Arne Zellentin <zarne@users.sf.net>

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

from jack.generic import *
from jack.globals import *

try:
    from fcntl import F_SETFL
except:
    from FCNTL import F_SETFL

try:
    from os import O_NONBLOCK
except:
    from FCNTL import O_NONBLOCK

try:
    import libdiscid
except:
    print("Please install the libdiscid module available at https://pythonhosted.org/python-libdiscid/")
    sys.exit(1)

try:
    import eyed3.id3
except:
    print("Please install the eyeD3 module available from https://eyed3.readthedocs.io/")
    sys.exit(1)

try:
    import mutagen.mp3 as mp3
    import mutagen.flac as flac
    import mutagen.mp4 as mp4
    import mutagen.oggvorbis as oggvorbis
except:
    print("Please install the Mutagen module available at")
    print("https://mutagen.readthedocs.io/")
    sys.exit(1)