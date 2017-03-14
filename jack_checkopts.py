# jack_checkopts: check the options for consistency, a module for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2004  Arne Zellentin <zarne@users.sf.net>

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

import signal
import types
import sys
import os

import jack_utils
import jack_version
import jack_plugins
import jack_functions

from jack_globals import *
import jack_freedb
import jack_helpers

# special option handling


def checkopts(cf, cf2):
    if cf2.has_key('image_file'):
        cf.rupdate(
            {'rip_from_device': {'val': 0}, 'read_ahead': {'val': 1}}, "check")

    if cf2.has_key('image_toc_file'):
        cf.rupdate(
            {'rip_from_device': {'val': 0}, 'read_ahead': {'val': 1}}, "check")

    if cf2.has_key('space_from_argv'):
        cf.rupdate({'space_set_from_argv': {'val': 1}}, "check")

    if cf2.has_key('only_dae') and cf2['only_dae']['val']:
        cf.rupdate({'encoders': {'val': 0}}, "check")

    if cf2.has_key('query_when_ready') and cf2['query_when_ready']['val']:
        cf.rupdate(
            {'read_freedb_file': {'val': 1}, 'set_id3tag': {'val': 1}}, "check")

    if cf2.has_key('query_on_start') and cf2['query_on_start']['val']:
        cf.rupdate({'set_id3tag': {'val': 1}}, "check")

    if cf2.has_key('create_dirs') and cf2['create_dirs']['val']:
        cf.rupdate({'rename_dir': {'val': 1}}, "check")

    if cf2.has_key('freedb_rename') and cf2['freedb_rename']['val']:
        cf.rupdate(
            {'read_freedb_file': {'val': 1}, 'set_id3tag': {'val': 1}}, "check")

    if cf2.has_key('edit_cddb'):
        warning("--edit-cddb is obsolete, please use --edit-freedb")
        cf.rupdate({'edit_freedb': {'val': 1}}, "check")

    if cf2.has_key('id3_genre_txt'):
        genre = jack_functions.check_genre_txt(cf2['id3_genre_txt']['val'])
        if genre != cf['_id3_genre']:
            cf.rupdate({'id3_genre': {'val': genre}}, "check")
        del genre

    if not cf2.has_key('vbr'):
        if cf2.has_key('bitrate') and cf2.has_key('vbr_quality'):
            cf.rupdate({'vbr': {'val': 1}}, "check")
        elif cf2.has_key('bitrate'):
            cf.rupdate({'vbr': {'val': 0}}, "check")
        elif cf2.has_key('vbr_quality'):
            cf.rupdate({'vbr': {'val': 1}}, "check")

    for i in cf2.keys():
        if not cf.has_key(i):
            error("unknown config item `%s'" % i)


def consistency_check(cf):

    # set plugins path and import freedb_server plugin
    sys.path.extend(map(expand, cf['_plugin_path']))
    jack_plugins.import_freedb_servers()

    # check freedb server
    if cf.has_key('freedb_server'):
        if not jack_freedb.freedb_servers.has_key(cf['freedb_server']['val']):
            error("unknown server, choose one: " + `jack_freedb.freedb_servers.keys()`)

    # check dir_template and scan_dirs
    if len(cf['_dir_template'].split(os.path.sep)) > cf['_scan_dirs']:
        warning("dir-template consists of more sub-paths (%i) than scan-dirs (%i). Jack may not find the workdir next time it is run. (Auto-raised)" %
                (len(cf['_dir_template'].split(os.path.sep)), cf['_scan_dirs']))
        cf.rupdate(
            {'scan_dirs': {'val': len(cf['_dir_template'].split(os.path.sep))}}, "check")

    # check for unsername
    if cf['username']['val'] == None:
        if os.environ.has_key('USER') and os.environ['USER'] != "":
            cf['username']['val'] = os.environ['USER']
        elif os.environ.has_key('LOGNAME') and os.environ['LOGNAME'] != "":
            cf['username']['val'] = os.environ['LOGNAME']
        else:
            error("can't determine your username, please set it manually.")
        debug("username is " + cf['_username'])

    # check for hostname
    if cf['hostname']['val'] == None:
        cf['hostname']['val'] = os.uname()[1]
        debug("hostname is " + cf['_hostname'])

    # check for e-mail address
    if len(jack_freedb.freedb_servers[cf['_freedb_server']]['my_mail']) <= 3 or jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail'] == "default":
        tmp_mail = jack_freedb.freedb_servers[
            cf['freedb_server']['val']]['my_mail']
        tmp_mail2 = cf['_my_mail']
        if len(cf['_my_mail']) <= 3 or cf['_my_mail'] == "default" or cf['_my_mail'].find("@") < 1:
            env = os.getenv("EMAIL")
            if env:
                jack_freedb.freedb_servers[
                    cf['freedb_server']['val']]['my_mail'] = env
            else:
                jack_freedb.freedb_servers[cf['freedb_server']['val']][
                    'my_mail'] = cf['username']['val'] + "@" + cf['hostname']['val']
            if len(cf['my_mail']['history']) > 1:
                warning("illegal mail address changed to " +
                        jack_freedb.freedb_servers[cf['freedb_server']['val']]['my_mail'])
        else:
            jack_freedb.freedb_servers[
                cf['freedb_server']['val']]['my_mail'] = cf['_my_mail']
        debug("mail is " + jack_freedb.freedb_servers[cf['freedb_server']['val']][
              'my_mail'] + ", was " + tmp_mail + " / " + tmp_mail2)
        del tmp_mail, tmp_mail2

    # if cf.has_key('charset'):
    #    if not cf['char_filter']['val']:
    #        warning("charset has no effect without a char_filter")
    #                 this is not true, the ogg tag uses this.

    if len(cf['replacement_chars']['val']) == 0:
        cf.rupdate({'replacement_chars': {'val': ["", ]}}, "check")

    # stretch replacement_chars
    if len(cf['_unusable_chars']) > len(cf['_replacement_chars']):
        warning("unusable_chars contains more elements than replacement_chars")
        u, r = cf['_unusable_chars'], cf['_replacement_chars']
        while len(u) > len(r):
            if type(r) == types.ListType:
                r.append(r[-1])
            elif type(r) == types.StringType:
                r = r + r[-1]
            else:
                error("unsupported type: " + `type(
                    cf['replacement_chars']['val'][-1])`)
        cf.rupdate({'replacement_chars': {'val': r}}, "check")
        del u, r
    elif len(cf['_replacement_chars']) > len(cf['_unusable_chars']):
        # This has no practical negative effect but print a warning anyway
        warning("replacement_chars contains more elements than unusable_chars")

    if cf['silent_mode']['val']:
        cf['terminal']['val'] = "dumb"
        cf['xtermset_enable']['val'] = 0
        out_f = open(cf['_out_file'], "a")
        err_f = open(cf['_err_file'], "a")
        os.dup2(out_f.fileno(), STDOUT_FILENO)
        out_f.close()
        os.dup2(err_f.fileno(), STDERR_FILENO)
        err_f.close()
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)

    # load plugins, compile stuff
    jack_helpers.init()

    if not jack_helpers.helpers.has_key(cf['_encoder']) or jack_helpers.helpers[cf['_encoder']]['type'] != "encoder":
        dummy = []
        for i in jack_helpers.helpers.keys():
            if jack_helpers.helpers[i]['type'] == "encoder":
                dummy.append(i)
        error("Invalid encoder, choose one of " + ", ".join(dummy))

    if not jack_helpers.helpers.has_key(cf['_ripper']) or jack_helpers.helpers[cf['_ripper']]['type'] != "ripper":
        dummy = []
        for i in jack_helpers.helpers.keys():
            if jack_helpers.helpers[i]['type'] == "ripper":
                dummy.append(i)
        error("Invalid ripper, choose one of " + ", ".join(dummy))

    if (cf['vbr_quality']['val'] > 10) or (cf['vbr_quality']['val'] < -1):
        error("invalid vbr quality, must be between -1 and 10")

    # check for option conflicts:
    if cf['_otf'] and cf['_only_dae']:
        warning("disabling on-the-fly operation because we're doing DAE only")
        cf.rupdate({'otf': {'val': 0}}, "check")

    if cf['_otf'] and cf['_keep_wavs']:
        warning(
            "disabling on-the-fly operation because we want to keep the wavs")
        cf.rupdate({'otf': {'val': 0}}, "check")

    if cf['_otf'] and cf['_image_file']:
        warning("disabling on-the-fly operation as we're reading from image.")
        cf.rupdate({'otf': {'val': 0}}, "check")

    if cf['_vbr'] and not jack_helpers.helpers[cf['_encoder']].has_key('vbr-cmd'):
        warning("disabling VBR because " +
                cf['_encoder'] + " doesn't support it.")
        cf.rupdate({'vbr': {'val': 0}}, "check")

    if cf['_otf']:
        for i in (cf['_ripper'], cf['_encoder']):
            if not jack_helpers.helpers[i].has_key(('vbr-' * cf['_vbr'] * (i == cf['_encoder'])) + 'otf-cmd'):
                error("can't do on-the-fly because " + jack_helpers.helpers[
                      i]['type'] + " " + i + " doesn't support it.")

    if not cf['_vbr'] and not jack_helpers.helpers[cf['_encoder']].has_key('cmd'):
        error("can't do fixed bitrate because " +
              cf['encoder']['val'] + " doesn't support it. Use -v")

    if cf['_ripper'] == "cdparanoia" and cf['_sloppy']:
        jack_helpers.helpers['cdparanoia']['cmd'] = jack_helpers.helpers[
            'cdparanoia']['cmd'].replace("--abort-on-skip", "")
        jack_helpers.helpers['cdparanoia']['otf-cmd'] = jack_helpers.helpers[
            'cdparanoia']['otf-cmd'].replace("--abort-on-skip", "")

    if cf['_query_on_start'] and cf['_query_when_ready']:
        error("it doesn't make sense to query now _and_ when finished.")

    if cf['_dont_work'] and cf['_query_when_ready']:
        warning("you want to use --query-now / -Q instead of --query / -q")

# Checks concerning options specified by the user (in the global or user rc
# files or the command line), i.e. options/values that are not the default
# jack options from jack_config.


def check_rc(cf, global_cf, user_cf, argv_cf):

    all_keys = global_cf.keys() + user_cf.keys() + argv_cf.keys()
    userdef_keys = user_cf.keys() + argv_cf.keys()
    if 'base_dir' not in all_keys:
        warning(
            "You have no standard location set, putting files into the current directory. Please consider setting base_dir in ~/.jack3rc.")

    # Check if the default ripper is installed, and if not, look for another
    # one
    if 'ripper' not in all_keys:
        default_ripper = cf["ripper"]["val"]
        if not jack_utils.in_path(default_ripper):
            rippers = [i for i in jack_helpers.helpers if jack_helpers.helpers[i][
                "type"] == "ripper" and jack_helpers.helpers[i].has_key("toc_cmd")]
            for cmd in rippers:
                if jack_utils.in_path(cmd):
                    warning("Using ripper %s since default ripper %s is not available." %
                            (cmd, default_ripper))
                    cf.rupdate({'ripper': {'val': cmd}}, "check")
                    break
            else:
                error("No valid ripper found on your system.")

    # Check whether ripper and encoder exist in $PATH.  Skip the check if
    # it's a plugin since we cannot assume the name of the plugin
    # corresponds to the executable.
    for t in ("ripper", "encoder"):
        helper = cf[t]["val"]
        if t in userdef_keys and not helper.startswith("plugin_"):
            if not jack_utils.in_path(helper):
                error("Helper %s '%s' not found on your system." % (t, helper))

    # If the default CD device doesn't exist, see whether we can find another
    # one
    if ('cd_device' not in all_keys and cf["rip_from_device"]["val"] and
            not os.path.exists(cf["cd_device"]["val"])):
        default = cf["cd_device"]["val"]
        devices = []
        # All CD devices can be found in /proc on Linux
        cdrom_info = "/proc/sys/dev/cdrom/info"
        if os.path.exists(cdrom_info):
            try:
                info = open(cdrom_info, "r")
            except (IOError, OSError):
                pass
            else:
                for line in info.readlines():
                    if line.startswith("drive name:"):
                        devices = [
                            "/dev/" + x for x in line.rstrip().split("\t")[2:]]
                        break
                info.close()
        message = "Default CD device %s does not exist" % default
        if not devices:
            warning("%s." % message)
        elif len(devices) == 1:
            warning("%s, using %s." % (message, devices[0]))
            cf.rupdate({'cd_device': {'val': devices[0]}}, "check")
        else:
            warning("%s but there are several CD devices." % message)
            for i in range(len(devices)):
                print "%2d" % (i + 1) + ".) " + devices[i]
            input = 0
            while input <= 0 or input > len(devices):
                try:
                    input = raw_input("Please choose: ")
                except KeyboardInterrupt:
                    sys.exit(0)
                if input.isdigit():
                    input = int(input)
                else:
                    input = 0
            devices[0] = devices[input - 1]
            cf.rupdate({'cd_device': {'val': devices[0]}}, "check")
