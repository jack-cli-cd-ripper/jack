# jack.tocentry - class for CDDA TOCs - part ("module") of
# jack - extract audio from a CD and MP3ify it using 3rd party software
# Copyright (C) 1999,2000  Arne Zellentin <zarne@users.sf.net>

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

entry_fields = ['type', 'copy', 'preemphasis', 'channels', 'media',
                'filename', 'start', 'length', 'pregap']
compat_fields = ['number', 'length', 'start', 'copy',
                 'preemphasis', 'channels', 'rip', 'bitrate', 'rip_name', 'mcn', 'isrc']


class TOCentry:

    def __init__(self, raw_dict={}):
        self.number = None
        self.type = None
        self.copy = None            # means no
        self.preemphasis = None     # means no
        self.channels = None
        self.media = None           # "image" or "cd"
        self.image_name = None      # only for image-reader: name of image
        self.readable_name = None   # name the file is renamed to
        self.rip_name = None        # name of file while ripping / encoding
        self.pregap = 0
        self.start = None
        self.length = 0
        self.bitrate = None         # compat?#XXX
        self.rip = None             # compat
        self.mcn = None
        self.isrc = None

        if raw_dict:    # for compatibility: allow to read old-style track info
            num = 1
            for i in compat_fields:
                self.__dict__[i] = raw_dict[num]
                num = num + 1

    def export(self):
        "compatibility"
        track = []
        for i in compat_fields:
            track.append(self.__dict__[i])
        return track

    # intercept setting of attributes
    def __setattr__(self, name, value):
        if name == 'pregap' and value:
            self.__dict__['start'] = self.start + (value - self.pregap)
            self.__dict__['length'] = self.length - (value - self.pregap)
            self.__dict__['pregap'] = value

        else:
            self.__dict__[name] = value

    # for debugging purposes only.
    def initialized(self):
        ok = 1
        for i in entry_fields:
            if not self.__dict__[i]:
                ok = 0
                break
        return ok
