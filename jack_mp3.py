# jack_mp3 - mp3 layer stuff for
# jack - extract audio from a CD and MP3ify it using 3rd party software
# Copyright (C) 1999-2001  Arne Zellentin <zarne@users.sf.net>
# Transformed from mp3info (c) Thorvald Natvig

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

DEBUG = 0

import string
import types
from os import stat
from stat import ST_SIZE
from StringIO import StringIO

global warnings
global F, f, xing, id3v2, start_offset

# constants
mode_names = ["stereo", "j-stereo", "dual-ch", "single-ch", "multi-ch"]
layer_names = ["I", "II", "III"]
version_names = ["MPEG-1", "MPEG-2 LSF", "MPEG-2.5"]
version_nums = ["1", "2", "2.5"]
bitrates = \
    [[[0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
        [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
        [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]],
     [[0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]],
     [[0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
        [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]]]
s_freq = \
    [[44100, 48000, 32000, 0],
     [22050, 24000, 16000, 0],
     [11025, 8000, 8000, 0]]

bpf_fact = [0, 12000, 144000, 144000]

# Xing stuff
FRAMES_FLAG = 0x0001
BYTES_FLAG = 0x0002
TOC_FLAG = 0x0004
VBR_SCALE_FLAG = 0x0008


def get_l4(s):
    return reduce(lambda a, b: ((a << 8) + b), map(long, map(ord, s)))


def decode_xing():
    global F, f, xing
    # defaults:
    frames = bytes = scale = toc = None
    where = f.tell()
    try:
        if 1:
            if DEBUG:
                print "Xing at", where
            # 32-bit fields; "Xing", flags, frames, bytes, 100 toc
            flags = get_l4(f.read(4))
            if flags & FRAMES_FLAG:
                frames = get_l4(f.read(4))
            if flags & BYTES_FLAG:
                bytes = get_l4(f.read(4))
            if flags & TOC_FLAG:
                toc = map(lambda x: ord(x), f.read(100))
                for j in range(len(toc)):
                    toc[j] = int(toc[j] / 256.0 * bytes)
            if flags & VBR_SCALE_FLAG:
                scale = get_l4(f.read(4))

            if DEBUG > 2:
                print "Xing: frames=%i" % frames
                print "Xing: bytes=%i" % bytes
                print "Xing: toc=", toc
                print "Xing: scale=%i" % scale

            xing = {}
            if frames:
                xing['x_frames'] = frames
            if bytes:
                xing['x_bytes'] = bytes
            if toc:
                xing['x_toc'] = toc
            if scale:
                xing['x_scale'] = scale
            xing['x_header_at'] = where - 4

        else:
            return None

    except:
        if DEBUG:
            import traceback
            traceback.print_exc()
        f.seek(where + 1)
        return None


def find_xing(framelen):
    "read (and skip) the Xing header if present"
    where = f.tell()
    x = f.read(framelen)
    pos = string.find(x, "Xing")
    if pos >= 0:
        f.seek(where + pos + 4)
        decode_xing()
        f.seek(where + framelen)
    else:
        f.seek(where)


def reread_f(size):
    global F, f
    pos = f.tell()
    f.seek(F.offset)
    if DEBUG:
        print "reread_f: now at", f.tell()
    F_offset = F.offset
    F_file = F.file
    F = StringIO(f.read(F.len + size + 10))
    F.file = F_file
    F.offset = F_offset
    f.seek(pos)


def handle_id3v2(version, flags, data):
    global id3v2
    if DEBUG:
        print "ID3:", `version`, `flags`, len(data)
    id3v2 = {}
    id3v2['version'] = tuple(version)


def read_id3v2():
    #$49 44 33 yy yy xx zz zz zz zz ; yy < $FF; zz < $80
    # I  D  3  yy yy xx zz zz zz zz
    # 0  1  2  3  4  5  6  7  8  9
    global F, f
    where = f.tell()
    header = f.read(10)
    if header[:3] != "ID3":
        if DEBUG:
            print "no header?", where, `header`
        f.seek(where)
        return None

    header = list(header)
    for i in range(3, 10):
        header[i] = ord(header[i])

    if not (header[3] < 0xff) or not (header[4] < 0xff):
        f.seek(where)
        return None
    if not (header[6] < 0x80) or not (header[7] < 0x80):
        f.seek(where)
        return None
    if not (header[8] < 0x80) or not (header[9] < 0x80):
        f.seek(where)
        return None

    size = header[6:]
    size = list(size)
    value = 0
    for i in size:
        value = value << 7
        value = value | i
    size = value

    reread_f(size)

    flags = header[5]
    version = header[3:5]
    return handle_id3v2(version, flags, f.read(size))


def decode_header(buffer):
    "get mp3 info. Transformed from mp3info (c) Thorvald Natvig"

    try:
        switch = (ord(buffer[1]) >> 3 & 0x3)
        if switch == 3:
            version = 0
        elif switch == 2:
            version = 1
        elif switch == 0:
            version = 2
        else:
            return None

        bitrate_index = (ord(buffer[2]) >> 4) & 0x0F
        sampling_frequency = (ord(buffer[2]) >> 2) & 0x3
        mode = (ord(buffer[3]) >> 6) & 0x3

        x = {}
        x['error_protection'] = not (ord(buffer[1]) & 0x1)
        x['padding'] = (ord(buffer[2]) >> 1) & 0x01
        x['extension'] = ord(buffer[2]) & 0x01
        x['mode_ext'] = (ord(buffer[3]) >> 4) & 0x03
        x['copyright'] = (ord(buffer[3]) >> 3) & 0x01
        x['original'] = (ord(buffer[3]) >> 2) & 0x1
        x['emphasis'] = (ord(buffer[3])) & 0x3
        x['mode_name'] = mode_names[mode]
        x['lay'] = 4 - ((ord(buffer[1]) >> 1) & 0x3)
        x['layer_name'] = layer_names[x['lay'] - 1]
        x['version_name'] = version_names[version]
        x['version_num'] = version_nums[version]
        x['bitrate'] = bitrates[version][x['lay'] - 1][bitrate_index]
        if not x['bitrate']:
            raise IllegalError_may_be_free_format
        x['sfreq'] = s_freq[version][sampling_frequency]
        if not x['sfreq']:
            raise IllegalError_illegal_sfreq

    except:
        if DEBUG:
            import traceback
            traceback.print_exc()
            print "Illegal header, so far:", x
        x = None

    return x


def extend_frameinfo(x):
    if x['version_num'] == "1":
        x['samples_per_frame'] = 1152
    elif x['version_num'] == "2":
        x['samples_per_frame'] = 576
    else:
        print "What is the spf for %s?" % x['version_name'], "(%s)" % x['version_num']

    # calculate BPF
    x['bpf'] = (x['bitrate'] * bpf_fact[x['lay']]) / x['sfreq']
    x['framesize'] = (x['bitrate'] * bpf_fact[x['lay']]) / x[
        'sfreq'] + x['padding']
    # stereo = (mode == MPG_MD_MONO) ? 1 : 2;
    return x


def syncronize(what=1):
    global F, f
    index = f.tell()
    x = {}
    # search intelligently (i.e. fast) for any header
    fields = ["\377", "I", "X", "R"][:what]
    if not warnings:
        fields.remove("R")
    # while index < len(f.buf) - 4:
    while index < F.len - 4 + start_offset:
        # print index
        if F.buf[index - start_offset] in fields:
            if F.buf[index - start_offset + 1] >= "\340":
                # a valid header must start with 11 set bits
                f.seek(index)
                x = decode_header(f.read(4))
                if x:
                    where = f.tell() - 4
                    x['header_at'] = where
                    x = extend_frameinfo(x)
                    next_header = where + x['framesize']
                    if DEBUG:
                        print "MPEG header found at %i, expect next header at %i." % (x['header_at'], next_header)
                    f.seek(next_header)
                    buf = f.read(4)
                    y = None
                    if buf[:2] >= "\377\340":
                        y = decode_header(buf)
                    if y:
                        # two headers, that's certain enough.
                        f.seek(x['header_at'])
                        break
                    else:
                        if DEBUG:
                            print "but no valid header follows at %i." % next_header
                        f.seek(where)
                        index = where
                        x = None
            elif F.buf[index - start_offset:index - start_offset + 3] == "ID3":
                if not id3v2:
                    f.seek(index)
                    read_id3v2()
                    if id3v2:
                        if DEBUG:
                            print "ID3v2 found, now at %i" % f.tell(), id3v2
                        index = f.tell()
                        fields.remove("I")
                        continue
                    else:
                        f.seek(index)
            elif F.buf[index - start_offset:index - start_offset + 4] == "Xing":
                f.seek(index + 4)
                decode_xing()
                if xing:
                    if DEBUG:
                        print "Xing header found without frame sync."
                    index = f.tell()
                    fields.remove("X")
                    continue
                else:
                    f.seek(index + 4)

            elif F.buf[index - start_offset:index - start_offset + 4] == "RIFF":
                if warnings:
                    print "skipping RIFF header at %i..." % F.tell()
                fields.remove("R")
        index = index + 1
    return x


def mp3format(file, warn=1, max_skip=100000, offset=0):
    global F, f, xing, id3v2, warnings, start_offset

    warnings = warn
    start_offset = offset

    f = xing = id3v2 = None
    if DEBUG:
        print "examining", file, "warnings=%i" % warnings, "offset=%i" % start_offset, "max_skip=%i" % max_skip

    # XXX we're using StringIO because it's faster - transitionally.
    if type(file) == types.StringType:
        f = open(file, "r")
    elif hasattr(file, 'seek'):
        f = file
    else:
        print "unknown object:", file
        return None
    f.seek(start_offset)
    search_in = f.read(max_skip)
    F = StringIO(search_in)
    F.file = file
    f.seek(start_offset)
    F.offset = start_offset

    x = syncronize(what=4)

    if not x:
        if warnings:
            print "Warning: no MP3 header found in the first", F.tell(), "bytes of file\n       : \"" + file + "\"."
        return {}

    # we're quite sure we have a valid header now
    if warnings > 1:
        print "Warning: MP3 header found at offset", f.tell() - 4

    # fill in convenience stuff
    x = extend_frameinfo(x)

    # the xing header is normally embedded in the first valid frame
    # but sometimes it appears earlier, I don't know why. Use the 1st.
    if not xing:
        find_xing(x['framesize'])

    if xing:
        x.update(xing)
        if x.has_key('x_frames'):
            x['length_in_samples'] = x['x_frames'] * x['samples_per_frame']
            x['length'] = float(x['length_in_samples']) / x['sfreq']
            # should use the real file size instead of x_bytes.
            if x.has_key("x_bytes"):
                x['bitrate'] = int(
                    (x['x_bytes'] * 8.0 / x['length']) / 100 + 0.5)
                x['bitrate'] = x['bitrate'] / 10.0
        else:
            print "strange xing=" + `xing`
    else:
        x['length'] = stat(file)[ST_SIZE] * 8.0 / (x['bitrate'] * 1000)
    if id3v2:
        x['id3v2'] = id3v2

    if DEBUG > 1:
        print x
    return x


class MP3:

    def __init__(self, file, name=None):

        self.file = None
        self.name = name
        if type(file) == types.StringType:
            self.file = open(file, "rb")
            self.name = file
        elif hasattr(file, 'seek'):
            self.file = file
        else:
            print "unknown object:", file
            return None
