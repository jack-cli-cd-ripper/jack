#!/usr/bin/env python

"""Setup script for the jack module distribution."""

# this is work in progress
#print "This is work in progress, install manually. Read doc/INSTALL."
#from sys import exit
#exit(1)

from distutils.core import setup, Extension

setup( # Distribution meta-data
    name = "jack",
    version = "3.0.0",
    description = "A frontend for several cd-rippers and mp3 encoders",
    author = "Arne Zellentin",
    author_email = "zarne@users.sf.net",
    url = "http://www.home.unix-ag.org/arne/jack/",

    # Description of the modules and packages in the distribution
    ext_modules = [ Extension('jack_cursesmodule',
    ['cursesmodule/jack_cursesmodule.c'], libraries=["ncurses"],
    extra_compile_args=["-Wno-strict-prototypes"]) ],

    py_modules = ['jack_CDTime', 'jack_constants', 'jack_helpers',
        'jack_prepare', 'jack_tag', 'jack_TOC', 'jack_display', 'jack_init',
        'jack_progress', 'jack_targets', 'jack_TOCentry', 'jack_encstuff',
        'jack_m3u', 'jack_rc', 'jack_term', 'jack_argv', 'jack_freedb',
        'jack_main_loop', 'jack_ripstuff', 'jack_utils', 'jack_checkopts',
        'jack_functions', 'jack_misc', 'jack_status', 'jack_version',
        'jack_children', 'jack_generic', 'jack_mp3', 'jack_t_curses',
        'jack_workers', 'jack_config', 'jack_globals', 'jack_playorder',
        'jack_t_dumb']
)

print "If you have installed the modules, copy jack to some place in your $PATH,"
print "like /usr/local/bin/."
