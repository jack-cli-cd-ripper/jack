# jack.checkopts: check the options for consistency, a module for
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

import jack.utils
import jack.version
import jack.functions

from jack.globals import *
import jack.metadata
import jack.helpers

# special option handling


def checkopts(cf, cf2):
    if 'image_file' in cf2:
        cf.rupdate({'rip_from_device': {'val': 0}, 'read_ahead': {'val': 1}}, "check")

    if 'image_toc_file' in cf2:
        cf.rupdate({'rip_from_device': {'val': 0}, 'read_ahead': {'val': 1}}, "check")

    if 'space_from_argv' in cf2:
        cf.rupdate({'space_set_from_argv': {'val': 1}}, "check")

    if 'only_dae' in cf2 and cf2['only_dae']['val']:
        cf.rupdate({'encoders': {'val': 0}}, "check")

    if 'query_when_ready' in cf2 and cf2['query_when_ready']['val']:
        cf.rupdate({'read_metadata_file': {'val': 1}, 'set_tag': {'val': 1}}, "check")

    if 'query_on_start' in cf2 and cf2['query_on_start']['val']:
        cf.rupdate({'set_tag': {'val': 1}}, "check")

    if 'create_dirs' in cf2 and cf2['create_dirs']['val']:
        cf.rupdate({'rename_dir': {'val': 1}}, "check")

    if 'metadata_rename' in cf2 and cf2['metadata_rename']['val']:
        cf.rupdate({'read_metadata_file': {'val': 1}, 'set_tag': {'val': 1}}, "check")

    if 'edit_cddb' in cf2:
        warning("--edit-cddb is obsolete, please use --edit-metadata")
        cf.rupdate({'edit_metadata': {'val': 1}}, "check")

    if 'edit_freedb' in cf2:
        warning("--edit-freedb is obsolete, please use --edit-metadata")
        cf.rupdate({'edit_metadata': {'val': 1}}, "check")

    if 'vbr' not in cf2:
        if 'bitrate' in cf2 and 'vbr_quality' in cf2:
            cf.rupdate({'vbr': {'val': 1}}, "check")
        elif 'bitrate' in cf2:
            cf.rupdate({'vbr': {'val': 0}}, "check")
        elif 'vbr_quality' in cf2:
            cf.rupdate({'vbr': {'val': 1}}, "check")

    for i in list(cf2.keys()):
        if i not in cf:
            error("unknown config item `%s'" % i)


def consistency_check(cf):

    # check metadata server
    if 'metadata_server' in cf:
        if cf['metadata_server']['val'] not in jack.metadata.metadata_servers:
            error("unknown server, choose one: " + repr(list(jack.metadata.metadata_servers.keys())))

    # check dir_template and scan_dirs
    if len(cf['_dir_template'].split(os.path.sep)) > cf['_scan_dirs']:
        warning("dir-template consists of more sub-paths (%i) than scan-dirs (%i). Jack may not find the workdir next time it is run. (Auto-raised)" % (len(cf['_dir_template'].split(os.path.sep)), cf['_scan_dirs']))
        cf.rupdate({'scan_dirs': {'val': len(cf['_dir_template'].split(os.path.sep))}}, "check")

    # check for unsername
    if cf['username']['val'] == None:
        if 'USER' in os.environ and os.environ['USER'] != "":
            cf['username']['val'] = os.environ['USER']
        elif 'LOGNAME' in os.environ and os.environ['LOGNAME'] != "":
            cf['username']['val'] = os.environ['LOGNAME']
        else:
            error("can't determine your username, please set it manually.")
        debug("username is " + cf['_username'])

    # check for hostname
    if cf['hostname']['val'] == None:
        cf['hostname']['val'] = os.uname()[1]
        debug("hostname is " + cf['_hostname'])

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
            if type(r) == list:
                r.append(r[-1])
            elif type(r) == str:
                r = r + r[-1]
            else:
                error("unsupported type: " + repr(type(cf['replacement_chars']['val'][-1])))
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

    # load and compile stuff
    jack.helpers.init()

    if cf['_encoder'] not in jack.helpers.helpers or jack.helpers.helpers[cf['_encoder']]['type'] != "encoder":
        dummy = []
        for i in list(jack.helpers.helpers.keys()):
            if jack.helpers.helpers[i]['type'] == "encoder":
                dummy.append(i)
        error("Invalid encoder, choose one of " + ", ".join(dummy))

    if cf['_ripper'] not in jack.helpers.helpers or jack.helpers.helpers[cf['_ripper']]['type'] != "ripper":
        dummy = []
        for i in list(jack.helpers.helpers.keys()):
            if jack.helpers.helpers[i]['type'] == "ripper":
                dummy.append(i)
        error("Invalid ripper, choose one of " + ", ".join(dummy))

    if (cf['vbr_quality']['val'] > 10) or (cf['vbr_quality']['val'] < -1):
        error("invalid vbr quality, must be between -1 and 10")

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

    if cf['_vbr'] and 'vbr-cmd' not in jack.helpers.helpers[cf['_encoder']]:
        warning("disabling VBR because " + cf['_encoder'] + " doesn't support it.")
        cf.rupdate({'vbr': {'val': 0}}, "check")

    if cf['_otf']:
        for i in (cf['_ripper'], cf['_encoder']):
            if ('vbr-' * cf['_vbr'] * (i == cf['_encoder'])) + 'otf-cmd' not in jack.helpers.helpers[i]:
                error("can't do on-the-fly because " + jack.helpers.helpers[i]['type'] + " " + i + " doesn't support it.")

    if not cf['_vbr'] and 'cmd' not in jack.helpers.helpers[cf['_encoder']]:
        error("can't do fixed bitrate because " + cf['encoder']['val'] + " doesn't support it. Use -v")

    if cf['_ripper'] == "cdparanoia" and cf['_sloppy']:
        jack.helpers.helpers['cdparanoia']['cmd'] = jack.helpers.helpers['cdparanoia']['cmd'].replace("--abort-on-skip", "")
        jack.helpers.helpers['cdparanoia']['otf-cmd'] = jack.helpers.helpers['cdparanoia']['otf-cmd'].replace("--abort-on-skip", "")

    if cf['_query_on_start'] and cf['_query_when_ready']:
        error("it doesn't make sense to query now _and_ when finished.")

    if cf['_dont_work'] and cf['_query_when_ready']:
        warning("you want to use --query-now / -Q instead of --query / -q")

# Checks concerning options specified by the user (in the global or user rc
# files or the command line), i.e. options/values that are not the default
# jack options from jack.config.


def check_rc(cf, global_cf, user_cf, argv_cf):

    all_keys = list(global_cf.keys()) + list(user_cf.keys()) + list(argv_cf.keys())
    userdef_keys = list(user_cf.keys()) + list(argv_cf.keys())
    if 'base_dir' not in all_keys:
        warning(f"You have no standard location set, putting files into the current directory. Please consider setting base_dir in {cf['_user_rc'][0]}.")

    # Check if the default ripper is installed, and if not, look for another
    # one
    if 'ripper' not in all_keys:
        default_ripper = cf["ripper"]["val"]
        if not jack.utils.in_path(default_ripper):
            rippers = [i for i in jack.helpers.helpers if jack.helpers.helpers[i]["type"] == "ripper" and "toc_cmd" in jack.helpers.helpers[i]]
            for cmd in rippers:
                if jack.utils.in_path(cmd):
                    warning("Using ripper %s since default ripper %s is not available." % (cmd, default_ripper))
                    cf.rupdate({'ripper': {'val': cmd}}, "check")
                    break
            else:
                error("No valid ripper found on your system.")

    # Check whether ripper and encoder exist in $PATH.
    for t in ("ripper", "encoder"):
        helper = cf[t]["val"]
        if t in userdef_keys and not jack.utils.in_path(helper):
            error("Helper %s '%s' not found on your system." % (t, helper))

    # If the default CD device doesn't exist, see whether we can find another
    # one
    if ('cd_device' not in all_keys and cf["rip_from_device"]["val"] and not os.path.exists(cf["cd_device"]["val"])):
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
                        devices = ["/dev/" + x for x in line.rstrip().split("\t")[2:]]
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
                print("%2d" % (i + 1) + ".) " + devices[i])
            userinput = 0
            while userinput <= 0 or userinput > len(devices):
                try:
                    userinput = input("Please choose: ")
                except KeyboardInterrupt:
                    sys.exit(0)
                if userinput.isdigit():
                    userinput = int(userinput)
                else:
                    userinput = 0
            devices[0] = devices[userinput - 1]
            cf.rupdate({'cd_device': {'val': devices[0]}}, "check")
