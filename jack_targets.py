### jack_targets.py: supportet target formats for
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 2002  Arne Zellentin <zarne@users.sf.net>

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

import jack_utils

try:
    import ogg.vorbis
    has_ogg_vorbis = 1
    if ogg.vorbis.__version__ < "0.5":
        has_ogg_vorbis = 0
        jack_utils.debug("ogg.vorbis tagging disabled, version is too low.")
except:
    has_ogg_vorbis = 0
    jack_utils.debug("ogg.vorbis tagging disabled.")

# supported target file fomats
targets = {
    'mp3': {
        'can_cbr': 1,               # can do CBR = constant bitrate
        'can_vbr': 1,               # can do VBR = variable bitrate
        'can_id3': 1,               # can set a ID3 tag
        'can_pretag': 0,            # can set tag info before encoding
        'can_posttag': 1,           # can set tag info after encoding
        'file_extension': ".mp3"    # the extension for this target format
        },
    'ogg': {
        'can_cbr': 0,
        'can_vbr': 1,
        'can_id3': 1,
        'can_pretag': 1,
        'can_posttag': (1 & has_ogg_vorbis),
        'file_extension': ".ogg"
        },
    'flac': {
        'can_cbr': 0,
        'can_vbr': 1,
        'can_id3': 1,
        'can_pretag': 0,
        'can_posttag': 1,
        'file_extension': ".flac"
        },
    'mpc': {
        'can_cbr': 0,
        'can_vbr': 1,
        'can_id3': 0,
        'can_pretag': 0,
        'can_posttag': 0,
        'file_extension': ".mpc"
        }
    }
