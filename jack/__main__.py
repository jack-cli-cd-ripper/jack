#!/usr/bin/python
### jack - extract audio from a CD and encode it using 3rd party software
### Copyright (C) 1999-2004  Arne Zellentin <zarne@users.sf.net>

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

### If you want to comment on this program, contact me: zarne@users.sf.net ###
### Visit the homepage: http://www.home.unix-ag.org/arne/jack/

### see CHANGELOG for recent changes in this program
### see TODO if you want to see what needs to be implemented

import os
import sys
import time
import wave
import types
import posix
import string
import select
import signal
import pprint
import traceback
import locale

from jack.globals import *

import jack.version
import jack.misc
import jack.mp3
import jack.argv
import jack.rc
import jack.helpers
import jack.targets
import jack.metadata
import jack.display
import jack.term
import jack.children
import jack.tag
import jack.workers
import jack.utils
import jack.ripstuff
import jack.encstuff
import jack.checkopts
import jack.status
import jack.functions
import jack.main_loop
import jack.progress
import jack.prepare


##############################################################################
###################### M A I N ###############################################
##############################################################################

def main():
    locale.setlocale(locale.LC_ALL, "")

    # say hello...
    print("This is", jack.version.name, jack.version.version, jack.version.copyright, jack.version.url)

    ### interpret options
    global_cf = jack.rc.load(cf, cf['global_rc']['val'])
    jack.checkopts.checkopts(cf, global_cf)
    cf.rupdate(global_cf, "global_rc")
    user_cf = jack.rc.load(cf, cf['user_rc']['val'])
    jack.checkopts.checkopts(cf, user_cf)
    cf.rupdate(user_cf, "user_rc")
    help, argv_cf = jack.argv.parse_argv(cf, sys.argv)
    jack.checkopts.checkopts(cf, argv_cf)
    cf.rupdate(argv_cf, "argv")
    if help:
        jack.argv.show_usage(cf, help-1)
        sys.exit(0)
    debug("global_cf: " + repr(global_cf))
    debug("user_cf: " + repr(user_cf))
    debug("argv_cf: " + repr(argv_cf))

    jack.checkopts.check_rc(cf, global_cf, user_cf, argv_cf)
    jack.checkopts.consistency_check(cf)

    if cf['save_args']['val'] == 1:
        count = jack.rc.save(cf['user_rc']['val'], cf)
        info("%d options saved in %s" % (count, cf['user_rc']['val']))
        sys.exit()

    ext = jack.targets.targets[jack.helpers.helpers[cf['_encoder']]['target']]['file_extension']

    ### search for a dir containing a toc-file or do the multi-mode
    toc_just_read = jack.prepare.find_workdir()
    os.environ["JACK_CUR_DIR"] = os.getcwd()
    os.environ["JACK_BASE_DIR"] = cf['_base_dir']
    # now we are set to go as we know we are in the right dir

    ### check toc (operation mode)
    if cf['_check_toc']:
        jack.prepare.check_toc()
        sys.exit(0)

    ### read and interpret toc_file
    track1_offset = jack.prepare.read_toc_file()

    ### make sure we have a metadata file
    metadata_form_file = jack.metadata.get_metadata_form_file(jack.metadata.get_metadata_api(cf['_metadata_server']))
    if not os.path.exists(metadata_form_file):
        jack.metadata.metadata_template(jack.ripstuff.all_tracks)

    ### init status
    jack.status.init(jack.ripstuff.all_tracks)

    #XXX## read progress info into status

    jack.ripstuff.all_tracks_orig = []
    for i in jack.ripstuff.all_tracks:
        jack.ripstuff.all_tracks_orig.append(i[:])

    status = jack.prepare.init_status()

    jack.prepare.tracknum = {}
    for i in jack.ripstuff.all_tracks:
        jack.prepare.tracknum[i[NUM]] = i

    ### now read in the progress file
    status = jack.prepare.read_progress(status, jack.ripstuff.all_tracks)

    ### filter out data tracks
    jack.prepare.filter_tracks(toc_just_read, status)

    ### Parse tracks from argv, generate todo
    todo = jack.prepare.gen_todo()
    if len(todo) == 0:
        error("nothing to do. bye.")

    ### Lookup the CD on MusicBrainz
    if cf['_metadata_lookup']:
        jack.prepare.metadata_lookup()
        sys.exit(0)

    ### do query on start
    metadata_rename = 0
    if cf['_query_if_needed']:
        if not os.path.exists(metadata_form_file + ".bak"):
            cf['_query_on_start'] = 1
    if cf['_query_on_start']:
        metadata_rename = jack.prepare.query_on_start(todo)

    ### update metadata dbfile
    if cf['_update_metadata']:
        if not jack.tag.track_names:
            err, jack.tag.track_names, metadata_rename, jack.tag.mb_query_data = jack.metadata.interpret_db_file(jack.ripstuff.all_tracks, todo, metadata_form_file, verb = 1, dirs = 0)
        jack.metadata.metadata_template(jack.ripstuff.all_tracks, jack.tag.track_names)
        jack.utils.ex_edit(metadata_form_file)
        info("Don't forget to activate your changes locally with -R")
        sys.exit(0)

    ### update progress file at user's request (operation mode)
    if cf['_upd_progress']:
        jack.prepare.update_progress(status, todo)
        sys.exit(0)

    ### undo renaming (operation mode)
    if cf['_undo_rename']:
        jack.prepare.undo_rename(status, todo)
        sys.exit(0)

    #### Reorder if told so
    if cf['_reorder']:
        todo.sort(jack.utils.cmp_toc)
        todo.reverse()

    #### check how much bytes we can burn
    if cf['space_from_argv']['history'][-1][0] == "argv":
        space = jack.ripstuff.raw_space = cf['_space_from_argv']
    else:
        space = jack.ripstuff.raw_space = jack.functions.df()

    #### check what is already there
    space, remove_q, wavs_todo, mp3s_todo, dae_queue, enc_queue, trc_tracks = jack.prepare.what_todo(space, todo)

    if cf['_todo_exit']:           # print what needs to be done, then exit
        jack.prepare.print_todo(todo, wavs_todo, mp3s_todo)
        sys.exit(0)

    # now mp3s_todo contains the tracks where the wavs only need to be coded and
    # wavs_todo lists those tracks which need to be dae'd end enc'd. The dae_queue
    # has been filled from wavs_todo (todo is superflous now). The main_loop
    # will handle the tracks in mp3s_todo.

    ### make sure we have enough space to rip the whole thing
    jack.prepare.check_space(space, wavs_todo, mp3s_todo)

    cf['_max_load'] = cf['_max_load'] + cf['_encoders'] #XXX

    if not cf['_dont_work'] and dae_queue:     # check if inserted cd matches toc.
        jack.prepare.check_cd() # why? paranoia or needed? XXX
        if cf['_rip_from_device']:
            all_tracks_on_cd = jack.functions.gettoc(cf['_toc_prog'])
            if not cf['_force'] and not jack.utils.cmp_toc_cd(jack.ripstuff.all_tracks_orig, all_tracks_on_cd, what=(NUM, LEN)):
                error("you did not insert the right cd")

    ### if we have work to do, we may have to remove some files first
    if remove_q:
        jack.prepare.remove_files(remove_q)

    ### bail out now if told so
    if cf['_dont_work']:
        info("quitting now as requested.")
        sys.exit(0)

    ### install signal handlers
    signal.signal(signal.SIGTERM, jack.display.sig_handler)
    signal.signal(signal.SIGINT, jack.display.sig_handler)
    signal.signal(signal.SIGQUIT, jack.display.sig_handler)
    signal.signal(signal.SIGHUP, jack.display.sig_handler)


           #\                         /#
    #########> real work starts here <#############################################
           #/                         \#

    global_error = None
    if (wavs_todo or mp3s_todo):
        jack.ripstuff.gen_printable_names(jack.tag.track_names, todo)
        jack.term.init(cf['_terminal'], cf['_xtermset_enable'])
        jack.display.init()
        try:
            jack.term.enable()
            global_error = jack.main_loop.main_loop(mp3s_todo, wavs_todo, space, dae_queue, enc_queue, track1_offset, trc_tracks)
        except SystemExit:
            jack.term.disable()
            print(jack.display.options_string)
            print("--- Last status: ---------------------------------------------------------------")
            jack.status.print_status(form = 'short')
            sys.exit(0)
        except:
            jack.term.disable()
            warning("abnormal exit")
            traceback.print_exc()
            sys.exit(1)
    # Set the files we have processed but this may still be overwritten by
    # jack.tag.tag() called below.
    os.environ["JACK_JUST_ENCODED"] = "\n".join([x[NAME] + ext for x in mp3s_todo])
    os.environ["JACK_JUST_RIPPED"] = "\n".join([x[NAME] + ".wav" for x in wavs_todo])

    jack.term.disable()
    if cf['_query_when_ready']:
        info("querying...")
        if jack.metadata.metadata_query(jack.metadata.metadata_id(jack.ripstuff.all_tracks), jack.ripstuff.all_tracks, metadata_form_file):
            jack.display.exit()

    if cf['_query_when_ready'] or cf['_read_metadata_file'] or cf['_query_on_start']:
        err, jack.tag.track_names, metadata_rename, jack.tag.mb_query_data = jack.metadata.interpret_db_file(jack.ripstuff.all_tracks, todo, metadata_form_file, verb = 1, dirs = 1)
        if err:
            error("could not read metadata file")

    if jack.term.term_type == "curses":
        if jack.display.options_string:
            print(jack.display.options_string)
        print("The final status was:")
        jack.status.print_status(form = 'short')

    if global_error:
        if cf['_exec_when_done']:
            os.system(cf['_exec_err'])
        error("aborting because of previous error(s) [%i]." % global_error)

    jack.tag.tag(metadata_rename)

    if jack.functions.progress_changed:
        jack.functions.progress("all", "done", str(time.strftime("%b %2d %H:%M:%S", time.localtime(time.time()))))

    if cf['_remove_files']:
        print("cleaning up in", os.getcwd())
        for i in [cf['_progress_file'], cf['_toc_file'], cf['_def_toc'], metadata_form_file, metadata_form_file + ".bak"]:
            if os.path.exists(i):
                os.remove(i)

    if cf['_exec_when_done']:
        os.system(cf['_exec_no_err'])

    jack.display.exit()      # call the cleanup function & exit

if __name__ == "__main__":
    sys.exit(main())


###############################################################################
##################################         ####################################
##################################  T H E  ####################################
##################################  E N D  ####################################
##################################         ####################################
###############################################################################
