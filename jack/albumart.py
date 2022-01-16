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
import re
import base64
import hashlib
import requests
import shutil
import json
import datetime
import dateparser
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image

import jack.functions
import jack.version
from jack.init import oggvorbis
from jack.init import mp3
from jack.init import id3
from jack.init import flac
from jack.init import mp4
from jack.globals import *

def imagedepth(mode):
    imagemodes = {
            '1': 1, # (1-bit pixels, black and white, stored with one pixel per byte)
            'L': 8, # (8-bit pixels, black and white)
            'P': 8, # (8-bit pixels, mapped to any other mode using a color palette)
            'RGB': 24, # (3x8-bit pixels, true color)
            'RGBA': 32, # (4x8-bit pixels, true color with transparency mask)
            'CMYK': 32, # (4x8-bit pixels, color separation)
            'YCbCr': 24, # (3x8-bit pixels, color video format)
            'LAB': 24, # (3x8-bit pixels, the L*a*b color space)
            'HSV': 24, # (3x8-bit pixels, Hue, Saturation, Value color space)
            'I': 32, # (32-bit signed integer pixels)
            'F': 32, # (32-bit floating point pixels)
            'LA': 16, # (L with alpha)
            'PA': 16, # (P with alpha)
            'RGBX': 24, # (true color with padding)
            'RGBa': 32, # (true color with premultiplied alpha)
            'La': 16, # (L with premultiplied alpha)
            'I;16': 16, # (16-bit unsigned integer pixels)
            'I;16L': 16, # (16-bit little endian unsigned integer pixels)
            'I;16B': 16, # (16-bit big endian unsigned integer pixels)
            'I;16N': 16, # (16-bit native endian unsigned integer pixels)
            'BGR;15': 15, # (15-bit reversed true colour)
            'BGR;16': 16, # (16-bit reversed true colour)
            'BGR;24': 24, # (24-bit reversed true colour)
            'BGR;32': 32, # (32-bit reversed true colour)
    }
    if mode in imagemodes:
        return imagemodes[mode]
    return None


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
    makechanges = 0
    new_pic = id3.APIC(
            encoding = id3.Encoding.UTF8,
            mime = "image/" + imgobj.format.lower(),
            type = id3.PictureType.COVER_FRONT,
            data = imgdata
        )

    old_pics = tagobj.tags.getall('APIC')
    for old_pic in old_pics:
        if old_pic.encoding != new_pic.encoding or old_pic.mime != new_pic.mime or old_pic.type != new_pic.type or old_pic.data != new_pic.data:
            makechanges += 1
            debug("removing images from " + audiofile)
            save_existing_albumart(old_pic.data, old_pic.mime)
    if not old_pics:
        makechanges += 1

    if makechanges:
        debug("adding image " + imgfile + " into " + audiofile)
        tagobj.tags.delall('APIC')
        tagobj.tags.add(new_pic)

def embed_albumart_mp4(tagobj, audiofile, imgfile, imgdata, imgobj):
    makechanges = 0

    imageformats = {'JPEG': mp4.MP4Cover.FORMAT_JPEG, 'PNG': mp4.MP4Cover.FORMAT_PNG}
    new_pic = [mp4.MP4Cover(imgdata, imageformat=imageformats[imgobj.format])]

    if 'covr' in tagobj.tags:
        if  tagobj.tags['covr'] != new_pic:
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
        tagobj.tags['covr'] = new_pic

def embed_albumart_flac(tagobj, audiofile, imgfile, imgdata, imgobj):
    new_pic = flac.Picture()
    new_pic.data = imgdata
    new_pic.type = id3.PictureType.COVER_FRONT
    new_pic.mime = "image/" + imgobj.format.lower()
    (new_pic.width, new_pic.height) = imgobj.size
    new_pic.depth = imagedepth(imgobj.mode)

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
    new_pic.mime = "image/" + imgobj.format.lower()
    (new_pic.width, new_pic.height) = imgobj.size
    new_pic.depth = imagedepth(imgobj.mode)

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

def assess_albumart(filename):
    reject = 0
    try:
        imgdata = open(filename, "rb").read()
    except:
        reject += 1
        debug("rejecting %s, reason: can not open" % (filename,))
        return
    try:
        imgobj = Image.open(BytesIO(imgdata))
    except:
        reject += 1
        debug("rejecting %s, reason: can not load as picture" % (filename,))
        return
    if imgobj.format != 'JPEG' and imgobj.format != 'PNG':
        reject += 1
        debug("rejecting %s, reason: picture format %s is not PNG or JPEG" % (filename, imgobj.format))
    size = os.stat(filename).st_size
    (width, height) = imgobj.size
    if size > cf['_albumart_max_size']:
        reject += 1
        debug("rejecting %s, reason: too large (%d>%d)" % (filename, size, cf['_albumart_max_size']))
    if size < cf['_albumart_min_size']:
        reject += 1
        debug("rejecting %s, reason: too small (%d<%d)" % (filename, size, cf['_albumart_min_size']))
    if width > cf['_albumart_max_width']:
        reject += 1
        debug("rejecting %s, reason: too wide (%d>%d)" % (filename, width, cf['_albumart_max_width']))
    if width < cf['_albumart_min_width']:
        reject += 1
        debug("rejecting %s, reason: too narrow (%d<%d)" % (filename, width, cf['_albumart_min_width']))
    if height > cf['_albumart_max_height']:
        reject += 1
        debug("rejecting %s, reason: too high (%d>%d)" % (filename, height, cf['_albumart_max_height']))
    if height < cf['_albumart_min_height']:
        reject += 1
        debug("rejecting %s, reason: too low (%d<%d)" % (filename, height, cf['_albumart_min_height']))
    return reject == 0

def search_albumart():
    search_root = "."
    if cf['_albumart_ignorecase']:
        flags = re.IGNORECASE
    else:
        flags = 0
    for path, dirnames, filenames in os.walk(search_root):
        if path != search_root and not cf['_albumart_recurse']:
            continue
        for filename in filenames:
            for pattern in cf['_albumart_search']:
                if re.match(pattern, filename, flags=flags):
                    filepath = os.path.join(path, filename)
                    if assess_albumart(filepath):
                        return filepath
    return None

def embed_albumart(tagobj, target, audiofile):
    if not cf['_embed_albumart']:
        return
    if not cf['_albumart_file']:
        cf['_albumart_file'] = search_albumart()
    if not cf['_albumart_file']:
        return
    imgfile = cf['_albumart_file']
    if os.path.exists(imgfile):
        imgsize = os.stat(imgfile).st_size

        imgdata = open(imgfile, "rb").read()
        imgobj = Image.open(BytesIO(imgdata))
        if imgobj.format != 'JPEG' and imgobj.format != 'PNG':
            warning("skipping %s with unsupported image format %s" % (imgfile, imgobj.format))
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

def fetch_caa_albumart(release):
    base_url = f'https://coverartarchive.org/release/{ release["id"] }/'
    if 'cover-art-archive' in release:
        caa = release['cover-art-archive']
        for art_type in cf['_fetch_albumart_types']:
            # original
            artfile = "%s%s.jpg" % (cf['_fetch_albumart_prefix'], art_type)
            if art_type in caa and caa[art_type] and not os.path.exists(artfile):
                err, response = jack.musicbrainz.get_response("%s%s.jpg" % (base_url, art_type))
                if not err:
                    with open(artfile, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                    response.close()
            # thumbnails
            for size in cf['_fetch_albumart_sizes']:
                artfile = "%s%s-%d.jpg" % (cf['_fetch_albumart_prefix'], art_type, size)
                if art_type in caa and caa[art_type] and not os.path.exists(artfile):
                    err, response = jack.musicbrainz.get_response("%s%s-%d.jpg" % (base_url, art_type, size))
                    if not err:
                        with open(artfile, 'wb') as out_file:
                            shutil.copyfileobj(response, out_file)
                        response.close()

def fetch_itunes_albumart(artist, album):
    baseurl = 'https://itunes.apple.com/search'
    country = cf['_fetch_itunes_albumart_country']
    prefix = cf['_fetch_itunes_albumart_prefix']
    limit = cf['_fetch_itunes_albumart_limit']
    fetchlist = cf['_fetch_itunes_albumart_sizes']

    user_agent = "%s/%s (%s)" % (jack.version.name, jack.version.version, jack.version.url)
    headers = {'User-Agent': user_agent}

    search_term = requests.utils.quote(artist + ' ' + album)
    search_url = "%s?term=%s&country=%s&media=music&entity=album&limit=%d" % (baseurl, search_term, country, limit)

    session = requests.Session()
    session.headers.update(headers)

    r = session.get(search_url)
    querydata = json.loads(r.text)

    if 'results' in querydata:
        for result in querydata['results']:

            itunes_artist = result['artistName']
            itunes_album = result['collectionName']

            itunes_name = jack.utils.unusable_charmap(itunes_artist + " - " + itunes_album)
            suffix = ""

            # iTunes API shows thumbnail pictures only. This is an undocumented trick to get high quality versions.
            # Taken from https://github.com/bendodson/itunes-artwork-finder
            http_url = urlparse(result['artworkUrl100'])._replace(scheme='http', netloc='is5.mzstatic.com').geturl()

            art_urls = {}
            art_urls['thumb']    = http_url
            art_urls['standard'] = http_url.replace("100x100bb", "600x600bb")
            art_urls['high']     = http_url.replace("100x100bb", "100000x100000-999")

            for size in fetchlist:
                if size in art_urls:
                    if len(fetchlist) > 1:
                        suffix = "." + size
                    filename = prefix + itunes_name + suffix + ".jpg"
                    download(session, art_urls[size], filename)

    session.close()

def download(session, url, filename):
    "fast chunked downloading of binary data with restoring modification date"
    try:
        with open(filename, "xb") as fd:
            r = session.get(url, stream=True)
            if r.status_code == 200 and len(r.history) == 0:
                for data in r.iter_content(chunk_size=32768):
                    fd.write(data)
                fd.close()
                info("Downloaded " + filename)
                last_modified = r.headers.get('Last-Modified')
                if last_modified:
                    timestamp = datetime.datetime.timestamp(dateparser.parse(last_modified))
                    stinfo = os.stat(filename)
                    os.utime(filename, (stinfo.st_atime, timestamp))
            else:
                warning("Could not download %s, status %d" % (filename, r.status_code))
                os.remove(filename)
    except FileExistsError:
        r = session.head(url)
        if r.status_code == 200 and len(r.history) == 0:
            remote_length = int(r.headers.get('Content-Length'))
            if remote_length:
                local_length = os.stat(filename).st_size
                if remote_length != local_length:
                    warning("different filesize for %s: web: %d local: %d" % (filename, remote_length, local_length))
            last_modified = r.headers.get('Last-Modified')
            if last_modified:
                timestamp = datetime.datetime.timestamp(dateparser.parse(last_modified))
                if timestamp != os.stat(filename).st_mtime:
                    warning("different remote timestamp for %s")
