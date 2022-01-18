#!/usr/bin/env python3

"""Setup script for the jack module distribution."""

from setuptools import setup, find_packages
import jack.version

# libdiscid is preferred, but cannot be installed with pip, as it is a wrapper only
# fall back to discid if our distro does not satisfy all requirements
require_discid = False
try:
    import libdiscid
except:
    require_discid = True

PACKAGES = find_packages(exclude=find_packages(where="deprecated"))

REQUIRES = [
    'mutagen',
    'pillow',
    'requests',
    'dateparser',
]

if require_discid:
    REQUIRES.append('discid')

setup(
    setup_requires=['setuptools_scm'],

    name=jack.version.name,
    use_scm_version=True,
    description="A frontend for several cd-rippers and mp3 encoders",
    author=jack.version.author,
    author_email=jack.version.email,
    url=jack.version.url,
    license=jack.version.license,

    install_requires=REQUIRES,
    packages=PACKAGES,

    entry_points={"console_scripts": ["jack = jack.__main__:main"]},
)
