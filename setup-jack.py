#!/usr/bin/env python

"""Setup script for the (patched) curses module distribution."""

# this is work in progress
print "This is work in progress, install manually. Read doc/INSTALL."
from sys import exit
exit(1)


from distutils.core import setup, Extension

setup (# Distribution meta-data
       name = "jack",
       version = "2.99.5",
       description = "A frontend for several cd-rippers and mp3 encoders",
       author = "Arne Zellentin",
       author_email = "arne@unix-ag.org",
       url = "http://www.home.unix-ag.org/arne/jack/",

       # Description of the modules and packages in the distribution
       #ext_modules = [ Extension('cursesmodule', ['cursesmodule/cursesmodule.c']) ]
      )
