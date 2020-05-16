# Jack

Jack is command-line CD ripper. It extracts audio from a CD, encodes it using
3rd party software and augment it with metadata from various sources

As all CLI things, Jack (the ripper) is fast and efficient, and that's why we
like it.

This is a heavily modified fork of https://github.com/jack-cli-cd-ripper/jack
which is becoming obsolete, as it requires Python 2, and needs FreeDB which
has been declared dead.

This fork intends to achieve the following:
* port to Python 3 - done
* replace CDDB.py with python-libdiscid - done
* replace eyeD3 with mutagen - done
* add support for MusicBrainz - under development
* add support for extended, picard-like MusicBrainz tagging - todo
* add support for M4A, using fdkaac and mutagen - mostly done
* encode to multiple formats - todo
* encode from lossless to lossy formats - todo
* lots of cleanups and small changes - continuous process

## Usage

For now, see the original repo.

### Requirements

* Python 3
* python-libdiscid for disc recognition
* python-musicbrainzngs for MusicBrainz support
* mutagen for tagging
* an encoder like oggenc for Ogg/Vorbis (default), flac (Free Lossless Audio
  Codec), lame (MP3) or fdkaac (M4A/AAC)
* a Digital Audio Extraction tool like cdparanoia


## Authors and Copyrights

Jack is Free Libre Open Source Software distributed under the GNU General Public
License version 2, or (at your option) any later version.

The original home of the project was http://www.home.unix-ag.org/arne/jack/ and
the code was hosted in SourceForge.

Jack has first been developed by the following authors, be they praised:

* Copyright (C) 1999-2005 Arne Zellentin <zarne@users.sf.net>, for the Jack code
* Copyright (C) 2002-2016 Martin Michlmayr <tbm@debian.org>, Michael Banck
  <mbanck@debian.org>, for all the Debian patches
* Copyright (C) 2020 Pim Zandbergen <pim+jack@zandbergen.org>, for the changes
  in this fork


## Contributions

Pull Requests and contributions in general are welcome.
