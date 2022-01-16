#!/usr/bin/env python3

"""Setup script for the jack module distribution."""

from setuptools import setup, find_packages
import jack.version

PACKAGES = find_packages(exclude=find_packages(where="deprecated"))

REQUIRES = [
    #FIXME, we require either discid or libdiscid, libdiscid is preferred but requires an external C-library to be present in your distro
    'discid',
    'mutagen',
    'pillow',
    'requests',
    'dateparser',
]

setup(
    name=jack.version.name,
    version=jack.version.version,
    description="A frontend for several cd-rippers and mp3 encoders",
    author=jack.version.author,
    author_email=jack.version.email,
    url=jack.version.url,
    license=jack.version.license,

    install_requires=REQUIRES,
    packages=PACKAGES,

    entry_points={"console_scripts": ["jack = jack.__main__:main"]},
)
