# jack.argv - argv parser and help printing -- part of
# jack - extract audio from a CD and MP3ify it using 3rd party software
# Copyright (C) 2002-2004  Arne Zellentin <zarne@users.sf.net>

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
import types

import jack.utils
import jack.generic

from jack.globals import *
from jack.misc import safe_int


def show_usage(cf, longhelp):
    l = []
    for i in list(cf.keys()):
        if not longhelp and 'help' not in cf[i]:
            continue
        s = ""
        if 'usage' in cf[i]:
            if not longhelp and 'vbr_only' in cf[i] and cf[i]['vbr_only'] != cf['_vbr']:
                continue
            if 'long' in cf[i]:
                s = "  --%s" % cf[i]['long']
                if 'short' in cf[i]:
                    s = s + ", -%s" % cf[i]['short']
            else:
                error("internal error in show_usage")

            x_char = " "
            l.append([s, cf[i]['usage'] + jack.utils.yes(cf[i])])
    max_len = 0
    for i in l:
        max_len = max(max_len, len(i[0]))

    l.sort()
    print("usage: jack [option]...")
    for i in l:
        jack.generic.indent(i[0] + " " * (max_len - len(i[0])), i[1])

    if longhelp:
        print("""
While Jack is running, press q or Q to quit,
    p or P to disable ripping (you need the CD drive)
    p or P (again) or c or C to resume,
    e or E to pause/continue all encoders and
    r or R to pause/continue all rippers.
""")
    else:
        print("These are the most common options. For a complete list, run jack --longhelp")


def get_next(argv, i, extra_arg=None, allow_equal=1):
    if extra_arg != None:
        return i, extra_arg
    elif allow_equal and argv[i].find("=") > 0:
        return i, argv[i].split("=", 1)[1]
    else:
        i = i + 1
        if len(argv) > i:
            return i, argv[i]
        else:
            return i, None


def istrue(x):
    return x.upper() in ["Y", "YES", "1", "TRUE"]


def parse_option(cf, argv, i, option, alt_arg, origin="argv"):
    ty = cf[option]['type']
    if ty == 'toggle':
        if alt_arg:
            return i, istrue(alt_arg)
        else:
            return i, not cf[option]['val']

    if ty == float:
        i, data = get_next(argv, i, alt_arg)
        if data != None:
            try:
                data = float(data)
                return i, data
            except:
                return None, "option `%s' needs a float argument" % option
        else:
            return None, "Option `%s' needs exactly one argument" % option

    if ty == int:
        i, data = get_next(argv, i, alt_arg)
        if data != None:
            try:
                data = int(data)
                return i, data
            except:
                return None, "option `%s' needs an integer argument" % option

            return i, safe_int(data, "option `%s' needs an integer argument" % option)
        else:
            return None, "Option `%s' needs exactly one argument" % option

    if ty == bytes or ty == str:
        i, data = get_next(argv, i, alt_arg)
        if data != None:
            return i, data
        else:
            return None, "Option `%s' needs exactly one string argument" % option

    if ty == list:
        l = []
        if origin == "argv":
            valid_short_opts = [cf[key]['short']
                                for key in list(cf.keys()) if 'short' in cf[key]]
            valid_long_opts = [cf[key]['long']
                               for key in list(cf.keys()) if 'long' in cf[key]]
            while 1:
                i, data = get_next(argv, i, alt_arg, 0)
                if data != None:
                    if data == ";":
                        break
                    # The end of a list has to be signaled with a semicolon but
                    # many users forget this; therefore, check whether the next list
                    # entry is a valid option, and if so, assume the end of the list
                    # has been reached.
                    if data.startswith("--") and data[2:].split('=', 1)[0] in valid_long_opts:
                        i -= 1
                        break
                    if data.startswith("-") and len(data) == 2 and data[1] in valid_short_opts:
                        i -= 1
                        break
                    l.append(data)
                    if alt_arg:  # only one option in --opt=val form
                        break
                else:
                    break

        elif origin == "rcfile":
            i, data = get_next(argv, i, alt_arg)
            l = eval(data)
        if l and type(l) == list:
            return i, l
        else:
            return None, "option `%s' takes a non-empty list (which may be terminated by \";\")" % option
    # default
    return None, "unknown argument type for option `%s'." % option


def parse_argv(cf, argv):
    argv_cf = {}
    allargs = {}
    for i in list(cf.keys()):
        if 'long' in cf[i]:
            if len(cf[i]['long']) < 2 or cf[i]['long'] in allargs:
                print("Hey Arne, don't bullshit me!")
                print(cf[i])
                sys.exit(1)
            else:
                allargs[cf[i]['long']] = i
        if 'short' in cf[i]:
            if len(cf[i]['short']) != 1 or cf[i]['short'] in allargs:
                print("Hey Arne, don't bullshit me!")
                print(cf[i])
                sys.exit(1)
            else:
                allargs[cf[i]['short']] = i
    i = 1
    help = 0
    while i < len(argv):
        if argv[i] in ("-h", "--help"):
            help = 1
            i = i + 1
            continue

        if argv[i] in ("--longhelp", "--long-help"):
            help = 2
            i = i + 1
            continue

        option = ""
        tmp_option = tmp_arg = None

        if argv[i].find("=") >= 2:
            tmp_option, tmp_arg = argv[i].split("=", 1)
        else:
            tmp_option = argv[i]

        if len(tmp_option) == 2 and tmp_option[0] == "-":
            o = tmp_option[1]
            if o in allargs:
                option = allargs[o]

        elif tmp_option == "--override":
            i, option = get_next(argv, i, tmp_arg)
            if option.find("=") > 0:
                option, tmp_arg = option.split("=", 1)
            if option == None:
                print("--override takes two arguments: <VARIABLE> <VALUE>")
                sys.exit(1)

        elif len(tmp_option) > 2 and tmp_option[0:2] == "--":
            o = tmp_option[2:]
            if o in allargs:
                option = allargs[o]

        if option:
            i, value = parse_option(cf, argv, i, option, tmp_arg)
            if i == None:
                error(value)
            if option not in argv_cf:
                argv_cf[option] = {}
            argv_cf[option].update({'val': value})
        else:
            print("unknown option `%s'" % argv[i])
            show_usage(cf)
            sys.exit(1)
        if not i:
            break
        i = i + 1
    return help, argv_cf
# end of parse_argv()
