# -*- coding: iso-8859-15 -*-
### jack_plugins: plugin architecture for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 2004  Arne Zellentin <zarne@users.sf.net>

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

import sys

from jack_globals import *
import jack_helpers
import jack_freedb

def load_plugin(name, structure):
    import_statement = "from jack_%s import %s" % (name, structure)
    get_statement = "tmp = %s[name]" % structure
    exec(import_statement) in locals()
    exec(get_statement) in locals()
    return tmp

def import_freedb_servers():
    if cf['_freedb_server'].startswith("plugin_"):
        tmp = load_plugin(cf['_freedb_server'], "plugin_freedb_servers")
        jack_freedb.freedb_servers[cf['_freedb_server']] = tmp

def import_helpers():
    for i in (cf['_encoder'], cf['_ripper']):
        if i.startswith("plugin_"):
            tmp = load_plugin(i, "plugin_helpers")
            if jack_helpers.helpers.has_key(i):
                warning("plugin %s already loaded, skipping.", i)
                continue
            jack_helpers.helpers[i] = tmp
