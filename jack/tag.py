# -*- coding: utf-8 -*-
# jack.tag: name information (ID3 among others) stuff for
# jack - tag audio from a CD and encode it using 3rd party software
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

import os
import sys
import re

import jack.functions
import jack.ripstuff
import jack.targets
import jack.helpers
import jack.metadata
import jack.utils
import jack.misc
import jack.m3u

from jack.init import oggvorbis
from jack.init import mp3
from jack.init import id3
from jack.init import flac
from jack.init import mp4
from jack.globals import *

track_names = None
mb_query_data = None

a_artist = None
a_title = None


def tag(metadata_rename):
    global a_artist, a_title

    medium_position = 0
    medium_count = 0
    medium_tagging = False

    ext = jack.targets.targets[jack.helpers.helpers[cf['_encoder']]['target']]['file_extension']

    if cf['_vbr'] and not cf['_only_dae']:
        total_length = 0
        total_size = 0
        for i in jack.ripstuff.all_tracks_todo_sorted:
            total_length = total_length + i[LEN]
            total_size = total_size + jack.utils.filesize(i[NAME] + ext)

    if cf['_set_tag'] and not jack.targets.targets[jack.helpers.helpers[cf['_encoder']]['target']]['can_posttag']:
        cf['_set_tag'] = 0

    if jack.metadata.names_available:
        a_artist = track_names[0][0]
        a_title = track_names[0][1]
        medium_position = track_names[0][4]
        medium_count = track_names[0][5]

        if medium_count == -1 or medium_count > 1:
            medium_tagging = True
            if medium_count == -1:
                medium_count = 0

    all_targets = []
    for helper_key, helper_values in jack.helpers.helpers.items():
        if helper_values['type'] == 'encoder':
            target = helper_values['target']
            if target not in all_targets:
                all_targets.append(target)

    if cf['_set_tag'] or metadata_rename:
        jack.m3u.init()
        # use metadata year and genre data if available
        if cf['_year'] == None and len(track_names[0]) >= 3:
            cf['_year'] = track_names[0][2]
        if cf['_genre'] == None and len(track_names[0]) == 4:
            cf['_genre'] = track_names[0][3]
        if cf['_genre']:
            cf['_genre'] = fix_genre_case(cf['_genre'])

        print("Tagging", end=' ')
        for i in jack.ripstuff.all_tracks_todo_sorted:
            sys.stdout.write(".")
            sys.stdout.flush()

            track_position = i[NUM]
            track_count = len(jack.ripstuff.all_tracks_orig)

            all_exts = [ext,]
            for check_ext in all_targets:
                check_ext = "." + check_ext
                if check_ext == ext:
                    continue
                encname = i[NAME] + check_ext
                if os.path.exists(encname):
                    all_exts.append(check_ext)
            
            for cur_ext in all_exts:
                target = cur_ext[1:]
                encname = i[NAME] + cur_ext
                wavname = i[NAME] + ".wav"
                if track_names[i[NUM]][0]:
                    t_artist = track_names[i[NUM]][0]
                else:
                    t_artist = a_artist
                t_name = track_names[i[NUM]][1]
                if not cf['_only_dae'] and cf['_set_tag']:
                    if target == "mp3":
                        track_info = "%s/%s" % (track_position, track_count)
                        medium_info = "%s/%s" % (medium_position, medium_count)
                        audio = mp3.MP3(encname)
                        if audio.tags == None:
                            audio.add_tags()
                        # FIXME delete old tags
                        tags = audio.tags
                        if not cf['_various']:
                            tags.add(id3.TPE2(encoding=3, text=a_artist))
                        tags.add(id3.TPE1(encoding=3, text=t_artist))
                        tags.add(id3.TALB(encoding=3, text=a_title))
                        tags.add(id3.TIT2(encoding=3, text=t_name))
                        if cf['_genre']:
                            tags.add(id3.TCON(encoding=3, text=cf['_genre']))
                        if cf['_year']:
                            tags.add(id3.TDRL(encoding=3, text=cf['_year']))
                        tags.add(id3.TRCK(encoding=3, text=track_info))
                        if medium_tagging:
                            tags.add(id3.TPOS(encoding=3, text=medium_info))
                        audio.save()
                    elif target == "flac" or target == "ogg":   # both vorbis tags
                        if target == "flac":
                            f = flac.FLAC(encname)
                        elif target == "ogg":
                            f = oggvorbis.OggVorbis(encname)
                        if f.tags == None:
                            f.add_vorbiscomment()
                        f.delete() # delete old tags
                        if cf['_set_extended_tag']:
                            extended_tag(f.tags, "vorbis", track_position)
                        else:
                            if not cf['_various']:
                                f.tags['ALBUMARTIST'] = a_artist
                            f.tags['ARTIST'] = t_artist
                            f.tags['ALBUM'] = a_title
                            f.tags['TITLE'] = t_name
                            if cf['_genre']:
                                f.tags['GENRE'] = cf['_genre']
                            if cf['_year']:
                                f.tags['DATE'] = cf['_year']
                            f.tags['TRACKNUMBER'] = str(track_position)
                            f.tags['TRACKTOTAL'] = str(track_count)
                            if medium_tagging:
                                f.tags['DISCNUMBER'] = str(medium_position)
                                if medium_count:
                                    f.tags['DISCTOTAL'] = str(medium_count)
                            if cf['_various']:
                                f.tags['COMPILATION'] = "1"
                        f.save()
                    elif target == "m4a":
                        m4a = mp4.MP4(encname)
                        # delete old tags
                        keeptags = ['©too', '----:com.apple.iTunes:iTunSMPB'] # set by fdkaac
                        for tag in list(m4a.tags):
                            if tag not in keeptags:
                                m4a.tags.pop(tag)
                        if not cf['_various']:
                            m4a.tags['aART'] = [a_artist]
                        m4a.tags['©ART'] = [t_artist]
                        m4a.tags['©alb'] = [a_title]
                        m4a.tags['©nam'] = [t_name]
                        if cf['_genre']:
                            m4a.tags['©gen'] = [cf['_genre']]
                        if cf['_year']:
                            m4a.tags['©day'] = [cf['_year']]
                        m4a.tags['trkn'] = [(track_position, track_count)]
                        if medium_tagging:
                            m4a.tags['disk'] = [(medium_position, medium_count)]
                        m4a.tags['cpil'] = bool(cf['_various'])
                        m4a.save()
            if metadata_rename:
                newname = jack.metadata.filenames[i[NUM]]
                encname = i[NAME] + ext
                if i[NAME] != newname:
                    p_newname = newname
                    u_newname = newname
                    newname = newname
                    p_encname = i[NAME]
                    p_wavname = i[NAME]
                    ok = 1
                    if os.path.exists(newname + ext):
                        ok = 0
                        print('NOT renaming "' + p_encname + '" to "' + p_newname + ext + '" because dest. exists.')
                        if cf['_keep_wavs']:
                            print('NOT renaming "' + p_wavname + '" to "' + p_newname + ".wav" + '" because dest. exists.')
                    elif cf['_keep_wavs'] and os.path.exists(newname + ".wav"):
                        ok = 0
                        print('NOT renaming "' + p_wavname + '" to "' + p_newname + ".wav" + '" because dest. exists.')
                        print('NOT renaming "' + p_encname + '" to "' + p_newname + ext + '" because WAV dest. exists.')
                    if ok:
                        if not cf['_only_dae']:
                            try:
                                os.rename(encname, newname + ext)
                            except OSError:
                                error('Cannot rename "%s" to "%s" (Filename is too long or has unusable characters)' % (p_encname, p_newname + ext))
                            jack.m3u.add(newname + ext)
                        if cf['_keep_wavs']:
                            os.rename(wavname, newname + ".wav")
                            jack.m3u.add_wav(newname + ".wav")
                        for t in all_targets:
                            e = "." + t
                            if e != ext:
                                othername = i[NAME] + e
                                if os.path.exists(othername):
                                    if os.path.exists(newname + e):
                                        print('NOT renaming "' + othername + '" to "' + newname + e + '" because dest. exists.')
                                    else:
                                        os.rename(othername, newname + e)
                        jack.functions.progress(i[NUM], "ren", "%s-->%s" % (i[NAME], u_newname))
                    elif cf['_silent_mode']:
                        jack.functions.progress(i[NUM], "err", "while renaming track")
        print()

    if not cf['_silent_mode']:
        if jack.metadata.names_available:
            print("Done with \"" + a_artist + " - " + a_title + "\".")
        else:
            print("All done.", end=' ')
        if cf['_set_tag'] and cf['_year']:
            print("Year: %s" % cf['_year'])
        if cf['_set_tag'] and cf['_genre']:
            print("Genre: %s" % cf['_genre'])
        if cf['_vbr'] and not cf['_only_dae']:
            print("Avg. bitrate: %03.0fkbit" % ((total_size * 0.008) / (total_length / 75)))
        else:
            print()

    if jack.m3u.m3u:
        os.environ["JACK_JUST_ENCODED"] = "\n".join(jack.m3u.m3u)
    if jack.m3u.wavm3u:
        os.environ["JACK_JUST_RIPPED"] = "\n".join(jack.m3u.wavm3u)
    jack.m3u.write()

def fix_genre_case(genre):

    from mutagen._constants import GENRES

    for id3genre in GENRES:
        if genre.upper() == id3genre.upper():
            return id3genre
    return genre


def extended_tag(tagobject, tagtype, track_position):

    # taken from https://picard.musicbrainz.org/docs/mappings/
    mb_tag_map = [
        {
                # part of basic tagging
                "internalname": "album",
                "name": "Album",
                "mp3": "TALB",
                "vorbis": "ALBUM",
                "m4a": "©alb",
                "mbpath": ["_release_", "title"]
        },
        {
                "internalname": "albumsort",
                "name": "Album Sort Order",
                "mp3": "TSOA",
                "vorbis": "ALBUMSORT",
                "m4a": "soal",
                "mbpath": ["_release_", "sort-name"]
        },
        {
                # part of basic tagging
                "internalname": "title",
                "name": "Track Title",
                "mp3": "TIT2",
                "vorbis": "TITLE",
                "m4a": "©nam",
                "mbpath": ["_track_", "recording", "title"]
        },
        {
                "internalname": "titlesort",
                "name": "Track Title Sort Order",
                "mp3": "TSOT",
                "vorbis": "TITLESORT",
                "m4a": "sonm",
                "mbpath": ["_track_", "recording", "sort-name"]
        },
        {
                "internalname": "work",
                "name": "Work Title",
                "mp3": "TIT1",
                "vorbis": "WORK",
                "m4a": "©wrk",
        },
        {
                # part of basic tagging
                "internalname": "artist",
                "name": "Artist",
                "mp3": "TPE1",
                "vorbis": "ARTIST",
                "m4a": "©ART",
                "mbpath": ["_track_", "recording", "artist-credit-phrase"]
        },
        {
                "internalname": "artistsort",
                "name": "Artist Sort Order",
                "mp3": "TSOP",
                "vorbis": "ARTISTSORT",
                "m4a": "soar",
                "mbpath": ["_track_", "recording", "artist-credit", "_concatenate_", "artist", "sort-name"]
        },
        {
                # part of basic tagging, using equivalent of ["_release_", "artist-credit-phrase"]
                "internalname": "albumartist",
                "name": "Album Artist",
                "mp3": "TPE2",
                "vorbis": "ALBUMARTIST",
                "m4a": "aART",
                "mbpath": ["_release_", "artist-credit", "_concatenate_", "artist", "name"]
        },
        {
                "internalname": "albumartistsort",
                "name": "Album Artist Sort Order",
                "mp3": "TSO2",
                "vorbis": "ALBUMARTISTSORT",
                "m4a": "soaa",
                "mbpath": ["_release_", "artist-credit", "_concatenate_", "artist", "sort-name"]
        },
        {
                "internalname": "artists",
                "name": "Artists",
                "mp3": "TXXX:Artists",
                "vorbis": "ARTISTS",
                "m4a": "----:com.apple.iTunes:ARTISTS",
                "mbpath": ["_track_", "recording", "artist-credit", "_multi_", "artist", "name"]
        },
        {
                # part of basic tagging
                "internalname": "date",
                "name": "Release Date",
                "mp3": "TDRC",
                "vorbis": "DATE",
                "m4a": "©day",
                "mbpath": ["_release_", "date"]
        },
        {
                "internalname": "originalalbum",
                "name": "Original Album",
                "mp3": "TOAL",
                "vorbis": None,
                "m4a": None,
        },
        {
                "internalname": "originalartist",
                "name": "Original Artist",
                "mp3": "TOPE",
                "vorbis": None,
                "m4a": None,
        },
        {
                "internalname": "originaldate",
                "name": "Original Release Date",
                "mp3": "TDOR",
                "vorbis": "ORIGINALDATE",
                "m4a": None,
        },
        {
                "internalname": "originalyear",
                "name": "Original Release Year",
                "mp3": None,
                "vorbis": "ORIGINALYEAR",
                "m4a": None,
        },
        {
                "internalname": "originalfilename",
                "name": "Original Filename",
                "mp3": "TOFN",
                "vorbis": "ORIGINALFILENAME",
                "m4a": None,
        },
        {
                "internalname": "composer",
                "name": "Composer",
                "mp3": "TCOM",
                "vorbis": "COMPOSER",
                "m4a": "©wrt",
        },
        {
                "internalname": "composersort",
                "name": "Composer Sort Order",
                "mp3": "TSOC",
                "vorbis": "COMPOSERSORT",
                "m4a": "soco",
        },
        {
                "internalname": "lyricist",
                "name": "Lyricist",
                "mp3": "TEXT",
                "vorbis": "LYRICIST",
                "m4a": "----:com.apple.iTunes:LYRICIST",
        },
        {
                "internalname": "writer",
                "name": "Writer",
                "mp3": "TXXX:Writer",
                "vorbis": "WRITER",
                "m4a": "",
        },
        {
                "internalname": "conductor",
                "name": "Conductor",
                "mp3": "TPE3",
                "vorbis": "CONDUCTOR",
                "m4a": "----:com.apple.iTunes:CONDUCTOR",
        },
        {
                "internalname": "performer:instrument",
                "name": "Performer [instrument]",
                "mp3": "TMCL:instrument",
                "vorbis": "PERFORMER={artist} (instrument)",
                "m4a": "",
        },
        {
                "internalname": "remixer",
                "name": "Remixer",
                "mp3": "TPE4",
                "vorbis": "REMIXER",
                "m4a": "----:com.apple.iTunes:REMIXER",
        },
        {
                "internalname": "arranger",
                "name": "Arranger",
                "mp3": "TIPL:arranger",
                "vorbis": "ARRANGER",
                "m4a": "",
        },
        {
                "internalname": "engineer",
                "name": "Engineer",
                "mp3": "TIPL:engineer",
                "vorbis": "ENGINEER",
                "m4a": "----:com.apple.iTunes:ENGINEER",
        },
        {
                "internalname": "producer",
                "name": "Producer",
                "mp3": "TIPL:producer",
                "vorbis": "PRODUCER",
                "m4a": "----:com.apple.iTunes:PRODUCER",
        },
        {
                "internalname": "djmixer",
                "name": "Mix-DJ",
                "mp3": "TIPL:DJ-mix",
                "vorbis": "DJMIXER",
                "m4a": "----:com.apple.iTunes:DJMIXER",
        },
        {
                "internalname": "mixer",
                "name": "Mixer",
                "mp3": "TIPL:mix",
                "vorbis": "MIXER",
                "m4a": "----:com.apple.iTunes:MIXER",
        },
        {
                "internalname": "label",
                "name": "Record Label",
                "mp3": "TPUB",
                "vorbis": "LABEL",
                "m4a": "----:com.apple.iTunes:LABEL",
                "mbpath": ["_release_", "label-info-list", "_first_", "label", "name"]
        },
        {
                "internalname": "movement",
                "name": "Movement",
                "mp3": "MVNM",
                "vorbis": "MOVEMENTNAME",
                "m4a": "©mvn",
        },
        {
                "internalname": "movementnumber",
                "name": "Movement Number",
                "mp3": "MVIN",
                "vorbis": "MOVEMENT",
                "m4a": "mvi",
        },
        {
                "internalname": "movementtotal",
                "name": "Movement Count",
                "mp3": "MVIN",
                "vorbis": "MOVEMENTTOTAL",
                "m4a": "mvc",
        },
        {
                "internalname": "showmovement",
                "name": "Show Work & Movement",
                "mp3": "TXXX:SHOWMOVEMENT",
                "vorbis": "SHOWMOVEMENT",
                "m4a": "shwm",
        },
        {
                "internalname": "grouping",
                "name": "Grouping",
                "mp3": "GRP1",
                "vorbis": "GROUPING",
                "m4a": "©grp",
        },
        {
                "internalname": "subtitle",
                "name": "Subtitle",
                "mp3": "TIT3",
                "vorbis": "SUBTITLE",
                "m4a": "----:com.apple.iTunes:SUBTITLE",
        },
        {
                "internalname": "discsubtitle",
                "name": "Disc Subtitle",
                "mp3": "TSST",
                "vorbis": "DISCSUBTITLE",
                "m4a": "----:com.apple.iTunes:DISCSUBTITLE",
        },
        {
                # part of basic tagging
                "internalname": "tracknumber",
                "name": "Track Number",
                "mp3": "TRCK",
                "vorbis": "TRACKNUMBER",
                "m4a": "trkn",
                "mbpath": ["_track_", "position"]
        },
        {
                # part of basic tagging
                "internalname": "totaltracks",
                "name": "Total Tracks",
                "mp3": "TRCK",
                "vorbis": "TRACKTOTAL",
                "m4a": "trkn",
                "mbpath": ["_medium_", "track-count"]
        },
        {
                # part of basic tagging
                "internalname": "discnumber",
                "name": "Disc Number",
                "mp3": "TPOS",
                "vorbis": "DISCNUMBER",
                "m4a": "disk",
                "mbpath": ["_medium_", "position"]
        },
        {
                # part of basic tagging
                "internalname": "totaldiscs",
                "name": "Total Discs",
                "mp3": "TPOS",
                "vorbis": "DISCTOTAL",
                "m4a": "disk",
                "mbpath": ["_release_", "medium-count"]
        },
        {
                # part of basic tagging
                "internalname": "compilation",
                "name": "Compilation (iTunes)",
                "mp3": "TCMP",
                "vorbis": "COMPILATION",
                "m4a": "cpil",
                "mbpath": ["_compilation_"]
        },
        {
                "internalname": "comment:description",
                "name": "Comment",
                "mp3": "COMM:description",
                "vorbis": "COMMENT",
                "m4a": "©cmt",
        },
        {
                # part of basic tagging
                "internalname": "genre",
                "name": "Genre",
                "mp3": "TCON",
                "vorbis": "GENRE",
                "m4a": "©gen",
                "mbpath": ["_genre_"]
        },
        {
                "internalname": "_rating",
                "name": "Rating",
                "mp3": "POPM",
                "vorbis": "RATING:user@email",
                "m4a": None,
        },
        {
                "internalname": "bpm",
                "name": "BPM",
                "mp3": "TBPM",
                "vorbis": "BPM",
                "m4a": "tmpo",
        },
        {
                "internalname": "mood",
                "name": "Mood",
                "mp3": "TMOO",
                "vorbis": "MOOD",
                "m4a": "----:com.apple.iTunes:MOOD",
        },
        {
                "internalname": "lyrics:description",
                "name": "Lyrics",
                "mp3": "USLT:description",
                "vorbis": "LYRICS",
                "m4a": "©lyr",
        },
        {
                "internalname": "media",
                "name": "Media",
                "mp3": "TMED",
                "vorbis": "MEDIA",
                "m4a": "----:com.apple.iTunes:MEDIA",
                "mbpath": ["_medium_", "format"]
        },
        {
                "internalname": "catalognumber",
                "name": "Catalog Number",
                "mp3": "TXXX:CATALOGNUMBER",
                "vorbis": "CATALOGNUMBER",
                "m4a": "----:com.apple.iTunes:CATALOGNUMBER",
                "mbpath": ["_release_", "label-info-list", "_first_", "catalog-number"]
        },
        {
                "internalname": "show",
                "name": "Show Name",
                "mp3": None,
                "vorbis": None,
                "m4a": "tvsh",
        },
        {
                "internalname": "showsort",
                "name": "Show Name Sort Order",
                "mp3": None,
                "vorbis": None,
                "m4a": "sosn",
        },
        {
                "internalname": "podcast",
                "name": "Podcast",
                "mp3": None,
                "vorbis": None,
                "m4a": "pcst",
        },
        {
                "internalname": "podcasturl",
                "name": "Podcast URL",
                "mp3": None,
                "vorbis": None,
                "m4a": "purl",
        },
        {
                "internalname": "releasestatus",
                "name": "Release Status",
                "mp3": "TXXX:MusicBrainz Album Status",
                "vorbis": "RELEASESTATUS",
                "m4a": "----:com.apple.iTunes:MusicBrainz Album Status",
        },
        {
                "internalname": "releasetype",
                "name": "Release Type",
                "mp3": "TXXX:MusicBrainz Album Type",
                "vorbis": "RELEASETYPE",
                "m4a": "----:com.apple.iTunes:MusicBrainz Album Type",
        },
        {
                "internalname": "releasecountry",
                "name": "Release Country",
                "mp3": "TXXX:MusicBrainz Album Release Country",
                "vorbis": "RELEASECOUNTRY",
                "m4a": "----:com.apple.iTunes:MusicBrainz Album Release Country",
                "mbpath": ["_release_", "country"]
        },
        {
                "internalname": "script",
                "name": "Script",
                "mp3": "TXXX:SCRIPT",
                "vorbis": "SCRIPT",
                "m4a": "----:com.apple.iTunes:SCRIPT",
                "mbpath": ["_release_", "text-representation", "script"]
        },
        {
                "internalname": "language",
                "name": "Language",
                "mp3": "TLAN",
                "vorbis": "LANGUAGE",
                "m4a": "----:com.apple.iTunes:LANGUAGE",
                "mbpath": ["_release_", "text-representation", "language"]
        },
        {
                "internalname": "copyright",
                "name": "Copyright",
                "mp3": "TCOP",
                "vorbis": "COPYRIGHT",
                "m4a": "cprt",
        },
        {
                "internalname": "license",
                "name": "License",
                "mp3": "WCOP",
                "vorbis": "LICENSE",
                "m4a": "----:com.apple.iTunes:LICENSE",
        },
        {
                # handled by encoder
                "internalname": "encodedby",
                "name": "Encoded By",
                "mp3": "TENC",
                "vorbis": "ENCODEDBY",
                "m4a": "©too",
        },
        {
                # handled by encoder
                "internalname": "encodersettings",
                "name": "Encoder Settings",
                "mp3": "TSSE",
                "vorbis": "ENCODERSETTINGS",
                "m4a": None,
        },
        {
                "internalname": "gapless",
                "name": "Gapless Playback",
                "mp3": None,
                "vorbis": None,
                "m4a": "pgap",
        },
        {
                "internalname": "barcode",
                "name": "Barcode",
                "mp3": "TXXX:BARCODE",
                "vorbis": "BARCODE",
                "m4a": "----:com.apple.iTunes:BARCODE",
                "mbpath": ["_release_", "barcode"]
        },
        {
                "internalname": "isrc",
                "name": "ISRC",
                "mp3": "TSRC",
                "vorbis": "ISRC",
                "m4a": "----:com.apple.iTunes:ISRC",
        },
        {
                "internalname": "asin",
                "name": "ASIN",
                "mp3": "TXXX:ASIN",
                "vorbis": "ASIN",
                "m4a": "----:com.apple.iTunes:ASIN",
                "mbpath": ["_release_", "asin"]
        },
        {
                "internalname": "musicbrainz_recordingid",
                "name": "MusicBrainz Recording Id",
                "mp3": "UFID://musicbrainz.org",
                "vorbis": "MUSICBRAINZ_TRACKID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Track Id",
                "mbpath": ["_track_", "recording", "id"]
        },
        {
                "internalname": "musicbrainz_trackid",
                "name": "MusicBrainz Track Id",
                "mp3": "TXXX:MusicBrainz Release Track Id",
                "vorbis": "MUSICBRAINZ_RELEASETRACKID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Release Track Id",
                "mbpath": ["_track_", "id"]
        },
        {
                "internalname": "musicbrainz_albumid",
                "name": "MusicBrainz Release Id",
                "mp3": "TXXX:MusicBrainz Album Id",
                "vorbis": "MUSICBRAINZ_ALBUMID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Album Id",
                "mbpath": ["_release_", "id"]
        },
        {
                "internalname": "musicbrainz_originalalbumid",
                "name": "MusicBrainz Original Release Id",
                "mp3": "TXXX:MusicBrainz Original Album Id",
                "vorbis": "MUSICBRAINZ_ORIGINALALBUMID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Original Album Id",
        },
        {
                "internalname": "musicbrainz_artistid",
                "name": "MusicBrainz Artist Id",
                "mp3": "TXXX:MusicBrainz Artist Id",
                "vorbis": "MUSICBRAINZ_ARTISTID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Artist Id",
                "mbpath": ["_track_", "recording", "artist-credit", "_multi_", "artist", "id"]
        },
        {
                "internalname": "musicbrainz_originalartistid",
                "name": "MusicBrainz Original Artist Id",
                "mp3": "TXXX:MusicBrainz Original Artist Id",
                "vorbis": "MUSICBRAINZ_ORIGINALARTISTID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Original Artist Id",
        },
        {
                "internalname": "musicbrainz_albumartistid",
                "name": "MusicBrainz Release Artist Id",
                "mp3": "TXXX:MusicBrainz Album Artist Id",
                "vorbis": "MUSICBRAINZ_ALBUMARTISTID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Album Artist Id",
                "mbpath": ["_release_", "artist-credit", "_multi_", "artist", "id"]
        },
        {
                "internalname": "musicbrainz_releasegroupid",
                "name": "MusicBrainz Release Group Id",
                "mp3": "TXXX:MusicBrainz Release Group Id",
                "vorbis": "MUSICBRAINZ_RELEASEGROUPID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Release Group Id",
        },
        {
                "internalname": "musicbrainz_workid",
                "name": "MusicBrainz Work Id",
                "mp3": "TXXX:MusicBrainz Work Id",
                "vorbis": "MUSICBRAINZ_WORKID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Work Id",
        },
        {
                "internalname": "musicbrainz_trmid",
                "name": "MusicBrainz TRM Id",
                "mp3": "TXXX:MusicBrainz TRM Id",
                "vorbis": "MUSICBRAINZ_TRMID",
                "m4a": "----:com.apple.iTunes:MusicBrainz TRM Id",
        },
        {
                "internalname": "musicbrainz_discid",
                "name": "MusicBrainz Disc Id",
                "mp3": "TXXX:MusicBrainz Disc Id",
                "vorbis": "MUSICBRAINZ_DISCID",
                "m4a": "----:com.apple.iTunes:MusicBrainz Disc Id",
                "mbpath": ["_disc_id_"]
        },
        {
                "internalname": "acoustid_id",
                "name": "AcoustID",
                "mp3": "TXXX:Acoustid Id",
                "vorbis": "ACOUSTID_ID",
                "m4a": "----:com.apple.iTunes:Acoustid Id",
        },
        {
                "internalname": "acoustid_fingerprint",
                "name": "AcoustID Fingerprint",
                "mp3": "TXXX:Acoustid Fingerprint",
                "vorbis": "ACOUSTID_FINGERPRINT",
                "m4a": "----:com.apple.iTunes:Acoustid Fingerprint",
        },
        {
                "internalname": "musicip_puid",
                "name": "MusicIP PUID",
                "mp3": "TXXX:MusicIP PUID",
                "vorbis": "MUSICIP_PUID",
                "m4a": "----:com.apple.iTunes:MusicIP PUID",
        },
        {
                "internalname": "musicip_fingerprint",
                "name": "MusicIP Fingerprint",
                "mp3": "TXXX:MusicMagic Fingerprint",
                "vorbis": "FINGERPRINT=MusicMagic Fingerprint",
                "m4a": "----:com.apple.iTunes:fingerprint",
        },
        {
                "internalname": "website",
                "name": "Website (official artist website)",
                "mp3": "WOAR",
                "vorbis": "WEBSITE",
                "m4a": None,
        },
        {
                "internalname": "key",
                "name": "Initial key",
                "mp3": "TKEY",
                "vorbis": "KEY",
                "m4a": "----:com.apple.iTunes:initialkey",
        },
        {
                "internalname": "replaygain_album_gain",
                "name": "ReplayGain Album Gain",
                "mp3": "TXXX:REPLAYGAIN_ALBUM_GAIN",
                "vorbis": "REPLAYGAIN_ALBUM_GAIN",
                "m4a": "----:com.apple.iTunes:REPLAYGAIN_ALBUM_GAIN",
        },
        {
                "internalname": "replaygain_album_peak",
                "name": "ReplayGain Album Peak",
                "mp3": "TXXX:REPLAYGAIN_ALBUM_PEAK",
                "vorbis": "REPLAYGAIN_ALBUM_PEAK",
                "m4a": "----:com.apple.iTunes:REPLAYGAIN_ALBUM_PEAK",
        },
        {
                "internalname": "replaygain_album_range",
                "name": "ReplayGain Album Range",
                "mp3": "TXXX:REPLAYGAIN_ALBUM_RANGE",
                "vorbis": "REPLAYGAIN_ALBUM_RANGE",
                "m4a": "----:com.apple.iTunes:REPLAYGAIN_ALBUM_RANGE",
        },
        {
                "internalname": "replaygain_track_gain",
                "name": "ReplayGain Track Gain",
                "mp3": "TXXX:REPLAYGAIN_TRACK_GAIN",
                "vorbis": "REPLAYGAIN_TRACK_GAIN",
                "m4a": "----:com.apple.iTunes:REPLAYGAIN_TRACK_GAIN",
        },
        {
                "internalname": "replaygain_track_peak",
                "name": "ReplayGain Track Peak",
                "mp3": "TXXX:REPLAYGAIN_TRACK_PEAK",
                "vorbis": "REPLAYGAIN_TRACK_PEAK",
                "m4a": "----:com.apple.iTunes:REPLAYGAIN_TRACK_PEAK",
        },
        {
                "internalname": "replaygain_track_range",
                "name": "ReplayGain Track Range",
                "mp3": "TXXX:REPLAYGAIN_TRACK_RANGE",
                "vorbis": "REPLAYGAIN_TRACK_RANGE",
                "m4a": "----:com.apple.iTunes:REPLAYGAIN_TRACK_RANGE",
        },
        {
                "internalname": "replaygain_reference_loudness",
                "name": "ReplayGain Reference Loudness",
                "mp3": "TXXX:REPLAYGAIN_REFERENCE_LOUDNESS",
                "vorbis": None,
                "m4a": None,
        }
    ]

    if not cf['_set_extended_tag']:
        print("no extended tagging wanted")
        return
    if not mb_query_data:
        print("no extended metadata available")
        return

    # prepare data
    chosen_release = mb_query_data['chosen_release']
    genre = mb_query_data['genre']
    disc_id = mb_query_data['result']['disc']['id']
    release = mb_query_data['result']['disc']['release-list'][chosen_release]
    medium = None
    for m in release['medium-list']:
        for d in m['disc-list']:
            if d['id'] == disc_id:
                medium = m
    track = medium['track-list'][track_position - 1]

    for map_entry in mb_tag_map:
        if not 'mbpath' in map_entry:
            continue
        mbpath = map_entry['mbpath']

        built_path = None
        built_paths = []
        depth = 0
        for item in mbpath:
            if item[:1] == '_' and item[-1:] == '_':
                if item == "_release_":
                    built_path = release
                elif item == "_medium_":
                    built_path = medium
                elif item == "_track_":
                    built_path = track
                elif item == "_disc_id_":
                    built_path = disc_id
                elif item == "_genre_":
                    built_path = genre
                elif item == "_first_":
                    built_path = built_path[0]
                elif item == "_concatenate_":
                    concat_string = ""
                    concat_path = mbpath[depth+1:]
                    # concatenate dicts and strings
                    for next_item in built_path:
                        if isinstance(next_item, str):
                            concat_string += next_item
                        elif isinstance(next_item, dict):
                            for key, value in next_item.items():
                                if key == concat_path[0]:
                                    sub_path = next_item
                                    for sub_item in concat_path:
                                        if sub_item in sub_path:
                                            sub_path = sub_path[sub_item]
                                    concat_string += sub_path
                    built_path = concat_string
                    break
                elif item == "_multi_":
                    remain_items = mbpath[depth+1:]
                    multi_built_path = None
                    for multi_path in built_path:
                        if isinstance(multi_path, dict):
                            multi_built_path = multi_path
                            for rem_item in remain_items:
                                if rem_item in multi_built_path:
                                    multi_built_path = multi_built_path[rem_item]
                            built_paths.append(multi_built_path)
                    built_path = None
                    break
                else:
                    print("unknown special item", item)
                    built_path = None
            else:
                if item in built_path:
                    built_path = built_path[item]
                else:
                    built_path = None
                    break
            depth += 1

        if built_path:
            built_paths.append(built_path)
        for built_path in built_paths:
            debug("tagging" + map_entry['name'] +  "-->" + str(built_path))

            if tagtype == "vorbis":
                tagobject.append([map_entry['vorbis'], str(built_path)])
    return
