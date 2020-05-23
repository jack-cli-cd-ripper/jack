# -*- coding: utf-8 -*-
# jack.plugins: plugin architecture for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 2004  Arne Zellentin <zarne@users.sf.net>

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

from jack.globals import *
import jack.helpers
import jack.metadata


def load_plugin(name, structure):
    import_statement = "from jack_%s import %s" % (name, structure)
    get_statement = "tmp = %s[name]" % structure
    try:
        exec((import_statement), locals())
    except ImportError as e:
        error(str(e))
    try:
        exec((get_statement), locals())
    except KeyError:
        error("Plugin %s doesn't have an appropriate helper definition." % name)
    return tmp


def import_metadata_servers():
    if cf['_metadata_server'].startswith("plugin_"):
        tmp = load_plugin(cf['_metadata_server'], "plugin_metadata_servers")
        jack.metadata.metadata_servers[cf['_metadata_server']] = tmp


def import_helpers():
    for i in (cf['_encoder'], cf['_ripper']):
        if i.startswith("plugin_"):
            tmp = load_plugin(i, "plugin_helpers")
            if i in jack.helpers.helpers:
                warning("plugin %s already loaded, skipping.", i)
                continue
            jack.helpers.helpers[i] = tmp
