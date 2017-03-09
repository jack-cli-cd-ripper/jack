# Jack

Jack is command-line CD ripper. It extracts audio from a CD, encodes it using
3rd party software and augment it with metadata from
[CDDB](https://en.wikipedia.org/wiki/CDDB).

As all CLI things, Jack (the ripper) is fast and efficient, and that's why we
like it.


## Usage

Rip, encode, tag and put all metadata from CDDB in the track files:

```shell
$ jack --query
```

Write, augment or fix metadata in the track files:

```shell
$ vim jack.freedb
$ jack --rename
```

Publish the augmented/fixed metadata to CDDB:

```shell
$ jack --submit
```

Use to save frequently uses options to your `~/.jack3rc` configuration file:

```shell
$ jack --encoder-name=flac --save
```


## Installation

### Requirements

* Right now only python-2.7 is supported - as found on Debian GNU/Linux 9.0 (stretch)
* CDDB.py  - see `doc/INSTALL` on how to get/install it
* eyeD3    - see `doc/INSTALL` on how to get/install it
* an encoder like oggenc for Ogg/Vorbis (default), flac (Free Lossless Audio
  Codec) or lame (MP3)
* a Digital Audio Extraction tool like cdparanoia

Read `doc/INSTALL` for further installation details. It's very unlikely that
it'll run out of the box, you need to install additional software.


## Authors and Copyrights

Jack is Free Libre Open Source Software distributed under the GNU General Public
License version 2, or (at your option) any later version.

This repository is the new home of the project. The development and maintenance
of Jack has been taken over by longtime faithful users of Jack. This has been
possible by the fact that Jack is Libre Software.

The previous home of the project was http://www.home.unix-ag.org/arne/jack/ and
the code was hosted in SourceForge.

Jack has first been developed by the following authors, be they praised:

* Copyright (C) 1999-2005 Arne Zellentin <zarne@users.sf.net>, for the Jack code
* Copyright (C) 2002-2016 Martin Michlmayr <tbm@debian.org>, Michael Banck
  <mbanck@debian.org>, for all the Debian patches


## Contributions

Pull Requests and contributions in general are welcome.



