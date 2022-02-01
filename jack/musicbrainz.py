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
import requests

import jack.functions
import jack.progress
import jack.utils
import jack.tag
import jack.misc
import jack.version

from jack.globals import *


def musicbrainz_template(tracks, names=""):
    data = {
        'empty': True,
        'prog_version': jack.version.version,
    }
    form_file = jack.metadata.get_metadata_form_file(jack.metadata.get_metadata_api(cf['_metadata_server']))
    if os.path.exists(form_file):
        os.rename(form_file, form_file + ".bak")
    with open(form_file, "w") as f:
        f.write(json.dumps(data, indent=4) + "\n")


def get_response(url):
    debug(f"get_response({ url })")
    headers = {'User-Agent': jack.version.user_agent}

    try:
        r = requests.get(url, headers=headers)
        return 0, r
    except requests.exceptions.HTTPError as e:
        warning('The server couldn\'t fulfill the request. Error code: '
                + str(e.code))
        return 1, None
    except requests.exceptions.URLError as e:
        warning('The server couldn\'t be reached. Reason: ' + str( e.reason))
        return 1, None


def read_data_from(file):
    if not os.path.exists(file):
        return None
    with open(file, "r") as f:
        query_data = json.loads(f.read())

    if 'empty' in query_data and query_data['empty']:
        # this is an empty template
        return None

    return query_data


def musicbrainz_query(cd_id, tracks, file):

    host = jack.metadata.get_metadata_host('musicbrainz')
    toc = musicbrainz_gettoc(tracks)
    mb_id = cd_id['musicbrainzngs']
    includes = "artists+artist-credits+artist-rels+recordings+release-groups+release-rels+recording-rels+release-group-rels+isrcs+labels+label-rels+genres+url-rels+work-rels"
    query_url = "http://" + host + "/ws/2/discid/" + mb_id + "?toc=" + toc + "&inc=" + includes + "&fmt=json"
    err, response = get_response(query_url)
    if err:
        return err
    result = json.loads(response.text)
    response.close()

    chosen_release = None
    old_chosen_release = None
    old_release_id = None
    if not cf['_refresh_metadata']:
        old_query_data = read_data_from(file)
        if old_query_data:
            old_chosen_release = old_query_data['chosen_release']
            old_release_id = old_query_data['result']['releases'][old_chosen_release]['id']

            # remember the earlier choice to add disambiguation to the album title
            if 'add_disambiguation' in old_query_data and old_query_data['add_disambiguation']:
                cf['_add_disambiguation'] = True

    if 'releases' in result:
        releases = result['releases']
        if len(releases) == 0:
            print("MusicBrainz did not return releases. Try adding one using this URL:\n" + musicbrainz_getlookupurl(tracks, cd_id))
            err = 1
            return err
        exact_matches = False
        for release in releases:
            for medium in release['media']:
                for disc in medium['discs']:
                    if disc['id'] == mb_id:
                        exact_matches = True
        if len(releases) == 1 and exact_matches == True:
            chosen_release = 0
        else:
            if old_release_id:
                for idx, rel in enumerate(releases):
                    if rel['id'] == old_release_id:
                        chosen_release = idx
                        warning("automatically selected release " + old_release_id)

            if chosen_release == None:
                if exact_matches:
                    print("Found multiple exact matches. Choose one:")
                else:
                    print("Found the following inexact matches. Choose one:")
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
        'prog_version': jack.version.version,
        'chosen_release': chosen_release,
        'result': result,
    }
    if cf['_add_disambiguation']:
        query_data['add_disambiguation'] = True

    if os.path.exists(file):
        os.rename(file, file + ".bak")
    # dump the result in json format
    of = open(file, "w")
    of.write(json.dumps(query_data, indent=4) + "\n")
    of.close()

    artist_as_credited = ""
    for ac in release['artist-credit']:
        artist_as_credited += ac['name']
        if 'joinphrase' in ac:
            artist_as_credited += ac['joinphrase']

    info('matched "%s - %s"' % (artist_as_credited, release['title']))

    if cf['_fetch_albumart'] and 'coverartarchive' in cf['_albumart_providers']:
        jack.albumart.fetch_caa_albumart(result['releases'][chosen_release])

    if cf['_fetch_albumart'] and 'discogs' in cf['_albumart_providers']:
        jack.albumart.fetch_discogs_albumart(result['releases'][chosen_release])

    if cf['_fetch_albumart'] and 'iTunes' in cf['_albumart_providers']:
        jack.albumart.fetch_itunes_albumart(artist_as_credited, release['title'])

    err = 0
    return err


mb_names_calls = 0

def musicbrainz_names(cd_id, tracks, todo, name, verb=None, warn=None):
    "returns err, [(artist, albumname), (track_01-artist, track_01-name), ...], cd_id, mb_query_data"

    global mb_names_calls
    err = 0
    names = []
    read_id = None

    # load the musicbrainz query data that was previously dumped as json data
    query_data = read_data_from(name)
    if not query_data:
        err = 1
        return err, names, read_id, query_data

    if not 'releases' in query_data['result'] or len(query_data['result']['releases']) == 0:
        print("MusicBrainz did not return releases. Try adding one using this URL:\n" + musicbrainz_getlookupurl(tracks, cd_id))
        err = 1
        return err, names, read_id, query_data

    # user chose a specific release
    chosen_release = 0
    if 'chosen_release' in query_data and query_data['chosen_release']:
        chosen_release = int(query_data['chosen_release'])
    release = query_data['result']['releases'][chosen_release]

    # get the artist name for use in constructing the path
    artist_as_credited = ""
    artist_as_in_mb = ""
    artist_as_sort_name = ""
    for ac in release['artist-credit']:
        artist_as_credited += ac['name']
        artist_as_in_mb += ac['artist']['name']
        artist_as_sort_name += ac['artist']['sort-name']
        if 'joinphrase' in ac:
            artist_as_credited += ac['joinphrase']
            artist_as_in_mb += ac['joinphrase']
            artist_as_sort_name += ac['joinphrase']

    if cf['_file_artist'] == 'as-credited':
        a_artist = artist_as_credited
    elif cf['_file_artist'] == 'as-sort-name':
        a_artist = artist_as_sort_name
    else:
        a_artist = artist_as_in_mb

    # remember the earlier choice to add disambiguation to the album title
    if 'add_disambiguation' in query_data and query_data['add_disambiguation']:
        cf['_add_disambiguation'] = True

    # get the album name for use in constructing the path
    album = release['title']
    if cf['_add_disambiguation'] and 'disambiguation' in release and len(release['disambiguation']):
        album += " (" + release['disambiguation'] + ")"
    if 'date' in release:
        date = release['date']
    else:
        date = None
        if mb_names_calls == 0:
            warning("no date found in metadata")
    read_id = query_data['query_id']
    genre = None

    if a_artist == "Various Artists":
        if not cf['_various'] and not ['argv', False] in cf['various']['history']:
            cf['_various'] = 1

    exact_match = None
    medium_position = None
    medium_count = len(release['media'])
    for idx, medium in enumerate(release['media']):
        for disc in medium['discs']:
            if disc['id'] == read_id:
                exact_match = idx
                medium_position = idx + 1

    if exact_match == None:
        if mb_names_calls == 0:
            attach_url = musicbrainz_getlookupurl(tracks, cd_id) + "&filter-release.query=" + release['id']
            warning("Inexact match. If you are sure the release matches, then attach the Disc ID using this URL: " +
                    attach_url + "\n")
        best_match = None
        if medium_count == 1:
            best_match = 0
            medium_position = 1
        else:
            least_deviation = None
            for idx, medium in enumerate(release['media']):
                if len(medium['tracks']) == len(tracks):
                    deviation = 0
                    for track in medium['tracks']:
                        track_position = int(track['position']) - 1
                        toc_track_len = tracks[track_position][LEN] * 1000 // CDDA_BLOCKS_PER_SECOND
                        mb_track_len = int(track['length'])
                        deviation += abs(mb_track_len - toc_track_len)
                    if least_deviation == None or deviation < least_deviation:
                        least_deviation = deviation
                        best_match = idx
                        medium_position = idx + 1

    if medium_position:
        medium = release['media'][medium_position - 1]
        if exact_match == None and medium_count > 1 and mb_names_calls == 0:
            warning("guessed medium position %d/%d" % (medium_position, medium_count))
    else:
        error("cannot determine medium position in chosen release")
        sys.exit()

    disc_subtitle = None
    if 'title' in medium and len(medium['title']):
        disc_subtitle = medium['title']
    names.append([a_artist, album, date, genre, medium_position, medium_count, disc_subtitle])
    for track in medium['tracks']:
        artist_as_credited = ""
        artist_as_in_mb = ""
        artist_as_sort_name = ""
        for ac in track['recording']['artist-credit']:
            artist_as_credited += ac['name']
            artist_as_in_mb += ac['artist']['name']
            artist_as_sort_name += ac['artist']['sort-name']
            if 'joinphrase' in ac:
                artist_as_credited += ac['joinphrase']
                artist_as_in_mb += ac['joinphrase']
                artist_as_sort_name += ac['joinphrase']
        if cf['_file_artist'] == 'as-credited':
            t_artist = artist_as_credited
        elif cf['_file_artist'] == 'as-sort-name':
            t_artist = artist_as_sort_name
        else:
            t_artist = artist_as_in_mb
        t_title = track['recording']['title']
        t_artist = jack.utils.smart_truncate(t_artist)
        t_title = jack.utils.smart_truncate(t_title)
        names.append([t_artist, t_title])

    # try to use year from chosen release array element
    if cf['_year'] is None:
        try:
            mb_date = release['date'][:4]
            cf['_year'] = mb_date
            debug("using year from ['releases'][chosen_release]['date']"
                  + f" = { repr(mb_date) } -> { cf['_year'] }")
        except (TypeError, ValueError) as ex:
            warning("could not parse year from ['releases'][chosen_release]"
                    + f"['date']: { ex }")

    if len(names) == 0:
        print("error interpreting musicbrainz result")
        err = 1

    mb_names_calls += 1
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

def musicbrainz_lookup(tracks, cd_id):

    import webbrowser

    url = musicbrainz_getlookupurl(tracks, cd_id)
    print("opening url", url, "in browser")
    webbrowser.open(url)
