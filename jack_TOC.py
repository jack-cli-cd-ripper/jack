# jack_toc - class for CDDA TOCs - part ("module") of
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


class TOC:

    def __init__(self):
        self.data = []
        self.image_file = None
        self.end_pos = 0
        self.in_need_of_image_name = []

    def __len__(self):
        return len(self.data)

    def append(self, entry):

# if we don't have a image_name specified, we'll take the first one available

        if entry.image_name == "":
            self.in_need_of_image_name.append(entry.number)
        elif self.in_need_of_image_name:
            for i in self.in_need_of_image_name:

# FIXME: maybe we can't reference a track by it's number?

                self.data[i].image_name = entry.image_name
            self.in_need_of_image_name = []

# if the entry has a pregap this needs to be added to the previous track and
# substracted from the current one

        if entry.pregap:
            self.data[-1].length = self.data[-1].length + entry.pregap
            self.end_pos = self.end_pos + entry.pregap
        self.data.append(entry)

        self.end_pos = self.end_pos + entry.length

# update image_file

        self.same_image()

    def export(self):
        "compatibility"
        tracks = []
        for i in self.data:
            track = i.export()
            tracks.append(track)
        return tracks

    def image_filenames(self):
        "return list of all used filenames"
        names = []
        for i in self.data:
            names.append(i.image_name)
        return names

    def same_image(self):
        "check whether all image_files are set to the same file"
        names = self.image_filenames()[1:]
        if not names:
            return 0
        first = names[0]
        same = 1
        for i in names:
            if not i == first:
                same = 0
                break
        if same:
            self.image_file = first
        else:
            self.image_file = None
        return same
