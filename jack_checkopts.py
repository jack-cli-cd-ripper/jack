### jack_checkopts: check the options for consistency, a module for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2002  Arne Zellentin <zarne@users.sf.net>

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
from jack_freedb import freedb_servers
from jack_helpers import helpers
from jack_targets import targets


# special option handling
def checkopts(cf, cf2):
    if cf2.has_key('image_file'):
        cf['rip_from_device']['val'] = 0
        cf['read_ahead']['val'] = 0          # we do not want to waste discspace

    if cf2.has_key('image_toc_file'):
        cf['rip_from_device']['val'] = 0
        cf['read_ahead']['val'] = 0          # we do not want to waste discspace

    if cf2.has_key('space_from_argv'):
        cf['space_set_from_argv'] = {'val': 1}

    if cf2.has_key('freedb_server') and cf['freedb_server']:
        if not freedb_servers.has_key(cf['freedb_server']['val']):
            print "Error: unknown server, choose one or define one in", prefs_file + ":"
            print freedb_servers.keys()
            exit(1)

    if cf2.has_key('only_dae') and cf['only_dae']:
        cf['encoders']['val'] = 0

    #XXX
    if cf2.has_key('no_various') and cf['no_various']:
        cf['various']['val'] = 2

    if cf2.has_key('query_when_ready') and cf['query_when_ready']:
        cf['read_freedb_file']['val'] = 1
        cf['set_id3tag']['val'] = 1

    if cf2.has_key('query_on_start') and cf['query_on_start']:
        cf['set_id3tag']['val'] = 1

    if cf2.has_key('continue_failed_query') and cf['continue_failed_query']:
        cf['query_on_start']['val'] = 1
        cf['set_id3tag']['val'] = 1

    if cf2.has_key('create_dirs') and cf['create_dirs']:
        cf['rename_dir']['val'] = 1

    if cf2.has_key('freedb_rename') and cf['freedb_rename']:
        cf['read_freedb_file']['val'] = 1
        cf['set_id3tag']['val'] = 1

    if cf2.has_key('id3_genre_txt') and cf['id3_genre_txt']['val']:
        if upper(cf['id3_genre_txt']['val']) == "HELP":
            cf['id3_genre']['val'] = -2  # print genre list later
        elif upper(cf['id3_genre_txt']['val']) == "NONE":
            cf['id3_genre']['val'] = 255 # set genre to [unknown]
        else:
            import ID3
            temp_id3 = ID3.ID3("/dev/null")
            cf['id3_genre']['val'] = temp_id3.find_genre(cf['id3_genre_txt']['val'])
            if cf['id3_genre']['val'] == -1:
                print "Error: illegal genre. Try '" + prog_name + " --id3-genre help' for a list."
                sys.exit(1)
            del temp_id3

def consistency_check(cf):
    # check for unsername
    if cf['username']['val'] == None:
        if os.environ.has_key('USER'):
            cf['username']['val'] = os.environ['USER']
        elif os.environ.has_key('LOGNAME'):
            cf['username']['val'] = os.environ['LOGNAME']
        else:
            jack_utils.error("can't determine your username, pleas set it manually.")

    # check for hostname
    if cf['hostname']['val'] == None:
        cf['hostname']['val'] = os.uname()[1]

    # check options for consitency
    if cf.has_key('charset'):
        if not cf['char_filter']['val']:
            print "Warning: option --charset has no effect without a char_filter"

    if len(freedb_servers[cf['freedb_server']['val']]['my_mail']) <= 3 or freedb_servers[cf['freedb_server']['val']]['my_mail'] == "default":
        freedb_servers[cf['freedb_server']['val']]['my_mail'] = cf['username']['val'] + "@" + cf['hostname']['val']

    if len(cf['replacement_chars']['val']) == 0:
        cf['replacement_chars']['val'] = [""]
    while len(cf['unusable_chars']['val']) > len(cf['replacement_chars']['val']): # stretch rep._chars
        if type(cf['replacement_chars']['val']) == types.ListType:
            cf['replacement_chars']['val'].append(cf['replacement_chars']['val'][-1])
        elif type(cf['replacement_chars']['val']) == types.StringType:
            cf['replacement_chars']['val'] = cf['replacement_chars']['val'] + cf['replacement_chars']['val'][-1]
        else:
            print "Error: unsupported type: " + `type(cf['replacement_chars']['val'][-1])`
            sys.exit(1)

    if cf['id3_genre']['val'] == -2:
        print "available genres=" + `id3genres`
        sys.exit(0)
    if cf['silent_mode']['val']:
        cf['terminal'] = "dumb"
        cf['xtermset_enable']['val'] = 0
        cf['out_f']['val'] = open(out_file, "a")
        cf['err_f']['val'] = open(err_file, "a")
        os.dup2(cf['out_f']['val'].fileno(), STDOUT_FILENO)
        cf['out_f']['val'].close()
        os.dup2(cf['err_f']['val'].fileno(), STDERR_FILENO)
        cf['err_f']['val'].close()
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)

    if not helpers.has_key(cf['encoder']['val']) or helpers[cf['encoder']['val']]['type'] != "encoder":
        print "Invalid encoder, choose one of (",
        for dummy in helpers.keys():
            if helpers[dummy]['type'] == "encoder":
                print dummy,
        print ")"
        sys.exit(1)

    if not helpers.has_key(cf['ripper']['val']) or helpers[cf['ripper']['val']]['type'] != "ripper":
        print "Invalid ripper, choose one of (",
        for dummy in helpers.keys():
            if helpers[dummy]['type'] == "ripper":
                print dummy,
        print ")"
        sys.exit(1)

    if (cf['vbr_quality']['val'] > 10) or (cf['vbr_quality']['val'] < 0):
        print "Invalid vbr quality, must be between 0 and 10"
        sys.exit(1)

    if helpers[cf['encoder']['val']].has_key('inverse-quality') and helpers[cf['encoder']['val']]['inverse-quality']:
        cf['vbr_quality']['val'] = min(9, 10 - cf['vbr_quality']['val'])

    # check for option conflicts:
    if cf['otf']['val'] and cf['only_dae']['val']:
        print "Warning: disabling on-the-fly operation because we're doing DAE only."
        cf['otf']['val'] = 0

    if cf['otf']['val'] and cf['keep_wavs']['val']:
        print "Warning: disabling on-the-fly operation because we want to keep the wavs."
        cf['otf']['val'] = 0

    if cf['otf']['val'] and cf['image_file']['val']:
        print "Warning: disabling on-the-fly operation as we're reading from image."
        cf['otf']['val'] = 0

    if cf['otf']['val']:
        for i in (cf['ripper']['val'], cf['encoder']['val']):
            if not helpers[i].has_key(('vbr-' * vbr * (i == cf['encoder']['val'])) + 'otf-cmd'):
                print "Error: can't do on-the-fly because " + helpers[i]['type'] + " " + i + " doesn't support it."
                exit()

    if cf['vbr']['val'] and not helpers[cf['encoder']['val']].has_key('vbr-cmd'):
        print "Warning: disabling VBR because " + cf['encoder']['val'] + " doesn't support it."
        cf['vbr']['val'] = 0

    if not cf['vbr']['val'] and not helpers[cf['encoder']['val']].has_key('cmd'):
        print "Error: can't do CBR because " + cf['encoder']['val'] + " doesn't support it.\nUse -v or set vbr=1 in your .jackrc."
        exit()

    #XXX
    #if cf['xtermset_enable']['val'] and jack_cursutils.curses_enable and not jack_cursutils.jack_curses_enable:
        #print "xtermset makes no sense with incomplete curses, disabling xtermset."
        #print "please resize your terminal before running jack."
        #cf['xtermset_enable']['val'] = 0

    if cf['ripper']['val'] == "cdparanoia" and cf['sloppy']['val']:
        helpers['cdparanoia']['cmd'] = replace(helpers['cdparanoia']['cmd'], "--abort-on-skip", "")
        helpers['cdparanoia']['otf-cmd'] = replace(helpers['cdparanoia']['otf-cmd'], "--abort-on-skip", "")

    if cf['query_on_start']['val'] and cf['query_when_ready']['val']:
        print "Error: it doesn't make sense to query now _and_ when finished."
        sys.exit()

def setup(cf):
    cf['ext'] = {'val': targets[helpers[cf['encoder']['val']]['target']]['file_extension']}

