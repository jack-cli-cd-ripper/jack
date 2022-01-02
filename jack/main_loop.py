# -*- coding: utf-8 -*-
# jack.main_loop: the main encoding loop for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2004  Arne Zellentin <zarne@users.sf.net>

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

import traceback
import signal
import select
import time
import sys
import os

import jack.functions
import jack.ripstuff
import jack.encstuff
import jack.children
import jack.display
import jack.helpers
import jack.targets
import jack.workers
import jack.status
import jack.utils
import jack.misc
import jack.term

from jack.globals import *

def main_loop(mp3s_todo, wavs_todo, space, dae_queue, enc_queue, track1_offset, trc_tracks):
    global helper_new_status
    global helper_final_status
    global helper_percent

    global_error = 0    # remember if something went wrong
    actual_load = -2    # this is always smaller than max_load
    waiting_load = 0    # are we waiting for the load to drop?
    waiting_space = 0   # are we waiting for disk space to be freed?
    space_waiting = 0   # how much space _running_ subprocesses will consume
    space_adjust = 0    # by how much space has been modified
    blocked = 0         # we _try_ do detect deadlocks
    cycles = 0          # it's sort of a timer
    last_update = 0     # screen updates are done once per second
    pause = 0           # no new encoders are started if pause==1
    flags = "[   ]"     # runtime controllable flags
    enc_running = 0     # what is going on?
    dae_running = 0     # what is going on?

    rotate = "/-\\|"
    rotate_ball = " .o0O0o."
    rot_cycle = len(rotate)
    rot_ball_cycle = len(rotate_ball)
    rot_count = 0
    global_done = 0
    first_encoder = 1
    ext = jack.targets.targets[jack.helpers.helpers[cf['_encoder']]['target']]['file_extension']
    global_blocks = jack.functions.tracksize(wavs_todo)[BLOCKS] + jack.functions.tracksize(mp3s_todo)[BLOCKS]

    #
    # MAIN LOOP ###
    #

    global_start = time.time()
    while mp3s_todo or enc_queue or dae_queue or enc_running or dae_running:
        orig_space = space
        # feed in the WAVs which have been there from the
        # start
        if mp3s_todo and jack.functions.tracksize(mp3s_todo[0])[ENC] < space:
            waiting_space = 0
            enc_queue.append(mp3s_todo[0])
            space = space - jack.functions.tracksize(mp3s_todo[0])[ENC]
            jack.status.enc_stat_upd(mp3s_todo[0][NUM], "waiting for encoder.")
            mp3s_todo = mp3s_todo[1:]

        # start new DAE subprocess

        elif (len(enc_queue) + enc_running) < (cf['_read_ahead'] + cf['_encoders']) and dae_queue and dae_running < cf['_rippers'] and ((jack.functions.tracksize(dae_queue[0])[BOTH] < space) or (cf['_only_dae'] and jack.functions.tracksize(dae_queue[0])[WAV] < space) or (cf['_otf'] and jack.functions.tracksize(dae_queue[0])[ENC] < space)):
            waiting_space = 0
            this_is_ok = 1
            if pause:
                this_is_ok = 0
                jack.status.dae_stat_upd(dae_queue[0][NUM], "Paused. Press 'c' to continue.")
            elif cf['_rip_from_device']:
                all_tracks_on_cd = jack.functions.gettoc(cf['_toc_prog'])
                if not jack.utils.cmp_toc_cd(jack.ripstuff.all_tracks_orig, all_tracks_on_cd, what=(NUM, LEN)):
                    while dae_queue:
                        track = dae_queue[0]
                        dae_queue = dae_queue[1:]
                        jack.status.dae_stat_upd(track[NUM], "Wrong disc - aborting this track")
                    global_error = global_error + 1
                    this_is_ok = 0
            if this_is_ok:
                if cf['_only_dae']:
                    space_waiting = space_waiting + jack.functions.tracksize(dae_queue[0])[WAV]
                    space = space - jack.functions.tracksize(dae_queue[0])[WAV]
                elif cf['_otf']:
                    space_waiting = space_waiting + jack.functions.tracksize(dae_queue[0])[ENC]
                    space = space - jack.functions.tracksize(dae_queue[0])[ENC]
                else:
                    space_waiting = space_waiting + jack.functions.tracksize(dae_queue[0])[BOTH]
                    space = space - jack.functions.tracksize(dae_queue[0])[BOTH]
                dae_running = dae_running + 1
                track = dae_queue[0]
                dae_queue = dae_queue[1:]
                if cf['_otf']:
                    # note: image_reader can't do otf at the moment.
                    jack.status.dae_stat_upd(track[NUM], ":DAE: waiting for status report...")
                    if cf['_encoder'] in ("lame", "gogo", "flac", "mppenc"):
                        jack.status.enc_stat_upd(track[NUM], "[no otf status for %s]" % cf['_encoder'])
                    else:
                        jack.status.enc_stat_upd(track[NUM], "waiting for encoder.")
                    enc_running = enc_running + 1
                    if first_encoder:
                        first_encoder = 0
                        global_start = time.time()
                    data = jack.workers.start_new_otf(track, cf['_ripper'], cf['_encoder'])
                    jack.children.children.append(data['rip'])
                    jack.children.children.append(data['enc'])
                else:
                    if jack.status.enc_status[track[NUM]]:
                        jack.status.enc_cache[track[NUM]] = jack.status.enc_status[track[NUM]]
                        jack.status.enc_stat_upd(track[NUM], "[...]")
                    jack.status.dae_stat_upd(track[NUM], ":DAE: waiting for status report...")
                    if cf['_rip_from_device']:
                        jack.children.children.append(jack.workers.start_new_ripper(track, cf['_ripper']))
                    elif cf['_image_file']:
                        jack.children.children.append(jack.workers.ripread(track, track1_offset))
                    else:
                        jack.status.dae_stat_upd(track[NUM], ":?AE: don't know how to rip this!")

        # start new encoder subprocess

        if enc_queue and enc_running < cf['_encoders']:
            if jack.functions.tracksize(enc_queue[0])[ENC] <= space + space_waiting:
                waiting_space = 0
                actual_load = jack.misc.loadavg()
                if actual_load < cf['_max_load']:
                    waiting_load = 0
                    enc_running = enc_running + 1
                    track = enc_queue[0]
                    enc_queue = enc_queue[1:]
                    jack.status.enc_stat_upd(track[NUM], "waiting for encoder...")
                    if track[NUM] in trc_tracks:
                        decoder = trc_tracks[track[NUM]]
                        data = jack.workers.start_new_transcoder(track, decoder, cf['_encoder'])
                        jack.children.children.append(data['dec'])
                        jack.children.children.append(data['enc'])
                    else:
                        jack.children.children.append(jack.workers.start_new_encoder(track, cf['_encoder']))
                    if first_encoder:
                        first_encoder = 0
                        global_start = time.time()
                else:
                    waiting_load = 1

        # check for subprocess output

        readfd = [sys.stdin.fileno()]
        for i in jack.children.children:
            readfd.append(i['fd'])
        try:
            rfd, wfd, xfd = select.select(readfd, [], [], cf['_update_interval'])
        except:
            rfd, wfd, xfd = [], [], []
            jack.term.tmod.sig_winch_handler(None, None)

        # check for keyboard commands

        if sys.stdin.fileno() in rfd:
            last_update = last_update - cf['_update_interval']
            cmd = jack.term.tmod.getkey()
            sys.stdin.flush()
            if cmd.upper() == "Q":
                jack.display.exit()
            elif not pause and cmd.upper() == "P":
                pause = 1
                flags = flags[:1] + "P" + flags[2:]
            elif cmd.upper() == "C" or pause and cmd.upper() == "P":
                pause = 0
                flags = flags[:1] + " " + flags[2:]
            elif not flags[3] == "e" and cmd.upper() == "E":
                for i in jack.children.children:
                    if i['type'] == "encoder":
                        os.kill(i['pid'], signal.SIGSTOP)
                        flags = flags[:3] + "e" + flags[4:]
            elif flags[3] == "e" and cmd.upper() == "E":
                for i in jack.children.children:
                    if i['type'] == "encoder":
                        os.kill(i['pid'], signal.SIGCONT)
                        flags = flags[:3] + " " + flags[4:]
            elif not flags[2] == "r" and cmd.upper() == "R":
                for i in jack.children.children:
                    if i['type'] == "ripper":
                        os.kill(i['pid'], signal.SIGSTOP)
                        flags = flags[:2] + "r" + flags[3:]
            elif flags[2] == "r" and cmd.upper() == "R":
                for i in jack.children.children:
                    if i['type'] == "ripper":
                        os.kill(i['pid'], signal.SIGCONT)
                        flags = flags[:2] + " " + flags[3:]
            elif cmd.upper() == "U":
                cycles = 29     # do periodic stuff _now_
            else:
                if not jack.term.tmod.move_pad(cmd):
                    if cmd == 'KEY_RESIZE':
                        continue
                    # open("/tmp/jack-unhandled-keys", "a").write(cmd + "\n")
                last_update = time.time()

        # read from file with activity
        for i in jack.children.children:

            if i['type'] == "decoder":
                continue

            if i['fd'] in rfd:
                if os.uname()[0] == "Linux" and i['type'] != "image_reader":
                    try:
                        x = i['file'].read()
                    except (IOError, ValueError):
                        pass
                else:
                    read_chars = 0
                    x = ""
                    while read_chars < jack.helpers.helpers[i['prog']]['status_blocksize']:
                        try:
                            xchar = i['file'].read(1)
                        except (IOError, ValueError):
                            break
                        x = x + xchar
                        read_chars = read_chars + 1
                        try:
                            rfd2, wfd2, xfd2 = select.select([i['fd']], [], [], 0.0)
                        except:
                            rfd2, wfd2, xfd2 = [], [], []
                            jack.term.tmod.sig_winch_handler(None, None)
                        if i['fd'] not in rfd2:
                            break
                # put read data into child's buffer
                i['buf'] = i['buf'] + x

                if 'filters' in jack.helpers.helpers[i['prog']]:
                    for fil in jack.helpers.helpers[i['prog']]['filters']:
                        i['buf'] = fil[0].sub(fil[1], i['buf'])

                i['buf'] = i['buf'][-jack.helpers.helpers[i['prog']]['status_blocksize']:]

        # check for exiting child processes
        if jack.children.children:
            respid, res = os.waitpid(-1, os.WNOHANG)
            if respid != 0:
                last_update = last_update - cf['_update_interval']  # ensure info is printed
                new_ch = []
                exited_proc = []
                for i in jack.children.children:
                    if i['pid'] == respid:
                        if exited_proc != []:
                            error("pid " + repr(respid) + " found at multiple child processes")
                        exited_proc = i
                    else:
                        new_ch.append(i)
                if not exited_proc:
                    error("unknown process (" + repr(respid) + ") has exited")
                jack.children.children = new_ch
                x = ""
                try:
                    x = exited_proc['file'].read()
                except (IOError, ValueError):
                    pass
                exited_proc['buf'] = (exited_proc['buf'] + x)[-jack.helpers.helpers[exited_proc['prog']]['status_blocksize']:]
                exited_proc['file'].close()

                global_error = global_error + res
                track = exited_proc['track']
                num = track[NUM]
                stop_time = time.time()
                speed = (track[LEN] / float(CDDA_BLOCKS_PER_SECOND)) / (stop_time - exited_proc['start_time'])

                if exited_proc['type'] in ("ripper", "image_reader"):
                    dae_running = dae_running - 1
                    if cf['_exec_when_done'] and exited_proc['type'] == "ripper" and dae_running == 0 and len(dae_queue) == 0:
                        os.system(cf['_exec_rip_done'])
                    if not res:
                        if not exited_proc['otf']:
                            if os.path.exists(track[NAME] + ".wav"):
                                if jack.functions.tracksize(track)[WAV] != jack.utils.filesize(track[NAME] + ".wav"):
                                    res = 242
                                    jack.status.dae_stat_upd(num, jack.status.get_2_line(exited_proc['buf']))
                            else:
                                jack.status.dae_stat_upd(num, jack.status.get_2_line(exited_proc['buf']))
                                res = 243
                            global_error = global_error + res
                    if res and not cf['_sloppy']:
                        if os.path.exists(track[NAME] + ".wav"):
                            os.remove(track[NAME] + ".wav")
                            space = space + jack.functions.tracksize(track)[WAV]
                            if cf['_otf']:
                                os.kill(exited_proc['otf-pid'], signal.SIGTERM)
                                if os.path.exists(track[NAME] + ext):
                                    os.remove(track[NAME] + ext)
                                space = space + jack.functions.tracksize(track)[ENC]
                            if not cf['_otf'] and not cf['_only_dae'] and track not in jack.encstuff.mp3s_ready:
                                space = space + jack.functions.tracksize(track)[ENC]
                            jack.status.dae_stat_upd(num, 'DAE failed with status ' + repr(res) + ", wav removed.")
                    else:
                        if exited_proc['type'] == "image_reader":
                            jack.status.dae_stat_upd(num, jack.status.get_2_line(exited_proc['buf']))
                        else:
                            if exited_proc['otf'] and 'otf-final_status_fkt' in jack.helpers.helpers[exited_proc['prog']]:
                                exec((jack.helpers.helpers[exited_proc['prog']]['otf-final_status_fkt']), globals(), locals())
                            else:
                                last_status = None   # (only used in cdparanoia)
                                exec((jack.helpers.helpers[exited_proc['prog']]['final_status_fkt']), globals(), locals())
                            jack.status.dae_stat_upd(num, helper_final_status)
                        if jack.status.enc_cache[num]:
                            jack.status.enc_stat_upd(num, jack.status.enc_cache[num])
                            jack.status.enc_cache[num] = ""
                        jack.functions.progress(num, "dae", jack.status.dae_status[num])
                        if not cf['_otf'] and not cf['_only_dae'] and track not in jack.encstuff.mp3s_ready:
                            if waiting_space:
                                mp3s_todo.append(track)
                                space = space + jack.functions.tracksize(track)[ENC]
                            else:
                                jack.status.enc_stat_upd(num, 'waiting for encoder.')
                                enc_queue.append(track)
                    space_waiting = space_waiting - jack.functions.tracksize(track)[WAV]

                elif exited_proc['type'] == "encoder":
                    enc_running = enc_running - 1
                    # completed vbr files shouldn't be to small, but this still
                    # caused confusion so again, vbr is an exception:
                    if not cf['_vbr'] and not res and jack.functions.tracksize(track)[ENC] * 0.99 > jack.utils.filesize(track[NAME] + ext):
                        res = 242
                        global_error = global_error + res
                    if res:
                        global_blocks = global_blocks - exited_proc['track'][LEN]
                        global_start = global_start + exited_proc['elapsed'] // (enc_running + 1)
                        if global_start > time.time():
                            global_start = time.time()
                        if os.path.exists(track[NAME] + ext):
                            # mp3enc doesn't report errors when out of disk
                            # space...
                            os.remove(track[NAME] + ext)
                        space = space + jack.functions.tracksize(track)[ENC]
                        jack.status.enc_stat_upd(num, 'coding failed, err#' + repr(res))
                    else:
                        global_done = global_done + exited_proc['track'][LEN]
                        if cf['_vbr']:
                            rate = int((jack.utils.filesize(track[NAME] + ext) * 0.008) / (track[LEN] / 75.0))
                        else:
                            rate = track[RATE]
                        jack.status.enc_stat_upd(num, "[coding @" + '%s' % jack.functions.pprint_speed(speed) + "x done, %dkbit" % rate)
                        jack.functions.progress(num, "enc", repr(rate), jack.status.enc_status[num])
                        if not cf['_otf'] and not cf['_keep_wavs'] and not track[NUM] in trc_tracks:
                            os.remove(track[NAME] + ".wav")
                            space = space + jack.functions.tracksize(track)[WAV]
                elif exited_proc['type'] == "decoder":
                    pass
                else:
                    error("child process of unknown type (" + exited_proc['type'] + ") exited")
                if global_error:
                    jack.display.smile = " :-["

        space_adjust += orig_space - space

        if last_update + cf['_update_interval'] <= time.time():
            last_update = time.time()

            # interpret subprocess output

            for i in jack.children.children:
                if i['type'] == "ripper":
                    if len(i['buf']) == jack.helpers.helpers[i['prog']]['status_blocksize']:
                        if i['otf'] and 'otf-status_fkt' in jack.helpers.helpers[i['prog']]:
                            exec((jack.helpers.helpers[i['prog']]['otf-status_fkt']), globals(), locals())
                        else:
                            exec((jack.helpers.helpers[i['prog']]['status_fkt']), globals(), locals())
                        if helper_new_status:
                            try:
                                jack.status.dae_stat_upd(i['track'][NUM], ":DAE: " + helper_new_status)
                            except:
                                debug("error in dae_stat_upd")

                elif i['type'] == "encoder":
                    if len(i['buf']) == jack.helpers.helpers[i['prog']]['status_blocksize']:
                        loc = {'i': i, 'helper_percent': 0}
                        try:
                            exec((jack.helpers.helpers[i['prog']]['percent_fkt']), globals(), loc)
                        except:
                            debug("error in percent_fkt of %s. Traceback: %s " % (jack.helpers.helpers[i['prog']], traceback.format_exc()))
                        i['percent'] = loc['helper_percent']
                        if i['percent'] > 0:
                            i['elapsed'] = time.time() - i['start_time']
                            speed = ((i['track'][LEN] / float(CDDA_BLOCKS_PER_SECOND)) * (i['percent'] / 100)) / i['elapsed']
                            eta = (100 - i['percent']) * i['elapsed'] // i['percent']
                            eta_ms = "%02i:%02i" % (eta // 60, eta % 60)
                            jack.status.enc_stat_upd(i['track'][NUM], '%2i%% done, ETA:%6s, %sx' % (i['percent'], eta_ms, jack.functions.pprint_speed(speed)))
                            # jack.term.tmod.dae_stat_upd(i['track'][NUM],
                            # None, i['percent'])

                elif i['type'] == "image_reader":
                    line = str(jack.status.get_2_line(i['buf'], default="")).strip()
                    if line:
                        jack.status.dae_stat_upd(i['track'][NUM], line)
                        if line.startswith("Error"):
                            global_error = global_error + 1

                elif i['type'] == "decoder":
                    pass

                else:
                    error("unknown subprocess type \"" + i['type'] + "\".")

            cycles = cycles + 1
            if cycles % 30 == 0:
                if cf['_recheck_space'] and not cf['space_from_argv']['history'][-1][0] == "argv":
                    actual_space = jack.functions.df()
                    if space_adjust:
                        diff = actual_space - space
                        if diff > space_adjust:
                            space = space + space_adjust
                            space_adjust = 0
                            waiting_space = 0
                        else:
                            space = space + diff
                            space_adjust = space_adjust - diff
                    else:
                        if actual_space < space:
                            space_adjust = space - actual_space
                            space = actual_space

            if space_adjust and enc_running == 0 and dae_running == 0:
                waiting_space = waiting_space + 1
            if not waiting_space >= 2 and not waiting_load and enc_running == 0 and dae_running == 0:
                blocked = blocked + 1
            else:
                blocked = 0

            total_done = global_done
            for i in jack.children.children:
                total_done = total_done + (i['percent'] // 100) * i['track'][LEN]
            elapsed = time.time() - global_start
            if global_blocks > 0:
                helper_percent = total_done // global_blocks
            else:
                helper_percent = 0
            if helper_percent > 0 and elapsed > 40:
                eta = ((1 - helper_percent) * elapsed // helper_percent)
                eta_hms = " ETA=%i:%02i:%02i" % (eta // 3600, (eta % 3600) // 60, eta % 60)
            else:
                eta_hms = ""

            if (flags[1:-1]).strip():
                print_flags = " " + flags
            else:
                print_flags = ""
            if dae_running:
                rot = rotate_ball[rot_count % rot_ball_cycle]
            else:
                rot = rotate[rot_count % rot_cycle]
            rot_count = rot_count + 1

            # print status

            if blocked > 2:
                jack.display.special_line = " ...I feel blocked - quit with 'q' if you get bored... "
                if blocked > 5:
                    space = jack.functions.df() - cf['_keep_free']
            elif waiting_load and waiting_space >= 2:
                jack.display.special_line = " ...waiting for load (%.2f)" % actual_load + ") < %.2f" % cf['_max_load'] + " and for " + jack.functions.pprint_i(space_adjust, "%i %sBytes") + " to be freed... "
            elif waiting_space >= 2:
                jack.display.special_line = " ...waiting for " + jack.functions.pprint_i(space_adjust, "%i %sBytes") + " to be freed.... "
            elif waiting_load:
                jack.display.special_line = " ...waiting for load (%.2f) to drop below %.2f..." % (actual_load, cf['_max_load'])
            else:
                jack.display.special_line = None

            jack.display.bottom_line = "(" + rot + ") " \
                + "SPACE:" * (space_adjust != 0) \
                + "space:" * (space_adjust == 0) \
                + jack.functions.pprint_i(space, "%i%sB") \
                + (" waiting_WAVs:%02i" % len(enc_queue)) \
                + " DAE:" + repr(cf['_rippers'] - dae_running) + "+" + repr(dae_running) \
                + " ENC:" + repr(cf['_encoders'] - enc_running) + "+" + repr(enc_running) \
                + eta_hms \
                + " errors: " + repr(global_error) \
                + jack.display.smile + print_flags

            jack.term.tmod.update(jack.display.special_line, jack.display.bottom_line)

    return global_error

# end of main loop #########################################################
