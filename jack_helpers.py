# -*- coding: iso-8859-15 -*-
### jack_helpers: helper applications for
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

import string

helpers = {
    'builtin': {
        'type': "dummy",
        'status_blocksize': 160
        },

    'oggenc': { # based on a patch kindly provided by Bryan Larsen.
        'type': "encoder",
        'target': "ogg",
        'can_tag': 1,
        #'vbr-cmd': "oggenc -o %o -t %t -a %a -N %n -l %l -G %g -d %y -b %r %i",
        'vbr-cmd': "oggenc -o %o -t %t -a %a -N %n -l %l -G %g -d %y -q %q %i",
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
s = string.split(i['buf'], '\r')
if len(s) >= 2:
    s = s[-2]
if len(s) == 1:
    s = s[0]
y0 = string.find(s, "[")
y1 = string.find(s, "%]")
if y0 != -1 and y1 != -1:
    percent = float(s[y0 + 1:y1])
else:
    percent = 0
""",
    },

    'mp3enc': {
        'type': "encoder",
        'target': "mp3",
        'cmd': "mp3enc -v -qual 9 -br %r -if %i -of %o",
        'otf-cmd': "mp3enc -v -qual 9 -br %r -sti -be -of %o",
        'status_blocksize': 99,
        'bitrate_factor': 1000,
        'status_start': "%",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 4:
    s = s[-2]
    if string.find(s, "%") >= 0:
        y = string.split(s, " ", 3)
        percent = float(y[0]) / (i['track'][LEN] * CDDA_BLOCKSIZE / 2) * 100.0
    else:
        percent = 0
""",
    },

    'l3enc': {
        'type': "encoder",
        'target': "mp3",
        'cmd': "l3enc -hq -br %r %i %o",
        'status_blocksize': 99,
        'bitrate_factor': 1000,
        'status_start': "%",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 2: s = s[-2]
if len(s) == 1: s = s[0]
if string.find(s, "%") >= 0:
    y = string.split(s, " / ")
    y0 = string.split(y[0])[-1]
    y1 = string.split(y[1])[0]
    percent=float(y0) / float(y1) * 100.0
else:
    percent = 0
""",
    },

    'lame': {
        'type': "encoder",
        'target': "mp3",
        'inverse-quality': 1,
        'cmd': "lame --alt-preset cbr %r --strictly-enforce-ISO %i %o",
        'vbr-cmd': "lame --alt-preset standard --nohist --strictly-enforce-ISO %i %o",
        'otf-cmd': "lame --alt-preset cbr %r --strictly-enforce-ISO - %o",
        'vbr-otf-cmd': "lame --alt-preset standard --nohist --strictly-enforce-ISO - %o",
        'status_blocksize': 160,
        'bitrate_factor': 1,
        'status_start': "%",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 2: s=s[-2]
if len(s) == 1: s=s[0]
if string.find(s, "%") >= 0:       # status reporting starts here
    y = string.split(s, "/")
    y1 = string.split(y[1], "(")[0]
    percent = float(y[0]) / float(y1) * 100.0
elif string.find(s, "Frame:") >= 0:    # older versions, like 3.13
    y = string.split(s, "/")
    y0 = string.split(y[0], "[")[-1]
    y1 = string.split(y[1], "]")[0]
    percent = float(y0) / float(y1) * 100.0
else:
    percent = 0
""",
    },

    'gogo': { # Thanks to José Antonio Pérez Sánchez for the vbr and otf presets
        'type': "encoder",
        'target': "mp3",
        'inverse-quality': 1,
        'cmd': "gogo %i %o -b %r",
        'vbr-cmd': "gogo %i %o -v %q",
        'otf-cmd': "gogo stdin %o -b %r",
        'vbr-otf-cmd': "gogo stdin %o -v 4",
        'status_blocksize': 160,
        'bitrate_factor': 1,
        'status_start': "%",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 2: s=s[-2]
if len(s) == 1: s=s[0]
if string.find(s, "%") >= 0: # status reporting starts here
    s = replace(s, "\000", " ")
    y = string.split(s, "/")
    y0 = string.split(y[0], "{")[-1]
    y1 = string.split(y[1], "}")[0]
    percent = float(y0) / float(y1) * 100.0
else:
    percent = 0
""",
    },

    'bladeenc': {
        'type': "encoder",
        'target': "mp3",
        'cmd': "bladeenc %i %o -br %r",
        'status_blocksize': 180,
        'bitrate_factor': 1000,
        'status_start': "%",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 2: s=s[-2]
if string.find(s, "Status:") != -1:
    y = string.split(s[8:])
    percent = float(string.split(y[0], '%')[0])
else:
    percent = 0
""",
    },

# xing  definitions kindly provided by Sebastian Weber
    'xing': {
        'type': "encoder",
        'target': "mp3",
        'cmd': "xingmp3enc -B %r %i %o",
        'vbr-cmd': "xingmp3enc -V 100 %i %o",
        'otf-cmd': "xingmp3enc -b %r -- %o",
        'vbr-otf-cmd': "xingmp3enc -V 100 -- %o",
        'status_blocksize': 160,
        'bitrate_factor': 1,
        'status_start': "%",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 2: s = s[-2]
if string.find(s, "ETA:") != -1:
    y = string.strip(string.split(s, '%')[0])
    if len(y) == 0:
        percent = 0
    else:
        percent = float(y)
else:
    percent = 0
""",
    },

    'flac': {
        'type': "encoder",
        'target': "flac",
        'vbr-cmd': "flac -o %o %i",     
        'vbr-otf-cmd': "flac -fr -fb -fc 2 -fp 16 -fs 44100 -o %o", 
        'status_blocksize': 160,
        'status_start': "%", 
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')    
if len (s) >= 2: s = s[-2]
if len (s) == 1: s = s[0]       
y0 = string.find(s, ": ")             
y1 = string.find (s, "%")
if y0 != -1 and y1 != -1: 
    percent = float(s[y0 + 1:y1])
else:                   
    percent = 0         
""",
    },

    'mppenc': {
        'type': "encoder",
        'target': "mpc",
        'can_tag': 0,
        'vbr-cmd': "mppenc --standard %i %o",
        #'vbr-otf-cmd': "mppenc --standard - %o", # doesn't work, needs WAVE
        'status_blocksize': 160,
        'status_start': "-.-",
        'percent_fkt': r"""
s = string.split(i['buf'], '\r')
if len(s) >= 3:
    s = s[-3]
    s = string.split(string.strip(s))
    if len(s) >= 3 and s[2] == "kbps" and s[0] != "-.-":
        percent = float(s[0])
    else:
        percent = 0
""",
    },

    'cdparanoia': {
        'type': "ripper",
        'cmd': "cdparanoia --abort-on-skip -d %d %n %o",
        'otf-cmd': "cdparanoia --abort-on-skip -e -d %d %n -R -",
        'status_blocksize': 600,
        'status_start': "%",
        'status_fkt': r"""
#  (== PROGRESS == [                       >      .| 011923 00 ] == :-) . ==)
tmp = string.split(i['buf'], '\r')[-2]
new_status = tmp[17:48] + tmp[49:69] # 68->69 because of newer version
#new_status = string.split(i['buf'], '\r')[-2][17:69] # 68->69 because of newer version
""",
        'otf-status_fkt': r"""
buf = i['buf']
tmp = string.split(buf, "\n")
new_status = ""
if len(tmp) >= 2:
    tmp = string.split(tmp[-2], " @ ")
    if tmp[0] == "##: -2 [wrote]":
        percent = (float(tmp[1]) - (i['track'][START] * CDDA_BLOCKSIZE / 2.0)) / (i['track'][LEN] * CDDA_BLOCKSIZE / 2.0) * 100.0
        new_status = "[otf - reading, %2i%%]" % percent
""",
        'final_status_fkt': r"""
last_status="0123456789012345 [ -- error decoding status --  ]" # fallback
for tmp in string.split(exited_proc['buf'], '\r'):
    if string.find(tmp, "PROGRESS") != -1:
        last_status = tmp
final_status = ("%4.1fx" % speed) + last_status[16:48] + "]"
""",
        'otf-final_status_fkt': r"""
final_status = "[otf - done]"
""",
        #'toc': 1,  # we can't generate correct freedb IDs with cdparanoia.
        'toc_cmd': "cdparanoia -d %d -Q 2>&1",
        'toc_fkt': r"""
while l:
    l = string.rstrip(l)
    if l and l[0:5] == "TOTAL":
        start = 0
    if l and l == '=' * (len(l)):
        start = 1
    elif l and start:
        l = string.split(l, '.', 1)
        num = int(l[0])
        l = string.split(l[1])
        erg.append([num, int(l[0]), int(l[2]), l[4] == 'OK', l[5] == 'yes', int(l[6]), 1, cf['_bitrate'], cf['_name'] % num])
    l = p.readline()
""",
    },

    'cdda2wav': {
        'type': "ripper",
        'cmd': "cdda2wav --no-infofile -H -v 1 -D %D -O wav -t %n %o",
        'status_blocksize': 200,
        'status_start': "percent_done:",
        'status_fkt': r"""
x = string.split(i['buf'], '\r')[-2]
if string.find(x, '%') != -1:
    new_status = "ripping: " + string.strip(string.split(i['buf'], '\r')[-2])
else:
    new_status = "waiting..."
""",
        'final_status_fkt': r"""
final_status = ("%4.1f" % speed) + "x [ DAE done with cdda2wav       ]"
""",
        'toc': 1,
        'toc_cmd': "cdda2wav --no-infofile -D %D -J -v 35 --gui 2>&1",
        'toc_fkt': r"""
while 1:
    l = p.readline()
    if not l:
        break
    if l[0] == "T" and l[1] in string.digits and l[2] in string.digits and l[3] == ":":
        num, start, length, type, pre, copy, ch = string.split(l)[:7]
        if type == "audio":
            num = int(num[1:3])
            start = int(start)
            length = string.replace(length,".", ":")
            length = timestrtoblocks(length)
            pre = pre == "pre-emphasized"
            copy = copy != "copydenied"
            ch = [ "none", "mono", "stereo", "three", "quad" ].index(ch)
            erg.append([num, length, start, copy, pre, ch, 1, cf['_bitrate'], cf['_name'] % (num + 1)])
""",
        'toc_cmd_old': "cdda2wav --no-infofile -D %D -J -v 35 2>&1",
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
    l = string.strip(l)
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
        l = string.split(l, "(")[1:]
        for i in l:
            x = string.split(i, ")")[0]
            x = string.strip(x)
            try:
                new_starts.append(int(x))
            except:
                pass
        continue

    if new_toc1 and l and l[0] in string.digits:
        l = string.split(l, "(")[1:]
        for i in l:
            if string.find(i, ":") >= 0:
                x = string.split(i, ")")[0]
                x = replace(x, ".", ":")
                new_lengths.append(timestrtoblocks(x))
        continue

    # old cdda2wav
    if l and l[0:11] == "Album title":
        start = 1
    elif l and start:
        l = string.split(l)
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
            msf = string.split(l[2], ":")
            sf = string.split(msf[1], ".")
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
x = string.split(i['buf'], '\r')[-2]
if string.find(x, 'total:') != -1:
    new_status = string.strip(string.split(i['buf'], '\r')[-2])
else:
    new_status = "waiting..."
""",
        'final_status_fkt': r"""
final_status = ("%4.1f" % speed) + "x [ DAE done with dagrab         ]"
""",
        'toc': 1,
        'toc_cmd': "dagrab -d %d -i 2>&1",
        'toc_fkt': r"""
while l:
    l = string.strip(l)
    if l and l[0:5] == "track":
        start = 1
    elif l and start:
        l = string.split(l)
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
x = string.split(i['buf'], '\r')[-2]
if string.find(x, 'total:') != -1:
    new_status = string.strip(string.split(i['buf'], '\r')[-2])
else:
    new_status = "waiting..."
""",
        'final_status_fkt': r"""
final_status = ("%4.1" % speed) + "x [ DAE done with tosha          ]"
""",
        'toc': 1,
        'toc_cmd': "tosha -d %d -iq 2>&1",
        'toc_fkt': r"""
while l:
    l = string.rstrip(l)
    if l:
        l = string.split(l)
        num = int(l[0])
        erg.append([num, 1 + int(l[3]) - int(l[2]), int(l[2]), 0, 0, 2, 1, cf['_bitrate'], cf['_name'] % num])
    l = p.readline()
""",
    },

    'CDDB.py': {
        'type': "toc-reader",
        'toc': 1,
        'toc_fkt': r"""
import cdrom
device = cdrom.open(cf['_cd_device'])
(first, last) = cdrom.toc_header(device)
toc = []
for i in range(first, last + 1):
    (min, sec, frame) = cdrom.toc_entry(device, i)
    toc.append(min * 60 * 75 + sec * 75 + frame)
(min, sec, frame) = cdrom.leadout(device)
device.close()
toc.append(min * 60 * 75 + sec * 75 + frame)
for i in range(first, last + 1):
    erg.append([i, toc[i - first + 1] - toc[i - first], toc[i - first] - toc[0], 0, 0, 2, 1, cf['_bitrate'], cf['_name'] % i])
""",
    }
}

# compile exec strings # comment these lines out if it doesn't work...
for h in helpers.keys():
    for i in helpers[h].keys():
        if i[-4:] == "_fkt":
            helpers[h][i] = compile(helpers[h][i], '<string>', 'exec')

