# jack.version: define program version and name for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 2002  Arne Zellentin <zarne@users.sf.net>

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

import glob
import os
import sys


authors = [
        {
            "name": "Arne Zellentin",
            "email": "zarne@users.sf.net"
            },
        {
            "name": "Pim Zandbergen",
            "email": "pim@zandbergen.org",
            },
        ]

name = __name__

try:
    import importlib.metadata
    version = importlib.metadata.version(name)
except importlib.metadata.PackageNotFoundError:
    try:
        import setuptools_scm
        version = setuptools_scm.get_version(root='..', relative_to=__file__)
    except (LookupError, ModuleNotFoundError):
        version = "4.x"

py_version = sys.version.split(' ')[0]
author = ", ".join(x["name"] for x in authors)
copyright = "(C)2021 " + author
email = ", ".join("%s <%s>" % (x["name"], x["email"]) for x in authors)
license = "GPLv2"
url = "https://github.com/jack-cli-cd-ripper/jack"
rcversion = 31
