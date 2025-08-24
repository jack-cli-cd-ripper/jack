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

import sys
from jack.generic import *
from jack.globals import *

required_modules = {
    'libdiscid': {'site': 'https://pythonhosted.org/python-libdiscid/', 'distro-name': 'python3-libdiscid'},
    'mutagen': {'site': 'https://mutagen.readthedocs.io/', 'distro-name': 'python3-mutagen'},
    'pillow': {'site': 'https://pillow.readthedocs.io/', 'distro-name': 'python3-pillow'},
    'python-dateutil': {'site': 'https://dateutil.readthedocs.io/', 'distro-name': 'python3-dateutil'},
    'requests': {'site': 'https://docs.python-requests.org', 'distro-name': 'python3-requests'},
}

def please_install(module, use_pip=True):
    use_pip = "use pip to " if use_pip else ""
    print("Please %sinstall the %s module described at %s .\n"
          "or your distribution package manager where it is probably called '%s'." %
        (use_pip, module,
         required_modules[module]['site'], required_modules[module]['distro-name']))
    sys.exit(1)

import jack.discid
if not jack.discid.init():
    please_install('libdiscid')

try:
    import mutagen.mp3 as mp3
    import mutagen.id3 as id3
    import mutagen.flac as flac
    import mutagen.mp4 as mp4
    import mutagen.oggvorbis as oggvorbis
except ImportError:
    please_install('mutagen')

try:
    import requests
except ImportError:
    please_install('requests')

try:
    import dateutil
except ImportError:
    please_install('dateutil')

try:
    import PIL
except ImportError:
    please_install('pillow')
