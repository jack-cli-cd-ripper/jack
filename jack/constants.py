# jack.constants
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 2002  Arne Zellentin <zarne@users.sf.net>

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

# track representation format
# LEN and START is in cdda-blocks:
# [ track#, len, start, copy, pre, ch, unused, bitrate, filename ]
fields = ["NUM", "LEN", "START", "COPY", "PRE", "CH", "RIP", "RATE", "NAME", "MCN", "ISRC"]
NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME, MCN, ISRC = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

# jack.functions.tracksize() return list format
ENC, WAV, BOTH, PEAK, AT, CDR, BLOCKS = 0, 1, 2, 3, 4, 5, 6

# more constants
CDDA_BLOCKSIZE = 2352
CDDA_BLOCKS_PER_SECOND = 75
MSF_OFFSET = 150
CHILD = 0
CDDA_MAXTRACKS = 100
STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2
