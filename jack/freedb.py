# jack.metadata: metadata server for use in
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
import re

import jack.functions
import jack.progress
import jack.utils
import jack.tag
import jack.misc
import jack.version

from jack.globals import *

NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME = list(range(9))
freedb_inexact_match = -1

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


def freedb_split(field, s, max=78):
    "split a field into multiple lines of 78 char max."
    x = ""
    s = field + "=" + s
    while len(s) > max:
        x = x + s[:max] + "\n"
        s = field + "=" + s[max:]
    return x + s + "\n"


def freedb_template(tracks, names=""):
    "generate a freedb submission template"
    form_file = jack.metadata.get_metadata_form_file(jack.metadata.get_metadata_api(cf['_metadata_server']))
    if os.path.exists(form_file):
        os.rename(form_file, form_file + ".bak")
    f = open(form_file, "w")
    f.write("# xmcd CD database file\n#\n# Track frame offsets:\n")
    for i in tracks:
        f.write("#       " + repr(i[START] + MSF_OFFSET) + "\n")
    f.write("#\n# Disc length: " + repr((MSF_OFFSET + tracks[-1][START] + tracks[-1][LEN]) // CDDA_BLOCKS_PER_SECOND))
    f.write(" seconds\n#\n# Revision: 0\n")
    f.write("# Submitted via: " + jack.version.name + " " + jack.version.version + "\n#\n")
    f.write("DISCID=" + jack.metadata.metadata_id(tracks)['cddb'] + "\n")
    if names:
        if names[1][0]:  # various
            if "VARIOUS" in names[0][0].upper():
                f.write(freedb_split("DTITLE", "Various / " + names[0][1]))
            else:
                f.write(freedb_split("DTITLE", "Various / " + names[0][0] + " - " + names[0][1]))
        else:
            f.write(freedb_split("DTITLE", names[0][0] + " / " + names[0][1]))
    else:
        f.write("DTITLE=\n")
    freedb_year, freedb_genre = -1, None
    if cf['_genre']:
        freedb_genre = cf['_genre']
    elif names and len(names[0]) == 4:
        freedb_genre = names[0][3]
    if cf['_year']:
        freedb_year = cf['_year']
    elif names and len(names[0]) == 4:
        freedb_year = names[0][2]
    if freedb_year:
        f.write("DYEAR=%s\n" % freedb_year)
    else:
        f.write("DYEAR=\n")
    if freedb_genre:
        f.write("DGENRE=%s\n" % freedb_genre)
    else:
        f.write("DGENRE=\n")
    for i in tracks:
        if names:
            if names[i[NUM]][0]:  # various
                f.write(freedb_split("TTITLE" + repr(i[NUM] - 1), names[i[NUM]][0] + " - " + names[i[NUM]][1]))
            else:
                f.write(freedb_split("TTITLE" + repr(i[NUM] - 1), names[i[NUM]][1]))
        else:
            f.write("TTITLE" + repr(i[NUM] - 1) + "=\n")
    f.write("EXTD=\n")
    for i in tracks:
        f.write("EXTT" + repr(i[NUM] - 1) + "=\n")
    f.write("PLAYORDER=\n")


def freedb_query(cd_ids, tracks, file):
    if cf['_freedb_dir']:
        if local_freedb(cd_ids['cddb'], cf['_freedb_dir'], file) == 0:  # use local database (if any)
            return 0

    qs = "cmd=cddb query " + cd_ids['cddb'] + " " + repr(len(tracks)) + " "  # query string
    for i in tracks:
        qs = qs + repr(i[START] + MSF_OFFSET) + " "
    qs = qs + repr((MSF_OFFSET + tracks[-1][START] + tracks[-1][LEN]) // CDDA_BLOCKS_PER_SECOND)
    hello = "hello=" + cf['_username'] + " " + cf['_hostname'] + " " + jack.metadata.metadata_servers[cf['_metadata_server']]['id']
    qs = urllib.parse.quote_plus(qs + "&" + hello + "&proto=6", "=&")
    url = "http://" + jack.metadata.metadata_servers[cf['_metadata_server']]['host'] + "/~cddb/cddb.cgi?" + qs
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
            cd_ids['cddb'] = buf[1]
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
                warning(buf + f.read().decode(cf['_charset']) + " --don't know what to do, aborting query.")
                err = 1
                return err
            else:
                error(buf + f.read().decode(cf['_charset']) + " --don't know what to do, aborting query.")

        cmd = "cmd=cddb read " + freedb_cat + " " + cd_ids['cddb']
        url = "http://" + jack.metadata.metadata_servers[cf['_metadata_server']]['host'] + "/~cddb/cddb.cgi?" + urllib.parse.quote_plus(cmd + "&" + hello + "&proto=6", "=&")
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


def freedb_names(cd_ids, tracks, todo, name, verb=0, warn=1):
    "returns err, [(artist, albumname), (track_01-artist, track_01-name), ...], cd_ids, mb_query_data"
    err = 0
    tracks_on_cd = tracks[-1][NUM]
    freedb = {}
    f = open(name, "rb")  # first the freedb info is read in...
    while 1:
        bline = f.readline()
        if not bline:
            break
        try:
            line = bline.decode("utf-8")
        except:
            try:
                line = bline.decode("latin1")
            except:
                print(bline)
                error("could not decode above line")
        line = line.replace("\n", "")
        # cannot use rstrip, we need trailing spaces
        line = line.replace("\r", "")
        # I consider "\r"s as bugs in db info
        for i in ["DISCID", "DTITLE", "DYEAR", "DGENRE", "TTITLE", "EXTD", "EXTT", "PLAYORDER"]:
            if jack.functions.starts_with(line, i):
                buf = line
                if "=" in buf:
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
                warning("no freedb info for track %02i (\"TTITLE%i\")" % (i[NUM], i[NUM] - 1))
            freedb["TTITLE%i" % (i[NUM] - 1)] = "[not set]"

    for i in list(freedb.keys()):  # check that there is no extra info
        if i[0:6] == "TTITLE":
            if int(i[6:]) > tracks_on_cd - 1:
                err = 2
                if verb:
                    warning("extra freedb info for track %02i (\"%s\"), cd has only %02i tracks." % (int(i[6:]) + 1, i, tracks_on_cd))

    if "DTITLE" not in freedb:
        err = 3
        if verb:
            warning("freedb entry doesn't contain disc title info (\"DTITLE\").")
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
            if i == cd_ids['cddb']:
                id_matched = 1
        if not id_matched and warn and freedb_inexact_match < 1:
            print("Warning: CD signature ID and ID from FreeDB file do not match.")
            print("         CD signature: " + cd_ids['cddb'])
            print("         FreeDB ID:    " + ",".join(read_ids))
        for i in read_ids:
            for j in i:
                if j not in "0123456789abcdef":
                    if verb:
                        warning("the disc's id is not 8-digit hex (\"DISCID\").")
                    err = 5
            if len(i) != 8:
                if verb:
                    warning("the disc's id is not 8-digit hex (\"DISCID\").")
                err = 5

    dtitle = freedb['DTITLE']
    dtitle = dtitle.replace(" / ", "/")    # kill superflous slashes
    dtitle = dtitle.replace("/ ", "/")
    dtitle = dtitle.replace(" /", "/")
    dtitle = dtitle.replace("(unknown disc title)", "(unknown artist)/(unknown disc title)")  # yukk!
    if not dtitle:
        dtitle = "(unknown artist)/(unknown disc title)"
    if not "/" in dtitle:
        if cf['_various'] == 1:
            dtitle = "Various/" + dtitle
            warning("bad disc title, using %s. Please fix." % dtitle)
        else:
            dtitle = "(unknown artist)/" + dtitle

    album_artist, album_title = dtitle.split("/", 1)
    album_artist = album_artist.strip()
    album_title = album_title.strip()
    year = None
    genre = None
    if 'DYEAR' in freedb:
        year = freedb['DYEAR']
        if cf['_year'] == None:
            cf['_year'] = year
        elif cf['_year'] != year:
            warning("Specified and FreeDB year differ (%d vs %d)" % (cf['_year'], year))
    if 'DGENRE' in freedb:
        genre = freedb['DGENRE'].strip()

    # extract disc number from album title
    album_title, medium_position, medium_count, medium_title = jack.metadata.split_albumtitle(album_title)

    names = []
    names.append([album_artist, album_title, year, genre, medium_position, medium_count, medium_title])

    if names[0][0] == "(unknown artist)":
        if verb:
            warning("the disc's title must be set to \"artist / title\" (\"DTITLE\").")
        err = 6

    if names[0][0].upper() in ("VARIOUS", "VARIOUS ARTISTS", "SAMPLER", "COMPILATION", "DIVERSE", "V.A.", "VA"):
        if not cf['_various'] and not ['argv', False] in cf['various']['history']:
            cf['_various'] = 1

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
                            warning("brace" + repr(j) + " does not close exactly once.")
                        err = 9

                if cf['_various_swap']:
                    buf = [buf[1], buf[0]]
                buf[0] = buf[0].strip()
                buf[1] = buf[1].strip()
                names.append(buf)
        else:
            err = 7
            if verb:
                warning("could not separate artist and title in all TTITLEs. Try setting freedb_pedantic = 0 or use --various=no. Maybe additional information is contained in the EXTT fields. check %s and use either --extt-is-artist or --extt-is-title." % jack.metadata.get_metadata_form_file("cddb"))
    else:
        for i in range(tracks_on_cd):
            buf = freedb['TTITLE' + repr(i)]
            names.append(["", buf.strip()])

    # append the EXTT fields to the track names
    if cf['_extt_is_comment']:
        for i in range(len(names[1:])):
            if 'EXTT' + repr(i) in freedb and freedb['EXTT' + repr(i)]:
                names[i + 1][1] = names[i + 1][1] + " (%s)" % freedb['EXTT' + repr(i)]
            else:
                print("Warning: track %i (starting at 0) has no EXTT entry." % i)

    return err, names, read_id, None
