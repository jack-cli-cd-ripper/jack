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
import locale
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
locale_names = None

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
                                error('Cannot rename "%s" to "%s" (Filename is too long or has unusable characters)' %
                                      (p_encname, p_newname + ext))
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
                        jack.functions.progress(
                            i[NUM], "ren", "%s-->%s" % (i[NAME], u_newname))
                    elif cf['_silent_mode']:
                        jack.functions.progress(
                            i[NUM], "err", "while renaming track")
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
