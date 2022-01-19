# Jack

Jack is command-line CD ripper. It extracts audio from a CD, encodes it using
3rd party software and augment it with metadata from various sources

As all CLI things, Jack (the ripper) is fast and efficient, and that's why we
like it.

This is a heavily modified branch, that started as a fork.
The main branch is becoming obsolete, as it requires Python 2

This branch features the following enhancements and changes:
* port to Python 3
* replace CDDB.py with libdiscid
* replace eyeD3 with mutagen
* add support for MusicBrainz while keeping support for freedb/gnudb
* add support for extended tagging, compatible with MusicBrainz Picard
* add support for M4A, using fdkaac and mutagen
* transcoding from lossless to lossy formats
* automatic downloading of album art from coverartarchive, iTunes and discogs
* automatic, highly configurable embedding of album art

## Usage

For now, see the original repo.

### Requirements

* Python 3
* Python 3 modules libdiscid, mutagen, requests, pillow and dateparser
* an encoder like oggenc for Ogg/Vorbis (default), flac (Free Lossless Audio
  Codec), lame (MP3) or fdkaac (M4A/AAC)
* cdparanoia


## Authors and Copyrights

Jack is Free Libre Open Source Software distributed under the GNU General Public
License version 2, or (at your option) any later version.

The original home of the project was http://www.home.unix-ag.org/arne/jack/ and
the code was hosted in SourceForge.

Jack has first been developed by the following authors, be they praised:

* Copyright (C) 1999-2022 Arne Zellentin <zarne@users.sf.net>
* Copyright (C) 2020-2022 Pim Zandbergen <pim@zandbergen.org>
* Copyright (C) 2002-2016 Martin Michlmayr <tbm@debian.org>, Michael Banck
  <mbanck@debian.org>, for all the Debian patches


## Contributions

Pull Requests and contributions in general are welcome.
