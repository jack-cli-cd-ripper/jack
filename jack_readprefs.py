### jack_readprefs: read and parse preferences file for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 2002  Arne Zellentin <zarne@users.sf.net>

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

import os

prefs_file = os.path.join(os.environ['HOME'], "/.jackrc")

if path.exists(prefs_file):
    jackrc_version = "0.too old"
    jackrc_py_version = "0.unknown"
    execfile(prefs_file)
    if jackrc_version < "2.99.7":
        print "Error: Your " + path.basename(prefs_file) + " is too old. I'm sorry for the inconvenience,"
        print "but you have to re-configure jack:"
        print "  1. back up", prefs_file
        print "  2. remove", prefs_file
        print "  3. run", prog_name, "once - this will generate a new one"
        print "  4. edit", prefs_file, "- use your backup for hints."
        sys.exit(1)

    elif jackrc_version != prog_version:
        print "Warning: Your " + path.basename(prefs_file) + "'s version (" + jackrc_version + ") doesn't match this version"
        print "       : of jack (" + prog_version + ")."
        print "       : make sure that nothing important is missing! (sleeping 5s)"
        sleep(5)

    if py_version != jackrc_py_version:
        print "Warning: Your " + path.basename(prefs_file) + "'s version (" + jackrc_py_version + ") doesn't match this version"
        print "       : of python (" + py_version + ")."
        print "       : If jack doesn't work, re-install jack and related modules (sleeping 5s)"
        sleep(5)

else:
    if not environ.has_key('http_proxy'):
        print "Warning: http_proxy is not set, you may want to set it."
    print 'Info: no preferences "' + prefs_file + '" found, creating a new one...'
    f = open(prefs_file, "w")
    f.write("# preferences for " + prog_name + "-" + prog_version + "\n")
    f.write("# remove this file to get a new one filled with the defaults.\n")
    f.write("# This file is parsed as python code, it's easy to break things.\n\n")
    f.write("jackrc_version = \"" + prog_version + "\"\n")
    f.write("jackrc_py_version = \"" + py_version + "\"\n\n")
    f.write(prefs)
    f.close()
    print "    : done. now edit this file and start " + prog_name + " again."
    exit()

