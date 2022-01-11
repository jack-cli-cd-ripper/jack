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
import pprint

import jack.utils
import jack.generic

from jack.globals import *
from jack.misc import safe_int


def show_usage(cf, longhelp=False):
    print("usage: jack [option]...")

    for i in list(cf.keys()):
        if not longhelp and 'help' not in cf[i]:
            continue

        options = ""
        if (not longhelp
                and 'vbr_only' in cf[i]
                and cf[i]['vbr_only'] != cf['_vbr']):
            continue
        if 'long' in cf[i]:
            isbool = cf[i]['type'] == bool
            val = cf[i]['val']
            prefix = "--no-" if isbool and val else "--"
            options = f"  {prefix}{cf[i]['long']}"
            if 'short' in cf[i]:
                options += f", -{cf[i]['short']}"

            if 'usage' in cf[i]:
                prefix = "don't " if isbool and val else ""
                description = f"{prefix}{cf[i]['usage']}"
                if not isbool:
                    description += jack.utils.yes(cf[i])

                print(jack.generic.indent(options, description, margin=20))
            else:
                debug("no usage in " + i + ": " + str(cf[i]))

    if longhelp:
        print("""
For options that take an argument, the current default value is shown
in brackets. Some have a flag symbol appended:
    #: modified in global rc file
    $: modified in user rc file
    +: further documentation available in jack --help <option>

While Jack is running, press q or Q to quit,
    p or P to disable ripping (you need the CD drive)
    p or P (again) or c or C to resume,
    e or E to pause/continue all encoders and
    r or R to pause/continue all rippers.
""")
    else:
        print()
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
    if type(x) == bool:
        return x
    elif type(x) == str:
        return x.upper() in ("Y", "YES", "1", "TRUE")
    else:
        raise TypeError


def parse_option(cf, argv, i, option, alt_arg, origin="argv"):
    ty = cf[option]['type']
    if ty == bool:
        if alt_arg is not None:
            return i, istrue(alt_arg)
        else:
            return i, True

    elif ty == float:
        i, data = get_next(argv, i, alt_arg)
        if data != None:
            try:
                data = float(data)
                return i, data
            except:
                return None, "option `%s' needs a float argument" % option
        else:
            return None, "Option `%s' needs exactly one argument" % option

    elif ty == int:
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

    elif ty in (bytes, str):
        i, data = get_next(argv, i, alt_arg)
        if data != None:
            return i, data
        else:
            return None, "Option `%s' needs exactly one string argument" % option

    elif ty == list:
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
    else:
        # default
        return None, "unknown argument type for option `%s'." % option


def parse_argv(cf, argv):
    help_args = ("-h", "--help")
    longhelp_args = ("--longhelp", "--long-help")
    all_help_args = (*help_args, *longhelp_args)

    argv_cf = {}
    allargs = {}
    for i in list(cf.keys()):
        if 'long' in cf[i]:
            if len(cf[i]['long']) < 2 or cf[i]['long'] in allargs:
                error(f"[internal] option not long or amibiguos: {cf[i]}")
            else:
                allargs[cf[i]['long']] = i
        if 'short' in cf[i]:
            if len(cf[i]['short']) != 1 or cf[i]['short'] in allargs:
                error(f"[internal] option not short or amibiguos: {cf[i]}")
            else:
                allargs[cf[i]['short']] = i
    i = 1
    help = 0
    while i < len(argv):
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

        elif tmp_option in ("--set", "--get", *all_help_args):
            if tmp_option in help_args:
                help = 1
            if tmp_option in longhelp_args:
                help = 2

            i, var = get_next(argv, i, tmp_arg)

            if var is None:
                if tmp_option in all_help_args:
                    break
                else:
                    error(f"{tmp_option} needs an argument")

            if var.find("=") > 0:
                var, tmp_arg = option.split("=", 1)

            if var in allargs:
                var = allargs[var]
            else:
                stripped = var.lstrip("-").replace("_", "-")
                candidates = [x for x in allargs if stripped in x]
                if len(candidates) != 1:
                    error(f"unknown config option: {tmp_option}. Candidates: "
                            + repr(candidates))
                var = allargs[candidates[0]]

            cmd = f"--{cf[var]['long']}"

            if tmp_option == "--set":
                if var in cf and cf[var]['type'] == bool:
                    i, tmp_arg = get_next(argv, i, allow_equal = False)

                if var == None:
                    error("--set takes two arguments: <VARIABLE> <VALUE>")

                option = var

            elif tmp_option == "--get":
                print(cf[var]['val'])
                sys.exit(0)

            elif tmp_option in all_help_args:
                print()
                print(f"{var}:")
                pprint.pprint({k: v for k, v in cf[var].items()
                    if k not in ("doc", "usage")},
                        indent=4)
                print()
                print(f"{cmd}: {cf[var]['usage']}")
                print()
                if 'doc' in cf[var]:
                    print(cf[var]['doc'])
                    print()

                sys.exit(0)

        elif len(tmp_option) > 5 and tmp_option.startswith("--no-"):
            o = tmp_option[5:]
            if cf[allargs[o]]['type'] == bool:
                tmp_arg = not istrue(tmp_arg) if tmp_arg else False
                if o in allargs:
                    option = allargs[o]

        elif len(tmp_option) > 2 and tmp_option.startswith("--"):
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
