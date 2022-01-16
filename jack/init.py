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

import jack.discid
from jack.generic import *
from jack.globals import *

required_modules = {
    'libdiscid': {'site': 'https://pythonhosted.org/python-libdiscid/', 'distro-name': 'python3-libdiscid'},
    'mutagen': {'site': 'https://mutagen.readthedocs.io/', 'distro-name': 'python3-mutagen'},
    'pillow': {'site': 'https://pillow.readthedocs.io/', 'distro-name': 'python3-pillow'},
    'dateparser': {'site': 'https://dateparser.readthedocs.io/', 'distro-name': 'python3-dateparser'},
    'requests': {'site': 'https://docs.python-requests.org', 'distro-name': 'python3-requests'},
}

try:
    from fcntl import F_SETFL
except:
    from FCNTL import F_SETFL

try:
    from os import O_NONBLOCK
except:
    from FCNTL import O_NONBLOCK

if not jack.discid.init():
    module = 'libdiscid'
    print("Please install the %s module described at %s .\nUse your distribution package manager where it is probably called '%s'." %
        (module, required_modules[module]['site'], required_modules[module]['distro-name']))
    sys.exit(1)

try:
    import mutagen.mp3 as mp3
    import mutagen.id3 as id3
    import mutagen.flac as flac
    import mutagen.mp4 as mp4
    import mutagen.oggvorbis as oggvorbis
except:
    module = 'mutagen'
    print("Please use pip to install the %s module described at %s ,\nor your distribution package manager where it is probably called '%s'." %
        (module, required_modules[module]['site'], required_modules[module]['distro-name']))
    sys.exit(1)

try:
    import requests
except:
    module = 'requests'
    print("Please use pip to install the %s module described at %s ,\nor your distribution package manager where it is probably called '%s'." %
        (module, required_modules[module]['site'], required_modules[module]['distro-name']))
    sys.exit(1)

try:
    import dateparser
except:
    module = 'dateparser'
    print("Please use pip to install the %s module described at %s ,\nor your distribution package manager where it is probably called '%s'." %
        (module, required_modules[module]['site'], required_modules[module]['distro-name']))
    sys.exit(1)

try:
    import PIL
except:
    module = 'pillow'
    print("Please use pip to install the %s module described at %s ,\nor your distribution package manager where it is probably called '%s'." %
        (module, required_modules[module]['site'], required_modules[module]['distro-name']))
    sys.exit(1)
