### jack_checkopts: check the options for consistency, a module for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2003  Arne Zellentin <zarne@users.sf.net>

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

import jack_utils
import jack_version
import jack_functions

from jack_globals import *
import jack_freedb
from jack_helpers import helpers
from jack_targets import targets

# special option handling
def checkopts(cf, cf2):
    if cf2.has_key('image_file'):
        cf.rupdate({'rip_from_device': {'val': 0}, 'read_ahead':{'val': 0}}, "check")

    if cf2.has_key('image_toc_file'):
        cf.rupdate({'rip_from_device': {'val': 0}, 'read_ahead':{'val': 0}}, "check")

    if cf2.has_key('space_from_argv'):
        cf.rupdate({'space_set_from_argv': {'val': 1}}, "check")

    if cf2.has_key('freedb_server'):
        if not jack_freedb.freedb_servers.has_key(cf2['freedb_server']['val']):
            error("unknown server, choose one: " + `jack_freedb.freedb_servers.keys()`)

    if cf2.has_key('only_dae') and cf2['only_dae']['val']:
        cf.rupdate({'encoders': {'val': 0}}, "check")

    if cf2.has_key('no_various') and cf2['no_various']['val']:
        cf.rupdate({'various': {'val': 0}}, "check")

    if cf2.has_key('query_when_ready') and cf2['query_when_ready']['val']:
        cf.rupdate({'read_freedb_file': {'val': 1}, 'set_id3tag':{'val': 1}}, "check")

    if cf2.has_key('query_on_start') and cf2['query_on_start']['val']:
        cf.rupdate({'set_id3tag': {'val': 1}}, "check")

    if cf2.has_key('cont_failed_query') and cf2['cont_failed_query']['val']:
        cf.rupdate({'query_on_start': {'val': 1}, 'set_id3tag':{'val': 1}}, "check")

    if cf2.has_key('create_dirs') and cf2['create_dirs']['val']:
        cf.rupdate({'rename_dir': {'val': 1}}, "check")

    if cf2.has_key('freedb_rename') and cf2['freedb_rename']['val']:
        cf.rupdate({'read_freedb_file': {'val': 1}, 'set_id3tag':{'val': 1}}, "check")

    if cf2.has_key('id3_genre_txt'):
        genre = jack_functions.check_genre_txt(cf2['id3_genre_txt']['val'])
        if genre != cf['_id3_genre']:
            cf.rupdate({'id3_genre': {'val': genre}}, "check")
        del genre

    for i in cf2.keys():
        if not cf.has_key(i):
            error("unknown config item `%s'" % i)

def consistency_check(cf):
    # check for unsername
    if cf['username']['val'] == None:
        if os.environ.has_key('USER'):
            cf['username']['val'] = os.environ['USER']
        elif os.environ.has_key('LOGNAME'):
            cf['username']['val'] = os.environ['LOGNAME']
        else:
            error("can't determine your username, pleas set it manually.")
        debug("username is " + cf['_username'])

    # check for hostname
    if cf['hostname']['val'] == None:
        cf['hostname']['val'] = os.uname()[1]
        debug("hostname is " + cf['_hostname'])

    # check for e-mail address
    if len(jack_freedb.freedb_servers[cf['_freedb_server']]['my_mail']) <= 3 or jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail'] == "default":
        tmp_mail = jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail']
        tmp_mail2 = cf['_my_mail']
        if len(cf['_my_mail']) <= 3 or cf['_my_mail'] == "default" or cf['_my_mail'].find("@") < 1:
            jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail'] = cf['username']['val'] + "@" + cf['hostname']['val']
            if len(cf['my_mail']['history']) > 1:
                warning("illegal mail address changed to " + jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail'])
        else:
            jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail'] = cf['_my_mail']
        debug("mail is " + jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail'] + ", was " + tmp_mail + " / " + tmp_mail2)
        del tmp_mail, tmp_mail2

    if cf.has_key('charset'):
        if not cf['char_filter']['val']:
            warning("charset has no effect without a char_filter")

    if len(cf['replacement_chars']['val']) == 0:
        cf.rupdate({'replacement_chars': {'val': ["",]}}, "check")

    # stretch replacement_chars
    if len(cf['_unusable_chars']) > len(cf['_replacement_chars']):
        u, r = cf['_unusable_chars'], cf['_replacement_chars']
        while len(u) > len(r):
            if type(r) == types.ListType:
                r.append(r[-1])
            elif type(r) == types.StringType:
                r = r + r[-1]
            else:
                error("unsupported type: " + `type(cf['replacement_chars']['val'][-1])`)
        cf.rupdate({'replacement_chars': {'val': r}}, "check")
        del u, r

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

    if not helpers.has_key(cf['_encoder']) or helpers[cf['_encoder']]['type'] != "encoder":
        dummy = []
        for i in helpers.keys():
            if helpers[i]['type'] == "encoder":
                dummy.append(i)
        error("Invalid encoder, choose one of " + `dummy`)

    if not helpers.has_key(cf['_ripper']) or helpers[cf['_ripper']]['type'] != "ripper":
        dummy = []
        for i in helpers.keys():
            if helpers[i]['type'] == "ripper":
                dummy.append(i)
        error("Invalid ripper, choose one of " + `dummy`)

    if (cf['vbr_quality']['val'] > 10) or (cf['vbr_quality']['val'] < -1):
        error("invalid vbr quality, must be between -1 and 10")

    if helpers[cf['_encoder']].has_key('inverse-quality') and helpers[cf['_encoder']]['inverse-quality']:
        # this is a bit ugly but works for
        # oggenc: -1 ... 10
        # lame:    0 ...  9
        cf.rupdate({'vbr_quality': {'val': min(9, 10 - cf['vbr_quality']['val'])}}, "check")

    # check for option conflicts:
    if cf['_otf'] and cf['_only_dae']:
        warning("disabling on-the-fly operation because we're doing DAE only")
        cf.rupdate({'otf': {'val': 0}}, "check")

    if cf['_otf'] and cf['_keep_wavs']:
        warning("disabling on-the-fly operation because we want to keep the wavs")
        cf.rupdate({'otf': {'val': 0}}, "check")

    if cf['_otf'] and cf['_image_file']:
        warning("disabling on-the-fly operation as we're reading from image.")
        cf.rupdate({'otf': {'val': 0}}, "check")

    if cf['_otf']:
        for i in (cf['_ripper'], cf['_encoder']):
            if not helpers[i].has_key(('vbr-' * cf['_vbr'] * (i == cf['_encoder'])) + 'otf-cmd'):
                error("can't do on-the-fly because " + helpers[i]['type'] + " " + i + " doesn't support it.")

    if cf['_vbr'] and not helpers[cf['_encoder']].has_key('vbr-cmd'):
        warning("disabling VBR because " + cf['_encoder'] + " doesn't support it.")
        cf.rupdate({'vbr': {'val': 0}}, "check")

    if not cf['_vbr'] and not helpers[cf['_encoder']].has_key('cmd'):
        error("can't do CBR because " + cf['encoder']['val'] + " doesn't support it. Use -v")

    if cf['_ripper'] == "cdparanoia" and cf['_sloppy']:
        helpers['cdparanoia']['cmd'] = replace(helpers['cdparanoia']['cmd'], "--abort-on-skip", "")
        helpers['cdparanoia']['otf-cmd'] = replace(helpers['cdparanoia']['otf-cmd'], "--abort-on-skip", "")

    if cf['_query_on_start'] and cf['_query_when_ready']:
        error("it doesn't make sense to query now _and_ when finished.")

    if cf['_dont_work'] and cf['_query_when_ready']:
        warning("you want to use --query-now / -Q instead of --query / -q")
