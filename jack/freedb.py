# jack.freedb: freedb server for use in
# jack - extract audio from a CD and encode it using 3rd party software
# Copyright (C) 1999-2003  Arne Zellentin <zarne@users.sf.net>

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

import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import string
import sys
import os
import locale
import codecs
import tempfile
import shutil
import re

import jack.playorder
import jack.functions
import jack.progress
import jack.utils
import jack.tag
import jack.misc

from jack.version import prog_version, prog_name
from jack.globals import *

import libdiscid

names_available = None          # freedb info is available
dir_created = None              # dirs are only renamed if we have created them
NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME = list(range(9))
freedb_inexact_match = -1
filenames = []

# Warning: code duplication.  Make a function through which information can
# be requested, and let it fall back to generic information (e.g. my_mail,
# mail, id) and only require individual entries to have 'host').  FIXME
freedb_servers = {
    'freedb': {
        'host': "freedb.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-at': {
        'host': "at.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-au': {
        'host': "au.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-ca': {
        'host': "ca.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-es': {
        'host': "es.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-fi': {
        'host': "fi.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-jp': {
        'host': "jp.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-ru': {
        'host': "ru.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-uk': {
        'host': "uk.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-uk2': {
        'host': "uk2.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-us': {
        'host': "us.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
}


def interpret_db_file(all_tracks, todo, freedb_form_file, verb, dirs=0, warn=None):
    "read freedb file and rename dir(s)"
    global names_available, dir_created
    freedb_rename = 0
    if warn == None:
        err, track_names, locale_names, cd_id, revision = freedb_names(
            freedb_id(all_tracks), all_tracks, todo, freedb_form_file, verb=verb)
    else:
        err, track_names, locale_names, cd_id, revision = freedb_names(
            freedb_id(all_tracks), all_tracks, todo, freedb_form_file, verb=verb, warn=warn)
    if (not err) and dirs:
        freedb_rename = 1

# The user wants us to use the current dir, unconditionally.

        if cf['_claim_dir']:
            dir_created = jack.utils.split_dirname(os.getcwd())[-1]
            jack.functions.progress("all", "mkdir", dir_created)
            cf['_claim_dir'] = 0

        if cf['_rename_dir'] and dir_created:
            new_dirs, new_dir = jack.utils.mkdirname(
                track_names, cf['_dir_template'])
            old_dir = os.getcwd()
            old_dirs = jack.utils.split_dirname(old_dir)
            dirs_created = jack.utils.split_dirname(dir_created)

# only do the following if we are where we think we are and the dir has to be
# renamed.

            if jack.utils.check_path(dirs_created, old_dirs) and not jack.utils.check_path(dirs_created, new_dirs):
                jack.utils.rename_path(dirs_created, new_dirs)
                print("Info: cwd now", os.getcwd())
                jack.functions.progress("all", 'ren', str(dir_created + "-->" + new_dir))

    if not err:
        cd = track_names[0]
        year = genretxt = None
        if len(cd) > 2:
            year = repr(cd[2])
        if len(cd) > 3:
            genretxt = id3genres[cd[3]]
        filenames.append('')  # FIXME: possibly put the dir here, but in no
        # case remove this since people access filenames with i[NUM] which
        # starts at 1
        num = 1
        for i in track_names[1:]:
            replacelist = {"n": cf['_rename_num'] % num, "l": cd[1], "t": i[1],
                           "y": year, "g": genretxt}
            if cf['_various']:
                replacelist["a"] = i[0]
                newname = jack.misc.multi_replace(
                    cf['_rename_fmt_va'], replacelist, "rename_fmt_va", warn=(num == 1))
            else:
                replacelist["a"] = cd[0]
                newname = jack.misc.multi_replace(
                    cf['_rename_fmt'], replacelist, "rename_fmt", warn=(num == 1))
            exec("newname = newname" + cf['_char_filter'])
            for char_i in range(len(cf['_unusable_chars'])):
                try:
                    a = str(cf['_unusable_chars'][char_i])
                    b = str(cf['_replacement_chars'][char_i])
                except UnicodeDecodeError:
                    warning("Cannot substitute unusable character %d."
                            % (char_i + 1))
                else:
                    newname = newname.replace(a, b)
            filenames.append(newname)
            num += 1
        names_available = 1
    else:
        freedb_rename = 0
    return err, track_names, locale_names, freedb_rename, revision
# / end of interpret_db_file /#


def local_freedb(cd_id, freedb_dir, outfile="/tmp/testfilefreedb"):
    "Use file from local freedb directory"
    # Moritz Moeller-Herrmann kindly provided this functionality.
    if not os.path.isdir(freedb_dir):
        error("freedb directory not found")
    if not os.access(freedb_dir, 5):
        error("freedb directory access not permitted")
    cat = [freedb_dir]  # category listing
    for entry in os.listdir(freedb_dir):
        if os.path.isdir(os.path.join(freedb_dir, entry)):
            cat.append(os.path.join(freedb_dir, entry))
    for musicdir in cat:
        for m in os.listdir(musicdir):
            if m == cd_id:
                idfile = os.path.join(musicdir, cd_id)
                inf = open(idfile, "r")
                outf = open(outfile, "w")
                buf = inf.readline()
                while buf:
                    buf = buf.replace("\n", "")    # we need trailing spaces
                    if buf != ".":
                        outf.write(buf + "\n")
                    buf = inf.readline()
                inf.close()
                outf.close()
                return 0
    print("No local matching freedb entry found")
    return 1


def freedb_id(tracks, warn=0):
    from jack.globals import START, MSF_OFFSET, CDDA_BLOCKS_PER_SECOND
    "calculate freedb (aka CDDB) disc-id"
    cdtoc = []
    if not tracks:
        if warn:
            warning("no tracks! No disc inserted? No/wrong ripper?")
        return 0

    first_track = 1
    track_offsets = []
    for i in tracks:
        track_offsets.append(i[START] + MSF_OFFSET)
        last_track = i[NUM]
        num_sectors = i[START] + i[LEN] + MSF_OFFSET
    disc = libdiscid.put(first_track, last_track, num_sectors, track_offsets)

    return disc.freedb_id


def freedb_split(field, s, max=78):
    "split a field into multiple lines of 78 char max."
    x = ""
    s = field + "=" + s
    while len(s) > max:
        x = x + s[:max] + "\n"
        s = field + "=" + s[max:]
    return x + s + "\n"


def freedb_template(tracks, names="", revision=0):
    "generate a freedb submission template"
    if os.path.exists(cf['_freedb_form_file']):
        os.rename(cf['_freedb_form_file'], cf['_freedb_form_file'] + ".bak")
    f = open(cf['_freedb_form_file'], "w")
    f.write("# xmcd CD database file\n#\n# Track frame offsets:\n")
    for i in tracks:
        f.write("#       " + repr(i[START] + MSF_OFFSET) + "\n")
    f.write("#\n# Disc length: " + repr(
            (MSF_OFFSET + tracks[-1][START] + tracks[-1][LEN]) // CDDA_BLOCKS_PER_SECOND))
    f.write(" seconds\n#\n# Revision: %i\n" % revision)
    f.write("# Submitted via: " + prog_name + " " + prog_version + "\n#\n")
    f.write("DISCID=" + freedb_id(tracks) + "\n")
    if names:
        if names[1][0]:  # various
            if names[0][0].upper().find("VARIOUS") >= 0:
                f.write(freedb_split("DTITLE", "Various / " + names[0][1]))
            else:
                f.write(
                    freedb_split("DTITLE", "Various / " + names[0][0] + " - " + names[0][1]))
        else:
            f.write(freedb_split("DTITLE", names[0][0] + " / " + names[0][1]))
    else:
        f.write("DTITLE=\n")
    freedb_year, freedb_id3genre = -1, -1
    if cf['_id3_genre'] >= 0 and cf['_id3_genre'] < len(id3genres) or cf['_id3_genre'] == 255:
        freedb_id3genre = cf['_id3_genre']
    elif names and len(names[0]) == 4:
        freedb_id3genre = names[0][3]
    if cf['_id3_year'] >= 0:
        freedb_year = cf['_id3_year']
    elif names and len(names[0]) == 4:
        freedb_year = names[0][2]
    if freedb_year >= 0:
        f.write("DYEAR=%d\n" % freedb_year)
    else:
        f.write("DYEAR=\n")
    if freedb_id3genre >= 0:
        f.write("DGENRE=%s\n" % id3genres[freedb_id3genre])
    else:
        f.write("DGENRE=\n")
    for i in tracks:
        if names:
            if names[i[NUM]][0]:  # various
                f.write(
                    freedb_split("TTITLE" + repr(i[NUM] - 1),
                                 names[i[NUM]][0] +
                                 " - " +
                                 names[i[NUM]][1]
                                 )
                )
            else:
                f.write(
                    freedb_split("TTITLE" + repr(i[NUM] - 1), names[i[NUM]][1]))
        else:
            f.write("TTITLE" + repr(i[NUM] - 1) + "=\n")
    f.write("EXTD=\n")
    for i in tracks:
        f.write("EXTT" + repr(i[NUM] - 1) + "=\n")
    f.write("PLAYORDER=\n")


def freedb_query(cd_id, tracks, file):
    if cf['_freedb_dir']:
        if local_freedb(cd_id, cf['_freedb_dir'], file) == 0:  # use local database (if any)
            return 0

    qs = "cmd=cddb query " + cd_id + " " + repr(len(tracks)) + " "  # query string
    for i in tracks:
        qs = qs + repr(i[START] + MSF_OFFSET) + " "
    qs = qs + repr((MSF_OFFSET + tracks[-1][START] + tracks[-1][LEN]) // CDDA_BLOCKS_PER_SECOND)
    hello = "hello=" + cf['_username'] + " " + cf[
        '_hostname'] + " " + freedb_servers[cf['_freedb_server']]['id']
    qs = urllib.parse.quote_plus(qs + "&" + hello + "&proto=6", "=&")
    url = "http://" + \
        freedb_servers[cf['_freedb_server']]['host'] + "/~cddb/cddb.cgi?" + qs
    if cf['_cont_failed_query']:
        try:
            f = urllib.request.urlopen(url)
        except IOError:
            traceback.print_exc()
            err = 1
            return err
    else:
        f = urllib.request.urlopen(url)
    buf = f.readline().decode(cf['_charset'])
    if buf and buf[0:1] == "2":
        if buf[0:3] in ("210", "211"):  # Found inexact or multiple exact matches, list follows
            if buf[0:3] == "211":
                global freedb_inexact_match
                freedb_inexact_match = 1
            print("Found the following matches. Choose one:")
            num = 1
            matches = []
            while 1:
                buf = f.readline().decode(cf['_charset'])
                if not buf:
                    break
                buf = buf.rstrip()
                if buf != ".":
                    print("%2i" % num + ".) " + buf)
                    matches.append(buf)
                    num = num + 1
            x = -1
            while x < 0 or x > num - 1:
                userinput = input(" 0.) none of the above: ")
                if not userinput:
                    continue
                try:
                    x = int(userinput)
                except ValueError:
                    x = -1    # start the loop again
                if not x:
                    print("ok, aborting.")
                    sys.exit()

            buf = matches[x - 1]
            buf = buf.split(" ", 2)
            freedb_cat = buf[0]
            cd_id = buf[1]
            err = 0

        elif buf[0:3] == "200":
            buf = buf.split()
            freedb_cat = buf[1]
        elif buf[0:3] == "202":
            if cf['_cont_failed_query']:
                warning(buf + f.read().decode(cf['_charset']) + " How about trying another --server?")
                err = 1
                return err
            else:
                error(buf + f.read().decode(cf['_charset']) + " How about trying another --server?")
        else:
            if cf['_cont_failed_query']:
                warning(
                    buf + f.read().decode(cf['_charset']) + " --don't know what to do, aborting query.")
                err = 1
                return err
            else:
                error(
                    buf + f.read().decode(cf['_charset']) + " --don't know what to do, aborting query.")

        cmd = "cmd=cddb read " + freedb_cat + " " + cd_id
        url = "http://" + freedb_servers[cf['_freedb_server']][
            'host'] + "/~cddb/cddb.cgi?" + urllib.parse.quote_plus(cmd + "&" + hello + "&proto=6", "=&")
        f = urllib.request.urlopen(url)
        buf = f.readline().decode(cf['_charset'])
        if buf and buf[0:3] == "210":  # entry follows
            if os.path.exists(file):
                os.rename(file, file + ".bak")
            of = open(file, "w")
            buf = f.readline().decode(cf['_charset'])
            while buf:
                buf = buf.rstrip()
                if buf != ".":
                    of.write(buf + "\n")
                buf = f.readline().decode(cf['_charset'])
            of.close()
            jack.functions.progress("all", "freedb_cat", freedb_cat)
            jack.progress.status_all['freedb_cat'] = freedb_cat
            err = 0
        else:
            print(buf.rstrip())
            print(f.read().decode(cf['_charset']))
            warning("could not query freedb entry")
            err = 1
        f.close()
    else:
        print(buf.rstrip())
        print(f.read().decode(cf['_charset']))
        warning("could not check freedb category")
        err = 2
    f.close()
    return err


def freedb_names(cd_id, tracks, todo, name, verb=0, warn=1):
    "returns err, [(artist, albumname), (track_01-artist, track_01-name), ...], cd_id, revision"
    err = 0
    tracks_on_cd = tracks[-1][NUM]
    freedb = {}
    f = open(name, "r")  # first the freedb info is read in...
    while 1:
        line = f.readline()
        if not line:
            break
        line = line.replace("\n", "")
        # cannot use rstrip, we need trailing spaces
        line = line.replace("\r", "")
        # I consider "\r"s as bugs in db info
        if jack.functions.starts_with(line, "# Revision:"):
            revision = int(line[11:])
        for i in ["DISCID", "DTITLE", "DYEAR", "DGENRE", "TTITLE", "EXTD", "EXTT", "PLAYORDER"]:
            if jack.functions.starts_with(line, i):
                buf = line
                if buf.find("=") != -1:
                    buf = buf.split("=", 1)
                    if buf[1]:
                        if buf[0] in freedb:
                            if buf[0] == "DISCID":
                                freedb[buf[0]] = freedb[buf[0]] + ',' + buf[1]
                            else:
                                freedb[buf[0]] = freedb[buf[0]] + buf[1]
                        else:
                            freedb[buf[0]] = buf[1]
                continue

    for i in tracks:    # check that info is there for all tracks
        if "TTITLE%i" % (i[NUM] - 1) not in freedb:   # -1 because freedb starts at 0
            if i[NUM] in [x[NUM] for x in todo]:
                err = 1
            if verb:
                warning("no freedb info for track %02i (\"TTITLE%i\")" %
                        (i[NUM], i[NUM] - 1))
            freedb["TTITLE%i" % (i[NUM] - 1)] = "[not set]"

    for i in list(freedb.keys()):  # check that there is no extra info
        if i[0:6] == "TTITLE":
            if int(i[6:]) > tracks_on_cd - 1:
                err = 2
                if verb:
                    warning("extra freedb info for track %02i (\"%s\"), cd has only %02i tracks." %
                            (int(i[6:]) + 1, i, tracks_on_cd))

    if "DTITLE" not in freedb:
        err = 3
        if verb:
            warning(
                "freedb entry doesn't contain disc title info (\"DTITLE\").")
        freedb['DTITLE'] = "[not set]"

    if "DISCID" not in freedb:
        err = 4
        if verb:
            warning("freedb entry doesn't contain disc id info (\"DISCID\").")
        read_id = "00000000"
    else:
        read_id = freedb['DISCID']
        read_ids = freedb['DISCID'].split(",")
        id_matched = 0
        for i in read_ids:
            if i == cd_id:
                id_matched = 1
        if not id_matched and warn and freedb_inexact_match < 1:
            print("Warning: CD signature ID and ID from FreeDB file do not match.")
            print("         CD signature: " + cd_id)
            print("         FreeDB ID:    " + ",".join(read_ids))
        for i in read_ids:
            for j in i:
                if j not in "0123456789abcdef":
                    if verb:
                        warning(
                            "the disc's id is not 8-digit hex (\"DISCID\").")
                    err = 5
            if len(i) != 8:
                if verb:
                    warning("the disc's id is not 8-digit hex (\"DISCID\").")
                err = 5

    if 'PLAYORDER' in freedb:
        jack.playorder.order = freedb('PLAYORDER')

    dtitle = freedb['DTITLE']
    dtitle = dtitle.replace(" / ", "/")    # kill superflous slashes
    dtitle = dtitle.replace("/ ", "/")
    dtitle = dtitle.replace(" /", "/")
    dtitle = dtitle.replace("(unknown disc title)", "(unknown artist)/(unknown disc title)")  # yukk!
    if not dtitle:
        dtitle = "(unknown artist)/(unknown disc title)"
    if dtitle.find("/") == -1:
        if cf['_various'] == 1:
            dtitle = "Various/" + dtitle
            warning("bad disc title, using %s. Please fix and submit." %
                    dtitle)
        else:
            dtitle = "(unknown artist)/" + dtitle

    names = [dtitle.split("/", 1)]
    year = -1
    if 'DYEAR' in freedb:
        try:
            year = int(freedb['DYEAR'])
            if cf['_id3_year'] <= 0:
                cf['_id3_year'] = year
            elif cf['_id3_year'] != year:
                warning("Specified and FreeDB year differ (%d vs %d)" %
                        (cf['_id3_year'], year))
        except ValueError:
            warning("DYEAR has to be an integer but it's the string '%s'" %
                    freedb['DYEAR'])
        else:
            if year == 0:
                warning("DYEAR should not be 0 but empty")
    genre = -1
    if 'DGENRE' in freedb:
        try:
            genre = int(freedb['DGENRE'])
        except ValueError:
            if freedb['DGENRE'].upper() in [x.upper() for x in id3genres]:
                genre = [x.upper()
                         for x in id3genres].index(freedb['DGENRE'].upper())
                if cf['_id3_genre'] <= 0:
                    cf['_id3_genre'] = genre
                elif cf['_id3_genre'] != genre:
                    warning("Specified and FreeDB genre differ (%s vs %s)" %
                            (id3genres[cf['_id3_genre']], id3genres[genre]))
        else:
            warning("DGENRE should be a string, not an integer.")
    if 'EXTD' in freedb and 'DYEAR' not in freedb:
        extra_tag_pos = freedb['EXTD'].find("YEAR:")
        if extra_tag_pos >= 0:
            arg = freedb['EXTD'][extra_tag_pos + 5:].lstrip().split()[0]
            if arg.isdigit():
                year = int(arg)
    if genre != -1:
        names[0].extend([year, genre])
    elif year != -1:
        names[0].extend([year])
    if names[0][0] == "(unknown artist)":
        if verb:
            warning(
                "the disc's title must be set to \"artist / title\" (\"DTITLE\").")
        err = 6

    if names[0][0].upper() in ("VARIOUS", "VARIOUS ARTISTS", "SAMPLER", "COMPILATION", "DIVERSE", "V.A.", "VA"):
        if not cf['_various'] and not ['argv', False] in cf['various']['history']:
            cf['_various'] = 1

# user says additional info is in the EXTT fields

    if cf['_various'] and cf['_extt_is_artist']:
        for i in range(tracks_on_cd):
            if freedb['EXTT' + repr(i)]:
                names.append([freedb['EXTT' + repr(i)], freedb['TTITLE' + repr(i)]])
            else:
                err = 8
                if verb:
                    warning("no EXTT info for track %02i." % i)

    elif cf['_various'] and cf['_extt_is_title']:
        for i in range(tracks_on_cd):
            if freedb['EXTT' + repr(i)]:
                names.append([freedb['TTITLE' + repr(i)], freedb['EXTT' + repr(i)]])
            else:
                err = 8
                if verb:
                    warning("no EXTT info for track %02i." % i)

    # we'll try some magic to separate artist and title

    elif cf['_various']:
        found = [[], [], [], [], [], []]
        # lenght=3   2   1 , 3   2   1 (secondary)
        ignore = string.ascii_letters + string.digits
        titles = []
        braces = [['"', '"'], ["'", "'"], ["(", ")"], ["[", "]"], ["{", "}"]]

        # first generate a list of track titles

        for i in range(tracks_on_cd):
            titles.append(freedb['TTITLE' + repr(i)])

        # now try to find a string common to all titles with length 3...1

        for i in (3, 2, 1):
            candidate_found = 0
            for j in range(len(titles[0]) - (i - 1)):

                # choose a possible candidate

                candidate = titles[0][j:j + i]
                illegal_letter = 0
                for k in candidate:
                    if k in ignore:

                        # candidate must not have characters from ignore

                        illegal_letter = 1
                        break
                if illegal_letter:
                    continue
                else:
                    candidate_found = 1

                # if we have a candidate, check that it occurs in all titles

                if candidate_found:
                    all_matched = 1
                    append_as_secondary = 0
                    for l in titles:
                        matches = 0
                        where = 0
                        brace = 0
                        for b in braces:
                            if b[0] in candidate:
                                brace = 1
                                where2 = l.find(candidate) + len(candidate)
                                where = where2
                                while l.find(b[1], where) != -1:
                                    where = l.find(b[1], where) + len(candidate)
                                    matches = matches + 1
                                where = where2
                                if not b[1] in candidate:
                                    while l.find(candidate, where) != -1:
                                        where = l.find(candidate, where) + len(candidate)
                                        matches = matches + 1
                                break   # only treat the first pair of braces
                        if not brace:
                            while l.find(candidate, where) != -1:
                                matches = matches + 1
                                where = l.find(candidate, where) + len(candidate)
                        if matches == 0:    # not found
                            all_matched = 0
                            break
                        elif matches == 1:  # found exactly once
                            pass
                        else:               # found multiple times
                            if cf['_freedb_pedantic']:
                                all_matched = 0
                                break
                            else:
                                append_as_secondary = 1
                                pass
                    if all_matched:
                        if append_as_secondary:
                            found[6 - i].append(candidate)
                        else:
                            found[3 - i].append(candidate)

                # if no candidate has been found, try one with less characters

                else:
                    continue

        tmp = []
        eliminate = [" "]
        for i in found:
            i.sort()        # I'm not sure anymore why/if this is needed
            i.reverse()
            for j in i:
                if j not in eliminate:
                    tmp.append(j)
        found = tmp
        del tmp
        if found:
            # FIXME: when I have time, all candidate should be associated with
            #        a priority. At the moment, fav_seps prefers favorites
            #        over secondary candidates (i.e. candidates occuring multiple
            #        times. EVIL!
            fav_seps = [" - ", " / "]
            sep = ""
            for i in fav_seps:
                if i in found:
                    sep = i
                    break
            if not sep:
                sep = found[0]
            closing_brace = ""
            for j in braces:
                if j[0] in sep:
                    closing_brace = j[1]
                    break
            for i in titles:
                buf = i.split(sep, 1)
                if closing_brace:
                    lenbefore = len(buf[0] + buf[1])
                    buf[0] = buf[0].replace(closing_brace, "")
                    buf[1] = buf[1].replace(closing_brace, "")
                    lenafter = len(buf[0] + buf[1])
                    if lenafter != lenbefore - len(closing_brace):
                        if verb:
                            warning(
                                "brace" + repr(j) + " does not close exactly once.")
                        err = 9

                if cf['_various_swap']:
                    buf = [buf[1], buf[0]]
                names.append(buf)
        else:
            err = 7
            if verb:
                warning("could not separate artist and title in all TTITLEs. Try setting freedb_pedantic = 0 or use --various=no. Maybe additional information is contained in the EXTT fields. check %s and use either --extt-is-artist or --extt-is-title." %
                        cf['_freedb_form_file'])
    else:
        for i in range(tracks_on_cd):
            buf = freedb['TTITLE' + repr(i)]
            names.append(["", buf])

    # append the EXTT fields to the track names
    if cf['_extt_is_comment']:
        for i in range(len(names[1:])):
            if 'EXTT' + repr(i) in freedb and freedb['EXTT' + repr(i)]:
                names[i + 1][1] = names[i + 1][
                    1] + " (%s)" % freedb['EXTT' + repr(i)]
            else:
                print("Warning: track %i (starting at 0) has no EXTT entry." % i)

    locale_names = []
    # clean up a bit and create names for the appropriate locale:
    # FIXME: this for loop doesn't actually change the variable names at all!
    for i in names:
        t = []
        for j in [0, 1]:
            if i[j]:
                i[j] = (i[j]).strip()
                while (i[j]).find("    ") != -1:
                    i[j] = (i[j]).replace("    ", " ")
                while i[j][0] == '"' and i[j][-1] == '"':
                    i[j] = i[j][1:-1]
                while i[j][0] == '"' and (i[j][1:]).find('"') != -1:
                    i[j] = (i[j][1:]).replace('"', '', 1)
            x = i[j]
            t.append(x)
        locale_names.append(t)
    return err, names, locale_names, read_id, revision


def choose_cat(cat=["blues", "classical", "country", "data", "folk", "jazz", "misc", "newage", "reggae", "rock", "soundtrack"]):
    print("choose a category:")
    cat.sort()
    for i in range(0, len(cat)):
        print("%2d" % (i + 1) + ".) " + cat[i])

    x = -1
    while x < 0 or x > len(cat):
        if 'freedb_cat' in jack.progress.status_all and jack.progress.status_all['freedb_cat'][-1] in cat:
            userinput = input(" 0.) none of the above (default='%s'): " %
                              jack.progress.status_all['freedb_cat'][-1])
            if not userinput:
                x = cat.index(jack.progress.status_all['freedb_cat'][-1])
                continue
        else:
            userinput = input(" 0.) none of the above: ")
        try:
            x = int(userinput)
        except ValueError:
            x = -1    # start the loop again

        if not x:
            print("ok, aborting.")
            sys.exit(0)

    return cat[x - 1]


def do_freedb_submit(file, cd_id, cat=None):
    import http.client

    if not cat:
        hello = "hello=" + cf['_username'] + " " + cf[
            '_hostname'] + " " + prog_name + " " + prog_version
        print("Info: querying categories...")
        url = "http://" + freedb_servers[cf['_freedb_server']][
            'host'] + "/~cddb/cddb.cgi?" + urllib.parse.quote_plus("cmd=cddb lscat" + "&" + hello + "&proto=6", "=&")
        f = urllib.request.urlopen(url)
        buf = f.readline().decode(cf['_charset'])
        if buf[0:3] == "500":
            print("Info: LSCAT failed, using builtin categories...")
            cat = choose_cat()

        elif buf[0:3] == "210":
            cat = []
            while 1:
                buf = f.readline().decode(cf['_charset'])
                if not buf:
                    break
                buf = buf.rstrip()
                if buf != ".":
                    cat.append(buf)
            f.close()
            cat = choose_cat(cat)

        else:
            error("LSCAT failed: " + buf.rstrip() + f.read())

    print("OK, using category `" + cat + "'.")
    email = freedb_servers[cf['_freedb_server']]['my_mail']
    print("Your e-mail address is needed to send error messages to you.")
    x = input("enter your e-mail-address [" + email + "]: ")
    if x:
        email = x

    info("Submitting...")
    selector = '/~cddb/submit.cgi'
    proxy = ""
    if 'http_proxy' in os.environ:
        proxy = os.environ['http_proxy']

        def splittype(url):
            import re
            _typeprog = re.compile('^([^/:]+):')
            match = _typeprog.match(url)
            if match:
                    scheme = match.group(1)
                    return scheme, url[len(scheme) + 1:]
            return None, url

        def splithost(url):
            import re
            _hostprog = re.compile('^//([^/]+)(.*)$')
            match = _hostprog.match(url)
            if match:
                return match.group(1, 2)
            return None, url

        type, proxy = splittype(proxy)
        host, selector2 = splithost(proxy)
        h = http.client.HTTPConnection(host)
        h.putrequest('POST', 'http://' + freedb_servers[
                     cf['_freedb_server']]['host'] + selector)
    else:
        h = http.client.HTTPConnection(freedb_servers[cf['_freedb_server']]['host'])
        h.putrequest('POST', '/~cddb/submit.cgi')
    h.putheader('Category', cat)
    h.putheader('Discid', cd_id)
    h.putheader('User-Email', email)
    if cf['_debug']:
        debug(
            "will submit in test-mode, changes are not applied and you'll get an email which contains the data you submitted.")
        h.putheader('Submit-Mode', 'test')
    else:
        h.putheader('Submit-Mode', 'submit')
    h.putheader('Charset', 'UTF-8')
    if cf['_debug']:
        h.putheader(
            'X-Cddbd-Note', 'Submission will not be applied to database if --debug is on.')
    else:
        h.putheader('X-Cddbd-Note', 'data submitted with ' +
                    prog_name + ' (http://jack.sf.net)')
    h.putheader('Content-Length', str(jack.utils.filesize(file)))
    h.endheaders()
    # The user just wrote the file with a text editor so we assume that it
    # is in their locale.
    f = codecs.open(file, "r")
    try:
        text = f.read()
    except UnicodeDecodeError:
        print("The freedb file does not match your current locale. Please convert it")
        print("to " + locale.getpreferredencoding() + " manually.")
        sys.exit(1)
    h.send(text.encode("utf-8"))
    f.close()

    print()

    response = h.getresponse()
    err = response.status
    msg = response.reason
    headers = response.getheaders()
    buf = response.read()

    # lets see if it worked:
    if err == 404:
        print("This server doesn't seem to support database submission via http.")
        print("consider submitting via mail (" + progname + " -m). full error:\n")
    print(err, msg)


def do_freedb_mailsubmit(file, cd_id, cat=None):
    warning(
        "Support for freedb submission via e-mail may be dropped in future versions. Please begin to use HTTP to submit your entries (--submit)")
    sendmail = '/usr/lib/sendmail -t'
    # sendmail = 'cat > /tmp/jack.test.mailsubmit'
    if not cat:
        cat = choose_cat()
    print("OK, using `" + cat + "'.")
    if (freedb_servers[cf['_freedb_server']]['my_mail']).find("@") >= 1 and len(freedb_servers[cf['_freedb_server']]['my_mail']) > 3:
        return os.system("( echo 'To: " + freedb_servers[cf['_freedb_server']]['mail'] + "'; echo From: '" + freedb_servers[cf['_freedb_server']]['my_mail'] + "'; echo 'Subject: cddb " + cat + " " + cd_id + "' ; cat '" + file + "' ) | " + sendmail)
    else:
        print("please set your e-mail address. aborting...")


def update_revision(file):
    "Update the revision (and submitted-via) information in a FreeDB template"

    re_revision = re.compile(r"^#\s*Revision:\s*(\d+)")
    re_agent = re.compile(r"^#\s*Submitted via:")

    tmp, tmpname = tempfile.mkstemp()
    freedb_file = open(file, "r")
    revision = 0
    comments = 1
    for line in freedb_file.readlines():
        rev = re_revision.match(line)
        agent = re_agent.match(line)
        if rev:
            revision = int(rev.group(1)) + 1
            os.write(tmp, "# Revision: %d\n" % revision)
        elif agent:
            os.write(tmp, "# Submitted via: " +
                     prog_name + " " + prog_version + "\n")
        else:
            if not line.startswith("#"):
                # The 'Revisions' field is option but should be set when you
                # submit a new version.  Therefore, after the comments check
                # whether we've seen a revision and if not write one.
                if comments:
                    if revision == 0:
                        revision += 1
                        os.write(tmp, "# Revision: %d\n" % revision)
                    comments = 0
            os.write(tmp, line)
    os.close(tmp)
    freedb_file.close()
    try:
        shutil.copyfile(tmpname, file)
    except IOError:
        print("Cannot copy updated template over existing one.")
    try:
        os.unlink(tmpname)
    except IOError:
        print("Cannot remove temporary file %s." % tmpname)
