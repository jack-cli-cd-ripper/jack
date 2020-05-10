# -*- coding: utf-8 -*-
# jack.helpers: helper applications for
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

import string
import re

import jack.plugins

from jack.globals import *

helper_new_status = None
helper_final_status = None
helper_percent = None

helpers = {
    'builtin': {
        'type': "dummy",
        'status_blocksize': 160
    },

    'oggenc': {  # based on a patch kindly provided by Bryan Larsen.
        'type': "encoder",
        'target': "ogg",
        'can_tag': 1,
        'vbr-cmd': "oggenc -o %o -t %t -a %a -N %n -l %l -G %g -d %y -q %q %i",
        'cmd': "oggenc -o %o -t %t -a %a -N %n -l %l -G %g -d %y -b %r %i",
        'tags': {
            'ogg': {
                'track': "-t %s",
                'artist': "-a %s",
                'number': "-N %s",
                'album': "-l %s",
                'genre': "-G %s",
                'date': "-d %s",
            },
        },
        'status_blocksize': 64,
        'bitrate_factor': 1,
        'status_start': "%",
        'percent_fkt': r"""
global helper_percent
s = (i['buf'], '\r').split()
if len(s) >= 2:
    s = s[-2]
if len(s) == 1:
    s = s[0]
y0 = s.find("[")
y1 = s.find("%]")
if y0 != -1 and y1 != -1:
    try:
        helper_percent = float(s[y0 + 1:y1])
    except ValueError:
        helper_percent = 0
else:
    helper_percent = 0
""",
    },
    'lame': {
        'type': "encoder",
        'target': "mp3",
        'inverse-quality': 1,
        'cmd': "lame --preset cbr %r --strictly-enforce-ISO %i %o",
        'vbr-cmd': "lame --preset standard --vbr-new --nohist --strictly-enforce-ISO %i %o",
        'otf-cmd': "lame --preset cbr %r --strictly-enforce-ISO - %o",
        'vbr-otf-cmd': "lame --preset standard --vbr-new --nohist --strictly-enforce-ISO - %o",
        'status_blocksize': 160,
        'bitrate_factor': 1,
        'status_start': "%",
        'percent_fkt': r"""
global helper_percent
s = (i['buf']).split('\r')
if len(s) >= 2: s=s[-2]
if len(s) == 1: s=s[0]
if s.find("%") >= 0:       # status reporting starts here
    y = s.split("/")
    y1 = (y[1]).split("(")[0]
    helper_percent = float(y[0]) / float(y1) * 100.0
elif s.find("Frame:") >= 0:    # older versions, like 3.13
    y = s.split("/")
    y0 = (y[0]).split("[")[-1]
    y1 = (y[1]).split("]")[0]
    helper_percent = float(y0) / float(y1) * 100.0
else:
    helper_percent = 0
""",
    },
    'flac': {
        'type': "encoder",
        'target': "flac",
        'vbr-cmd': "flac -o %o %i",
        'vbr-otf-cmd': "flac --channels 2 --bps 16 --sample-rate 44100 --force-raw-format --endian=big --sign=signed -o %o -",
        'status_blocksize': 160,
        'status_start': "%",
        'percent_fkt': r"""
global helper_percent
s = (i['buf']).split('\r')
if len (s) >= 2: s = s[-2]
if len (s) == 1: s = s[0]
y0 = s.rfind(": ")
y1 = s.find ("%", y0)
if y0 != -1 and y1 != -1:
    try:
        helper_percent = float(s[y0 + 1:y1])
    except ValueError:
        helper_percent = 0
else:
    helper_percent = 0
""",
    },
    'fdkaac': {
        'type': "encoder",
        'target': "m4a",
        'can_tag': 1,
        'cmd': "fdkaac --bitrate-mode 0 --bitrate %r -o %o %i",
        'vbr-cmd': "fdkaac --bitrate-mode %q -o %o %i",
        'status_blocksize': 160,
        'bitrate_factor': 1,
        'percent_fkt': r"""
global helper_percent
helper_percent = 0
""",
    },
    'cdparanoia': {
        'filters': [[r'\n', r'\r'], [r'(\r)+', r'\r'], [r'(Done\.\r)+', r'Done.\r']],
        'type': "ripper",
        'cmd': "cdparanoia --abort-on-skip -d %d %n %o",
        'otf-cmd': "cdparanoia --abort-on-skip -e -d %d %n -R -",
        'status_blocksize': 500,
        'status_start': "%",
        'status_fkt': r"""
global helper_new_status
# (== PROGRESS == [                              | 013124 00 ] == :^D * ==)
# (== PROGRESS == [                       >      .| 011923 00 ] == :-) . ==)
tmp = (i['buf']).split("\r")
if len(tmp) >= 2:
    tmp = tmp[-2] + " "
    helper_new_status = tmp[17:48] + tmp[49:69] # 68->69 because of newer version
else:
    helper_new_status = "Cannot parse status"
""",
        'otf-status_fkt': r"""
global helper_new_status
buf = i['buf']
tmp = buf.split("\n")
helper_new_status = ""
if len(tmp) >= 2:
    tmp = (tmp[-2]).split(" @ ")
    if tmp[0] == "##: -2 [wrote]":
        helper_percent = (float(tmp[1]) - (i['track'][START] * CDDA_BLOCKSIZE / 2.0)) / (i['track'][LEN] * CDDA_BLOCKSIZE / 2.0) * 100.0
        helper_new_status = "[otf - reading, %2i%%]" % helper_percent
""",
        'final_status_fkt': r"""
global helper_final_status
last_status="0123456789012345 [ -- error decoding status --  ]" # fallback
if 0 and cf['_debug']: # disabled for now
    import jack.version
    tmpf=open("%s.debug.%02d.txt" % (jack.version.prog_name, exited_proc['track'][NUM]), "w")
    tmpf.write(exited_proc['buf'])
    del tmpf
tmps = (exited_proc['buf']).split('\r')
tmps.reverse()
for tmp in tmps:
    if tmp.find("PROGRESS") != -1:
        last_status = tmp
        break
helper_final_status = ("%sx" % jack.functions.pprint_speed(speed)) + last_status[16:48] + "]"
""",
        'otf-final_status_fkt': r"""
global helper_final_status
helper_final_status = "[otf - done]"
""",
        # 'toc': 1,  # we can't generate correct freedb IDs with cdparanoia.
        'toc_cmd': "cdparanoia -d %d -Q 2>&1",
        # The output from cdparanoia which we parse looks like this:

        # cdparanoia III release 9.8 (March 23, 2001)
        # (C) 2001 Monty <monty@xiph.org> and Xiphophorus
        # ...
        # track        length               begin        copy pre ch
        # ===========================================================
        #   1.    13584 [03:01.09]        0 [00:00.00]    no   no  2
        #   2.    13769 [03:03.44]    13584 [03:01.09]    no   no  2
        # ...
        # TOTAL  121128 [26:55.03]    (audio only)

        # That is, we look for a line only consisting of === signs as the start,
        # for a line starting with "TOTAL" as the end, and take everything
        # inbetween (to be precise: the first number on each line)
        'toc_fkt': r"""
for l in p.readlines():
    l = l.rstrip()
    if not l:
        continue
    if l.startswith("TOTAL"):
        start = 0
    elif l == ('=' * len(l)):
        start = 1
    elif start:
        l = l.split('.', 1)
        if (l[0]).lstrip().isdigit():
            num = int(l[0])
            l = (l[1]).split()
            erg.append([num, int(l[0]), int(l[2]), l[4] == 'OK', l[5] == 'yes', int(l[6]), 1, cf['_bitrate'], cf['_name'] % num])
        else:
            warning("Cannot parse cdrecord TOC line: " + ". ".join(l))
""",
    },

    'cdda2wav': {
        'type': "ripper",
        'cmd': "cdda2wav --no-infofile -H -v 1 -D %d -O wav -t %n %o",
        'status_blocksize': 200,
        'status_start': "percent_done:",
        'status_fkt': r"""
global helper_new_status
tmp = (i['buf']).split("\r")
if len(tmp) >= 2:
    tmp = tmp[-2].lstrip()
    pct = tmp.find("%")
    if pct == -1:
        helper_new_status = "waiting..."
    else:
        # A normal line when it's ripping looks like this:
        #   7%
        # However, when an error occurs, it'll look something like this:
        #   0%cdda2wav: Operation not permitted. Cannot send SCSI cmd via ioctl
        info = tmp[:pct+1]
        error = info + "cdda2wav:"
        if tmp == info:
            helper_new_status = "ripping: " + info
        elif tmp.startswith(error):
            helper_new_status = "Error: " + tmp[len(error):].lstrip()
        else:
            helper_new_status = "Cannot parse status"
else:
    helper_new_status = "Cannot parse status"
""",
        'final_status_fkt': r"""
global helper_final_status
helper_final_status = ("%s" % jack.functions.pprint_speed(speed)) + "x [ DAE done with cdda2wav       ]"
""",
        'toc': 1,
        'toc_cmd': "cdda2wav --no-infofile -D %d -J -v toc --gui 2>&1",
        'toc_fkt': r"""
while 1:
    l = p.readline()
    if not l:
        break
    if l[0] == "T" and l[1] in string.digits and l[2] in string.digits and l[3] == ":":
        num, start, length, type, pre, copy, ch, dummy = l.split()[:8]
        if type == "audio":
            num = int(num[1:3])
            start = int(start)
            length = length.replace(".", ":")
            length = timestrtoblocks(length)
            pre = pre == "pre-emphasized"
            copy = copy != "copydenied"
            ch = [ "none", "mono", "stereo", "three", "quad" ].index(ch)
            erg.append([num, length, start, copy, pre, ch, 1, cf['_bitrate'], cf['_name'] % (num + 1)])
""",
        'toc_fkt_old': r"""
new_c2w = 0
new_toc1 = 0
new_toc2 = 0
new_lengths = []
new_starts = []
while 1:
    l = p.readline()
    if not l:
        break
    l = l.strip()
    # new cdda2wav
    if starts_with(l, "Table of Contents: total tracks"):
        new_toc1 = 1
        continue

    if starts_with(l, "Table of Contents: starting sectors"):
        new_toc2 = 1
        new_toc1 = 0
        new_c2w = 1
        continue

    if new_toc2 and l and l[0] in string.digits:
        l = l.split("(")[1:]
        for i in l:
            x = i.split(")")[0]
            x = x.strip()
            try:
                new_starts.append(int(x))
            except:
                pass
        continue

    if new_toc1 and l and l[0] in string.digits:
        l = l.split("(")[1:]
        for i in l:
            if i.find(":") >= 0:
                x = i.split(")")[0]
                x = replace(x, ".", ":")
                new_lengths.append(timestrtoblocks(x))
        continue

    # old cdda2wav
    if l and l[0:11] == "Album title":
        start = 1
    elif l and start:
        l = l.split()
        if l[0] == "Leadout:":
            start = 0
        else:
            num = int(l[0][1:3])
            if l[6] == "stereo":
                channels = 2
            elif l[6] == "mono":
                channels = 1
            else:
                channels = 0
            t_start = int(l[1])
            msf = (l[2]).split(":")
            sf = (msf[1]).split(".")
            t_length = int(sf[1]) + int(sf[0]) * 75 + int(msf[0]) * 60 * 75
            erg.append([num, t_length, t_start, l[5] == "copyallowed", l[4] != "linear", channels, 1, cf['_bitrate'], cf['_name'] % num])
if new_c2w and len(new_lengths) == len(new_starts) - 1:
    for i in range(min(len(new_lengths), len(new_starts))): # this provokes an error if the lists are of different length
        erg.append([i + 1, new_lengths[i], new_starts[i], 0, 0, 2, 1, cf['_bitrate'], cf['_name'] % (i + 1)])
""",
    },

    'dagrab': {
        'type': "ripper",
        'cmd': "dagrab -d %d -f %o %n",
        'status_blocksize': 100,
        'status_start': "total:",
        'status_fkt': r"""
global helper_new_status
tmp = (i['buf']).split("\r")
if len(tmp) >= 2:
    if (tmp[-2]).find('total:') != -1:
        helper_new_status = (tmp[-2]).strip()
    else:
        helper_new_status = "waiting..."
else:
    helper_new_status = "Cannot parse status"
""",
        'final_status_fkt': r"""
global helper_final_status
helper_final_status = ("%s" % jack.functions.pprint_speed(speed)) + "x [ DAE done with dagrab         ]"
""",
        'toc': 1,
        'toc_cmd': "dagrab -d %d -i 2>&1",
        'toc_fkt': r"""
while l:
    l = l.strip()
    if l and l[0:5] == "track":
        start = 1
    elif l and start:
        l = l.split()
        if l[3] == "leadout":
            start = 0
        else:
            num = int(l[0])
            channels = 2
            copy = 0
            pre = 0
            t_start = int(l[1]) - 150
            t_length = int(l[2])
            erg.append([num, t_length, t_start, copy, pre, channels, 1, cf['_bitrate'], cf['_name'] % num])
    l = p.readline()
""",
    },

    'tosha': {
        'type': "ripper",
        'cmd': "tosha -d %d -f wav -t %n -o %o",
        'status_blocksize': 100,
        'status_start': "total:",
        'status_fkt': r"""
global helper_new_status
x = (i['buf']).split('\r')[-2]
if x.find('total:') != -1:
    helper_new_status = ((i['buf']).split('\r')[-2]).strip()
else:
    helper_new_status = "waiting..."
""",
        'final_status_fkt': r"""
global helper_final_status
helper_final_status = ("%s" % jack.functions.pprint_speed(speed)) + "x [ DAE done with tosha          ]"
""",
        'toc': 1,
        'toc_cmd': "tosha -d %d -iq 2>&1",
        'toc_fkt': r"""
while l:
    l = l.rstrip()
    if l:
        l = l.split()
        num = int(l[0])
        erg.append([num, 1 + int(l[3]) - int(l[2]), int(l[2]), 0, 0, 2, 1, cf['_bitrate'], cf['_name'] % num])
    l = p.readline()
""",
    },
    'libdiscid': {
        'type': "toc-reader",
        'toc': 1,
        'toc_fkt': r"""
import libdiscid
if not os.path.exists(cf['_cd_device']):
    error("Device %s does not exist!" % cf['_cd_device'])
if not os.access(cf['_cd_device'], os.R_OK):
    error("You don't have permission to access device %s!" % cf['_cd_device'])
if not stat.S_ISBLK(os.stat(cf['_cd_device'])[stat.ST_MODE]):
    error("Device %s is not a block device!" % cf['_cd_device'])
try:
    disc = libdiscid.read(device=cf['_cd_device'], features=0)
except libdiscid.exceptions.DiscError as m:
    error("Access of CD device %s resulted in error: %s" % (cf['_cd_device'], m))

toc = list(disc.track_offsets)
toc.append(disc.leadout_track)
first = disc.first_track
last = disc.last_track
for i in range(first, last + 1):
    erg.append([i, toc[i - first + 1] - toc[i - first], toc[i - first] - MSF_OFFSET, 0, 0, 2, 1, cf['_bitrate'], cf['_name'] % i])
""",
    }
}

helpers['lame-user'] = helpers['lame'].copy()
helpers[
    'lame-user'].update({'cmd': "lame --preset cbr %r --strictly-enforce-ISO %i %o",
                         'vbr-cmd': "lame -V %q --vbr-new --nohist --strictly-enforce-ISO %i %o",
                         'otf-cmd': "lame --preset cbr %r --strictly-enforce-ISO - %o",
                         'vbr-otf-cmd': "lame -V %q --vbr-new --nohist --strictly-enforce-ISO - %o", })


def init():
    # import plugin
    jack.plugins.import_helpers()

    # compile exec strings
    for h in list(helpers.keys()):
        for i in list(helpers[h].keys()):
            if i[-4:] == "_fkt":
                helpers[h][i] = compile(helpers[h][i], '<string>', 'exec')

    # compile filters
    for h in list(helpers.keys()):
        if 'filters' in helpers[h]:
            newf = []
            for i in helpers[h]['filters']:
                newf.append([re.compile(i[0]), i[1]])
            helpers[h]['filters'] = newf
