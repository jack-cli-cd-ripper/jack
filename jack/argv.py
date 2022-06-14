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

import os
import sys
import types
import pprint

import jack.utils
import jack.generic

from jack.globals import *

txt_readme_md = """# Jack

Jack is command-line CD ripper. It extracts audio from a CD, encodes it using
3rd party software and augments it with metadata from various sources.

As all CLI things, Jack is fast and efficient, and that's why we
like it.

## Recent features

* port to Python 3
* replace CDDB.py with libdiscid
* replace eyeD3 with mutagen
* add support for MusicBrainz while keeping support for freedb/gnudb
* add support for extended tagging, compatible with MusicBrainz Picard
* add support for M4A, using fdkaac and mutagen
* transcoding from lossless to lossy formats
* automatic downloading of album art from coverartarchive, iTunes and discogs
* automatic, highly configurable embedding of album art

## Requirements

* Python 3
* libdiscid, a shared library written in C
* a Python 3 wrapper for libdiscid, either python-libdiscid or python-discid
* Python 3 modules mutagen, requests, pillow and dateutil
* an encoder like oggenc (Ogg/Vorbis), flac, lame (MP3) or fdkaac (M4A/AAC)
* a ripper like cdparanoia (recommended), cdda2wav, dagrab or tosha

## Usage

jack [option]...

Options of type bool can be negated with --no-[option].
Options that take an argument get that argument from the next option,
or from the form --[option]=[argument].
Options that take a list argument take that list from the following arguments
terminated with ';', the next option or the end of the options.

| Option | Type | Default value | Description |
|--------|------|---------------|-------------|
{}

## Interaction

{}

## Authors and Copyrights

Jack is Free Libre Open Source Software distributed under the GNU General Public
License version 2, or (at your option) any later version.

The original home of the project was http://www.home.unix-ag.org/arne/jack/ and
the code was hosted in SourceForge.

Jack has first been developed by the following authors, be they praised:

* Copyright (C) 1999-2022 Arne Zellentin <zarne@users.sf.net>
* Copyright (C) 2020-2022 Pim Zandbergen <pim@zandbergen.org>
* Copyright (C) 2002-2016 Martin Michlmayr <tbm@debian.org>, Michael Banck
  <mbanck@debian.org>, for all the Debian patches

## Contributions

Pull Requests and contributions in general are welcome.
"""

txt_interaction = """While Jack is running, press q or Q to quit,
    p or P to disable ripping (you need the CD drive)
    p or P (again) or c or C to resume,
    e or E to pause/continue all encoders and
    r or R to pause/continue all rippers."""

def show_usage(cf, verbosity, searches=None):
    "show program usage for config object cf."
    "verbosity=1: short help for all items"
    "verbosity=2: long help for all items"
    "verbosity=2: export full documentation as markdown"
    "searches=list: short help for items in list or all if list is empty"

    if searches:
        cf_filter = {x for v in searches.values() for x in v}

    _, shorthelp, longhelp, exporthelp = [x == verbosity for x in range(4)]

    if longhelp or shorthelp or searches:
        print("usage: jack [option]...")

    help_md = []
    for i in list(cf.keys()):
        if searches and i not in cf_filter:
            continue

        if not searches and shorthelp and 'help' not in cf[i]:
            continue

        if exporthelp:
            help_md.append(doc_md(cf, i))
            continue

        if (not (longhelp or shorthelp)
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
                jack.generic.indent(options, description, margin=20, show=True)

                if searches and longhelp and 'doc' in cf[i]:
                    print()
                    print(cf[i]['doc'])
                    print()
            else:
                debug("no usage in " + i + ": " + str(cf[i]))

    if searches:
        if len(cf_filter) > 1:
            print()
            jack.generic.indent("", "These are the options matching "
                    f"{jack.generic.human_readable_list(searches.keys())}. "
                    "For a complete list, run jack --longhelp", show=True)

    elif longhelp:
        print("""
For options that take an argument, the current default value is shown
in brackets. Some have a flag symbol appended:
    #: modified in global rc file
    $: modified in user rc file
    +: further documentation available in jack --longhelp <option>""")
        print()
        print(txt_interaction)

    elif shorthelp:
        print()
        jack.generic.indent("", "These are the most common options. "
                "For a complete list, run jack --longhelp", show=True)

    elif exporthelp:
        out = cf['_readme']
        if os.path.exists(out) and not cf['_force']:
            error(f"{out} exists")

        help_md = [x for x in help_md if x]
        help_md = "\n".join(help_md)
        with open(out, "w") as fd:
            fd.write(txt_readme_md.format(help_md, txt_interaction))
        info(f"wrote README to {out}")


def doc_md(cf, index):
    entry = cf[index]
    if not 'usage' in entry:
        return None
    options = ([f"--{entry[x]}" for x in entry if x == "long" ]
            + [f"-{entry[x]}" for x in entry if x == "short" ])

    desc = entry['usage']
    if 'doc' in entry:
        doc = entry['doc']
        if not doc.startswith("\n"):
            desc += "<br>"
        desc += "<br>"
        desc += entry['doc'].replace('\n', '<br>')

    default = entry['history'][0][1]
    if default is None:
        default = "-"
    else:
        if entry['type'] == bool:
            default = "yes" if default else "no"
        elif entry['type'] == str:
            default = repr(default)

    line = [f"{', '.join(options)}",
            f"{entry['type'].__name__}",
            f"{default}",
            f"{desc}"]

    for i in "|*^$":
        line = [x.replace(i, "\\" + i) for x in line]
    line = " | ".join(line)
    line = f"| {line} |"

    return line


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


def opt(cf, o):
    return f"--{cf[o]['long']}"


def parse_option(cf, argv, i, option, alt_arg, origin="argv"):
    ty = cf[option]['type']
    if ty == bool:
        return i, True if alt_arg is None else istrue(alt_arg)

    if ty in (float, int, bytes, str):
        i, data = get_next(argv, i, alt_arg)
        if data is None:
            return None, (f"Option {repr(opt(cf, option))} needs "
                    "exactly one argument")
        try:
            value = ty(data)
            return i, value
        except ValueError:
            return None, (f"option {repr(opt(cf, option))} needs "
                    f"an argument of type {ty.__name__}")

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
                    # many users forget this; therefore, check whether the next
                    # list entry is a valid option, and if so, assume the end
                    # of the list has been reached.
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
    help_args = ("-h", "--help")
    longhelp_args = ("--longhelp", "--long-help")
    all_help_args = (*help_args, *longhelp_args)

    allargs = {}
    for k, v in cf.items():
        if 'long' in v:
            if len(v['long']) < 2 or v['long'] in allargs:
                error(f"[internal] option not long or amibiguos: {v}")
            else:
                allargs[v['long']] = k
                if v['type'] == bool:
                    allargs[f"no-{v['long']}"] = k

        if 'short' in v:
            if len(v['short']) != 1 or v['short'] in allargs:
                error(f"[internal] option not short or amibiguos: {v}")
            else:
                allargs[v['short']] = k

    i = 1
    help = 0
    searches = {}
    argv_cf = {}
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

        elif tmp_option in ("--set", "--get", "--show", *all_help_args):
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

            if tmp_option in all_help_args:
                stripped = var.lstrip("-").replace("_", "-")
                if stripped in allargs:  # exact match
                    searches[var] = [allargs[stripped],]
                    i = i + 1
                    continue
                else:
                    candidates = [x for x in allargs if stripped in x]
                    if candidates:
                        searches[var] = [allargs[x] for x in candidates]
                        i = i + 1
                        continue

            if var not in allargs:
                error(f"unknown config option: {var}")

            var = allargs[var]

            if tmp_option == "--set":
                if cf[var]['type'] == bool:
                    i, tmp_arg = get_next(argv, i, allow_equal = False)

                if var == None:
                    error("--set takes two arguments: <VARIABLE> <VALUE>")

                option = var

            elif tmp_option == "--get":
                print(cf[var]['val'])
                sys.exit(0)

            elif tmp_option in ("--show",):
                print(f"{var}:")
                pprint.pprint(cf[var])
                sys.exit(0)

        elif len(tmp_option) > 2 and tmp_option.startswith("--"):
            o = tmp_option[2:]
            if o in allargs:
                if o.startswith('no-') and cf[allargs[o]]['type'] == bool:
                    tmp_arg = not istrue(tmp_arg) if tmp_arg else False
                option = allargs[o]

        if option:
            i, value = parse_option(cf, argv, i, option, tmp_arg)
            if i == None:
                error(value)
            if option not in argv_cf:
                argv_cf[option] = {}
            argv_cf[option].update({'val': value})
            if option in ("readme",):
                help = 3
        else:
            print("unknown option `%s'" % argv[i])
            show_usage(cf, 1)
            sys.exit(1)
        if not i:
            break

        i = i + 1

    return help, argv_cf, searches
