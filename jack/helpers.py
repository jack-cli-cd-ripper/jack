"""jack.helpers: helper applications"""

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

import re

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
        'cmd': "oggenc -o %o -b %r %i",
        'otf-cmd': "oggenc -o %o -b %r -",
        'vbr-cmd': "oggenc -o %o -q %q %i",
        'vbr-otf-cmd': "oggenc -o %o -q %q -",
        'status_blocksize': 64,
        'bitrate_factor': 1,
        'status_start': "%",
        'percent_fkt': r"""
s = str(i['buf']).split('\r')
if len(s) >= 2:
    s = s[-2]
if len(s) == 1:
    s = s[0]
y0 = s.find("[")
y1 = s.find("%]")
if y0 != -1 and y1 != -1:
    helper_percent = float(s[y0 + 1:y1].replace(",", "."))
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
#"   1500/9274   (16%)|    0:00/    0:04|    0:00/    0:04|   55.176x|    0:03 "
helper_percent = 20
s = str(i['buf']).replace('\n', '\r').split('\r')
if len(s) >= 2:
    s = s[-2]
if len(s) == 1:
    s = s[0]
if 'ETA' not in s:
    if "%" in s:
        # status reporting starts here
        y = s.split("/")
        y1 = (y[1]).split("(")[0]
        helper_percent = float(y[0]) / float(y1) * 100.0
    elif "Frame:" in s:
        # older versions, like 3.13, untested
        y = s.split("/")
        y0 = (y[0]).split("[")[-1]
        y1 = (y[1]).split("]")[0]
        helper_percent = float(y0) / float(y1) * 100.0
""",
    },
    'flac': {
        'type': "encoder",
        'target': "flac",
        'vbr-cmd': "flac -o %o %i",
        'vbr-otf-cmd': "flac --channels 2 --bps 16 --sample-rate 44100 --force-raw-format --endian=big --sign=signed -o %o -",
        'decode-otf-cmd': "flac --decode --stdout %i",
        'status_blocksize': 160,
        'status_start': "%",
        'percent_fkt': r"""
s = str(i['buf']).split('\r')
if len (s) >= 2:
    s = s[-2]
if len (s) == 1:
    s = s[0]
y0 = s.rfind(": ")
y1 = s.find ("%", y0)
if y0 != -1 and y1 != -1:
    helper_percent = float(s[y0 + 1:y1])
""",
    },
    'fdkaac': {
        'type': "encoder",
        'target': "m4a",
        'cmd': "fdkaac --moov-before-mdat --bitrate-mode 0 --bitrate %r -o %o %i",
        'vbr-cmd': "fdkaac --moov-before-mdat --bitrate-mode 5 -o %o %i",
        'otf-cmd': "fdkaac --moov-before-mdat --bitrate-mode 0 --bitrate %r -o %o -",
        'vbr-otf-cmd': "fdkaac --moov-before-mdat --bitrate-mode 5 -o %o -",
        'status_blocksize': 160,
        'bitrate_factor': 1,
        'percent_fkt': r"""
s = str(i['buf']).split('\r')
if len (s) >= 2:
    s = s[-2]
if len (s) == 1:
    s = s[0]
y1 = s.find("%]")
y0 = s.find("[", 0, y1)
if y0 != -1 and y1 != -1:
    helper_percent = float(s[y0 + 1:y1])
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
    tmpf=open("%s.debug.%02d.txt" % (jack.version.name, exited_proc['track'][NUM]), "w")
    tmpf.write(exited_proc['buf'])
    del tmpf
tmps = (exited_proc['buf']).split('\r')
tmps.reverse()
for tmp in tmps:
    if "PROGRESS" in tmp:
        last_status = tmp
        break
helper_final_status = ("%sx" % jack.functions.pprint_speed(speed)) + last_status[16:48] + "]"
""",
        'otf-final_status_fkt': r"""
global helper_final_status
helper_final_status = "[otf - done]"
""",
        # 'toc': 1,  # we can't generate correct metadata IDs with cdparanoia.
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
            erg.append([num, int(l[0]), int(l[2]), l[4] == 'OK', l[5] == 'yes', int(l[6]), 1, cf['_bitrate'], cf['_name'] % num, None, None])
        else:
            warning("Cannot parse cdrecord TOC line: " + ". ".join(l))
""",
    },

    'libdiscid': {
        'type': "toc-reader",
        'toc': 1,
        'toc_fkt': r"""
import jack.discid
import stat
jack.discid.init()

if not os.path.exists(cf['_cd_device']):
    error("Device %s does not exist!" % cf['_cd_device'])
if not os.access(cf['_cd_device'], os.R_OK):
    error("You don't have permission to access device %s!" % cf['_cd_device'])
if not stat.S_ISBLK(os.stat(cf['_cd_device'])[stat.ST_MODE]):
    error("Device %s is not a block device!" % cf['_cd_device'])
try:
    disc = jack.discid.read(device=cf['_cd_device'])
except jack.discid.DiscError as m:
    error("Access of CD device %s resulted in error: %s" % (cf['_cd_device'], m))

toc = jack.discid.toc(disc)
first = jack.discid.first(disc)
last = jack.discid.last(disc)

try:
    mcn = jack.discid.mcn(disc)
except NotImplementedError:
    mcn = None

try:
    isrcs = jack.discid.isrcs(disc)
except NotImplementedError:
    isrcs = None

for i in range(first, last + 1):
    isrc = None
    if isrcs and isrcs[i - first]:
        isrc = isrcs[i - first]
    erg.append([i, toc[i - first + 1] - toc[i - first], toc[i - first] - MSF_OFFSET, 0, 0, 2, 1, cf['_bitrate'], cf['_name'] % i, mcn, isrc])
""",
    }
}

helpers['lame-user'] = helpers['lame'].copy()
helpers['lame-user'].update({'cmd': "lame --preset cbr %r --strictly-enforce-ISO %i %o",
                         'vbr-cmd': "lame -V %q --vbr-new --nohist --strictly-enforce-ISO %i %o",
                         'otf-cmd': "lame --preset cbr %r --strictly-enforce-ISO - %o",
                         'vbr-otf-cmd': "lame -V %q --vbr-new --nohist --strictly-enforce-ISO - %o", })


def init():

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
