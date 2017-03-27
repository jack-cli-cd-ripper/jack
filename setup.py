#!/usr/bin/env python

"""Setup script for the jack module distribution."""

import os

from distutils.core import setup, Extension


basepath = os.path.dirname(__file__)

setup(  # Distribution meta-data
    name="jack",
    version="3.1.1",
    description="A frontend for several cd-rippers and mp3 encoders",
    author="Arne Zellentin",
    author_email="zarne@users.sf.net",
    url="http://www.home.unix-ag.org/arne/jack/",

    scripts=(os.path.join(basepath, 'bin', 'jack'),),
    # Description of the modules and packages in the distribution
    ext_modules=[Extension('jack_cursesmodule',
                           ['cursesmodule/jack_cursesmodule.c'], libraries=["ncursesw"],
                           include_dirs=["/usr/include/ncursesw"],
                           extra_compile_args=["-Wno-strict-prototypes"])],
    packages = ['jack'],
)

print "If you have installed the modules, copy jack to some place in your $PATH,"
print "like /usr/local/bin/."
