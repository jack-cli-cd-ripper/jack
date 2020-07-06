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

from sys import version

py_version = version.split(' ')[0]

name = "jack"
version = "4.0.0"

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

author = ", ".join(x["name"] for x in authors)
copyright = "(C)2020 " + author
email = ", ".join("%s <%s>" % (x["name"], x["email"]) for x in authors)

license = "GPLv2"

url = "https://github.com/pimzand/jack"

rcversion = 31
