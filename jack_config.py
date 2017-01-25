# -*- coding: iso-8859-15 -*-
### jack_config.py: default config settings for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 2002-2004  Arne Zellentin <zarne@users.sf.net>

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

import types
import os
import string
import jack_misc
import locale
import sys

import jack_version
from jack_globals import *

# this must be filled manually (done in main)

# we need a working locale
try:
    locale.getpreferredencoding()
except locale.Error, e:
    print "Locale problem:", e
    sys.exit(1)

# config space with attributes

cf = jack_misc.dict2({
    ### prefs ###
    'debug': {
        'type': 'toggle',
        'val': 0,
        'help': 1,
        'usage': "show debug information",
        'long': 'AUTO',
        },
    'debug_write': {
        'type': 'toggle',
        'val': 0,
        #'usage': "write debug information to a file",
        'long': 'AUTO',
        },
    'plugin_path': {
        'type': types.ListType,
        'val': ["~/.jack_plugins",],
        'usage': "directories in which jack plugins are searched for",
        'long': 'AUTO',
        },
    'ripper': {
        'type': types.StringType,
        'val': "cdparanoia",
        'doc': "use which program to rip: cdparanoia, tosha, cdda2wav, dagrab (untested)",
        'usage': "which program to use for extracting the audio data",
        'long': 'AUTO',
        },
    'cd_device': {
        'type': types.StringType,
        'val': "/dev/cdrom",
        'usage': "use which device for ripping",
        'long': 'device',
        },
    'encoder': {
        'type': types.StringType,
        'val': "oggenc",
        'doc': "this is a symbolic name (see helpers), NOT the executable's name",
        'usage': "use which encoder",
        'short': 'E',
        'long': 'encoder-name',
        },
    'vbr': {
        'type': 'toggle',
        'val': 1,
        'help': 1,
        'doc': "use variable bitrate for encoders which support it",
        'usage': "generate variable bitrate files",
        'short': 'v',
        'long': 'AUTO',
        },
    'vbr_quality': {
        'type': types.FloatType,
        'val': 6,
        'help': 1,
        'vbr_only': 1, # only show in --help if vbr is on
        'usage': "vbr encoding quality. -1 is lowest, 10 highest.",
        'long': 'quality',
        },
    'bitrate': {
        'type': types.IntType,
        'val': 160,
        'help': 1,
        'vbr_only': 0,
        'doc': "default bitrate",
        'usage': "target bitrate in kbit/s",
        'short': 'b',
        'long': 'AUTO',
        },
    'freedb_server': {
        'type': types.StringType,
        'val': "freedb",
        'doc': "your freedb server, see freedb_servers",
        'usage': "use which freedb server",
        'long': 'server',
        },
    'disable_http_proxy': {
        'type': 'toggle',
        'val': 0,
        'usage': "XXX todo!!! disable default proxy (environment variable \"http_proxy\") for freedb queries",
        'long': 'AUTO',
        },
    'my_mail': {
        'type': types.StringType,
        'val': "@",
        'usage': "your e-mail address, needed for freedb submissions",
        'long': 'AUTO',
        },
    'rename_fmt': {
        'type': types.StringType,
        'val': "%a - %l - %n - %t",
        'usage': "format of normal files",
        'long': 'AUTO',
        'doc': """specify how the resulting files are named:
    %n: track number
    %a: artist
    %t: track title
    %l: album title
    %y: album release year - individual track years are unsupported
    %g: album genre - individual track genres are unsupported""",
        },
    'rename_fmt_va': {
        'type': types.StringType,
        'val': "%l - %n - %a - %t",
        'usage': "format of Various Artists files",
        'long': 'AUTO',
        'doc': """specify how the resulting files are named:
    %n: track number
    %a: artist
    %t: track title
    %l: album title
    %y: album release year - individual track years are unsupported
    %g: album genre - individual track genres are unsupported""",
        },
    'rename_num': {
        'type': types.StringType,
        'val': "%02d",
        'long': 'AUTO',
        'usage': "track number format for %n, printf() style",
        },
    'rename_dir': {
        'type': 'toggle',
        'val': 1,
        'usage': "rename directory as well",
        'long': 'AUTO',
        },
    'append_year': {
        'type': types.StringType,
        'val': "",
        'usage': "append this string to the directory name",
        'long': 'AUTO',
        },
    'dir_template': {
        'type': types.StringType,
        'val': "%a/%l",
        'usage': "if directories are renamed, this is the format used",
        'doc': """specify how the resulting files are named:
    %a: artist
    %l: album title
    %g: album genre - individual track genres are unsupported""",
        'long': 'AUTO',
        },
    'char_filter': {
        'type': types.StringType,
        'val': "",
        'usage': "convert file names using a python method",
        'doc': r"""an example which converts to lowercase, even with non-ascii charsets: ".lower()" """,
        'long': 'AUTO',
        },
    'charset': {
        'type': types.StringType,
        'val': locale.getpreferredencoding(),
        'usage': 'charset of filenames',
        'doc': "examples: latin-1, utf-8, ...",
        'long': 'AUTO',
        },
    'unusable_chars': {
        'type': types.ListType,
        'val': ["/", "\r"],
        'usage': "characters which can't be used in filenames",
        'doc': """
put chars which can't be used in filenames here and their replacements
in replacement_chars.

example 1: replace all " " by "_":
unusable_chars = " "
replacement_chars = "_"

example 2: replace umlauts by an alternate representation and kill some
            special characters:
unusable_chars = "äöüÄÖÜß?*^()[]{}"
replacement_chars = ["ae", "oe", "ue", "Ae", "Oe", "Ue", "ss", ""]""",
        'long': 'AUTO',
        },
    'replacement_chars': {
        'type': types.ListType,
        'val': ["%", ""],
        'doc': "this is stretched to match unusable_chars' length using the last char as fill",
        'usage': "unusable chars are replaced by the corresponding list item",
        'long': 'AUTO',
        },
    'show_time': {
        'type': 'toggle',
        'val': 1,
        'doc': "Display the track length in the status screen",
        },
    'show_names': {
        'type': 'toggle',
        'val': 1,
        'doc': "XXX todo: auto id enough term width -- display freedb track names instead if \"track_01\", ... This will not fit in a 80x24 terminal.",
        },
    'scan_dirs': {
        'type': types.IntType,
        'val': 2,
        'usage': "scan in cwd n dir levels deep, e.g. 0 to disable",
        'long': 'AUTO',
        },
    'searchdirs': {
        'type': types.ListType,
        'val': [os.curdir],
        'usage': "search which directories",
        'long': 'search',
        },
    'base_dir': {
        'type': types.StringType,
        'val': os.curdir,
        'usage': "where to create directories and put the files",
        'long': 'workdir',
        'short': 'w',
        },
    'update_interval': {
        'type': types.FloatType,
        'val': 1.0,
        'doc': "update status screen every ... seconds",
        },
    'max_load': {
        'type': types.FloatType,
        'val': 10.0,
        'usage': "only start new encoders if load < max_load",
        'long': 'AUTO',
        },
    'xtermset_enable': {
        'type': 'toggle',
        'val': 0,
        'doc': "leave disabled if you don't have xtermset installed",
        },
    'restore_xterm_width': {
        'type': 'toggle',
        'val': 0,
        'doc': "XXX not implemented yet! reset xterm width when exiting",
        },
    'terminal': {
        'type': types.StringType,
        'val': "auto",
        'doc': "use what kind of terminal",
        },
    'default_width': {
        'type': types.IntType,
        'val': 80,
        'doc': "XXX unused! your xterm's width (autodetected with curses)",
        },
    'default_height': {
        'type': types.IntType,
        'val': 24,
        'doc': "XXX unused! your xterm's height (autodetected with curses)",
        },
    'usage_win': {
        'type': 'toggle',
        'val': 1,
        'usage': "show the help screen while running",
        'long': "AUTO",
        },
    'keep_free': {
        'type': types.IntType,
        'val': 5*2**20,
        'doc': "suspend if less than keep_free bytes are free. Don't set this to zero as encoded file size prediction is always a bit below actual sizes => we might need some extra space.",
        },
    'encoders': {
        'type': types.IntType,
        'val': 1,
        'usage': "encode how many files in parallel",
        'short': 'e',
        'long': 'AUTO',
        },
    'otf': {
        'type': 'toggle',
        'val': 0,
        'usage': "on-the-fly encoding *experimental*",
        'long': 'AUTO',
        },
    'create_dirs': {
        'type': 'toggle',
        'val': 1,
        'usage': "create subdir for files",
        'short': 'D',
        'long': 'AUTO',
        },
    'reorder': {
        'type': 'toggle',
        'val': 0,
        'usage': "reorder tracks to save space while encoding",
        'short': 'r',
        'long': 'AUTO',
        },
    'keep_wavs': {
        'type': 'toggle',
        'val': 0,
        'usage': "do not delete WAVs after encoding them",
        'short': 'k',
        'long': 'AUTO',
        },
    'only_dae': {
        'type': 'toggle',
        'val': 0,
        'usage': "only produce WAVs, implies --keep_wavs",
        'short': 'O',
        'long': 'AUTO',
        },
    'read_ahead': {
        'type': types.IntType,
        'val': 99,
        'usage': "read how many WAVs in advance",
        'short': 'a',
        'long': 'AUTO',
        },
    'nice_value': {
        'type': types.IntType,
        'val': 12,
        'usage': "nice-level of encoders",
        'short': 'n',
        'long': 'nice',
        },
    'overwrite': {
        'type': 'toggle',
        'val': 0,
        'usage': "overwrite existing files",
        'short': 'o',
        'long': 'AUTO',
        },
    'remove_files': {
        'type': 'toggle',
        'val': 0,
        'usage': "remove jack.* file when done",
        'long': 'AUTO',
        },
    'silent_mode': {
        'type': 'toggle',
        'val': 0,
        'usage': "be quiet (no screen output)",
        'long': 'AUTO',
        },
    'exec_when_done': {
        'type': 'toggle',
        'val': 0,
        'usage': "run predefined command when finished",
        'long': 'exec',
        'short': 'x',
        },
    'exec_rip_done': {
        'type': types.StringType,
        'val': "eject /dev/cdrom",
        'doc': "example: eject the CD when ripping is finished",
        },
    'exec_no_err': {
        'type': types.StringType,
        'val': "play /usr/local/audio/allok.wav",
        'doc': "example: play sound when finished",
        },
    'exec_err': {
        'type': types.StringType,
        'val': "play /usr/local/audio/error.wav",
        'doc': "example: this is played when an error occured",
        },
    'freedb_dir': {
        'type': types.StringType,
        'val': "",
        'doc': "change this to something like \"/var/spool/freedb\" and all queries will be done in this (local) directory; failed local queries will be done via network",
        },
    'freedb_pedantic': {
        'type': 'toggle',
        'val': 0,
        'doc': "don't be pedantic when parsing freedb data, e.g. the ambigous (various artists) TTITLE \"The Artist - Track a Title - Cool Remix\" is split at the first possible separator.",
        },
    ### prefs0 ###
    'force': {
        'type': 'toggle',
        'val': 0,
        'usage': "don't ask.",
        'long': 'AUTO',
        },
    'recheck_space': {
        'type': 'toggle',
        'val': 1,
        'doc': "yes we want to react to disk space dropping.",
        },
    'swap_byteorder': {
        'type': 'toggle',
        'val': 1,
        'usage': "swap byteorder when reading from image",
        'long': 'swab',
        'short': 'S',
        },
    'todo_exit': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "print what would be done and exit",
        'long': 'todo',
        },
    'space_from_argv': {
        'type': types.IntType,
        'val': 0,
        'usage': "force usable disk space, in bytes",
        'long': 'space',
        'short': 's',
        },
    'check_toc': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "compare toc-file and cd-toc, then exit",
        'long': 'AUTO',
        },
    'undo_rename': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "undo the last file renaming and exit",
        'long': 'AUTO',
        'short': 'u',
        },
    'dont_work': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "don't do DAE, encoding, renaming or tagging",
        'long': 'AUTO',
        'short': 'd',
        },
    'update_freedb': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "update the freedb info and exit",
        'long': 'AUTO',
        'short': 'U',
        },
    'sloppy': {
        'type': 'toggle',
        'val': 0,
        'doc': "XXX",
        'long': 'I-swear-I\'ll-never-give-these-files-to-anyone,-including-hot-babes-TM',
        },
    'tracks': {
        'type': types.StringType,
        'val': "",
        'save': 0,
        'usage': "which tracks to process (e.g. 1, 3, 5-9, 12-)",
        'long': 'tracks',
        'short': 't',
        },
    'name': {
        'type': types.StringType,
        'val': "track_%02d",
        'doc': "filename template (before renaming)",
        },
    'rippers': {
        'type': types.IntType,
        'val': 1,
        'doc': "not implemented: rip in parallel",
        },
    'toc_prog': {
        'type': types.StringType,
        'val': "CDDB.py",
        'doc': "use which helper program to read cd's toc",
        },
    ### prefs0 -- FREEDB stuff ###
    'query_on_start': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'help': 1,
        'usage': "do freedb query when starting",
        'long': 'query-now',
        'short': 'Q',
        },
    'query_if_needed': {
        'type': 'toggle',
        'val': 0,
        'help': 1,
        'usage': "query freedb when starting if not queried already",
        'long': 'AUTO',
        },
    'query_when_ready': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'help': 1,
        'usage': "do freedb query when all is done",
        'long': 'query',
        'short': 'q',
        },
    'cont_failed_query': {
        'type': 'toggle',
        'val': 0,
        'usage': "continue without freedb data if query fails",
        'long': 'AUTO',
        },
    'edit_cddb': {
        # For backwards compatibility only, use edit_freedb instead!
        'type': 'toggle',
        'val': 0,
        'long': 'AUTO',
        },
    'edit_freedb': {
        'type': 'toggle',
        'val': 0,
        'usage': "edit CDDB information before using it",
        'long': 'AUTO',
        },
    'various': {
        'type': 'toggle',
        'val': None,
        'save': 0,
        'usage': "assume CD has various artists",
        'long': 'AUTO',
        },
    'various_swap': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "exchange artist and title",
        'long': 'AUTO',
        },
    'extt_is_artist': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "extt contains artist",
        'long': 'AUTO',
        },
    'extt_is_title': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "extt contains track title",
        'long': 'AUTO',
        },
    'extt_is_comment': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "extt contains track comment",
        'long': 'AUTO',
        },
    'freedb_submit': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "http-submit freedb file to server and exit",
        'long': 'submit',
        },
    'freedb_mailsubmit': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "submit by e-mail - needs sendmail",
        'long': 'mail-submit',
        'short': 'm',
        },
    'read_freedb_file': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'doc': "read freedb file",
        },
    'freedb_rename': {
        'type': 'toggle',
        'val': 0,
        'help': 1,
        'save': 0,
        'usage': "rename according to freedb file, eg. after editing it",
        'long': 'rename',
        'short': 'R',
        },
    'set_id3tag': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'doc': "set id3 tag info",
        },
    'id3_genre': {
        'type': types.IntType,
        'val': -1,
        'save': 0,
        'doc': "set ID3 genre (empty=don't set, help=list)",
        },
    'id3_year': {
        'type': types.IntType,
        'val': -1,
        'save': 0,
        'usage': "set ID3 year (0=don't set)",
        'long': 'AUTO',
        'short': 'Y',
        },
    'username': {
        'type': types.StringType,
        'val': None,
        'doc': "required for freedb query",
        },
    'hostname': {
        'type': types.StringType,
        'val': None,
        'doc': "required for freedb query",
        },
    'image_toc_file': {
        'type': types.StringType,
        'val': None,
        'save': 0,
        'usage': "read another toc file which may point to an image-file",
        'long': 'from-tocfile',
        'short': 'f',
        },
    'image_file': {
        'type': types.StringType,
        'val': None,
        'save': 0,
        'usage': "read audio from an image file",
        'long': 'from-image',
        'short': 'F',
        },
    'rip_from_device': {
        'type': 'toggle',
        'val': 1,
        'save': 0,
        'doc': "rip from physical device, not from image_file",
        },
    'toc_file': {
        'type': types.StringType,
        'val': jack_version.prog_name + ".toc",
        'save': 0,
        'doc': "the toc file which is actually used",
        },
    'def_toc': {
        'type': types.StringType,
        'val': jack_version.prog_name + ".toc",
        'doc': "the default name of the toc file",
        },
    'freedb_form_file': {
        'type': types.StringType,
        'val': jack_version.prog_name + ".freedb",
        'doc': "name of submission template",
        },
    'out_file': {
        'type': types.StringType,
        'val': jack_version.prog_name + ".out",
        'doc': "in silent-mode, stdout goes here",
        },
    'err_file': {
        'type': types.StringType,
        'val': jack_version.prog_name + ".err",
        'doc': "in silent-mode, stderr here",
        },
    'progress_file': {
        'type': types.StringType,
        'val': jack_version.prog_name + ".progress",
        'doc': "subprocess output is cached here",
        },
    'progr_sep': {
        'type': types.StringType,
        'val': "/|\\",
        'doc': "field separator in progress_file",
        },
    'guess_mp3s': {
        'type': types.ListType,
        'val': [],
        'save': 0,
        'usage': "guess TOC from files (until terminating \";\")",
        'long': 'guess-toc',
        'short': 'g',
        },
    'upd_progress': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "re-generate progress file if \"lost\"",
        'long': 'AUTO',
        },
    'multi_mode': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "try to query freedb for all dirs in searchdirs which have no freedb data",
        'long': 'AUTO',
        },
    'claim_dir': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "rename the dir even if it was not created by jack",
        'long': 'AUTO',
        'short': 'C',
        },
    'wait_on_quit': {
        'type': 'toggle',
        'val': 0,
        'usage': "wait for key press before quitting",
        'long': 'wait',
        },
    'id3_genre_txt': {
        'type': types.StringType,
        'val': None,
        'save': 0,
        'usage': "set ID3 genre (empty=don't set, help=list)",
        'long': 'id3-genre',
        'short': 'G',
        },
    'save_args': {
        'type': 'toggle',
        'val': 0,
        'save': 0,
        'usage': "save options to rc file and exit",
        'long': 'save',
        },
    'global_rc': {
        'type': types.StringType,
        'val': "/etc/jackrc",
        'save': 0,
        'doc': "system-wide config file",
        },
    'user_rc': {
        'type': types.StringType,
        'val': "~/.jack3rc",
        'save': 0,
        'doc': "user config file",
        },
    'write_m3u': {
        'type': 'toggle',
        'val': 0,
        'usage': "create a playlist in .m3u format",
        'long': 'AUTO',
        },
    'write_id3v1': {
        'type': 'toggle',
        'val': 1,
        'usage': "write a smart id3v1 tag to the encoded file",
        'long': 'AUTO',
        },
    'write_id3v2': {
        'type': 'toggle',
        'val': 1,
        'usage': "write an id3v2 tag to the encoded file",
        'long': 'AUTO',
        },
    'playorder': {
        'type': 'toggle',
        'val': 0,
        'usage': "use the freedb PLAYORDER field to limit the tracks to rip (non-functional, sorry)",
        'long': 'AUTO',
        },
    })

for i in cf.keys():
    # expand long options
    if cf[i].has_key('long') and cf[i]['long'] == "AUTO":
        cf[i]['long'] = string.replace(i, "_", "-")
    # init history
    cf[i]['history'] = [ ["config", cf[i]['val'],],]
