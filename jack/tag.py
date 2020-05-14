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
discnum = None


def tag(metadata_rename):
    global a_artist, a_title

    ext = jack.targets.targets[
        jack.helpers.helpers[cf['_encoder']]['target']]['file_extension']

    if cf['_vbr'] and not cf['_only_dae']:
        total_length = 0
        total_size = 0
        for i in jack.ripstuff.all_tracks_todo_sorted:
            total_length = total_length + i[LEN]
            total_size = total_size + jack.utils.filesize(i[NAME] + ext)

    if cf['_set_tag'] and not jack.targets.targets[jack.helpers.helpers[cf['_encoder']]['target']]['can_posttag']:
        cf['_set_tag'] = 0

    if jack.metadata.names_available:
        a_artist = track_names[0][0]  # unicode
        a_title = track_names[0][1]  # unicode

        r1 = re.compile(r'( \(disc[ ]*| \(side[ ]*| \(cd[^a-z0-9]*)([0-9]*|One|Two|A|B)([^a-z0-9])', re.IGNORECASE)
        mo = r1.search(a_title)
        discnum = None
        if mo != None:
            discnum = a_title[mo.start(2):mo.end(2)].lstrip("0")
            a_title = a_title[0:mo.start(1)]
            if discnum == "One" or discnum == "one" or discnum == "A":
                discnum = "1"
            elif discnum == "Two" or discnum == "two" or discnum == "B":
                discnum = "2"

    if cf['_set_tag'] or metadata_rename:
        jack.m3u.init()
        # use metadata year and genre data if available
        if cf['_year'] == None and len(track_names[0]) >= 3:
            cf['_year'] = track_names[0][2]
        if cf['_genre'] == None and len(track_names[0]) == 4:
            cf['_genre'] = track_names[0][3]

        print("Tagging", end=' ')
        for i in jack.ripstuff.all_tracks_todo_sorted:
            sys.stdout.write(".")
            sys.stdout.flush()
            mp3name = i[NAME] + ext
            wavname = i[NAME] + ".wav"
            if track_names[i[NUM]][0]:
                t_artist = track_names[i[NUM]][0]
            else:
                t_artist = a_artist
            t_name = track_names[i[NUM]][1]
            if not cf['_only_dae'] and cf['_set_tag']:
                if jack.helpers.helpers[cf['_encoder']]['target'] == "mp3":
                    track_info = "%s/%s" % (i[NUM], len(jack.ripstuff.all_tracks_orig))
                    audio = mp3.MP3(mp3name)
                    if audio.tags is None:
                        audio.add_tags()
                    tags = audio.tags
                    tags.add(id3.TPE1(encoding=3, text=t_artist))
                    tags.add(id3.TALB(encoding=3, text=a_title))
                    tags.add(id3.TIT2(encoding=3, text=t_name))
                    tags.add(id3.TRCK(encoding=3, text=track_info)),
                    tags.add(id3.TCON(encoding=3, text=cf['_genre']))
                    tags.add(id3.TDRL(encoding=3, text=cf['_year']))
                    audio.save()
                elif jack.helpers.helpers[cf['_encoder']]['target'] == "flac":
                    f = flac.FLAC(mp3name)
                    if f.tags is None:
                        f.add_vorbiscomment()
                    f.tags['ALBUM'] = a_title
                    f.tags['TRACKNUMBER'] = str(i[NUM])
                    f.tags['TRACKTOTAL'] = str(len(jack.ripstuff.all_tracks_orig))
                    f.tags['TITLE'] = t_name
                    f.tags['ARTIST'] = t_artist
                    if cf['_genre']:
                        f.tags['GENRE'] = cf['_genre']
                    elif 'GENRE' in f.tags:
                        del f.tags['GENRE']
                    if cf['_year']:
                        f.tags['DATE'] = cf['_year']
                    elif 'DATE' in f.tags:
                        del f.tags['DATE']
                    if cf['_various']:
                        f.tags['COMPILATION'] = "1"
                    elif 'COMPILATION' in f.tags:
                        del f.tags['COMPILATION']
                    if discnum:
                        f.tags['DISCNUMBER'] = discnum
                    else:
                        if 'DISCNUMBER' in f.tags:
                            del f.tags['DISCNUMBER']
                        if 'DISCTOTAL' in f.tags:
                            del f.tags['DISCTOTAL']
                    f.save()
                elif jack.helpers.helpers[cf['_encoder']]['target'] == "m4a":
                    m4a = mp4.MP4(mp3name)
                    m4a.tags['\xa9nam'] = [t_name]
                    m4a.tags['\xa9alb'] = [a_title]
                    m4a.tags['\xa9ART'] = [t_artist]
                    if cf['_genre']:
                        m4a.tags['\xa9gen'] = [cf['_genre']]
                    elif '\xa9gen' in m4a.tags:
                        del m4a.tags['\xa9gen']
                    if cf['_year']:
                        m4a.tags['\xa9day'] = [cf['_year']]
                    elif '\xa9day' in m4a.tags:
                        del m4a.tags['\xa9day']
                    m4a.tags['cpil'] = bool(cf['_various'])
                    m4a.tags['trkn'] = [(i[NUM], len(jack.ripstuff.all_tracks_orig))]
                    if discnum:
                        m4a.tags['disk'] = [(discnum, 0)]
                    m4a.save()
                elif jack.helpers.helpers[cf['_encoder']]['target'] == "ogg":
                    f = oggvorbis.OggVorbis(mp3name)
                    if f.tags is None:
                        f.add_vorbiscomment()
                    f.tags['ALBUM'] = a_title
                    f.tags['TRACKNUMBER'] = str(i[NUM])
                    f.tags['TRACKTOTAL'] = str(len(jack.ripstuff.all_tracks_orig))
                    f.tags['TITLE'] = t_name
                    f.tags['ARTIST'] = t_artist
                    if cf['_genre']:
                        f.tags['GENRE'] = cf['_genre']
                    elif 'GENRE' in f.tags:
                        del f.tags['GENRE']
                    if cf['_year']:
                        f.tags['DATE'] = cf['_year']
                    elif 'DATE' in f.tags:
                        del f.tags['DATE']
                    if cf['_various']:
                        f.tags['COMPILATION'] = "1"
                    else:
                        if 'COMPILATION' in f.tags:
                            del f.tags['COMPILATION']
                    if discnum:
                        f.tags['DISCNUMBER'] = discnum
                    else:
                        if 'DISCNUMBER' in f.tags:
                            del f.tags['DISCNUMBER']
                        if 'DISCTOTAL' in f.tags:
                            del f.tags['DISCTOTAL']
                    f.save()
            if metadata_rename:
                newname = jack.metadata.filenames[i[NUM]]
                if i[NAME] != newname:
                    p_newname = newname
                    u_newname = newname
                    newname = newname
                    p_mp3name = i[NAME]
                    p_wavname = i[NAME]
                    ok = 1
                    if os.path.exists(newname + ext):
                        ok = 0
                        print('NOT renaming "' + p_mp3name + '" to "' + p_newname + ext + '" because dest. exists.')
                        if cf['_keep_wavs']:
                            print('NOT renaming "' + p_wavname + '" to "' + p_newname + ".wav" + '" because dest. exists.')
                    elif cf['_keep_wavs'] and os.path.exists(newname + ".wav"):
                        ok = 0
                        print('NOT renaming "' + p_wavname + '" to "' + p_newname + ".wav" + '" because dest. exists.')
                        print('NOT renaming "' + p_mp3name + '" to "' + p_newname + ext + '" because WAV dest. exists.')
                    if ok:
                        if not cf['_only_dae']:
                            try:
                                os.rename(mp3name, newname + ext)
                            except OSError:
                                error('Cannot rename "%s" to "%s" (Filename is too long or has unusable characters)' %
                                      (p_mp3name, p_newname + ext))
                            jack.m3u.add(newname + ext)
                        if cf['_keep_wavs']:
                            os.rename(wavname, newname + ".wav")
                            jack.m3u.add_wav(newname + ".wav")
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
