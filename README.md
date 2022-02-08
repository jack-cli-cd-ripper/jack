# Jack

Jack is command-line CD ripper. It extracts audio from a CD, encodes it using
3rd party software and augments it with metadata from various sources.

As all CLI things, Jack is fast and efficient, and that's why we
like it.

## Recent features

* port to Python 3
* replace CDDB.py with libdiscid
* replace eyeD3 with mutagen
* add support for MusicBrainz while keeping support for freedb/gnudb
* add support for extended tagging, compatible with MusicBrainz Picard
* add support for M4A, using fdkaac and mutagen
* transcoding from lossless to lossy formats
* automatic downloading of album art from coverartarchive, iTunes and discogs
* automatic, highly configurable embedding of album art

## Requirements

* Python 3
* libdiscid, a shared library written in C
* a Python 3 wrapper for libdiscid, either python-libdiscid or python-discid
* Python 3 modules mutagen, requests, pillow and dateparser
* an encoder like oggenc (Ogg/Vorbis), flac, lame (MP3) or fdkaac (M4A/AAC)
* a ripper like cdparanoia (recommended), cdda2wav, dagrab or tosha

## Usage

jack [option]...

Options of type bool can be negated with --no-[option].
Options that take an argument get that argument from the next option,
or from the form --[option]=[argument].
Options that take a list argument take that list from the following arguments
terminated with ';', the next option or the end of the options.

| Option | Type | Default value | Description |
|--------|------|---------------|-------------|
| --debug | bool | no | show debug information |
| --debug-write | bool | no | write debug information to a file |
| --ripper | str | 'cdparanoia' | which program to use for extracting the audio data<br><br>use which program to rip: cdparanoia, tosha, cdda2wav, dagrab (untested) |
| --device | str | '/dev/cdrom' | use which device for ripping |
| --encoder-name, -E | str | 'oggenc' | use which encoder<br><br>this is a symbolic name (see helpers), NOT the executable's name |
| --vbr, -v | bool | yes | generate variable bitrate files<br><br>use variable bitrate for encoders which support it |
| --quality | float | 6 | vbr encoding quality. -1 is lowest, 10 highest. |
| --bitrate, -b | int | 160 | target bitrate in kbit/s<br><br>default bitrate |
| --server | str | 'musicbrainz' | use which metadata server<br><br>your metadata server, see metadata_servers |
| --rename-fmt | str | '%a - %l - %n - %t' | format of normal files<br><br>specify how the resulting files are named:<br>    %n: track number<br>    %a: artist<br>    %t: track title<br>    %l: album title<br>    %y: album release year - individual track years are unsupported<br>    %Y: smart year - transforms to the append_year template if year is set<br>    %g: album genre - individual track genres are unsupported |
| --rename-fmt-va | str | '%l - %n - %a - %t' | format of Various Artists files<br><br>specify how the resulting files are named:<br>    %n: track number<br>    %a: artist<br>    %t: track title<br>    %l: album title<br>    %y: album release year - individual track years are unsupported<br>    %Y: smart year - transforms to the append_year template if year is set<br>    %g: album genre - individual track genres are unsupported |
| --rename-num | str | '%02d' | track number format for %n, printf() style |
| --rename-dir | bool | yes | rename directory as well |
| --append-year | str | '' | append this string to the directory name |
| --dir-template | str | '%a/%l' | if directories are renamed, this is the format used<br><br>specify how the resulting files are named:<br>    %a: artist<br>    %l: album title<br>    %g: album genre - individual track genres are unsupported<br>    %y: album release year - individual track years are unsupported<br>    %Y: smart year - transforms to the append_year template if year is set<br>    %d: disc number<br>    %D: number of discs<br>    %t: disc title |
| --dir-multi-cd-template | str | '%a/%l (CD %d)' |  dir_template, if album consists of multiple discs<br><br>specify how the resulting files are named:<br>    %a: artist<br>    %l: album title<br>    %g: album genre - individual track genres are unsupported<br>    %y: album release year - individual track years are unsupported<br>    %Y: smart year - transforms to the append_year template if year is set<br>    %d: disc number<br>    %D: number of discs<br>    %t: disc title |
| --dir-multi-cd-unknown-number-template | str | '%a/%l (CD %d)' |  dir_template, if album consists of multiple discs, and the number of discs is unknown<br><br>specify how the resulting files are named:<br>    %a: artist<br>    %l: album title<br>    %g: album genre - individual track genres are unsupported<br>    %y: album release year - individual track years are unsupported<br>    %Y: smart year - transforms to the append_year template if year is set<br>    %d: disc number<br>    %D: number of discs<br>    %t: disc title |
| --dir-titled-cd-template | str | '%a/%l (CD %d: %t)' |  dir_template, if album consists of multiple discs, and the current disc has a title<br><br>specify how the resulting files are named:<br>    %a: artist<br>    %l: album title<br>    %g: album genre - individual track genres are unsupported<br>    %y: album release year - individual track years are unsupported<br>    %Y: smart year - transforms to the append_year template if year is set<br>    %d: disc number<br>    %D: number of discs<br>    %t: disc title |
| --dir-titled-cd-unknown-number-template | str | '%a/%l (CD %d: %t)' |  dir_template, if album consists of an unknown number of multiple discs, and the current disc has a title<br><br>specify how the resulting files are named:<br>    %a: artist<br>    %l: album title<br>    %g: album genre - individual track genres are unsupported<br>    %y: album release year - individual track years are unsupported<br>    %Y: smart year - transforms to the append_year template if year is set<br>    %d: disc number<br>    %D: number of discs<br>    %t: disc title |
| --file-artist | str | 'as-in-mb' | which MusicBrainz artist name to use for filenames<br><br>valid arguments are 'as-in-mb' (default), 'as-credited' or 'as-sort-name' |
| --add-disambiguation | bool | no | add disambiguation to the album title |
| --char-filter | str | '' | convert file names using a python method<br><br>an example which converts to lowercase, even with non-ascii charsets: ".lower()"  |
| --charset | str | 'UTF-8' | charset of filenames<br><br>examples: latin-1, utf-8, ... |
| --unusable-chars | list | ['/', '\r'] | characters which can't be used in filenames<br><br>put chars which can't be used in filenames here and their replacements<br>in replacement_chars.<br><br>example 1: replace all " " by "_":<br>unusable_chars = " "<br>replacement_chars = "_"<br><br>example 2: replace umlauts by an alternate representation and kill some<br>            special characters:<br>unusable_chars = "äöüÄÖÜß?\*\^()[]{}"<br>replacement_chars = ["ae", "oe", "ue", "Ae", "Oe", "Ue", "ss", ""] |
| --replacement-chars | list | ['%', ''] | unusable chars are replaced by the corresponding list item<br><br>this is stretched to match unusable_chars' length using the last char as fill |
| --scan-dirs | int | 2 | scan in cwd n dir levels deep, e.g. 0 to disable |
| --search | list | ['.'] | search which directories |
| --workdir, -w | str | '.' | where to create directories and put the files |
| --max-load | float | 10.0 | only start new encoders if load < max_load |
| --usage-win | bool | yes | show the help screen while running |
| --encoders, -e | int | 1 | encode how many files in parallel |
| --otf | bool | no | on-the-fly encoding \*experimental\* |
| --create-dirs, -D | bool | yes | create subdir for files |
| --reorder, -r | bool | no | reorder tracks to save space while encoding |
| --keep-wavs, -k | bool | no | do not delete WAVs after encoding them |
| --only-dae, -O | bool | no | only produce WAVs, implies --keep_wavs |
| --read-ahead, -a | int | 99 | read how many WAVs in advance |
| --nice, -n | int | 12 | nice-level of encoders |
| --overwrite, -o | bool | no | overwrite existing files |
| --remove-files | bool | no | remove jack.\* file when done |
| --silent-mode | bool | no | be quiet (no screen output) |
| --exec, -x | bool | no | run predefined command when finished |
| --force | bool | no | don't ask. |
| --swab, -S | bool | yes | swap byteorder when reading from image |
| --todo | bool | no | print what would be done and exit |
| --space, -s | int | 0 | force usable disk space, in bytes |
| --check-toc | bool | no | compare toc-file and cd-toc, then exit |
| --undo-rename, -u | bool | no | undo the last file renaming and exit |
| --dont-work, -d | bool | no | don't do DAE, encoding, renaming or tagging |
| --update-metadata, -U | bool | no | update the metadata info and exit |
| --refresh-metadata | bool | no | forget about choices made in previous queries |
| --tracks, -t | str | '' | which tracks to process (e.g. 1, 3, 5-9, 12-) |
| --query-now, -Q | bool | no | do metadata query when starting |
| --query-if-needed | bool | no | query metadata server when starting if not queried already |
| --query, -q | bool | no | do metadata query when all is done |
| --cont-failed-query | bool | no | continue without metadata data if query fails |
| --edit-metadata | bool | no | edit metadata information before using it |
| --various | bool | - | assume CD has various artists |
| --various-swap | bool | no | exchange artist and title |
| --extt-is-artist | bool | no | extt contains artist |
| --extt-is-title | bool | no | extt contains track title |
| --extt-is-comment | bool | no | extt contains track comment |
| --rename, -R | bool | no | rename according to metadata file, eg. after editing it |
| --lookup | bool | no | start a browser and look up the CD |
| --set-dae-tag | bool | no | set DAE info tags<br><br>depends on set_extended_tag |
| --genre, -G | str | - | overrule genre from metadata |
| --year, -Y | str | - | overrule year from metadata (0=don't set) |
| --from-tocfile, -f | str | - | read another toc file which may point to an image-file |
| --from-image, -F | bytes | - | read audio from an image file |
| --guess-toc, -g | list | [] | guess TOC from files (until terminating ";") |
| --upd-progress | bool | no | re-generate progress file if "lost" |
| --multi-mode | bool | no | try to query metadata server for all dirs in searchdirs which have no metadata |
| --claim-dir, -C | bool | no | rename the dir even if it was not created by jack |
| --wait | bool | no | wait for key press before quitting |
| --save | bool | no | save options to rc file and exit |
| --get | str | - | show value of a config option |
| --write-m3u | bool | no | create a playlist in .m3u format |
| --download-progress-interval | int | 5 | interval in seconds for showing progress of slow downloads, zero is no progress |
| --embed-albumart | bool | no | embed album art |
| --show-albumart | bool | no | show the album art that has been embedded in an external viewer |
| --albumart-file | str | - | specific album art file to embed |
| --albumart-search | list | ['.\*[Cc]over.\*\\.(jpg\|jpeg\|png)\$', '.\*[Ff]ront.\*\\.(jpg\|jpeg\|png)\$', '\^[Ff]older\\.(jpg\|jpeg\|png)\$', '\^jack\\.caa\\.front.\*\\.jpg\$', '\^jack\\.itunes.\*\\.jpg\$', '\^jack\\.discogs.\*\\.jpg\$'] | list of regex patterns for matching local album art files |
| --albumart-ignorecase | bool | yes | ignore case when searching for local album art |
| --albumart-recurse | bool | no | recurse into subfolders when searching for local album art |
| --albumart-max-size | int | 1000000 | maximum size when considering album art file |
| --albumart-min-size | int | 5000 | minimum size when considering album art file |
| --albumart-max-width | int | 1200 | maximum width when considering album art file |
| --albumart-min-width | int | 250 | minimum width when considering album art file |
| --albumart-max-height | int | 1200 | maximum height when considering album art file |
| --albumart-min-height | int | 250 | minimum height when considering album art file |
| --albumart-save-prefix | str | 'jack.saved.' | prefix for saving existing embedded album art |
| --fetch-albumart | bool | no | download album art while querying |
| --overwrite-albumart | str | 'conditional' | whether to overwrite existing album art files, 'always', 'never' or 'conditional' (the default) |
| --albumart-providers | list | ['coverartarchive', 'iTunes', 'discogs'] | list of sources for album art, currently 'coverartarchive', 'iTunes' or 'discogs' |
| --caa-albumart-prefix | str | 'jack.caa.' | prefix for saving fetched album art files from coverartarchive |
| --caa-albumart-sizes | list | ['original', 'large'] | list of album art sizes to download from coverartarchive: 'original', 'small', 'large', '250', '500' or '1200' |
| --caa-albumart-types | list | ['front'] | download these album arts from coverartarchive ('front' and/or 'back') |
| --itunes-albumart-sizes | list | ['standard', 'high'] | list of album art sizes to download from iTunes: 'thumb', 'standard' or 'high' |
| --itunes-albumart-limit | int | 1 | limit number of matches when querying for iTunes album art, zero is no limit |
| --itunes-albumart-country | str | 'us' | two letter country code of iTunes store to query |
| --itunes-albumart-prefix | str | 'jack.itunes.' | prefix for saving fetched iTunes album art files |
| --discogs-albumart-prefix | str | 'jack.discogs.' | prefix for saving fetched discogs album art files |
| --discogs-albumart-types | list | ['primary'] | download these album arts from discogs ('primary' and/or 'secondary') |
| --discogs-albumart-token | str | - | discogs personal authentication token |
| --readme | str | - | export README.md to given file |

## Interaction

While Jack is running, press q or Q to quit,
    p or P to disable ripping (you need the CD drive)
    p or P (again) or c or C to resume,
    e or E to pause/continue all encoders and
    r or R to pause/continue all rippers.

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
