# -*- coding: utf-8 -*-
# jack.tag: name information (ID3 among others) stuff for
# jack - tag audio from a CD and encode it using 3rd party software
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

import os
import base64
import hashlib
from io import BytesIO
from PIL import Image

from jack.init import oggvorbis
from jack.init import mp3
from jack.init import id3
from jack.init import flac
from jack.init import mp4
from jack.globals import *

def save_existing_albumart(imgdata, mime):
    if mime == "image/jpeg":
        ext = "jpg"
    elif mime == "image/png":
        ext = "png"
    elif mime == "image/gif":
        ext = "gif"
    elif mime == "image/webp":
        ext = "webp"
    else:
        ext = "dat"
    md5 = hashlib.md5(imgdata).hexdigest()
    savefile = "jack.albumart-{0}.{1}".format(md5, ext)
    if not os.path.exists(savefile):
        debug("saving album art to " + savefile)
        fd = open(savefile, "wb")
        fd.write(imgdata)
        fd.close()
    else:
        debug(savefile + " already exists")

def embed_albumart_id3(tagobj, audiofile, imgfile, imgdata, imgobj):
    #TODO
    warning("ID3 albumart embedding currently not supported")
    return

def embed_albumart_mp4(tagobj, audiofile, imgfile, imgdata, imgobj):
    makechanges = 0

    mp4_covr = []
    mp4_covr.append(mp4.MP4Cover(imgdata, imageformat=mp4.MP4Cover.FORMAT_JPEG))

    if 'covr' in tagobj.tags:
        if  tagobj.tags['covr'] != mp4_covr:
            makechanges += 1
            debug("replacing image " + imgfile + " into " + audiofile)
            for covr in tagobj.tags['covr']:
                if covr.imageformat == mp4.MP4Cover.FORMAT_JPEG:
                    mime = "image/jpeg"
                elif covr.imageformat == mp4.MP4Cover.FORMAT_PNG:
                    mime = "image/png"
                else:
                    mime = None
                save_existing_albumart(bytes(covr), mime)
    else:
        makechanges += 1
        debug("adding image " + imgfile + " into " + audiofile)
    if makechanges:
        tagobj.tags['covr'] = mp4_covr

def embed_albumart_flac(tagobj, audiofile, imgfile, imgdata, imgobj):
    new_pic = flac.Picture()
    new_pic.data = imgdata
    new_pic.type = id3.PictureType.COVER_FRONT
    new_pic.mime = "image/jpeg"
    (new_pic.width, new_pic.height) = imgobj.size
    new_pic.depth = 24

    makechanges = 0
    if tagobj.pictures:
        for old_pic in tagobj.pictures:
            if old_pic.type != id3.PictureType.COVER_FRONT or old_pic.data != new_pic.data:
                makechanges += 1
                save_existing_albumart(old_pic.data, old_pic.mime)
    else:
        makechanges += 1
    if makechanges:
        if tagobj.pictures:
            debug("removing images from " + audiofile)
            tagobj.clear_pictures()
        debug("adding image to " + audiofile)
        tagobj.add_picture(new_pic)

def embed_albumart_ogg(tagobj, audiofile, imgfile, imgdata, imgobj):
    new_pic = flac.Picture()
    new_pic.data = imgdata
    new_pic.type = id3.PictureType.COVER_FRONT
    new_pic.mime = "image/jpeg"
    (new_pic.width, new_pic.height) = imgobj.size
    new_pic.depth = 24

    makechanges = 0
    picture_data = tagobj.get("metadata_block_picture", [])
    if picture_data:
        for b64_data in picture_data:
            old_pic = flac.Picture(base64.b64decode(b64_data))
            if old_pic.type != id3.PictureType.COVER_FRONT or old_pic.data != new_pic.data:
                makechanges += 1
                save_existing_albumart(old_pic.data, old_pic.mime)
    else:
        makechanges += 1
    if makechanges:
        debug("adding image to " + audiofile)
        encoded_data = base64.b64encode(new_pic.write())
        vcomment_value = encoded_data.decode("ascii")
        tagobj["metadata_block_picture"] = [vcomment_value]

def embed_albumart(tagobj, target, audiofile):
    if not cf['_embed_albumart']:
        return
    if not cf['_albumart_file']:
        return
    imgfile = cf['_albumart_file']
    if os.path.exists(imgfile):
        imgsize = os.stat(imgfile).st_size

        imgdata = open(imgfile, "rb").read()
        imgobj = Image.open(BytesIO(imgdata))
        if imgobj.format != 'JPEG':
            warning(imgfile + " is not a jpeg file")
            cf['_albumart_file'] = None
            return

        if target == "mp3":
            embed_albumart_id3(tagobj, audiofile, imgfile, imgdata, imgobj)
        elif target == "m4a":
            embed_albumart_mp4(tagobj, audiofile, imgfile, imgdata, imgobj)
        elif target == "flac":
            embed_albumart_flac(tagobj, audiofile, imgfile, imgdata, imgobj)
        elif target == "ogg":
            embed_albumart_ogg(tagobj, audiofile, imgfile, imgdata, imgobj)
        else:
            error("unknown target " + target)
    else:
        cf['_albumart_file'] = None
