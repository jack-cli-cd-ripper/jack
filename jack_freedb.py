### jack_freedb: freedb server for use in
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2003  Arne Zellentin <zarne@users.sf.net>

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; either version 2 of the License, or
### (at your option) any later version.

### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.

### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import urllib2, urllib
import string
import sys
import os

import jack_playorder
import jack_functions
import jack_progress
import jack_utils

from jack_version import prog_version, prog_name
from jack_globals import *

names_available = None          # freedb info is available
dir_created = None              # dirs are only renamed if we have created them
NUM, LEN, START, COPY, PRE, CH, RIP, RATE, NAME = range(9)

freedb_servers = {
    'freedb': {
        'host': "freedb.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
    },
    'freedb-de': {
        'host': "de.freedb.org",
        'id': prog_name + " " + prog_version,
        'mail': "freedb-submit@freedb.org",
        'my_mail': "default"
        },
    'cddb': {
        'host': "cddb.cddb.com",
        'id': "xmcd 2.6",
        'submit_mail': "freedb-submit@freedb.org",
        'my_mail': "default"
        },
    }

def interpret_db_file(all_tracks, freedb_form_file, verb, dirs = 0, warn = None):
    "read freedb file and rename dir(s)"
    global names_available, dir_created
    freedb_rename = 0
    if warn == None:
        err, track_names, cd_id, revision = freedb_names(freedb_id(all_tracks), all_tracks, freedb_form_file, verb = verb)
    else:
        err, track_names, cd_id, revision = freedb_names(freedb_id(all_tracks), all_tracks, freedb_form_file, verb = verb, warn = warn)
    if (not err) and dirs:
        freedb_rename = 1

# The user wants us to use the current dir, unconditionally.

        if cf['_claim_dir']:
            dir_created = jack_utils.split_dirname(os.getcwd())[-1]
            jack_functions.progress("all", "mkdir", dir_created)
            cf['_claim_dir'] = 0

        if cf['_rename_dir'] and dir_created:
            new_dirs, new_dir = jack_utils.mkdirname(track_names, cf['_dir_template'])
            old_dir = os.getcwd()
            old_dirs = jack_utils.split_dirname(old_dir)
            dirs_created = jack_utils.split_dirname(dir_created)

# only do the following if we are where we think we are and the dir has to be
# renamed.

            if jack_utils.check_path(dirs_created, old_dirs) and not jack_utils.check_path(dirs_created, new_dirs):
                jack_utils.rename_path(dirs_created, new_dirs)
                print "Info: cwd now", os.getcwd()
                jack_functions.progress("all", 'ren', dir_created + "-->" + new_dir)
    if not err:
        names_available = 1
    else:
        freedb_rename = 0
    return err, track_names, freedb_rename, revision
#/ end of interpret_db_file /#

def local_freedb(cd_id, freedb_dir, outfile = "/tmp/testfilefreedb"):
    "Use file from local freedb directory"
    # Moritz Moeller-Herrmann kindly provided this functionality.
    if not os.path.isdir(freedb_dir):
        error("freedb directory not found")
    if not os.access(freedb_dir, 5):
        error("freedb directory access not permitted")
    cat=[freedb_dir] # category listing
    for entry in os.listdir(freedb_dir):
        if os.path.isdir(os.path.join(freedb_dir, entry)):
            cat.append(os.path.join(freedb_dir, entry))
    for musicdir in cat:
        for m in os.listdir(musicdir):
            if m == cd_id:
                idfile = os.path.join(musicdir, cd_id)
                inf = open (idfile, "r")
                outf = open (outfile, "w")
                buf = inf.readline()
                while buf:
                    buf = string.replace(buf, "\n", "")    # we need trailing spaces
                    if buf != ".":
                        outf.write(buf + "\n")
                    buf = inf.readline()
                inf.close()
                outf.close()
                return 0
    print "No local matching freedb entry found"
    return 1

def freedb_sum(n):
    "belongs to freedb_id"
    ret = 0
    while n > 0:
        ret = ret + (n % 10)
        n = n / 10
    return ret

def freedb_id(tracks, warn=0):
    from jack_globals import START, MSF_OFFSET, CDDA_BLOCKS_PER_SECOND
    "calculate freedb (aka CDDB) disc-id"
    cdtoc = []
    if not tracks:
        if warn:
            warning("no tracks! No disc inserted? No/wrong ripper?")
        return 0
    for i in tracks:
        cdtoc.append(jack_functions.blockstomsf(i[START] + MSF_OFFSET))
    cdtoc.append(jack_functions.blockstomsf(tracks[-1][START] + tracks[-1][LEN]))

    n = t = 0
    for i in tracks:
        n = n + freedb_sum((i[START] + MSF_OFFSET) / CDDA_BLOCKS_PER_SECOND)
    t = (tracks[-1][START] + tracks[-1][LEN]) / CDDA_BLOCKS_PER_SECOND - tracks[0][START] / CDDA_BLOCKS_PER_SECOND

    return "%08x" % ((n % 0xff << long(24)) | (t << 8) | (len(tracks)))

def freedb_split(field, s, max = 78):
    "split a field into multiple lines of 78 char max."
    x = ""
    s = field + "=" + s
    while len(s) > max:
        x = x + s[:max] + "\n"
        s = field + "=" + s[max:]
    return x + s + "\n"

def freedb_template(tracks, names = "", revision = 0):
    "generate a freedb submission template"
    if os.path.exists(cf['_freedb_form_file']):
        os.rename(cf['_freedb_form_file'], cf['_freedb_form_file'] + ".bak")
    f = open(cf['_freedb_form_file'], "w")
    f.write("# xmcd CD database file\n#\n# Track frame offsets:\n")
    for i in tracks:
        f.write("#       " + `i[START] + MSF_OFFSET` + "\n")
    f.write("#\n# Disc length: " + `(MSF_OFFSET + tracks[-1][START] + tracks[-1][LEN]) / CDDA_BLOCKS_PER_SECOND`)
    f.write(" seconds\n#\n# Revision: %i\n" % revision)
    f.write("# Submitted via: " + prog_name + " " + prog_version + "\n#\n")
    f.write("DISCID=" + freedb_id(tracks) + "\n")
    if names:
        if names[1][0]: # various
            if string.find(string.upper(names[0][0]), "VARIOUS") >= 0:
                f.write(freedb_split("DTITLE", "Various / " + names[0][1]))
            else:
                f.write(freedb_split("DTITLE", "Various / " + names[0][0] + " - " + names[0][1]))
        else:
            f.write(freedb_split("DTITLE", names[0][0] + " / " + names[0][1]))
    else:
        f.write("DTITLE=\n")
    for i in tracks:
        if names:
            if names[i[NUM]][0]: # various
                f.write(
                        freedb_split("TTITLE" + `i[NUM]-1`,
                                     names[i[NUM]][0] +
                                     " - " +
                                     names[i[NUM]][1]
                                    )
                       )
            else:
                f.write(freedb_split("TTITLE" + `i[NUM]-1`, names[i[NUM]][1]))
        else:
            f.write("TTITLE" + `i[NUM]-1` + "=\n")
    freedb_year, freedb_id3genre = -1, -1
    if cf['_id3_genre'] >= 0 and cf['_id3_genre'] < len(id3genres) or cf['_id3_genre'] == 255:
        freedb_id3genre = cf['_id3_genre']
    elif names and len(names[0]) == 4:
        freedb_id3genre = names[0][3]
    if cf['_id3_year'] >= 0:
        freedb_year = cf['_id3_year']
    elif names and len(names[0]) == 4:
        freedb_year = names[0][2]
    if freedb_year >= 0 or freedb_id3genre >= 0:
        f.write("EXTD=\\nYEAR: %4s  ID3G: %3s\n" % (freedb_year, freedb_id3genre))
    else:
        f.write("EXTD=\n")
    for i in tracks:
        f.write("EXTT" + `i[NUM]-1` + "=\n")
    f.write("PLAYORDER=\n")

def freedb_query(cd_id, tracks, file):
    if cf['_freedb_dir']:
        if local_freedb(cd_id, cf['_freedb_dir'], file)==0: # use local database (if any)
            return 0

    qs = "cmd=cddb query " + cd_id + " " + `len(tracks)` + " " # query string
    for i in tracks:
        qs = qs + `i[START] + MSF_OFFSET` + " "
    qs = qs + `(MSF_OFFSET + tracks[-1][START] + tracks[-1][LEN]) / CDDA_BLOCKS_PER_SECOND`
    hello = "hello=" + cf['_username'] + " " + cf['_hostname'] + " " + freedb_servers[cf['_freedb_server']]['id']
    qs = urllib.quote_plus(qs + "&" + hello + "&proto=3", "=&")
    url = "http://" + freedb_servers[cf['_freedb_server']]['host'] + "/~cddb/cddb.cgi?" + qs
    if cf['_cont_failed_query']:
        try:
            f = urllib2.urlopen(url)
        except IOError:
            traceback.print_exc()
            err = 1
            return err
    else:
        f = urllib2.urlopen(url)
    buf = f.readline()
    if buf and buf[0:1] == "2":
        if buf[0:3] == "211": # Found inexact matches, list follows
            print "Found inexact matches choose one:"
            num = 1
            matches = []
            while 1:
                buf = f.readline()
                if not buf:
                    break
                buf = string.rstrip(buf)
                if buf != ".":
                    print "%2i" % num + ".) " + buf
                    matches.append(buf)
                    num = num + 1
            x = -1
            while x < 0 or x > num - 1:
                input = raw_input(" 0.) none of the above: ")
                if not input:
                    continue
                try:
                    x = int(input)
                except ValueError:
                    x = -1    # start the loop again
                if not x:
                    print "ok, aborting."
                    sys.exit()
 
            buf = matches[x-1]
            buf = string.split(buf, " ", 2)
            freedb_cat = buf[0]
            cd_id = buf[1]
            err = 0
 
        elif buf[0:3] == "200":
            buf = string.split(buf)
            freedb_cat = buf[1]
        elif buf[0:3] == "202":
            if cf['_cont_failed_query']:
                warning(buf + f.read() + " --how about trying another --server?")
                err = 1
                return err
            else:
                error(buf + f.read() + " --how about trying another --server?")
        else:
            if cf['_cont_failed_query']:
                warning(buf + f.read() + " --don't know what to do, aborting query.")
                err = 1
                return err
            else:
                error(buf + f.read() + " --don't know what to do, aborting query.")
 
        cmd = "cmd=cddb read " + freedb_cat + " " + cd_id
        url = "http://" + freedb_servers[cf['_freedb_server']]['host'] + "/~cddb/cddb.cgi?" + urllib.quote_plus(cmd + "&" + hello + "&proto=3", "=&")
        f = urllib2.urlopen(url)
        buf = f.readline()
        if buf and buf[0:3] == "210": # entry follows
            if os.path.exists(file):
                os.rename(file, file + ".bak")
            of = open(file, "w")
            buf = f.readline()
            while buf:
                buf = string.rstrip(buf)
                if buf != ".":
                    of.write(buf + "\n")
                buf = f.readline()
            of.close()
            jack_functions.progress("all", "freedb_cat", freedb_cat)
            jack_progress.status_all['freedb_cat'] = freedb_cat
            err = 0
        else:
            print string.rstrip(buf)
            print f.read()
            warning("could not query freedb entry")
            err = 1
        f.close()
    else:
        print string.rstrip(buf)
        print f.read()
        warning("could not check freedb category")
        err = 2
    f.close()
    return err

def freedb_names(cd_id, tracks, name, verb = 0, warn = 1):
    "returns err, [(artist, albumname), (track_01-artist, track_01-name), ...], cd_id, revision"
    err = 0
    tracks_on_cd = tracks[-1][NUM]
    freedb = {}
    f = open(name, "r") # first the freedb info is read in...
    while 1:
        line = f.readline()
        if not line:
            break
        line = string.replace(line, "\n", "")  # cannot use rstrip, we need trailing
                                        # spaces
        line = string.replace(line, "\r", "")  # I consider "\r"s as bugs in db info
        if jack_functions.starts_with(line, "# Revision:"):
            revision = int(line[11:])
        for i in ["DISCID", "DTITLE", "TTITLE", "EXTD", "EXTT", "PLAYORDER"]:
            if jack_functions.starts_with(line, i):
                buf = line
                if string.find(buf, "=") != -1:
                    buf = string.split(buf, "=", 1)
                    if buf[1]:
                        if freedb.has_key(buf[0]):
                            if buf[0] == "DISCID":
                                freedb[buf[0]] = freedb[buf[0]] + ',' + buf[1]
                            else:
                                freedb[buf[0]] = freedb[buf[0]] + buf[1]
                        else:
                            freedb[buf[0]] = buf[1]
                continue
 
    for i in tracks:    # check that info is there for all tracks
        if not freedb.has_key("TTITLE%i" % (i[NUM] - 1)):   # -1 because freedb starts at 0
            err = 1
            if verb:
                warning("no freedb info for track %02i (\"TTITLE%i\")" % (i[NUM], i[NUM] - 1))
            freedb["TTITLE%i" % (i[NUM] - 1)] = "[not set]"
 
    for i in freedb.keys():# check that there is no extra info
        if i[0:6] == "TTITLE":
            if int(i[6:]) > tracks_on_cd - 1:
                err = 2
                if verb:
                    warning("extra freedb info for track %02i (\"%s\"), cd has only %02i tracks." % (int(i[6:]) + 1, i, tracks_on_cd))
 
    if not freedb.has_key("DTITLE"):
        err = 3
        if verb:
            warning("freedb entry doesn't contain disc title info (\"DTITLE\").")
        freedb['DTITLE'] = "[not set]"
 
    if not freedb.has_key("DISCID"):
        err = 4
        if verb:
            warning("freedb entry doesn't contain disc id info (\"DISCID\").")
        read_id = "00000000"
    else:
        read_id = freedb['DISCID']
        read_ids = string.split(freedb['DISCID'], ",")
        id_matched = 0
        for i in read_ids:
            if i == cd_id:
                id_matched = 1
        if not id_matched and warn:
            print "Warning: calculated id (" + cd_id + ") and id from freedb file"
            print "       :", read_ids
            print "       : do not match, hopefully due to inexact match."
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

    if freedb.has_key('PLAYORDER'):
        jack_playorder.order = freedb('PLAYORDER')
 
    dtitle = freedb['DTITLE']
    dtitle = string.replace(dtitle, " / ", "/")    # kill superflous slashes
    dtitle = string.replace(dtitle, "/ ", "/")
    dtitle = string.replace(dtitle, " /", "/")
    dtitle = string.replace(dtitle, "(unknown disc title)", "(unknown artist)/(unknown disc title)") # yukk!
    if not dtitle:
        dtitle = "(unknown artist)/(unknown disc title)"
    if string.find(dtitle,"/") == -1:
        if cf['_various'] == 1:
            dtitle = "Various/" + dtitle
            warning("bad disc title, using %s. Please fix and submit." % dtitle)
        else:
            dtitle = "(unknown artist)/" + dtitle

    names = [string.split(dtitle,"/",1)]
    if freedb.has_key('EXTD'):
        extra_tag_pos = string.find(freedb['EXTD'], "\\nYEAR:")
        if extra_tag_pos >= 0:
            try:
                extd_info = freedb['EXTD'][extra_tag_pos + 7:]
                extd_year, extd_id3g = string.split(extd_info, "ID3G:", 1)
                extd_year, extd_id3g = int(extd_year), int(extd_id3g)
            except:
                print "can't handle '%s'." % freedb['EXTD']
            else:
                names = [string.split(dtitle, "/", 1)]
                names[0].extend([extd_year, extd_id3g])
    if names[0][0] == "(unknown artist)":
        if verb:
            warning("the disc's title must be set to \"artist / title\" (\"DTITLE\").")
        err = 6
 
    if string.upper(names[0][0]) in ("VARIOUS", "VARIOUS ARTISTS", "SAMPLER", "COMPILATION", "DIVERSE", "V.A.", "VA"):
        #XXX
        if not cf['_various']:
            cf['_various'] = 1
        elif cf['_various'] == 2:
            cf['_various'] = 0
 
# user says additional info is in the EXTT fields
 
    if cf['_various'] and cf['_extt_is_artist']:
        for i in range(tracks_on_cd):
            if freedb['EXTT'+`i`]:
                names.append([freedb['EXTT'+`i`], freedb['TTITLE'+`i`]])
            else:
                err = 8
                if verb:
                    warning("no EXTT info for track %02i." % i)
 
    elif cf['_various'] and cf['_extt_is_title']:
        for i in range(tracks_on_cd):
            if freedb['EXTT'+`i`]:
                names.append([freedb['TTITLE'+`i`], freedb['EXTT'+`i`]])
            else:
                err = 8
                if verb:
                    warning("no EXTT info for track %02i." % i)
 
# we'll try some magic to separate artist and title
 
    elif cf['_various']:
        found = [[], [], [], [], [], []]
        # lenght=3   2   1 , 3   2   1 (secondary)
        ignore = string.letters + string.digits
        titles = []
        braces = [['"', '"'], ["'", "'"], ["(", ")"], ["[", "]"], ["{", "}"]]
 
# first generate a list of track titles
 
        for i in range(tracks_on_cd):
            titles.append(freedb['TTITLE'+`i`])
 
# now try to find a string common to all titles with length 3...1
 
        for i in (3,2,1):
            candidate_found = 0
            for j in range(len(titles[0])-(i-1)):
 
# choose a possible candidate
 
                candidate = titles[0][j:j+i]
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
                                where2 = string.find(l, candidate) + len(candidate)
                                where = where2
                                while string.find(l, b[1], where) != -1:
                                    where = string.find(l, b[1], where) + len(candidate)
                                    matches = matches + 1
                                where = where2
                                if not b[1] in candidate:
                                    while string.find(l, candidate, where) != -1:
                                        where = string.find(l, candidate, where) + len(candidate)
                                        matches = matches + 1
                                break   # only treat the first pair of braces
                        if not brace:
                            while string.find(l, candidate, where) != -1:
                                matches = matches + 1
                                where = string.find(l, candidate, where) + len(candidate)
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
                            found[6-i].append(candidate)
                        else:
                            found[3-i].append(candidate)
 
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
                buf = string.split(i, sep, 1)
                if closing_brace:
                    lenbefore = len(buf[0] + buf[1])
                    buf[0] = string.replace(buf[0], closing_brace, "")
                    buf[1] = string.replace(buf[1], closing_brace, "")
                    lenafter = len(buf[0] + buf[1])
                    if lenafter != lenbefore - len(closing_brace):
                        if verb:
                            warning("brace" + `j` + " does not close exactly once.")
                        err = 9
                        
                if cf['_various_swap']:
                    buf = [buf[1], buf[0]]
                names.append(buf)
        else:
            err = 7
            if verb:
                warning("could not separate artist and title in all TTITLEs. Try setting freedb_pedantic = 0 or use --no-various Maybe additional information is contained in the EXTT fields. check %s and use either --extt-is-artist or --extt-is-title." % cf['_freedb_form_file'])
    else:
        for i in range(tracks_on_cd):
            buf = freedb['TTITLE'+`i`]
            names.append(["", buf])
 
    # append the EXTT fields to the track names
    if cf['_extt_is_comment']:
        for i in range(len(names[1:])):
            if freedb.has_key('EXTT'+`i`) and freedb['EXTT'+`i`]:
                names[i+1][1] = names[i+1][1] + " (%s)" % freedb['EXTT'+`i`]
            else:
                print "Warning: track %i (starting at 0) has no EXTT entry." % i
 
    # clean up a bit:
    for i in names:
        for j in [0, 1]:
            if i[j]:
                i[j] = string.strip(i[j])
                while string.find(i[j], "    ") != -1:
                    i[j] = string.replace(i[j], "    ", " ")
                while i[j][0] == '"' and i[j][-1] == '"':
                    i[j] = i[j][1:-1]
                while i[j][0] == '"' and string.find(i[j][1:], '"') != -1:
                    i[j] = string.replace(i[j][1:], '"', '', 1)
    return err, names, read_id, revision

def choose_cat(cat = ["blues", "classical", "country", "data", "folk", "jazz", "misc", "newage", "reggae", "rock", "soundtrack"]):
    print "choose a category:"
    cat.sort()
    for i in range(1, len(cat)):
        print "%2d" % i + ".) " + cat[i]

    x = -1
    while x < 0 or x > len(cat) - 1:
        if jack_progress.status_all.has_key('freedb_cat') and jack_progress.status_all['freedb_cat'][-1] in cat:
            input = raw_input(" 0.) none of the above (default='%s'): " % jack_progress.status_all['freedb_cat'][-1])
            if not input:
                x = cat.index(jack_progress.status_all['freedb_cat'][-1])
                continue
        else:
            input = raw_input(" 0.) none of the above: ")
        try:
            x = int(input)
        except ValueError:
            x = -1    # start the loop again

        if not x:
            print "ok, aborting."
            sys.exit(0)

    return cat[x]

def do_freedb_submit(file, cd_id):
    import httplib
    hello = "hello=" + cf['_username'] + " " + cf['_hostname'] + " " + prog_name + " " + prog_version
    print "Info: querying categories..."
    url = "http://" + freedb_servers[cf['_freedb_server']]['host'] + "/~cddb/cddb.cgi?" + urllib.quote_plus("cmd=cddb lscat" + "&" + hello + "&proto=3", "=&")
    f = urllib2.urlopen(url)
    buf = f.readline()
    if buf[0:3] == "500":
        print "Info: LSCAT failed, using builtin categories..."
        cat = choose_cat()

    elif buf[0:3] == "210":
        cat = ["null", ]
        while 1:
            buf = f.readline()
            if not buf:
                break
            buf = string.rstrip(buf)
            if buf != ".":
                cat.append(buf)
        f.close()
        cat = choose_cat(cat)

    else:
        error("LSCAT failed: " + string.rstrip(buf) + f.read())

    print "OK, using `" + cat + "'."
    email = freedb_servers[cf['_freedb_server']]['my_mail']
    print "Your e-mail address is needed to send error messages to you."
    x = raw_input("enter your e-mail-address [" + email + "]: ")
    if x:
        email = x

    sys.stdout.write("Submitting...") ; sys.stdout.flush()

    selector = '/~cddb/submit.cgi'
    proxy = ""
    if os.environ.has_key('http_proxy'):
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
            if match: return match.group(1, 2)
            return None, url

        type, proxy = splittype(proxy)
        host, selector2 = splithost(proxy)
        h = httplib.HTTP(host)
        h.putrequest('POST', 'http://' + freedb_servers[cf['_freedb_server']]['host'] + selector)
    else:
        h = httplib.HTTP(freedb_servers[cf['_freedb_server']]['host'])
        h.putrequest('POST', '/~cddb/submit.cgi')
    h.putheader('Category', cat)
    h.putheader('Discid', cd_id)
    h.putheader('User-Email', email)
    #h.putheader('Submit-Mode', 'test')
    h.putheader('Submit-Mode', 'submit')
    h.putheader('Charset', 'ISO-8859-1')
    h.putheader('X-Cddbd-Note', 'Problems submitting with ' + prog_name + '? Visit jack.sf.net.')
    h.putheader('Content-Length', str(jack_utils.filesize(file)))
    h.endheaders()
    f = open(file, "r")
    h.send(f.read())
    f.close()

    print

    err, msg, headers = h.getreply()
    f = h.getfile()
    if proxy:
        if err != 200:
            error("proxy: " + `err` + " " + msg + f.read())
        else:
            buf = f.readline()
            err, msg = buf[0:3], buf[4:]
            
    # lets see if it worked:
    if err == 404:
        print "This server doesn't seem to support database submission via http."
        print "consider submitting via mail (" + progname + " -m). full error:\n"
    print err, msg

def do_freedb_mailsubmit(file, cd_id):
    warning("Support for freedb submission via e-mail may be dropped in future versions. Please begin to use HTTP to submit your entries (--submit)")
    sendmail = '/usr/lib/sendmail -t'
    #sendmail = 'cat > /tmp/jack.test.mailsubmit'
    cat = choose_cat()
    print "OK, using `" + cat + "'."
    if string.find(freedb_servers[cf['_freedb_server']]['my_mail'], "@") >= 1 and len(freedb_servers[cf['_freedb_server']]['my_mail']) > 3:
        return os.system("( echo 'To: " + freedb_servers[cf['_freedb_server']]['mail'] + "'; echo From: '" + freedb_servers[cf['_freedb_server']]['my_mail'] + "'; echo 'Subject: cddb " + cat + " " + cd_id + "' ; cat '" + file + "' ) | " + sendmail)
    else:
        print "please set your e-mail address. aborting..."

