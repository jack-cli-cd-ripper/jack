# jack.workers: worker functions for
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

import sndhdr
import signal
import posix
import array
import fcntl
import wave
import time
import pty
import sys
import os

import jack.functions
import jack.ripstuff
import jack.helpers
import jack.targets
import jack.utils
import jack.tag

from jack.globals import *
from jack.helpers import helpers
from jack.init import F_SETFL, O_NONBLOCK


def default_signals():
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGQUIT, signal.SIG_DFL)
    signal.signal(signal.SIGHUP, signal.SIG_DFL)
    signal.signal(signal.SIGWINCH, signal.SIG_DFL)


def start_new_process(args, nice_value=0):
    "start a new process in a pty and renice it"
    data = {}
    data['start_time'] = time.time()
    pid, master_fd = pty.fork()
    if pid == CHILD:
        default_signals()
        if nice_value:
            os.nice(nice_value)
        os.execvp(args[0], [a for a in args])
    else:
        data['pid'] = pid
        if os.uname()[0] == "Linux":
            fcntl.fcntl(master_fd, F_SETFL, O_NONBLOCK)
        data['fd'] = master_fd
        data['file'] = os.fdopen(master_fd)
        data['cmd'] = args
        data['buf'] = ""
        data['otf'] = 0
        data['percent'] = 0
        data['elapsed'] = 0
        return data


def start_new_ripper(track, ripper):
    "start a new DAE process"
    helper = helpers[cf['_ripper']]
    cmd = (helper['cmd']).split()
    args = []
    for i in cmd:
        if i == "%n":
            args.append(repr(track[NUM]))
        elif i == "%o":
            args.append(track[NAME] + ".wav")
        elif i == "%d":
            args.append(cf['_cd_device'])
        else:
            args.append(i)
    data = start_new_process(args)
    data['type'] = "ripper"
    data['prog'] = cf['_ripper']
    data['track'] = track
    return data


def start_new_encoder(track, encoder):
    "start a new encoder process"
    helper = helpers[cf['_encoder']]
    if cf['_vbr']:
        cmd = (helper['vbr-cmd']).split()
    else:
        cmd = (helper['cmd']).split()

    args = []
    for i in cmd:
        if i == "%r":
            args.append(repr(track[RATE] * helper['bitrate_factor']))
        elif i == "%q":
            if 'inverse-quality' in helper and helper['inverse-quality']:
                quality = min(9, 10 - cf['_vbr_quality'])
            else:
                quality = cf['_vbr_quality']
            args.append("%.3f" % quality)
        elif i == "%i":
            args.append(track[NAME] + ".wav")
        elif i == "%o":
            args.append(track[NAME] + jack.targets.targets[jack.helpers.helpers[cf['_encoder']]['target']]['file_extension'])
        else:
            if jack.targets.targets[helper['target']]['can_pretag']:
                if i == "%t":
                    if jack.tag.track_names:
                        args.append(jack.tag.track_names[track[NUM]][1])
                    else:
                        args.append("")
                elif i == "%a":
                    if jack.tag.track_names:
                        if jack.tag.track_names[track[NUM]][0]:
                            args.append(jack.tag.track_names[track[NUM]][0])
                        else:
                            args.append(jack.tag.track_names[0][0])
                    else:
                        args.append("")
                elif i == "%n":
                    args.append(repr(track[NUM]))
                elif i == "%l":
                    if jack.tag.track_names:
                        args.append(jack.tag.track_names[0][1])
                    else:
                        args.append("")
                elif i == "%g":
                    if cf['_genre']:
                        args.append(cf['_genre'])
                    else:
                        args.append("")
                elif i == "%y":
                    if cf['_year']:
                        args.append(repr(cf['_year']))
                    else:
                        args.append('0')
                else:
                    args.append(i)
            else:
                args.append(i)
    data = start_new_process(args, cf['_nice_value'])
    data['type'] = "encoder"
    data['prog'] = cf['_encoder']
    data['track'] = track
    return data


def start_new_otf(track, ripper, encoder):
    "start a new ripper/encoder pair for on-the-fly encoding"
    data = {}
    data['rip'] = {}
    data['enc'] = {}
    data['rip']['otf'] = 1
    data['enc']['otf'] = 1
    enc_in, rip_out = os.pipe()
    data['rip']['fd'], rip_err = os.pipe()
    data['enc']['fd'], enc_err = os.pipe()
    args = []
    for i in (helpers[ripper]['otf-cmd']).split():
        if i == "%n":
            args.append(repr(track[NUM]))
        elif i == "%d":
            args.append(cf['_cd_device'])
        else:
            args.append(i)
    data['rip']['start_time'] = time.time()
    pid = os.fork()
    if pid == CHILD:
        default_signals()
        os.dup2(rip_out, STDOUT_FILENO)
        os.dup2(rip_err, STDERR_FILENO)
        os.close(rip_out)
        os.close(rip_err)
        os.execvp(args[0], args)
        # child won't see anything below...
    os.close(rip_out)
    os.close(rip_err)
    data['rip']['pid'] = pid
    data['rip']['cmd'] = helpers[cf['_ripper']]['otf-cmd']
    data['rip']['buf'] = ""
    data['rip']['percent'] = 0
    data['rip']['elapsed'] = 0
    data['rip']['type'] = "ripper"
    data['rip']['prog'] = cf['_ripper']
    data['rip']['track'] = track
    if cf['_vbr']:
        cmd = (helpers[cf['_encoder']]['vbr-otf-cmd']).split()
    else:
        cmd = (helpers[cf['_encoder']]['otf-cmd']).split()
    args = []
    for i in cmd:
        if i == "%r":
            args.append(repr(track[RATE] * helpers[cf['_encoder']]['bitrate_factor']))
        elif i == "%q":
            if 'inverse-quality' in helper and helper['inverse-quality']:
                quality = min(9, 10 - cf['_vbr_quality'])
            else:
                quality = cf['_vbr_quality']
            args.append("%.3f" % quality)
        elif i == "%o":
            args.append(track[NAME] + jack.targets.targets[jack.helpers.helpers[cf['_encoder']]['target']]['file_extension'])
        elif i == "%d":
            args.append(cf['_cd_device'])
        else:
            args.append(i)
    data['enc']['start_time'] = time.time()
    pid = os.fork()
    if pid == CHILD:
        default_signals()
        if cf['_nice_value']:
            os.nice(cf['_nice_value'])
        os.dup2(enc_in, STDIN_FILENO)
        os.dup2(enc_err, STDERR_FILENO)
        os.close(enc_in)
        os.close(enc_err)
        os.execvp(args[0], args)
        # child won't see anything below...
    os.close(enc_in)
    os.close(enc_err)
    data['enc']['pid'] = pid
    data['enc']['otf-pid'] = data['rip']['pid']
    data['enc']['cmd'] = cmd
    data['enc']['buf'] = ""
    data['enc']['percent'] = 0
    data['enc']['elapsed'] = 0
    data['enc']['type'] = "encoder"
    data['enc']['prog'] = cf['_encoder']
    data['enc']['track'] = track
    data['rip']['otf-pid'] = data['enc']['pid']

    if os.uname()[0] == "Linux":
        fcntl.fcntl(data['rip']['fd'], F_SETFL, O_NONBLOCK)
        fcntl.fcntl(data['enc']['fd'], F_SETFL, O_NONBLOCK)
    data['rip']['file'] = os.fdopen(data['rip']['fd'])
    data['enc']['file'] = os.fdopen(data['enc']['fd'])
    return data


def start_new_transcoder(track, decoder, encoder):
    "start a new decoder/encoder pair for transcoding"
    data = {}
    data['dec'] = {}
    data['enc'] = {}
    enc_in, dec_out = os.pipe()
    data['dec']['fd'], dec_err = os.pipe()
    data['enc']['fd'], enc_err = os.pipe()
    args = []
    for i in (helpers[decoder]['decode-otf-cmd']).split():
        if i == "%i":
            args.append(track[NAME] + jack.targets.targets[jack.helpers.helpers[decoder]['target']]['file_extension'])
        else:
            args.append(i)
    data['dec']['start_time'] = time.time()
    pid = os.fork()
    if pid == CHILD:
        default_signals()
        os.dup2(dec_out, STDOUT_FILENO)
        os.dup2(dec_err, STDERR_FILENO)
        os.close(dec_out)
        os.close(dec_err)
        os.execvp(args[0], args)
        # child won't see anything below...
    os.close(dec_out)
    os.close(dec_err)
    data['dec']['pid'] = pid
    data['dec']['cmd'] = helpers[decoder]['decode-otf-cmd']
    data['dec']['buf'] = ""
    data['dec']['percent'] = 0
    data['dec']['elapsed'] = 0
    data['dec']['type'] = "decoder"
    data['dec']['prog'] = decoder
    data['dec']['track'] = track
    if cf['_vbr']:
        cmd = (helpers[cf['_encoder']]['vbr-otf-cmd']).split()
    else:
        cmd = (helpers[cf['_encoder']]['otf-cmd']).split()
    args = []
    for i in cmd:
        if i == "%r":
            args.append(repr(track[RATE] * helpers[encoder]['bitrate_factor']))
        elif i == "%q":
            if 'inverse-quality' in helpers[encoder] and helpers[encoder]['inverse-quality']:
                quality = min(9, 10 - cf['_vbr_quality'])
            else:
                quality = cf['_vbr_quality']
            args.append("%.3f" % quality)
        elif i == "%o":
            args.append(track[NAME] + jack.targets.targets[jack.helpers.helpers[encoder]['target']]['file_extension'])
        else:
            args.append(i)
    data['enc']['start_time'] = time.time()
    pid = os.fork()
    if pid == CHILD:
        default_signals()
        if cf['_nice_value']:
            os.nice(cf['_nice_value'])
        os.dup2(enc_in, STDIN_FILENO)
        os.dup2(enc_err, STDERR_FILENO)
        os.close(enc_in)
        os.close(enc_err)
        os.execvp(args[0], args)
        # child won't see anything below...
    os.close(enc_in)
    os.close(enc_err)
    data['enc']['pid'] = pid
    data['enc']['otf-pid'] = data['dec']['pid']
    data['enc']['cmd'] = cmd
    data['enc']['buf'] = ""
    data['enc']['percent'] = 0
    data['enc']['elapsed'] = 0
    data['enc']['type'] = "encoder"
    data['enc']['prog'] = encoder
    data['enc']['track'] = track
    data['dec']['otf-pid'] = data['enc']['pid']

    if os.uname()[0] == "Linux":
        fcntl.fcntl(data['dec']['fd'], F_SETFL, O_NONBLOCK)
        fcntl.fcntl(data['enc']['fd'], F_SETFL, O_NONBLOCK)
    data['dec']['file'] = os.fdopen(data['dec']['fd'])
    data['enc']['file'] = os.fdopen(data['enc']['fd'])
    return data


# FIXME: all this offset stuff has to go, track 0 support has to come.
def ripread(track, offset=0):
    "rip one track from an image file."

    if track[NUM] == 1 and track[START] > CDDA_BLOCKS_PER_SECOND * 10 and cf['_pregap_name']:
        # silently extract the pregap track
        pregap = track.copy()
        pregap[NUM] = 0
        pregap[START] = 0
        pregap[LEN] = track[START]
        pregap[NAME] = cf['_pregap_name']
        extract_track_from_image(pregap, offset, silent=True)

    pid, master_fd = pty.fork()
    start_time = time.time()

    if pid == CHILD:
        # debug - will trigger 'A failure occured'!:
        # so=open("/tmp/jack.stdout", "w")
        # sys.stdout = so
        # se=open("/tmp/jack.stderr", "w+")
        # sys.stderr = se

        default_signals()

        print_flush(":fAE: waiting for status report...")
        hdr = extract_track_from_image(track, offset)
        stop_time = time.time()
        read_speed = track[LEN] // CDDA_BLOCKS_PER_SECOND // (stop_time - start_time)

        if read_speed < 100:
            print("[%2.0fx]" % read_speed, end=' ')
        else:
            print("[99x]", end=' ')
        if hdr[0] in ('bin', 'wav'):
            print("[      - read from image -     ]")
        else:
            print("[cdr-WARNING, check byteorder !]")
        sys.stdout.flush()
        posix._exit(0)

    # we are not the child
    data = {}
    data['start_time'] = start_time
    data['pid'] = pid
    data['fd'] = master_fd
    data['file'] = os.fdopen(master_fd)
    data['cmd'] = ""
    data['buf'] = ""
    data['type'] = "image_reader"
    data['prog'] = "builtin"
    data['track'] = track
    data['percent'] = 0
    data['otf'] = 0
    data['elapsed'] = 0
    return data


def extract_track_from_image(track, offset=0, silent=False):
    hdr = sndhdr.whathdr(cf['_image_file'])
    my_swap_byteorder = cf['_swap_byteorder']
    size_offset = offset
    if hdr:
        # most people probably use cdparanoia 1- (instead of 0- if
        # applicable) for image creation, so for a wav file use:
        image_offset = -offset
    else:
        if (cf['_image_file']).upper()[-4:] == ".CDR":
            # Unknown header, assuming cdr
            hdr = ('cdr', 44100, 2, -1, 16)

            # assume old cdrdao which started at track 1, not at block 0
            image_offset = -offset
        elif (cf['_image_file']).upper()[-4:] == ".BIN":
            # Unknown header, assuming bin
            hdr = ('bin', 44100, 2, -1, 16)

            # assume new cdrdao which starts at block 0, byteorder is reversed.
            my_swap_byteorder = not my_swap_byteorder

            if cf['_track_1_pregap_silence'] is None:
                image_offset = 0
            else:
                image_offset = -offset
                size_offset = 0
        elif (cf['_image_file']).upper()[-4:] == ".RAW":
            # Unknown header, assuming raw
            hdr = ('bin', 44100, 2, -1, 16)
            image_offset = 0
        else:
            warning("unsupported image file " + cf['_image_file'])
            sys.stdout.flush()
            posix._exit(4)

    expected_filesize = jack.functions.tracksize(jack.ripstuff.all_tracks)[CDR] + CDDA_BLOCKSIZE * size_offset

    # WAVE header is 44 Bytes for normal PCM files.
    if hdr[0] == 'wav':
        expected_filesize = expected_filesize + 44

    if abs(jack.utils.filesize(cf['_image_file']) - expected_filesize) > CDDA_BLOCKSIZE:
        warning("image file size mismatch, aborted. %d != %d" % (jack.utils.filesize(cf['_image_file']), expected_filesize))
        sys.stdout.flush()
        posix._exit(1)

    if hdr[0] == 'wav' and (hdr[1], hdr[2], hdr[4]) != (44100, 2, 16):
        warning("unsupported WAV, need CDDA_fmt, aborted.")
        sys.stdout.flush()
        posix._exit(2)

    if hdr[0] not in ('wav', 'cdr', 'bin'):
        warning("unsupported: " + hdr[0] + ", aborted.")
        sys.stdout.flush()
        posix._exit(3)

    # set up output wav file:
    wav = wave.open(track[NAME] + ".wav", 'wb')
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(44100)
    wav.setnframes(0)
    wav.setcomptype('NONE', 'not compressed')

    # calculate and seek to position in image file
    track_start = (track[START] + image_offset) * CDDA_BLOCKSIZE
    if hdr[0] == 'wav':
        track_start = track_start + 44
    f = open(cf['_image_file'], 'rb')
    f.seek(track_start)

    # copy / convert the data
    for i in range(0, track[LEN]):
        buf = array.array("h")
        buf.fromfile(f, CDDA_BLOCKSIZE // 2)

        # this is inverted as WAVE swabs them again
        if not my_swap_byteorder:
            buf.byteswap()

        wav.writeframesraw(buf.tobytes())

        if i % 1000 == 0:
            print_flush(":fAE: Block " + repr(i) + "/" + repr(track[LEN]) + (" (%2i%%)" % (i * 100 // track[LEN])), silent)

    wav.close()
    f.close()

    return hdr


def print_flush(arg, suppress=False):
    if not suppress:
        print(arg)
        sys.stdout.flush()
