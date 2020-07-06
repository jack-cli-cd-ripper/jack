# jack.discid: discid/libdiscid wrapper for
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2020  Arne Zellentin <zarne@users.sf.net>

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


def init(debug=False):
    global discid_read, DiscError, put, features, v

    try:
        from libdiscid import read as discid_read
        from libdiscid import put
        from libdiscid import DiscError
        from libdiscid import FEATURE_MCN, FEATURE_READ, FEATURE_ISRC
        features = FEATURE_MCN | FEATURE_READ | FEATURE_ISRC
        v = 1
    except ImportError:
        try:
            from discid.disc import read as discid_read
            from discid.disc import put
            from discid.disc import DiscError
            features = ['read', 'mcn', 'isrc']
            v = 2
        except ImportError:
            return False

    if debug:
        print("discid v=" + str(v))
        disc = read("/dev/cdrom")
        print("toc: " + repr(toc(disc)))
        print("first_track: " + repr(first(disc)))
        print("last_track: " + repr(last(disc)))
        print("mcn: " + repr(mcn(disc)))
        print("isrcs: " + repr(isrcs(disc)))

    return True


def read(device):
    return discid_read(device, features)


def toc(disc):
    if v == 1:
        toc = list(disc.track_offsets)
        toc.append(disc.leadout_track)
        return toc

    else:
        toc = []
        for t in disc.tracks:
            toc.append(t.offset)
        last_track = disc.tracks[disc.last_track_num - 1]
        toc.append(last_track.offset + last_track.sectors)
        return toc


def first(disc):
    if v == 1:
        return disc.first_track
    else:
        return disc.first_track_num


def last(disc):
    if v == 1:
        return disc.last_track
    else:
        return disc.last_track_num


def mcn(disc):
    return disc.mcn


def isrcs(disc):
    if v == 1:
        return disc.track_isrcs

    else:
        isrcs = []
        for t in disc.tracks:
            isrcs.append(t.isrc)
        return isrcs
