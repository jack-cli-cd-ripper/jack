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
                warning("imported genre '" + genre + "' from " + freedb_form_file)

    musicbrainzngs.set_useragent(jack.version.prog_name, jack.version.prog_version, jack.version.prog_devemail)

    mb_id = cd_id['musicbrainzngs']

    try:
        result = musicbrainzngs.get_releases_by_discid(mb_id, includes=["artists", "artist-credits", "labels", "recordings", "recording-rels"])
    except musicbrainzngs.ResponseError:
        print("no match for", cd_id['musicbrainzngs'], "or bad response")
        err = 1
        return err

    # allow user to choose release if there are multiple
    chosen_release = 0
    if 'disc' in result:
        if result['disc']['release-count'] > 1:
            print("Found the following matches. Choose one:")
            matches = []
            num = 1
            for rel in result['disc']['release-list']:
                description = rel['artist-credit-phrase'] + " - " + rel['title']
                if 'disambiguation' in rel:
                    description += " (" + rel['disambiguation'] + ")"
                if 'packaging' in rel:
                    description += " (" + rel['packaging'] + ")"
                if 'country' in rel:
                    description += " (" + rel['country'] + ")"
                description += " [" + rel['date'] + "]"
                print("%2i" % num + ".) " + description)
                num = num + 1
            x = -1
            while x < 0 or x > num - 1:
                userinput = input(" 0.) none of the above: ")
                if not userinput:
                    continue
                try:
                    x = int(userinput)
                except ValueError:
                    x = -1    # start the loop again
                if not x:
                    print("ok, aborting.")
                    sys.exit()
            chosen_release = x - 1

    query_data = {
        'query_id': mb_id,
        'query_date': datetime.datetime.now().isoformat(),
        'prog_version': jack.version.prog_version,
        'chosen_release': chosen_release,
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

    if 'cdstub' in query_data['result']:
        error("musicbrainz returned a \"cdstub\" result instead of a \"disc\" result")
    if not 'disc' in query_data['result']:
        error("musicbrainz did not return a \"disc\" result")

    # user chose a specific release
    if 'chosen_release' in query_data and query_data['chosen_release']:
        chosen_release = int(query_data['chosen_release'])

    names = []

    a_artist = query_data['result']['disc']['release-list'][chosen_release]['artist-credit-phrase']
    album = query_data['result']['disc']['release-list'][chosen_release]['title']
    if 'date' in query_data['result']['disc']['release-list'][chosen_release]:
        date = query_data['result']['disc']['release-list'][chosen_release]['date']
    else:
        warning("no date found in metadata")
    read_id = query_data['result']['disc']['id']
    genre = query_data['genre']


    for medium in query_data['result']['disc']['release-list'][chosen_release]['medium-list']:
        for disc in medium['disc-list']:
            if disc['id'] == read_id:
                if 'title' in medium:
                    album = medium['title']
                d_position = medium['position']
                names.append([a_artist, album, date, genre])
                for track in medium['track-list']:
                    t_artist = track['recording']['artist-credit-phrase']
                    t_title = track['recording']['title']
                    t_position = track['position']
                    t_number = track['number']
                    names.append([t_artist, t_title])
                break

    if len(names) == 0:
        error("error interpreting musicbrainz result")

    locale_names = names

    return err, names, locale_names, read_id, revision
