### jack_globals: Global storage space for
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

from jack_config import cf, cg
from ID3 import ID3
import sys

DEBUG = 1

# track representation format
# [ track#, len, start, copy, pre, ch, unused, bitrate, filename ]
fields = ["NUM", "LEN", "START", "COPY", "PRE", "CH", "RIP", "RATE", "NAME"]
NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME = range(len(fields))
# LEN and START is in cdda-blocks:
CDDA_BLOCKSIZE = 2352
# more constants
CDDA_BLOCKS_PER_SECOND = 75
MSF_OFFSET = 150
CHILD = 0
CDDA_MAXTRACKS = 100
STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2

# globals
dae_queue = []      # This stores the tracks to rip
enc_queue = []      # WAVs go here to get some codin'
enc_running = 0     # what is going on?
dae_running = 0     # what is going on?
scan_dirs = None    # to be overridden by argv
upd_progress = 0    # regenerate progress file if "lost"
progress_changed = 0# nothing written to progress, yet
global_error = 0    # remember if something went wrong
special_line = None # a status line
bottom_line = None  # a status line
extra_lines = None  # number of status lines actually displayed
xterm_geom_changed = 0      # only restore xterm size if it was changed
width = None                # if we need to restore xterm
height = None               # if we need to restore xterm
revision = 0                # initial revision of freedb data
status_all = {}             # progress info common for all track

#misc stuff
tmp = ID3("/dev/null")
id3genres = tmp.genres
del tmp

