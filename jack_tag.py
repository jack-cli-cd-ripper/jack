### jack_tag: name information (ID3 among others) stuff for
### jack - tag audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2003  Arne Zellentin <zarne@users.sf.net>

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; either version 2 of the License, or
### (at your option) any later version.

### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.

### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import string
import os

import jack_functions
import jack_ripstuff
import jack_targets
import jack_helpers
import jack_freedb
import jack_utils
import jack_misc
import jack_m3u

from jack_init import ogg
from jack_init import pyid3lib
from jack_globals import *

track_names = None
genretxt = None

a_artist = None
a_title = None

def tag(freedb_rename):
    global a_artist, a_title

    ext = jack_targets.targets[jack_helpers.helpers[cf['_encoder']]['target']]['file_extension']

    if cf['_vbr'] and not cf['_only_dae']:
        total_length = 0
        total_size = 0
        for i in jack_ripstuff.all_tracks_todo_sorted:
            total_length = total_length + i[LEN]
            total_size = total_size + jack_utils.filesize(i[NAME] + ext)

    if cf['_set_id3tag'] and not jack_targets.targets[jack_helpers.helpers[cf['_encoder']]['target']]['can_posttag']:
        cf['_set_id3tag'] = 0

    # maybe export?
    if jack_freedb.names_available:
        a_artist = track_names[0][0]
        a_title = track_names[0][1]

    if cf['_set_id3tag'] or freedb_rename:
        jack_m3u.init()
        if len(track_names[0]) == 4:
            # use freedb year and genre data if available
            if cf['_id3_genre'] == -1:
                cf['_id3_genre'] = track_names[0][3]
            if cf['_id3_year'] == -1:
                cf['_id3_year'] = track_names[0][2]

        for i in jack_ripstuff.all_tracks_todo_sorted:
            mp3name = i[NAME] + ext
            wavname = i[NAME] + ".wav"
            t_artist = track_names[i[NUM]][0]
            t_name = track_names[i[NUM]][1]
            t_comm = ""
            if not cf['_only_dae'] and cf['_set_id3tag']:
                if len(t_name) > 30:
                    if string.find(t_name, "(") != -1 and string.find(t_name, ")") != -1:
                        # we only use the last comment
                        t_comm = string.split(t_name, "(")[-1]
                        if t_comm[-1] == ")":
                            t_comm = t_comm[:-1]
                            if t_comm[-1] == " ":
                                t_comm = t_comm[:-1]
                            t_name2 = string.replace(t_name, " (" + t_comm + ") ", "")
                            t_name2 = string.replace(t_name2, " (" + t_comm + ")", "")
                            t_name2 = string.replace(t_name2, "(" + t_comm + ") ", "")
                            t_name2 = string.replace(t_name2, "(" + t_comm + ")", "")
                        else:
                            t_comm = ""
                if jack_helpers.helpers[cf['_encoder']]['target'] in ("mp3", "flac"):
                    if jack_helpers.helpers[cf['_encoder']]['target'] == "mp3" and cf['_write_id3v2']:
                        v2tag = pyid3lib.tag(mp3name)
                        v2tag.album = a_title
                        v2tag.track = (i[NUM], len(jack_ripstuff.all_tracks_orig))
                        v2tag.title = t_name
                        if t_artist:
                            v2tag.artist = t_artist
                        else:
                            v2tag.artist = a_artist
                        if cf['_id3_genre'] == 255:
                            try:
                                del v2tag.contenttype
                            except AttributeError:
                                pass
                        elif cf['_id3_genre'] != -1:
                            v2tag.contenttype = "(%d)" % (cf['_id3_genre'])
                        if cf['_id3_year'] != -1:
                            v2tag.year = `cf['_id3_year']`
                        v2tag.songlen = `int(i[LEN] * 1000.0 / 75 + 0.5)`
                        v2tag.update()
                    if cf['_write_id3v1']:
                        id3 = ID3(mp3name)
                        id3.album = a_title
                        id3.track = i[NUM] # this is ignored if we have an ID3v1.0 tag
                        if t_comm:
                            id3.comment = t_comm
                            id3.title = t_name2
                        else:
                            id3.title = t_name
                        if t_artist:
                            id3.artist = t_artist
                        else:
                            id3.artist = a_artist
                        if cf['_id3_genre'] != -1:
                            id3.genre = cf['_id3_genre']
                        elif not id3.had_tag:
                            id3.genre = 255
                        if cf['_id3_year'] != -1:
                            id3.year = `cf['_id3_year']`
                        id3.write()
                elif jack_helpers.helpers[cf['_encoder']]['target'] == "ogg":
                    vf = ogg.vorbis.VorbisFile(mp3name)
                    oggi = vf.comment()
                    oggi.clear()
                    oggi.add_tag('ALBUM', a_title.decode(cf['_charset']).encode('utf-8'))
                    oggi.add_tag('TRACKNUMBER', `i[NUM]`)
                    oggi.add_tag('TITLE', t_name.decode(cf['_charset']).encode('utf-8'))
                    if t_artist:
                        oggi.add_tag('ARTIST', t_artist.decode(cf['_charset']).encode('utf-8'))
                    else:
                        oggi.add_tag('ARTIST', a_artist.decode(cf['_charset']).encode('utf-8'))
                    if cf['_id3_genre'] != -1:
                        oggi.add_tag('GENRE', id3genres[cf['_id3_genre']])
                    if cf['_id3_year'] != -1:
                        oggi.add_tag('DATE', `cf['_id3_year']`)
                    oggi.write_to(mp3name)
            if freedb_rename:
                if t_artist:    # 'Various Artists'
                    replacelist = (("%n", cf['_rename_num'] % i[NUM]), ("%a", t_artist), ("%t", t_name), ("%l", a_title), ("%y", `cf['_id3_year']`), ("%g", genretxt))
                    newname = jack_misc.multi_replace(cf['_rename_fmt_va'], replacelist)
                    
                else:
                    replacelist = (("%n", cf['_rename_num'] % i[NUM]), ("%a", a_artist), ("%t", t_name), ("%l", a_title))
                    newname = jack_misc.multi_replace(cf['_rename_fmt'], replacelist)
                exec("newname = newname" + cf['_char_filter'])
                for char_i in range(len(cf['_unusable_chars'])):
                    newname = string.replace(newname, cf['_unusable_chars'][char_i], cf['_replacement_chars'][char_i])
                if i[NAME] != newname:
                    ok = 1
                    if os.path.exists(newname + ext):
                        ok = 0
                        print 'NOT renaming "' + mp3name + '" to "' + newname + ext + '" because dest. exists.'
                        if cf['_keep_wavs']:
                            print 'NOT renaming "' + wavname + '" to "' + newname + ".wav" + '" because dest. exists.'
                    elif cf['_keep_wavs'] and os.path.exists(newname + ".wav"):
                        ok = 0
                        print 'NOT renaming "' + wavname + '" to "' + newname + ".wav" + '" because dest. exists.'
                        print 'NOT renaming "' + mp3name + '" to "' + newname + ext + '" because WAV dest. exists.'
                    if ok:
                        if not cf['_only_dae']:
                            os.rename(mp3name, newname + ext)
                            jack_m3u.add(newname + ext)
                        if cf['_keep_wavs']:
                            os.rename(wavname, newname + ".wav")
                            jack_m3u.add_wav(newname + ".wav")
                        jack_functions.progress(i[NUM], "ren", "%s-->%s" % (i[NAME], newname))
                    elif cf['_silent_mode']:
                        jack_functions.progress(i[NUM], "err", "while renaming track")

    if not cf['_silent_mode']:
        if jack_freedb.names_available:
            print "Done with \"" + a_artist+ " - " + a_title + "\"."
        else:
            print "All done.",
        if cf['_set_id3tag'] and cf['_id3_year'] != -1:
            print "Year: %4i" % cf['_id3_year'],
            if cf['_id3_genre'] == -1: print
        if cf['_set_id3tag'] and cf['_id3_genre'] != -1:
            if cf['_id3_genre'] <0 or cf['_id3_genre'] > len(id3genres):
                print "Genre: [unknown]"
            else:
                print "Genre: %s" % id3genres[cf['_id3_genre']]
        if cf['_vbr'] and not cf['_only_dae']:
            print "Avg. bitrate: %03.0fkbit" % ((total_size * 0.008) / (total_length / 75))
        else:
            print

    jack_m3u.write()

