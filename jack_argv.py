### jack_misc - argv parser and help printing -- part of
### jack - extract audio from a CD and MP3ify it using 3rd party software
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

import sys
import types
from jack_misc import safe_int

def show_usage(cf, long=0):
    l = []
    x_chars = {types.StringType: "*", types.IntType: "+"}
    for i in cf.keys():
        if not long and not cf[i].has_key('help'):
            continue
        s = ""
        if cf[i].has_key('usage'):
            if cf[i].has_key('short'):
                s = "  -%s" % cf[i]['short']
                if cf[i].has_key('long'):
                    s = s + ", --%s" % cf[i]['long']
            elif cf[i].has_key('long'):
                    s = "  --%s" % cf[i]['long']
            else:
                print "hm?", i, cf[i]
                sys.exit(1)

            x_char = " "
            if x_chars.has_key(cf[i]['type']):
                x_char = x_chars[cf[i]['type']]
            l.append([s, x_char + cf[i]['usage'] + " (%s)" % `cf[i]['val']`])
    max_len = 0
    for i in l:
        max_len = max(max_len, len(i[0]))
    print "usage: jack [option]..."
    print "Options marked \"*\" need a string argument; \"+\" marks integer argument."

    for i in l:
        print i[0], " " * (max_len - len(i[0])), i[1]

    if long: 
        print """    While Jack is running, press q or Q to quit,
                               p or P to disable ripping (you need the CD drive)
                               p or P (again) or c or C to resume,
                               e or E to pause/continue all encoders and
                               r or R to pause/continue all rippers.
"""
    else:
        print "These are the most commom options. For a complete list, run jack --longhelp"

def get_next(argv, i):
    i = i + 1
    if len(argv) > i:
        return i, argv[i]
    else:
        return None, None

def parse_option(cf, argv, i, option):
    ty = cf[option]['type']
    if ty == 'toggle':
        return i, not cf[option]['val']
    if ty == types.IntType:
        i, data = get_next(argv, i)
        if i:
            return i, safe_int(data, "Option `%s' needs an integer argument" % option)
        else:
            print "Option needs exactly one argument:", option
            sys.exit(1)
    if ty == types.StringType:
        i, data = get_next(argv, i)
        if i:
            return i, data
        else:
            print "Option needs exactly one argument:", option
            sys.exit(1)
    if ty == types.ListType:
        l = []
        while 1:
            i, data = get_next(argv, i)
            if i:
                if data == ";":
                    break
                l.append(data)
            else:
                break
        if l:
            return i, l
        else:
            print "Option takes a non-empty list (which may be terminated by \";\"):", option
            sys.exit(1)
    # default
    print "Unknown argument type for option `%s'." % option
    sys.exit(1)
            

def parse_argv(cf, argv):
    argv_cf = {}
    allargs = {}
    for i in cf.keys():
        if cf[i].has_key('long'):
            if len(cf[i]['long']) < 2 or allargs.has_key(cf[i]['long']):
                print "Hey Arne, don't bullshit me!"
                print cf[i]
                sys.exit(1)
            else:
               allargs[cf[i]['long']] = i
        if cf[i].has_key('short'):
            if len(cf[i]['short']) != 1 or allargs.has_key(cf[i]['short']):
                print "Hey Arne, don't bullshit me!"
                print cf[i]
                sys.exit(1)
            else:
               allargs[cf[i]['short']] = i
    i = 1
    while i < len(argv):
        if argv[i] in ("-h", "--help"):
            show_usage(cf)
            sys.exit(0)

        if argv[i] in ("--longhelp", "--long-help"):
            show_usage(cf, long=1)
            sys.exit(0)

        option = ""
        if len(argv[i]) == 2 and argv[i][0] == "-":
            o = argv[i][1]
            if allargs.has_key(o):
                option = allargs[o]

        elif argv[i] == "--override":
            i, option = get_next(argv, i)
            if not i:
                print "--override takes two arguments: <VARIABLE> <VALUE>"
                sys.exit(1)

        elif len(argv[i]) > 2 and argv[i][0:2] == "--":
            o = argv[i][2:]
            if allargs.has_key(o):
                option = allargs[o]

        if option:
            i, value = parse_option(cf, argv, i, option)
            if not argv_cf.has_key(option):
                argv_cf[option] = {}
            argv_cf[option]['val'] = value
        else:
            print "unknown option `%s'" % argv[i]
            show_usage(cf)
            sys.exit(1)
        if not i:
            break
        i = i + 1
    return argv_cf
# end of parse_argv()
