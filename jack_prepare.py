### jack_prepare: prepare everything for the main_loop; a module for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2004  Arne Zellentin <zarne@users.sf.net>

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
import types
import pprint
import os, sys

import jack_playorder
import jack_functions
import jack_progress
import jack_version
import jack_utils
import jack_ripstuff
import jack_targets
import jack_helpers
import jack_freedb
import jack_status
import jack_encstuff
import jack_misc
import jack_tag

from jack_globals import *

tracknum = None
datatracks = []

def find_workdir():
    "search for a dir containing a toc-file or do the multi-mode"
    tries = 0
    toc_just_read = 0
    debug("multi_mode:" + `cf['_multi_mode']`)
    while (not os.path.exists(cf['_toc_file'])) or cf['_multi_mode']:
        tries = tries + 1
        if tries > 2:
            break
        if cf['_guess_mp3s']:
            jack_ripstuff.all_tracks = jack_functions.guesstoc(cf['_guess_mp3s'])
        else:
            if cf['_multi_mode']:
                debug("multimode all_tracks reset")
                jack_ripstuff.all_tracks = []
            else:
                if cf['_image_toc_file']:
                    jack_ripstuff.all_tracks, dummy, dummy = jack_functions.cdrdao_gettoc(cf['_image_toc_file'])
                else:
                    jack_ripstuff.all_tracks = jack_functions.gettoc(cf['_toc_prog'])
                    toc_just_read = 1
                    # check that the generic device is usable, too
                    if cf['_gen_device'] and not os.access(cf['_gen_device'], os.R_OK | os.W_OK):
                        warning(r"""could not open generic device %s for reading and writing.""" % cf['_gen_device'])

            if cf['_scan_dirs']:
                dirs = [os.getcwd()]
            else:
                dirs = cf['_searchdirs']

            while cf['_scan_dirs'] > 0:
                cf['_scan_dirs'] = cf['_scan_dirs'] - 1
                new_dirs = []
                for i in dirs:
                    if not i in new_dirs:
                        new_dirs.append(i)
                    try:
                        subdir = os.listdir(i)
                    except OSError, msg:
                        print "skipped %s, %s" % (i, msg)
                        continue
                    for j in subdir:
                        dir = os.path.join(i,j)
                        if os.path.isdir(dir) and not dir in new_dirs:
                            new_dirs.append(dir)
                dirs = new_dirs
            possible_dirs = []  # dirs matching inserted CD
            jack_dirs = []      # dirs containing toc_file
            for i in dirs:
                if os.path.exists(os.path.join(i, cf['_toc_file'])):
                    jack_dirs.append(i)
                    file_toc, dummy, dummy = jack_functions.cdrdao_gettoc(os.path.join(i, cf['_toc_file']))
                    if jack_freedb.freedb_id(jack_ripstuff.all_tracks) == jack_freedb.freedb_id(file_toc):
                        possible_dirs.append(i)

            if cf['_multi_mode']:
                unique_dirs = []
                for i in range(len(jack_dirs)):
                    found = 0
                    for j in range(i + 1,len(jack_dirs)):
                        if os.path.samefile(jack_dirs[i], jack_dirs[j]):
                            found = 1
                    if not found:
                        unique_dirs.append(jack_dirs[i])
                for i in unique_dirs:
                    jack_ripstuff.all_tracks, dummy, track1_offset = jack_functions.cdrdao_gettoc(os.path.join(i, cf['_toc_file']))
                    err, jack_tag.track_names, cd_id, revision = freedb_names(jack_freedb.freedb_id(jack_ripstuff.all_tracks), jack_ripstuff.all_tracks,  os.path.join(i, cf['_freedb_form_file']), verb = 0, warn = 0)
                    if err or cf['_force']:# this means freedb data is not there yet
                        info("matching dir found: %d" % i)
                        pid = os.fork()
                        if pid == CHILD:
                            os.chdir(i)
                            ch_args = sys.argv
                            for killarg in ('--force', '--multi-mode'):
                                if killarg in ch_args:
                                    ch_args.remove(killarg)
                            info("running" + `ch_args`)
                            os.execvp(ch_args[0], ch_args)
                        else:
                            respid, res = os.waitpid(pid, 0)
                sys.exit()

            unique_dirs = []
            for i in range(len(possible_dirs)):
                found = 0
                for j in range(i + 1,len(possible_dirs)):
                    if os.path.samefile(possible_dirs[i], possible_dirs[j]):
                        found = 1
                if not found:
                    unique_dirs.append(possible_dirs[i])
                    info("matching dir found: " + possible_dirs[i])
            if len(unique_dirs) > 1:
                error("found more than one workdir, change to the correct one.")
            elif len(unique_dirs) == 1:
                os.chdir(unique_dirs[0])
            else:
                if cf['_create_dirs']:
                    cf['_base_dir'] = expand(cf['_base_dir'])
                    if not os.path.exists(cf['_base_dir']):
                        os.makedirs(cf['_base_dir'])
                    os.chdir(cf['_base_dir'])
                    dir_name = jack_version.prog_name + "-" + jack_freedb.freedb_id(jack_ripstuff.all_tracks, warn=0)
                    if not os.path.exists(dir_name) and not os.path.isdir(dir_name):
                        os.mkdir(dir_name)
                    os.chdir(dir_name)
                    jack_freedb.dir_created = dir_name
                    jack_functions.progress("all", "mkdir", jack_freedb.dir_created)

        if not cf['_multi_mode']:
            if not os.path.exists(cf['_toc_file']):
                jack_functions.cdrdao_puttoc(cf['_toc_file'], jack_ripstuff.all_tracks, jack_freedb.freedb_id(jack_ripstuff.all_tracks))
                jack_freedb.freedb_template(jack_ripstuff.all_tracks) # generate freedb form if tocfile is created
            if not os.path.exists(cf['_freedb_form_file']):
                jack_freedb.freedb_template(jack_ripstuff.all_tracks)
        else:
            break
    return toc_just_read

def check_toc():
    "compare CD toc to tocfile"

    if cf['_check_toc']:
        cd_toc = jack_functions.gettoc(cf['_toc_prog'])
        if os.path.exists(cf['_toc_file']):
            file_toc, dummy, dummy = jack_functions.cdrdao_gettoc(cf['_toc_file'])
        else:
            print "no toc-file named " + cf['_toc_file'] + " found, exiting."
            jack_display.exit()
        print "This is the inserted CD:"
        pprint.pprint(cd_toc)
        print
        print "And This is what we expect:"
        pprint.pprint(file_toc)
        print
        if cmp(cd_toc, file_toc) == 0:
            print 'Yes, toc-file ("' + cf['_toc_file'] + '") matches inserted CD.'
        else:
            print 'No, toc-file ("' + cf['_toc_file'] + '") *DOES NOT* match inserted CD.'

def read_toc_file():
    "read and interpret toc_file"
    global is_submittable

    is_submittable = 0
    if os.path.exists(cf['_toc_file']):
        if cf['_image_toc_file']:
            cf['_toc_file'] = cf['_image_toc_file']

        jack_ripstuff.all_tracks, new_image_file, track1_offset = jack_functions.cdrdao_gettoc(cf['_toc_file'])

        if not os.path.exists(cf['_def_toc']):
            jack_functions.cdrdao_puttoc(cf['_def_toc'], jack_ripstuff.all_tracks, jack_freedb.freedb_id(jack_ripstuff.all_tracks))

        # if image_file is not set (-F), we can guess it from image_toc_file
        if not cf['_image_file'] and not cf['_rip_from_device']:
            cf['_image_file'] = new_image_file

        if cf['_rip_from_device']:
            cf['_image_file'] = ""

        is_submittable = 1
    return is_submittable, track1_offset

def filter_tracks(toc_just_read):
    "filter out data tracks"

    if toc_just_read and jack_helpers.helpers[cf['_ripper']].has_key("toc_cmd") and cf['_ripper'] != cf['_toc_prog']:
        ripper_tracks = jack_functions.gettoc(cf['_ripper'])
        if ripper_tracks != jack_ripstuff.all_tracks:
            for i in range(len(jack_ripstuff.all_tracks)):
                rtn = jack_utils.has_track(ripper_tracks, jack_ripstuff.all_tracks[i][NUM])
                if rtn >= 0:
                    for j in range(6):
                        # "NUM LEN START COPY PRE CH" (not: "RIP RATE NAME")
                        if ripper_tracks[rtn][j] != jack_ripstuff.all_tracks[i][j]:
                            jack_functions.progress(i + 1, "patch", "%s %d -> %d" % (fields[j], jack_ripstuff.all_tracks[i][j], ripper_tracks[rtn][j]))
                            debug("Track %02d %s" % (i + 1, fields[j]) + `jack_ripstuff.all_tracks[i][j]` + " != " + `ripper_tracks[rtn][j]` + " (trusting %s; to the right)" % cf['_ripper'])
                else:
                    jack_functions.progress(i + 1, "off", "non-audio")
                    datatracks.append(i + 1)
                    info("Track %02d not found by %s. Treated as non-audio." % (i + 1, cf['_ripper']))
        

def gen_todo():
    "parse tracks from argv, generate todo"
    global tracknum

    tracknum = {}
    for i in jack_ripstuff.all_tracks:
        tracknum[i[NUM]] = i

    if not cf['_tracks'] and not jack_playorder.order:
        todo = []
        for i in jack_ripstuff.all_tracks:
            if i[CH] == 2:
                todo.append(i)
            else:
                info("can't handle non audio track %i" % i[NUM])

    else:
        # example: "1,2,4-8,12-" ->  [ 1,2,4,5,6,7,8,12,13,...,n ]
        tlist = []
        if cf['_tracks']:
            tracks = string.split(cf['_tracks'], ",")
        else:
            tracks = string.split(jack_playorder.order, ",")
        for k in tracks:
            if string.find(k, '-') >= 0:
                k = string.split(k, '-')
                lower_limit = jack_misc.safe_int(k[0], "Track '%s' is not a number." % k[0])
                if k[1]:
                    upper_limit = jack_misc.safe_int(k[1], "Track '%s' is not a number." % k[1])
                else:
                    upper_limit = len(jack_ripstuff.all_tracks)
                for j in range(lower_limit, upper_limit + 1):
                    tlist.append(j)
            else:
                track = jack_misc.safe_int(k, "Track '%s' is not a number." % k)
                tlist.append(track)

        # uniq the track list
        tlist.sort()
        k = 0
        while k < len(tlist) - 1:
            if tlist[k] == tlist[k+1]:
                del tlist[k]
            else:
                k = k + 1

        # generate todo
        todo = []
        audiotracks = []
        for i in jack_ripstuff.all_tracks:
            if i[NUM] in datatracks:
                continue
            audiotracks.append(i[NUM])

        if audiotracks != range(1, audiotracks[-1] + 1):
            info("strange audio track layout " + `audiotracks`)
            continuous = 0
        else:
            continuous = 1
            
        for k in tlist:
            if continuous:
                if k < 1 or k > len(audiotracks):
                    warning('This CD has audio tracks 1-%d.  Ignoring request for track %d.' % (len(audiotracks), k))
                    continue
            else:
                if k < 1 or k > len(jack_ripstuff.all_tracks):
                    warning('This CD has tracks 1-%d.  Ignoring request for track %d.' % (len(jack_ripstuff.all_tracks), k))
                    continue
            if jack_ripstuff.all_tracks[k-1][CH] == 2:
                todo.append(jack_ripstuff.all_tracks[k-1])
            else:
                warning("can't handle non audio track %i" % k[NUM])

    for i in todo:
        jack_ripstuff.all_tracks_todo_sorted.append(i)

    return todo

def init_status():
    status = {}
    for i in jack_ripstuff.all_tracks:
        num = i[NUM]
        status[num] = {}
        status[num]['dae'] = []
        status[num]['enc'] = []
        status[num]['ren'] = []
        status[num]['names'] = [i[NAME],]
        status[num]['patch'] = []
        status[num]['off'] = []

    status['all'] = {}
    status['all']['mkdir'] = status['all']['names'] = [[],]
    status['all']['dae'] = []
    status['all']['enc'] = []
    status['all']['ren'] = []
    status['all']['patch'] = []
    status['all']['off'] = []
    status['all']['id3_genre'] = ["-1",]
    status['all']['id3_year'] = ["-1",]
    return status

def update_progress(todo):
    ext = jack_targets.targets[jack_helpers.helpers[cf['_encoder']]['target']]['file_extension']
    "update progress file at user's request (operation mode)"

    if cf['_upd_progress']:
        for i in todo:
            num = i[NUM]
            if not status[num]['dae']:
                if os.path.exists(i[NAME] + ".wav"):
                    status[num]['dae'] = "  *   [          simulated           ]"
                    jack_functions.progress(num, "dae", status[num]['dae'])
            if not status[num]['enc']:
                if os.path.exists(i[NAME] + ext):
                    if ext == ".mp3":
                        x = jack_mp3.mp3format(i[NAME] + ext)
                        temp_rate = x['bitrate']
                    elif ext == ".ogg":
                        x = ogg.vorbis.VorbisFile(i[NAME] + ext)
                        temp_rate = int(x.raw_total(0) * 8 / x.time_total(0) / 1000 + 0.5)
                    else:
                        error("don't know how to handle %s files." % ext)
                    status[num]['enc'] = `temp_rate` + cf['_progr_sep'] + "[simulated]"
                    jack_functions.progress(num, "enc", status[num]['enc'])

def read_progress(status, todo):
    "now read in the progress file"

    if os.path.exists(cf['_progress_file']):
        f = open(cf['_progress_file'], "r")
        while 1:
            buf = f.readline()
            if not buf:
                break

            # strip doesn't work here as we may have trailing spaces
            buf = string.replace(buf, "\n", "")

            # ignore empty lines
            if not buf:
                continue

            buf = string.split(buf, cf['_progr_sep'], 3)
            try:
                num = int(buf[0])
            except ValueError:
                num = buf[0]
            if buf[1] == 'undo':        # this needs special treatment as
                                        # the correct sequence is important

                status[num]['ren'].append(('Undo',))
            elif buf[1] == 'ren':
                status[num][buf[1]].append(buf[2:])
            else:
                status[num][buf[1]] = buf[2:]
        f.close()

    # names for 'all' can't be initialized earlier...
    status['all']['names'] = [status['all']['mkdir'][-1],]

                                        # extract names from renaming
    for i in status.keys():
        for j in status[i]['ren']:
            if j == ('Undo',):
                if len(status[i]['names']) > 1:
                    del status[i]['names'][-1]
                else:
                    error("more undos than renames, exit.")
            else:
                names = string.split(j[0], '-->', 1)
                if status[i]['names'][-1] == names[0]:
                    status[i]['names'].append(names[1])
            if type(i) == types.IntType:
                tracknum[i][NAME] = status[i]['names'][-1]
        del status[i]['ren']

    # status info for the whole CD is treated separately
    jack_progress.status_all = status['all']

    del status['all']

    # now clean up a little
    for i in status.keys():
        if len(status[i]['dae']) > 1 or len(status[i]['enc']) > 2:
            error("malformed progress file")
            sys.exit()
        if len(status[i]['enc']) == 2:
            tracknum[i][RATE] = int(float(status[i]['enc'][0]) + 0.5)
            status[i]['enc'] = status[i]['enc'][1]
        elif status[i]['enc'] and len(status[i]['enc']) == 1:
            tracknum[i][RATE] = cf['_bitrate']
        if status[i]['dae'] and len(status[i]['dae']) == 1:
            status[i]['dae'] = status[i]['dae'][0]

        if status[i]['patch']:
            for j in status[i]['patch']:
                p_what, p_from, dummy, p_to = string.split(j)
                p_from = int(p_from)
                p_to = int(p_to)
                if tracknum[i][fields.index(p_what)] == p_from:
                    tracknum[i][fields.index(p_what)] = p_to
                else:
                    error("illegal patch %s. " % j, + "Track %02d: %s is %d" % (i, p_what, todo[jack_utils.has_track(todo, i)][fields.index(p_what)]))

        if status[i]['off']:
            if jack_utils.has_track(todo, i) >= 0:
                del todo[jack_utils.has_track(todo, i)]
            if jack_utils.has_track(jack_ripstuff.all_tracks_todo_sorted, i) >= 0:
                del jack_ripstuff.all_tracks_todo_sorted[jack_utils.has_track(jack_ripstuff.all_tracks_todo_sorted, i)]

    # extract status from read progress data
    jack_status.extract(status)

    jack_freedb.dir_created = jack_progress.status_all['names'][-1]

    jack_progress.status_all['id3_genre'] = int(jack_progress.status_all['id3_genre'][-1])
    jack_progress.status_all['id3_year'] = int(jack_progress.status_all['id3_year'][-1])

    if cf['_id3_genre'] == -1:
        cf['_id3_genre'] = jack_progress.status_all['id3_genre']
    else:
        if cf['_id3_genre'] != jack_progress.status_all['id3_genre']:
            jack_functions.progress("all", "id3_genre", `cf['_id3_genre']`)

    jack_tag.genretxt = ""
    if cf['_id3_genre'] >= 0 and cf['_id3_genre'] < len(id3genres):
        jack_tag.genretxt = id3genres[cf['_id3_genre']]

    if cf['_id3_year'] == -1:
        cf['_id3_year'] = jack_progress.status_all['id3_year']
    else:
        if cf['_id3_year'] != jack_progress.status_all['id3_year']:
            jack_functions.progress("all", "id3_year", `cf['_id3_year']`)

    return status

def freedb_submit():
    "submit freedb data on user's request"
    if not is_submittable:
        error("can't submit in current state, please fix jack.freedb")

    err, jack_tag.track_names, cd_id, revision = jack_freedb.freedb_names(jack_freedb.freedb_id(jack_ripstuff.all_tracks), jack_ripstuff.all_tracks, cf['_freedb_form_file'])
    if err:
        error("invalid freedb file")
    else:
        if cf['_freedb_submit']:
            jack_freedb.do_freedb_submit(cf['_freedb_form_file'], cd_id)
        elif cf['_freedb_mailsubmit']:
            jack_freedb.do_freedb_mailsubmit(cf['_freedb_form_file'], cd_id)

    ### (9) do query on start

def query_on_start():
    info("querying...")
    if jack_freedb.freedb_query(jack_freedb.freedb_id(jack_ripstuff.all_tracks), jack_ripstuff.all_tracks, cf['_freedb_form_file']):
        if cf['_cont_failed_query']:
            
            x = raw_input("\nfreedb search failed, continue? ") + "x"
            if string.upper(x[0]) != "Y":
                sys.exit(0)
            cf['_query_on_start'] = 0
        else:
            jack_display.exit()

    if cf['_edit_cddb']:
        jack_utils.ex_edit(cf['_freedb_form_file'])

    if cf['_query_on_start']:
        err, jack_tag.track_names, freedb_rename, revision = jack_freedb.interpret_db_file(jack_ripstuff.all_tracks, cf['_freedb_form_file'], verb = cf['_query_on_start'], dirs = 1)
        if err:
            error("query on start failed to give a good freedb file, aborting.")
    else:
        err, jack_tag.track_names, freedb_rename, revision = jack_freedb.interpret_db_file(jack_ripstuff.all_tracks, cf['_freedb_form_file'], verb = cf['_query_on_start'], warn = cf['_query_on_start'])
    return freedb_rename

def undo_rename(status, todo):
    ext = jack_targets.targets[jack_helpers.helpers[cf['_encoder']]['target']]['file_extension']
    "undo renaming (operation mode)"
    maxnames = max(map(lambda x: len(x['names']), status.values()))
    if len(jack_progress.status_all['names']) >= maxnames:
        dir_too = 1
    else:
        dir_too = 0
    maxnames = max(maxnames, len(jack_progress.status_all['names']))
    if maxnames > 1:

        # undo dir renaming
        cwd = os.getcwd()
        if jack_freedb.dir_created and jack_utils.check_path(jack_freedb.dir_created, cwd) and dir_too:
            new_name, old_name = jack_progress.status_all['names'][-2:]
            jack_utils.rename_path(old_name, new_name)    # this changes cwd!
            info("cwd now " + os.getcwd())
            jack_functions.progress("all", "undo", "dir")

        else:
            maxnames = max(map(lambda x: len(x['names']), status.values()))

        # undo file renaming
        for i in todo:
            if maxnames < 2:
                break
            act_names = status[i[NUM]]['names']
            if len(act_names) == maxnames:
                for j in (ext, '.wav'):
                    new_name, old_name = act_names[-2:]
                    new_name, old_name = new_name + j, old_name + j
                    if not os.path.exists(old_name):
                        if j == ext:
                            print 'NOT renaming "' + old_name + '": it doesn\'t exist.'
                    else:
                        if os.path.exists(new_name):
                            print 'NOT renaming "' + old_name + '" to "' + new_name + '" because dest. exists.'
                        else:
                            jack_functions.progress(i[NUM], "undo", "-")
                            os.rename(old_name, new_name)
    else:
        info("nothing to do.")

def what_todo(space, todo):
    #### check what is already there
    wavs_todo = []
    mp3s_todo = []
    remove_q  = []
    ext = jack_targets.targets[jack_helpers.helpers[cf['_encoder']]['target']]['file_extension']

    for track in todo:
        wavs_todo.append(track)
        mp3s_todo.append(track)

    jack_encstuff.mp3s_ready = []
    for track in todo:
        mp3 = track[NAME] + ext
        if os.path.exists(mp3):
            if cf['_overwrite']:
                space = space + jack_utils.filesize(mp3)
                remove_q.append(mp3)
                jack_status.enc_status[track[NUM]] = "will o/w file."
            elif not cf['_force'] and not jack_status.enc_status[track[NUM]]:
                space = space + jack_utils.filesize(mp3)
                remove_q.append(mp3)
                jack_status.enc_status[track[NUM]] = "no encoder run."
            # with vbr encoded files can't legally be too small
            # but to reduce confusion, the check is then removed:
            elif not cf['_vbr'] and jack_utils.filesize(mp3) <= jack_functions.tracksize(track)[ENC] * 0.99: # found by trial'n'err
                space = space + jack_utils.filesize(mp3)
                remove_q.append(mp3)
                jack_status.enc_status[track[NUM]] = "encoded file too small by " + jack_functions.pprint_i(jack_functions.tracksize(track)[ENC] - jack_utils.filesize(mp3)) + "."
            elif not cf['_vbr'] and jack_utils.filesize(mp3) >= jack_functions.tracksize(track)[ENC] * 1.05: # found by trial'n'err
                space = space + jack_utils.filesize(mp3)
                remove_q.append(mp3)
                jack_status.enc_status[track[NUM]] = "enc. file too large by " + jack_functions.pprint_i(jack_utils.filesize(mp3) - jack_functions.tracksize(track)[ENC]) + "."
            else:
                mp3s_todo.remove(track)
                jack_encstuff.mp3s_ready.append(track)
        else:
            if jack_status.enc_status[track[NUM]]:
                jack_status.enc_status[track[NUM]] = "[file lost-doing again]"

    jack_ripstuff.wavs_ready = []
    for track in todo:
        wav = track[NAME] + ".wav"
        if os.path.exists(wav):
            if cf['_overwrite']:
                space = space + jack_utils.filesize(wav)
                remove_q.append(wav)
                jack_status.dae_status[track[NUM]] = "Existing WAV will be overwritten."
            elif jack_utils.filesize(wav) == jack_functions.tracksize(track)[WAV] and jack_status.dae_status[track[NUM]]:
                wavs_todo.remove(track)
                jack_ripstuff.wavs_ready.append(track)
            elif jack_utils.filesize(wav) == jack_functions.tracksize(track)[WAV]:
                space = space + jack_utils.filesize(wav)
                remove_q.append(wav)
                jack_status.dae_status[track[NUM]] =     " ---- [Existing WAV not done by jack.]"
                if jack_status.enc_status[track[NUM]] == "[file lost-doing again]":
                    jack_status.enc_status[track[NUM]] = ""
            else:
                space = space + jack_utils.filesize(wav)
                remove_q.append(wav)
                jack_status.dae_status[track[NUM]] =     " ---- [Existing WAV was not complete.]"
                if jack_status.enc_status[track[NUM]] == "[file lost-doing again]":
                    jack_status.enc_status[track[NUM]] = ""
        else:
            if jack_status.dae_status[track[NUM]]:
                if jack_status.enc_status[track[NUM]] == "[file lost-doing again]":
                    jack_status.dae_status[track[NUM]] = " ---- [    both lost, doing again    ]"
                    jack_status.enc_status[track[NUM]] = ""
                elif cf['_keep_wavs'] or track not in jack_encstuff.mp3s_ready:
                    jack_status.dae_status[track[NUM]] = " ---- [ WAV lost, doing again        ]"

    if cf['_only_dae']:
        cf['_keep_wavs'] = 1

    if not cf['_keep_wavs']:
        for track in todo:
            if track in jack_encstuff.mp3s_ready and track in wavs_todo:
                wavs_todo.remove(track)

    if cf['_reorder']:
        mp3s_todo.sort(jack_utils.cmp_toc)

    dae_queue = []                  # This stores the tracks to rip
    enc_queue = []                  # WAVs go here to get some codin'

    for track in wavs_todo:
        dae_queue.append(track)     # copy track to dae + code in queue
        if track in mp3s_todo:
            mp3s_todo.remove(track) # remove mp3s which are not there yet

    if cf['_only_dae']:             # if only_dae nothing is encoded _at_all_.
        mp3s_todo = []

    # overwrite cached bitrates with those from argv
    if cf['bitrate']['history'][-1][0] == "argv":
        for i in wavs_todo:
            i[RATE] = cf['_bitrate']
        for i in mp3s_todo:
            i[RATE] = cf['_bitrate']

    return space, remove_q, wavs_todo, mp3s_todo, dae_queue, enc_queue
#
#
#

def print_todo(todo, wavs_todo, mp3s_todo):
    "print what needs to be done"
    for i in jack_ripstuff.all_tracks:
        print "%02i" % i[NUM],
        if jack_utils.has_track(todo, i[NUM]) >= 0:
            print "*",
        else:
            print "-",
        if i in wavs_todo:
            print ":DAE:",
            # FIXME!
            if jack_status.dae_status[i[NUM]] != "[simulated]": print jack_status.dae_status[i[NUM]],
            if not cf['_only_dae']:
                print ":ENC:",
                if jack_status.enc_status[i[NUM]] != "[simulated]": print jack_status.enc_status[i[NUM]],
        if i in mp3s_todo:
            print ":ENC:",
            if jack_status.enc_status[i[NUM]] != "[simulated]": print jack_status.enc_status[i[NUM]],
        print

# overwrite cached bitrates from argv
if cf['bitrate']['history'][-1][0] == "argv":
    for i in wavs_todo:
        i[RATE] = cf['_bitrate']
    for i in mp3s_todo:
        i[RATE] = cf['_bitrate']

def check_space(space, wavs_todo, mp3s_todo):
    # check free space
    will_work = 1
    freeable_space = 0
    if cf['_keep_wavs']:
        space_needed = jack_functions.tracksize(wavs_todo)[BOTH]
    elif cf['_otf']:
        space_needed = jack_functions.tracksize(wavs_todo)[ENC]
    else:
        space_needed = jack_functions.tracksize(wavs_todo)[PEAK]
    if cf['_only_dae']:
        space_needed = jack_functions.tracksize(wavs_todo)[WAV]
    else:
        for i in mp3s_todo:
            if space + freeable_space>jack_functions.tracksize(i)[ENC]:
                if not cf['_keep_wavs']:
                    freeable_space = freeable_space + jack_functions.tracksize(i)[WAV] - jack_functions.tracksize(i)[ENC]
            else:
                will_work = 0
                # this is quite dirty
                space_needed = jack_functions.tracksize(i)[ENC] - space + freeable_space
                break

    if (space + freeable_space < space_needed or not will_work) and not cf['_dont_work']:
        error(("insufficient disk space (%sBytes needed), " + "try reorder or " * (not cf['_reorder']) + "free %sBytes.") % (jack_functions.pprint_i(space_needed - freeable_space, "%i %s"), jack_functions.pprint_i(space_needed - freeable_space - jack_ripstuff.raw_space, "%i %s")))


def check_cd():
    if cf['_rip_from_device']:
        all_tracks_on_cd = jack_functions.gettoc(cf['_toc_prog'])
        if not cf['_force'] and not jack_utils.cmp_toc_cd(jack_ripstuff.all_tracks_orig, all_tracks_on_cd, what=(NUM, LEN)):
            error("you did not insert the right cd")

def remove_files(remove_q):
    if cf['_silent_mode'] or cf['_dont_work']:
        print "remove these files before going on:"
        for i in remove_q:
            print i
        print "### . ###"

        if cf['_silent_mode']:
            sys.exit(3)

    else:
        print "/\\" * 40
        for i in remove_q:
            print i
        x = raw_input("These files will be deleted, continue? ") + "x"
        if cf['_force']:
            info("(forced)")
        else:
            if string.upper(x[0]) != "Y":
                sys.exit(0)

        for i in remove_q:
            os.remove(i)

