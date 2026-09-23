"""jack.rawtoc: the table of contents as the drive reports it"""

# jack.rawtoc: the table of contents as the drive reports it; a module for
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

# libdiscid leaves out the data track of a CD-Extra disc and the
# lead-out behind it, so jack.toc never has them. They are recorded in
# the progress file as a "rawtoc" line under "all", for possible future
# use such as AccurateRip lookups, like the MCN and ISRCs were recorded
# before jack had a use for them. Nothing reads the line yet.
#
#   all/|\rawtoc/|\1 11 230657 150 13733 ... 135361 180720d
#
# is the first and the last track, the lead-out, then the offset of every
# track in the libdiscid convention (frames from the start of the disc,
# including the 150 frames of the first pregap), data tracks suffixed d.

from jack.constants import NUM, LEN, START, MSF_OFFSET


def format_line(first, last, leadout, offsets):
    "offsets is a list of (offset, is_data) pairs, one per track"

    return " ".join([str(first), str(last), str(leadout)]
                    + [str(offset) + ("d" if is_data else "") for offset, is_data in offsets])


def from_tracks(tracks, data_tracks=()):
    "the line for tracks as read from a toc file, with the given track numbers marked as data"

    leadout = tracks[-1][START] + tracks[-1][LEN] + MSF_OFFSET
    offsets = [(t[START] + MSF_OFFSET, t[NUM] in data_tracks) for t in tracks]
    return format_line(tracks[0][NUM], tracks[-1][NUM], leadout, offsets)
