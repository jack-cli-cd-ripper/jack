# -*- coding: iso-8859-15 -*-
### jack_functions: functions for
### jack - extract audio from a CD and encode it using 3rd party software
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

import codecs
import traceback
import sndhdr
import types
import string
import sys
import os

import jack_TOCentry
import jack_CDTime
import jack_utils
import jack_TOC
import jack_mp3
import jack_helpers

from jack_globals import *

progress_changed = None

def df(fs = ".", blocksize = 1024):
    "returns free space on a filesystem (in bytes)"
    try:
        from os import statvfs
        statvfs_found = 1
    except:
        statvfs_found = 0

    if statvfs_found:
        (f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail, f_flag, f_namemax) = statvfs(fs)
        return long(f_bavail) * long(f_bsize)
    else:
        # Not very portable
        p = os.popen("df " + fs)
        s = string.split(string.rstrip(p.readline()))
        for i in range(len(s)):
            if s[i] == "Available":
                p.close()
                s = string.split(string.rstrip(p.readline()))
                return int(s[i]) * long(blocksize) - long(keep_free)

def get_sysload_linux_proc():
    "extract sysload from /proc/loadavg, linux only (?)"
    f = open("/proc/loadavg", "r")
    loadavg = float(string.split(f.readline())[0])
    return loadavg

def pprint_i(num, fmt = "%i%s", scale = 2.0**10, max = 4):
    "return a string describing an int in a more human-readable way"
    c = ""
    change = 0
    for i in ("K", "M", "G", "T"):
        if abs(num) >= scale:
            c = i
            num = num / scale
            change = 1
    if change:
        #num = num + 0.5
        if num > 999:
            return fmt % (num, c)
        elif num >= 100:
            return string.replace(fmt, "%i", "%s") % (`num`[:3], c)
        else:
            return string.replace(fmt, "%i", "%s") % (`num`[:4], c)
    else:
        return fmt % (num, c)

def pprint_speed(s, len=4):
    if len >= 4:
        if s < 10:
            return "%4.2f" % s
        if s < 100:
            return "%4.1f" % s
        if s < 1000:
            return "%4.0f" % s
        if s < 10000:
            return "%4d" % (s + 0.5)
        else:
            return "9999"
    elif len == 3:
        if s < 10:
            return "%3.1f" % s
        if s < 100:
            return "%3.0f" % s
        if s < 1000:
            return "%3d" % s + 0.5
        else:
            return "999"
    else:
        return "X" * len

def gettoc(toc_prog):
    "Returns track list"
    if jack_helpers.helpers[toc_prog].has_key('toc_cmd'):
        cmd = string.replace(jack_helpers.helpers[toc_prog]['toc_cmd'], "%d", cf['_cd_device'])
        if cf['_gen_device']:
            cmd = string.replace(cmd, "%D", cf['_gen_device'])
        p = os.popen(cmd)
        start = 0
        erg = []
        l = p.readline()
        exec(jack_helpers.helpers[toc_prog]['toc_fkt'])
        if p.close():
            error("%s failed - could not read CD's TOC." % toc_prog)
        else:
            return erg
    else:
        erg = []
        try:
            exec(jack_helpers.helpers[toc_prog]['toc_fkt'])
        except SystemExit:
            sys.exit(1)
        except:
            traceback.print_exc()
            error("""%s could not read the disk's TOC. If you already ripped the
               CD, you'll have to cd into the directory which is either named
               after the CD's title or still called jack-xxxxxxxx (xxxxxxxx is a
               hex number).""" % toc_prog)
        return erg

def guesstoc(names):
    "Return track list based on guessed lengths"
    num = 1
    start = 0
    erg = []
    progr = []
    for i in names:
        i_name = os.path.basename(i)[:-4]
        i_ext  = string.upper(os.path.basename(i)[-4:])
        if i_ext == ".MP3":
            x = jack_mp3.mp3format(i) 
            if not x:
                error("could not get MP3 info for file \"%x\"" % i)
            blocks = int(x['length'] * CDDA_BLOCKS_PER_SECOND + 0.5)
            #           NUM, LEN,    START, COPY, PRE, CH, RIP, RATE,
            #   NAME
            erg.append([num, blocks, start, 0,    0,   2,  1,   x['bitrate'],
                i_name])
            progr.append([num, "dae", "  *   [          simulated           ]"])
            progr.append([num, "enc", `x['bitrate']`, "[ s i m u l a t e d %3ikbit]" % (x['bitrate'] + 0.5)])
            if cf['_name'] % num != i_name:
                progr.append([num, "ren", cf['_name'] % num + "-->" + i_name])
        elif i_ext == ".WAV":
            x = sndhdr.whathdr(i)
            if not x:
                error("this is not WAV-format: " + i)
            if x != ('wav', 44100, 2, -1, 16):
                error("unsupportet format " + `x` +  " in " + i)
            blocks = jack_utils.filesize(i)
            blocks = blocks - 44    # substract WAV header
            extra_bytes = blocks % CDDA_BLOCKSIZE
            if not extra_bytes == 0:
                warning("this is not CDDA block-aligned: " + `i`)
                yes = raw_input("May I strip %d bytes (= %.4fseconds) off the end? " % (extra_bytes, extra_bytes / 2352.0 / 75.0))
                if not string.upper((yes + "x")[0]) == "Y":
                    print "Sorry, I can't process non-aligned files (yet). Bye!"
                    sys.exit()
                f = open(i, "r+")
                f.seek(-extra_bytes, 2)
                f.truncate()
                f.close()
                blocks = blocks - extra_bytes
            blocks = blocks / CDDA_BLOCKSIZE
            erg.append([num, blocks, start, 0, 0, 2, 1, cf['_bitrate'], i_name])
            progr.append([num, "dae", "  =p  [  s  i  m  u  l  a  t  e  d   ]"])
            if cf['_name'] % num != i_name:
                progr.append([num, "ren", cf['_name'] % num + "-->" + i_name])
        elif i_ext == ".OGG":
            error("you still have to wait for ogg support for this operation, sorry.")
        elif i_ext == ".FLAC":
            error("you still have to wait for FLAC support for this ooperation, sorry.")
        else:
            error("this is neither .mp3 nor .ogg nor .wav nor .flac: %s" % i)
        num = num + 1
        start = start + blocks
    for i in progr:     # this is deferred so that it is only written if no
                        # files fail
        progress(i)
    return erg

#XXX will be moved to jack_convert
def timestrtoblocks(str):
    "convert mm:ss:ff to blocks"
    str = string.split(str, ":")
    blocks = int(str[2])
    blocks = blocks + int(str[1]) * CDDA_BLOCKS_PER_SECOND
    blocks = blocks + int(str[0]) * 60 * CDDA_BLOCKS_PER_SECOND
    return blocks

B_MM, B_SS, B_FF = 0, 1, 2
def blockstomsf(blocks):
    from jack_globals import CDDA_BLOCKS_PER_SECOND
    "convert blocks to mm, ss, ff"
    mm = blocks / 60 / CDDA_BLOCKS_PER_SECOND
    blocks = blocks - mm * 60 * CDDA_BLOCKS_PER_SECOND
    ss = blocks / CDDA_BLOCKS_PER_SECOND
    ff = blocks % CDDA_BLOCKS_PER_SECOND
    return mm, ss, ff, blocks

def starts_with(str, with):
    "checks whether str starts with with"
    return str[0:len(with)] == with

## #XXX the following will be used if all references to it have been updated.
## meanwhile the wrapper below is used.

def real_cdrdao_gettoc(tocfile):     # get toc from cdrdao-style toc-file
    "returns TOC object, needs name of toc-file to read"
    toc = jack_TOC.TOC()

    if not os.path.exists(tocfile):
        error("Can't open TOC file '%s': file does not exist." % os.path.abspath(tocfile))
    try:
        f = open(tocfile, "r")
    except (IOError, OSError), e:
        error("Can't open TOC file '%s': %s" % (os.path.abspath(tocfile), e))

    tocpath, tocfiledummy = os.path.split(tocfile)

# a virtual track 0 is introduced which gets all of track 1s pregap.
# it is removed later if it is too small to contain anything interesting.

    actual_track = jack_TOCentry.TOCentry()
    actual_track.number = 0
    actual_track.type = "audio"
    actual_track.channels = 2
    actual_track.media = "image"
    actual_track.start = 0
    actual_track.length = 0
    actual_track.rip = 1
    actual_track.bitrate = cf['_bitrate']
    actual_track.image_name = ""
    actual_track.rip_name = cf['_name'] % 0

## tocfile data is read in line by line.

    num = 0
    while 1:
        line = f.readline()
        if not line:
            if actual_track.channels not in [1,2,4]:
                debug("track %02d: unknown number of channels, assuming 2" % num)
                actual_track.channels = 2
            toc.append(actual_track)
            break
        line = string.strip(line)

## everytime we encounter "TRACK" we increment num and append the actual
## track to the toc.
        
        if starts_with(line, "TRACK "):
            num = num + 1
            new_track = jack_TOCentry.TOCentry()
            new_track.number = num
            if actual_track:
                if actual_track.channels not in [1,2,4]:
                    debug("track %02d: unknown number of channels, assuming 2" % num)
                    actual_track.channels = 2
                toc.append(actual_track)
            actual_track = new_track
            actual_track.rip = 1
            actual_track.bitrate = cf['_bitrate']
            actual_track.start = toc.end_pos
            if line == "TRACK AUDIO":
                actual_track.type = "audio"
            else:
                actual_track.type = "other" # we don't care
                actual_track.channels = 0
                actual_track.rip = 0
                actual_track.bitrate = 0

## check the various track flags.
## FOUR_CHANNEL_AUDIO is not supported.
## we have to check for this before ripping. later. much later.

        elif line == "NO COPY":
            actual_track.copy = 0
        elif line == "COPY":
            actual_track.copy = 1
        elif line == "NO PRE_EMPHASIS":
            actual_track.preemphasis = 0
        elif line == "PRE_EMPHASIS":
            actual_track.preemphasis = 1
        elif line == "TWO_CHANNEL_AUDIO":
            actual_track.channels = 2
        elif line == "FOUR_CHANNEL_AUDIO":
            actual_track.channels = 4

## example: FILE "data.wav" 08:54:22 04:45:53

        elif starts_with(line, "FILE "):
            filename = line[string.find(line, "\"") + 1:string.rfind(line, "\"")]
            offsets = string.strip(line[string.rfind(line, "\"") + 1:])
            start, length = string.split(offsets)[:2]

## convert time string to blocks(int), update info.

            actual_track.length = jack_CDTime.CDTime(length).blocks
            actual_track.image_name = os.path.join(tocpath, filename)
            actual_track.rip_name = cf['_name'] % num

## example: START 00:01:53. This means the actual track starts 1:53s _after_
## the start given by the FILE statement. This so-called pregap needs to be
## added to the length of the previous track, added to the start of the
## actual track and subtracted from its length. This is done automagically
## by setting the pregap attribute.

        elif starts_with(line, "START "):
            actual_track.pregap = jack_CDTime.CDTime(string.split(line)[1]).blocks

    f.close()
    return toc


def cdrdao_gettoc(tocfile):     # get toc from cdrdao-style toc-file
    "just a wrapper for real_cdrdao_gettoc."
    toc = real_cdrdao_gettoc(tocfile)
    tracks = toc.export()
    track1_pregap = tracks[0][1]
    use_filename = toc.image_file
    # note: toc.image_file is None if different files are specified
    return tracks[1:], use_filename, track1_pregap


##XXX this will be moved to jack_convert
def msftostr(msf):
    "convert msf format to readable string"
    return "%02i" % msf[B_MM]+":"+"%02i" % msf[B_SS]+":"+"%02i" % msf[B_FF]

def cdrdao_puttoc(tocfile, tracks, cd_id):     # put toc to cdrdao toc-file
    "writes toc-file from tracks"
    f = open(tocfile, "w")
    f.write("CD_DA\n\n")
    f.write("// DB-ID=" + cd_id + "\n\n")
    for i in tracks:
        f.write("// Track " + `i[NUM]` + "\n")      # comments are cool
        if i[CH] in (2, 4):
            f.write("TRACK AUDIO\n")
        if i[CH] == 0:
            f.write("TRACK MODE1\n")
        if i[COPY]:
            f.write("COPY\n")
        else:
            f.write("NO COPY\n")
        if i[PRE]:
            f.write("PRE_EMPHASIS\n")
        else:
            f.write("NO PRE_EMPHASIS\n")
        if i[CH] == 2:
            f.write("TWO_CHANNEL_AUDIO\n")
        elif i[CH] == 4:
            f.write("FOUR_CHANNEL_AUDIO\n")
        elif i[CH] == 0:
            f.write("// not supported by jack!\n")
        else:
            error("illegal TOC: channels=%i, aborting." % i[CH])
        f.write('FILE "' + i[NAME] + '.wav" 0 ')
        x = i[LEN]
        if i[NUM] == 1:         # add pregap to track, virtually
            x = x + i[START]
        x = blockstomsf(x)
        f.write("%02i" % x[B_MM] + ":" + "%02i" % x[B_SS] + ":" + "%02i" % x[B_FF] + "\n")
        if i[NUM]==1 and i[START] != 0:
            f.write("START "+msftostr(blockstomsf(i[START]))+"\n")
        f.write("\n")

def tracksize(list, dont_dae = [], blocksize = 1024):
    "Calculates all kind of sizes for a track or a list of tracks."
    if list and type(list[0]) == types.IntType:
        list = ((list, ))
    peak, at, blocks = 0, 0, 0
    encoded_size = wavsize = cdrsize = 0
    for track in list:
        blocks = blocks + track[LEN]
        encoded_size = encoded_size + track[LEN] / CDDA_BLOCKS_PER_SECOND * track[RATE] * 1000 / 8
        # files can be a bit shorter, if someone knows a better way of guessing
        # filesizes, please let me know.
        count_thiswav = 1
        for i in dont_dae:
            if i[NUM] == track[NUM]:
                count_thiwav = 0
        thiscdrsize = track[LEN] * CDDA_BLOCKSIZE * count_thiswav
        wavsize = wavsize + thiscdrsize + 44
        cdrsize = cdrsize + thiscdrsize
        now = encoded_size + thiscdrsize + 44
        if now>peak:
            at = track[NUM]
            peak = now
    return encoded_size, wavsize, encoded_size + wavsize, peak, at, cdrsize, blocks

def progress(track, what="error", data="error", data2 = None):
    "append a line to the progress file"
    global progress_changed
    if type(track) in (types.TupleType, types.ListType):
        if len(track) == 3:
            track, what, data = track
        elif len(track) == 4:
            track, what, data, data2 = track
        else:
            error("illegal progress entry:" + `track` + " (" + `type(track)` + ")")

    if type(track) == types.IntType:
        first = "%02i" % track
    elif type(track) == types.StringType:
        first = track
    else:
        error("illegal progress entry:" + `track` + " (" + `type(track)` + ")")
    progress_changed = 1
    f = codecs.open (cf['_progress_file'], "a", "utf-8")
    f.write(first + cf['_progr_sep'] + what + cf['_progr_sep'] + data)
    if data2:
        f.write(cf['_progr_sep'] + data2)
    f.write("\n")
    f.close()

def check_genre_txt(genre):
    if isinstance(genre, int):
        if genre in range(0,256):
            return genre
        else:
            return None

    elif isinstance(genre, str):
        if string.upper(genre) == "HELP":
            info("available genres: " + string.join([x for x in eyeD3.genres if x != 'Unknown'], ", "))
            sys.exit(0)
        elif string.upper(genre) == "NONE":
            return 255 # set genre to [unknown]
        else:
            try:
                genre = int(genre)
                genre = check_genre_txt(genre)
                if isinstance(genre, int):
                    return genre
            except:
                for i in range(len(id3genres)):
                    if genre.upper() == id3genres[i].upper():
                        return i

    import jack_version
    error("illegal genre. Try '" + jack_version.prog_name + " --id3-genre help' for a list.")
