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

import sys
import os
import json
import datetime
import re

import jack.functions
import jack.progress
import jack.utils
import jack.tag
import jack.misc

from jack.version import prog_version, prog_name
from jack.globals import *

import musicbrainzngs


def musicbrainz_template(tracks, names="", revision=0):
    "for now no need to create musicbrainz templates"
    pass


def musicbrainz_query(cd_id, tracks, file):

    # MusicBrainz does not support genres
    # before we query MusicBrainz, try to retrieve the genre from jack.freedb or from the command line
    genre = cf['_genre']
    if genre == None:
        freedb_form_file = jack.metadata.get_metadata_form_file('cddb')
        if os.path.exists(freedb_form_file):
            freedb_data = open(freedb_form_file).read()
            mo = re.search(r"DGENRE=(.*)", freedb_data)
            if mo:
                genre = mo.group(1)

    musicbrainzngs.set_useragent(jack.version.prog_name, jack.version.prog_version, jack.version.prog_devemail)

    mb_id = cd_id['musicbrainzngs']

    try:
        result = musicbrainzngs.get_releases_by_discid(mb_id, includes=["artists", "artist-credits", "labels", "recordings"])
    except musicbrainzngs.ResponseError:
        print("no match for", cd_id['musicbrainzngs'], "or bad response")
        err = 1
        return err

    query_data = {
        'query_id': mb_id,
        'query_date': datetime.datetime.now().isoformat(),
        'prog_version': jack.version.prog_version,
        'genre': genre,
        'result': result,
    }

    if os.path.exists(file):
        os.rename(file, file + ".bak")
    # dump the result in json format
    of = open(file, "w")
    of.write(json.dumps(query_data, indent=4) + "\n")
    of.close()

    err = 0
    return err


def musicbrainz_names(cd_id, tracks, todo, name, verb=0, warn=1):
    "returns err, [(artist, albumname), (track_01-artist, track_01-name), ...], cd_id, revision"

    revision = 0    # FreeDB specific

    err = 0
    chosen_release = 0
    chosen_disc = 0

    # load the musicbrainz query data that was previously dumped as json data
    f = open(name, "r")
    query_data = json.loads(f.read())
    f.close()

    names = []

    a_artist = query_data['result']['disc']['release-list'][chosen_release]['artist-credit-phrase']
    album = query_data['result']['disc']['release-list'][chosen_release]['title']
    date = query_data['result']['disc']['release-list'][chosen_release]['date']
    read_id = query_data['result']['disc']['id']
    genre = query_data['genre']

    for m in query_data['result']['disc']['release-list'][chosen_release]['medium-list']:
        if  len(m['disc-list']) > 0 and 'id' in m['disc-list'][chosen_disc] and m['disc-list'][chosen_disc]['id'] == read_id:
            if 'title' in m:
                album = m['title']
            d_position = m['position']
            names.append([a_artist, album, date, genre])
            for t in m['track-list']:
                t_artist = t['recording']['artist-credit-phrase']
                t_title = t['recording']['title']
                t_position = t['position']
                t_number = t['number']
                names.append([t_artist, t_title])
            break

    locale_names = names

    return err, names, locale_names, read_id, revision
