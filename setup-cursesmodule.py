#!/usr/bin/env python

"""Setup script for the (patched) curses module distribution."""

from distutils.core import setup, Extension

setup (# Distribution meta-data
       name = "curses",
       version = "1.5b1",
       description = "standard curses module, patched to include newpad() and resizeterm()",
       author = "Arne Zellentin (just for the patch!)",
       author_email = "arne@unix-ag.org",
       url = "http://www.home.unix-ag.org/arne/jack/",

       # Description of the modules and packages in the distribution
       ext_modules = [ Extension('cursesmodule', ['cursesmodule/cursesmodule.c'], libraries=["ncurses"]) ]
      )
