# jack.metadata: metadata server for use in
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2003  Arne Zellentin <zarne@users.sf.net>

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

import string
import sys
import os
import re

import jack.functions
import jack.progress
import jack.utils
import jack.tag
import jack.misc
import jack.freedb
import jack.musicbrainz

from jack.version import prog_version, prog_name
from jack.globals import *

import libdiscid

names_available = None          # metadata info is available
dir_created = None              # dirs are only renamed if we have created them
NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME = list(range(9))
filenames = []

metadata_servers = {
    'freedb': {
        'host': "freedb.freedb.org",
        'id': prog_name + " " + prog_version,
        'api': "cddb",
    },
    'musicbrainz': {
        'host': "default",
        'id': prog_name + " " + prog_version,
        'api': "musicbrainzngs",
    },
}

metadata_apis = {
    'cddb': {
        'form_file_extension': ".freedb",
    },
    'musicbrainzngs': {
        'form_file_extension': ".musicbrainz",
    },
}

def get_metadata_api(server):
    "get the api used for the selected metadata server"
    return metadata_servers[server]['api']

def get_metadata_form_file(api):
    "get the filename for caching metadata"
    return jack.version.prog_name + metadata_apis[api]['form_file_extension']

def interpret_db_file(all_tracks, todo, metadata_form_file, verb, dirs=0, warn=None):
    "read metadata file and rename dir(s)"
    global names_available, dir_created
    metadata_rename = 0
    if warn == None:
        err, track_names, locale_names, cd_id, revision = metadata_names(
            metadata_id(all_tracks), all_tracks, todo, metadata_form_file, verb=verb)
    else:
        err, track_names, locale_names, cd_id, revision = metadata_names(
            metadata_id(all_tracks), all_tracks, todo, metadata_form_file, verb=verb, warn=warn)
    if (not err) and dirs:
        metadata_rename = 1

# The user wants us to use the current dir, unconditionally.

        if cf['_claim_dir']:
            dir_created = jack.utils.split_dirname(os.getcwd())[-1]
            jack.functions.progress("all", "mkdir", dir_created)
            cf['_claim_dir'] = 0

        if cf['_rename_dir'] and dir_created:
            new_dirs, new_dir = jack.utils.mkdirname(
                track_names, cf['_dir_template'])
            old_dir = os.getcwd()
            old_dirs = jack.utils.split_dirname(old_dir)
            dirs_created = jack.utils.split_dirname(dir_created)

# only do the following if we are where we think we are and the dir has to be
# renamed.

            if jack.utils.check_path(dirs_created, old_dirs) and not jack.utils.check_path(dirs_created, new_dirs):
                jack.utils.rename_path(dirs_created, new_dirs)
                print("Info: cwd now", os.getcwd())
                jack.functions.progress("all", 'ren', str(dir_created + "-->" + new_dir))

    if not err:
        cd = track_names[0]
        year = genre = None
        if len(cd) > 2:
            year = repr(cd[2])
        if len(cd) > 3:
            genre = repr(cd[3])
        filenames.append('')  # FIXME: possibly put the dir here, but in no
        # case remove this since people access filenames with i[NUM] which
        # starts at 1
        num = 1
        for i in track_names[1:]:
            replacelist = {"n": cf['_rename_num'] % num, "l": cd[1], "t": i[1],
                           "y": year, "g": genre}
            if cf['_various']:
                replacelist["a"] = i[0]
                newname = jack.misc.multi_replace(
                    cf['_rename_fmt_va'], replacelist, "rename_fmt_va", warn=(num == 1))
            else:
                replacelist["a"] = cd[0]
                newname = jack.misc.multi_replace(
                    cf['_rename_fmt'], replacelist, "rename_fmt", warn=(num == 1))
            exec("newname = newname" + cf['_char_filter'])
            for char_i in range(len(cf['_unusable_chars'])):
                try:
                    a = str(cf['_unusable_chars'][char_i])
                    b = str(cf['_replacement_chars'][char_i])
                except UnicodeDecodeError:
                    warning("Cannot substitute unusable character %d."
                            % (char_i + 1))
                else:
                    newname = newname.replace(a, b)
            filenames.append(newname)
            num += 1
        names_available = 1
    else:
        metadata_rename = 0
    return err, track_names, locale_names, metadata_rename, revision
# / end of interpret_db_file /#


def metadata_id(tracks, warn=0):
    from jack.globals import START, MSF_OFFSET, CDDA_BLOCKS_PER_SECOND
    "calculate disc-id for FreeDB or MusicBrainz"
    cdtoc = []
    if not tracks:
        if warn:
            warning("no tracks! No disc inserted? No/wrong ripper?")
        return 0

    first_track = 1
    track_offsets = []
    for i in tracks:
        track_offsets.append(i[START] + MSF_OFFSET)
        last_track = i[NUM]
        num_sectors = i[START] + i[LEN] + MSF_OFFSET
    disc = libdiscid.put(first_track, last_track, num_sectors, track_offsets)

    cd_id = {'cddb': disc.freedb_id, 'musicbrainzngs': disc.id}
    return cd_id


def metadata_template(tracks, names="", revision=0):
    api = get_metadata_api(cf['_metadata_server'])
    if api == 'cddb':
        return jack.freedb.freedb_template(tracks, names="", revision=0)
    elif api == 'musicbrainzngs':
        return jack.musicbrainz.musicbrainz_template(tracks, names="", revision=0)
    else:
        error("unknown api %s", api)


def metadata_query(cd_id, tracks, file):
    api = get_metadata_api(cf['_metadata_server'])
    if api == 'cddb':
        return jack.freedb.freedb_query(cd_id, tracks, file)
    elif api == 'musicbrainzngs':
        return jack.musicbrainz.musicbrainz_query(cd_id, tracks, file)
    else:
        error("unknown api %s", api)


def metadata_names(cd_id, tracks, todo, name, verb=0, warn=1):
    api = get_metadata_api(cf['_metadata_server'])
    if api == 'cddb':
        return jack.freedb.freedb_names(cd_id, tracks, todo, name, verb=0, warn=1)
    elif api == 'musicbrainzngs':
        return jack.musicbrainz.musicbrainz_names(cd_id, tracks, todo, name, verb=0, warn=1)
    else:
        error("unknown api %s", api)

def split_albumtitle(album_title):
    '''split legacy album title into real album title and medium numbers and medium title, compatible to MusicBrainz'''

    # for instance: David Guetta's "Nothing but the Beat (Disc 1: Vocal Album)" should be split
    # into album title "Nothing but the Beat", medium position 1, medium count -1 (unknown), medium title "Vocal Album"
    # More commonly: Coldplay's "Live In Buenos Aires (CD 2)" should split into "Live In Buenos Aires", 2, -1, None

    # FIXME, medium title extraction is not yet implented

    r1 = re.compile(r'( \(disc[ ]*| \(side[ ]*| \(cd[^a-z0-9]*)([0-9]*|One|Two|A|B)([^a-z0-9])', re.IGNORECASE)
    mo = r1.search(album_title)
    medium_position = None
    if mo != None:
        medium_position = album_title[mo.start(2):mo.end(2)].lstrip("0")
        album_title = album_title[0:mo.start(1)]
        if medium_position == "One" or medium_position == "one" or medium_position == "A":
            medium_position = "1"
        elif medium_position == "Two" or medium_position == "two" or medium_position == "B":
            medium_position = "2"
        return album_title, int(medium_position), -1, None

    return album_title, 0, 0, None

# user says additional info is in the EXTT fields

