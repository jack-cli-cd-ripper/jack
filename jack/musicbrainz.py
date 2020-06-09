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

import urllib.parse
import urllib.request
import urllib.error


def musicbrainz_template(tracks, names=""):
    "for now no need to create musicbrainz templates"
    pass


def musicbrainz_query(cd_id, tracks, file):

    host = jack.metadata.get_metadata_host('musicbrainz')
    toc = musicbrainz_gettoc(tracks)
    mb_id = cd_id['musicbrainzngs']
    includes = "artists+artist-credits+artist-rels+recordings+release-groups+release-rels+recording-rels+release-group-rels+isrcs+labels+label-rels+genres+url-rels+work-rels"
    query_url = "http://" + host + "/ws/2/discid/" + mb_id + "?toc=" + toc + "&inc=" + includes + "&fmt=json"
    user_agent = "%s/%s (%s)" % (jack.version.prog_name, jack.version.prog_version, jack.version.prog_url)
    headers = {'User-Agent': user_agent}

    request = urllib.request.Request(query_url, None, headers)
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        print('The server couldn\'t fulfill the request.')
        print('Error code: ', e.code)
        err = 1
        return err
    except urllib.error.URLError as e:
        print('The server couldn\'t be reached.')
        print('Reason: ', e.reason)
        err = 1
        return err
    response_data = response.read()
    result = json.loads(response_data)

    chosen_release = None
    if 'releases' in result:
        releases = result['releases']
        if len(releases) == 0:
            print("MusicBrainz did not return releases. Try adding one using this URL:\n" + musicbrainz_getlookupurl(tracks, cd_id))
            err = 1
            return err
        elif len(releases) == 1:
            chosen_release = 0
        elif len(releases) > 1:
            # FIXME this should be configurable behaviour
            old_chosen_release = None
            old_release_id = None
            if os.path.exists(file):
                f = open(file, "r")
                old_query_data = json.loads(f.read())
                f.close()

                old_chosen_release = old_query_data['chosen_release']
                old_release_id = old_query_data['result']['releases'][old_chosen_release]['id']

                for idx, rel in enumerate(releases):
                    if old_release_id and rel['id'] == old_release_id:
                        chosen_release = idx
                        warning("automatically selected release " + old_release_id)
 
            if chosen_release == None:
                print("Found the following matches. Choose one:")
                matches = []
                num = 1
                for rel in releases:
                    acp = ""
                    for ac in rel['artist-credit']:
                        acp += ac['name'] + ac['joinphrase']
                    description = acp + " - " + rel['title']
                    if 'disambiguation' in rel and rel['disambiguation'] and len(rel['disambiguation']):
                        description += " (" + rel['disambiguation'] + ")"
                    if 'packaging' in rel and rel['packaging'] and len(rel['packaging']):
                        description += " (" + rel['packaging'] + ")"
                    if 'country' in rel and rel['country'] and len(rel['country']):
                        description += " (" + rel['country'] + ")"
                    if 'date' in rel and rel['date'] and len(rel['date']):
                        description += " [" + rel['date'] + "]"
                    if 'media' in rel and len(rel['media']) > 1:
                        description += " (" + str(len(rel['media'])) + " CD's)"
                    if 'barcode' in rel and rel['barcode'] and len(rel['barcode']):
                        description += " (barcode: " + rel['barcode'] + ")"
                    labels = None
                    catalog_numbers = None
                    if 'label-info' in rel:
                        for li in rel['label-info']:
                            if 'label' in li and li['label']:
                                ln = li['label']['name']
                                if labels:
                                    labels += " / " + ln
                                else:
                                    labels = ln
                            if 'catalog-number' in li:
                                cn = li['catalog-number']
                                if catalog_numbers and cn:
                                    catalog_numbers += " / " + cn
                                else:
                                    catalog_numbers = cn
                    if labels:
                        description += " (label: " + labels + ")"
                    if catalog_numbers:
                        description += " (cat. nr: " + catalog_numbers + ")"
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
    "returns err, [(artist, albumname), (track_01-artist, track_01-name), ...], cd_id, mb_query_data"

    err = 0
    names = []
    read_id = None

    # load the musicbrainz query data that was previously dumped as json data
    f = open(name, "r")
    query_data = json.loads(f.read())
    f.close()

    if not 'releases' in query_data['result'] or len(query_data['result']['releases']) == 0:
        print("MusicBrainz did not return releases. Try adding one using this URL:\n" + musicbrainz_getlookupurl(tracks, cd_id))
        err = 1
        return err, names, read_id, query_data

    # user chose a specific release
    chosen_release = 0
    if 'chosen_release' in query_data and query_data['chosen_release']:
        chosen_release = int(query_data['chosen_release'])


    acp = ""
    for ac in query_data['result']['releases'][chosen_release]['artist-credit']:
        acp += ac['name']
        if 'joinphrase' in ac:
            acp += ac['joinphrase']
    a_artist = acp
    album = query_data['result']['releases'][chosen_release]['title']
    if 'date' in query_data['result']['releases'][chosen_release]:
        date = query_data['result']['releases'][chosen_release]['date']
    else:
        date = None
        warning("no date found in metadata")
    read_id = query_data['query_id']
    genre = None

    if a_artist.upper() in ("VARIOUS", "VARIOUS ARTISTS", "SAMPLER", "COMPILATION", "DIVERSE", "V.A.", "VA"):
        if not cf['_various'] and not ['argv', False] in cf['various']['history']:
            cf['_various'] = 1

    medium_position = None
    medium_count = len(query_data['result']['releases'][chosen_release]['media'])
    for idx, medium in enumerate(query_data['result']['releases'][chosen_release]['media']):
        for disc in medium['discs']:
            if disc['id'] == read_id:
                medium_position = idx + 1
                disc_subtitle = None
                if 'title' in medium and len(medium['title']):
                    disc_subtitle = medium['title']
                names.append([a_artist, album, date, genre, medium_position, medium_count, disc_subtitle])
                for track in medium['tracks']:
                    acp = ""
                    for ac in track['recording']['artist-credit']:
                        acp += ac['name']
                        if 'joinphrase' in ac:
                            acp += ac['joinphrase']
                    t_artist = acp
                    t_title = track['recording']['title']
                    if len(t_title) > 40 and ':' in t_title:
                        t_title = t_title.split(':')[0]
                    names.append([t_artist, t_title])
                break

    if medium_position == None:
        print("MusicBrainz returned releases, but none of them matched the disc ID. Try adding a disc id using this URL:\n" + musicbrainz_getlookupurl(tracks, cd_id))
        err = 1

    if len(names) == 0:
        print("error interpreting musicbrainz result")
        err = 1

    return err, names, read_id, query_data

def musicbrainz_gettoc(tracks):
    from jack.globals import START, MSF_OFFSET, CDDA_BLOCKS_PER_SECOND
    "get the toc for use in URL's"

    first_track = 1
    track_offsets = []
    for i in tracks:
        track_offsets.append(i[START] + MSF_OFFSET)
        last_track = i[NUM]
        num_sectors = i[START] + i[LEN] + MSF_OFFSET
    toc = str(first_track) + "+" + str(last_track) + "+" + str(num_sectors)
    for track_offset in track_offsets:
        toc += "+" + str(track_offset)

    return toc

def musicbrainz_getlookupurl(tracks, cd_id):
    host = jack.metadata.get_metadata_host('musicbrainz')
    toc = musicbrainz_gettoc(tracks)
    mb_id = cd_id['musicbrainzngs']
    url = "http://" + host + "/cdtoc/attach?id=" + mb_id + "&tracks=" + str(len(tracks)) + "&toc=" + toc

    return url

