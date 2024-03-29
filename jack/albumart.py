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
import json
import datetime
import shutil
import tempfile

from dateutil.parser import parse as parsedate
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


def save_existing_albumart(imgdata):
    md5 = hashlib.md5(imgdata).hexdigest()
    imgobj = Image.open(BytesIO(imgdata))
    ext = imgobj.format.lower()
    savefile = "%s%s.%s" % (cf['_albumart_save_prefix'], md5, ext)
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
            save_existing_albumart(old_pic.data)
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
                save_existing_albumart(bytes(covr))
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
                save_existing_albumart(old_pic.data)
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
                save_existing_albumart(old_pic.data)
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
        for pattern in cf['_albumart_search']:
            for filename in filenames:
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

    ret = False

    if not 'cover-art-archive' in release:
        return False
    if not 'artwork' in release['cover-art-archive']:
        return False
    if not release['cover-art-archive']['artwork']:
        return False

    base_url = f'https://coverartarchive.org/release/{ release["id"] }/'
    prefix = cf['_caa_albumart_prefix']
    art_types = cf['_caa_albumart_types']
    fetchlist = cf['_caa_albumart_sizes']
    suffix = ""

    headers = {'User-Agent': jack.version.user_agent}

    r = requests.get(base_url)
    if r.status_code != 200:
        r.close()
        return False

    query_data = json.loads(r.text)
    if 'images' not in query_data:
        return False

    for image in query_data['images']:
        for art_type in art_types:
            if art_type in image and image[art_type]:
                for size in fetchlist:
                    if len(fetchlist) > 1:
                        suffix = "." + size
                    if size == 'original':
                        url = image['image']
                    else:
                        if size in image['thumbnails']:
                            url = image['thumbnails'][size]
                        else:
                            continue
                    extension = url.split(".")[-1]
                    filename = prefix + art_type + suffix + "." + extension

                    # create a new session for each download, to avoid random disconnects
                    with requests.Session() as session:
                        session.headers.update(headers)
                        if download(session, url, filename, cf['_overwrite_albumart']):
                            ret = True
    return ret


def fetch_itunes_albumart(artist, album, country):

    ret = False

    baseurl = 'https://itunes.apple.com/search'
    country = validate_itunes_country(country)
    prefix = cf['_itunes_albumart_prefix']
    limit = cf['_itunes_albumart_limit']
    fetchlist = cf['_itunes_albumart_sizes']
    suffix = ""
    headers = {'User-Agent': jack.version.user_agent}
    search_term = requests.utils.quote(artist + ' ' + album)
    search_url = "%s?term=%s&country=%s&media=music&entity=album&limit=%d" % (baseurl, search_term, country, limit)

    debug(f"{search_url=}")

    with requests.Session() as session:
        session.headers.update(headers)

        r = session.get(search_url)
        if r.status_code != 200:
            return False

        querydata = json.loads(r.text)

        if 'results' not in querydata:
            return False

        for result in querydata['results']:

            itunes_artist = result['artistName']
            itunes_album = result['collectionName']

            # generate a safe filename: artist and album names can be extremely long
            itunes_filename = jack.utils.smart_truncate(itunes_artist) + " - " + jack.utils.smart_truncate(itunes_album)
            itunes_filename = jack.utils.unusable_charmap(itunes_filename)

            # iTunes API shows thumbnail pictures only. This is an undocumented trick to get high quality versions.
            # Taken from https://github.com/bendodson/itunes-artwork-finder
            http_url = urlparse(result['artworkUrl100'])._replace(scheme='http', netloc='is5.mzstatic.com').geturl()

            art_urls = {}
            art_urls['thumb']    = http_url
            art_urls['standard'] = http_url.replace("100x100bb", "600x600bb")
            art_urls['high']     = http_url.replace("100x100bb", "100000x100000-999")

            for size in fetchlist:
                if len(fetchlist) > 1:
                    suffix = "." + size
                if size in art_urls:
                    filename = prefix + itunes_filename + suffix + ".jpg"
                    if download(session, art_urls[size], filename, cf['_overwrite_albumart']):
                        ret = True

        return ret


def fetch_discogs_albumart(release):

    ret = False

    prefix = cf['_discogs_albumart_prefix']
    art_types = cf['_discogs_albumart_types']
    access_token = cf['_discogs_albumart_token']
    base_url = "https://api.discogs.com/releases/"
    headers = {'User-Agent': jack.version.user_agent}

    discogs_urls = []
    if 'relations' in release:
        for relation in release['relations']:
            if 'type' in relation and relation['type'] == "discogs" and 'url' in relation and 'resource' in relation['url']:
                discogs_urls.append(relation['url']['resource'])

    if not discogs_urls:
        return False

    with requests.Session() as session:
        session.headers.update(headers)

        for discogs_url in discogs_urls:
            discogs_release = discogs_url.split("/")[-1]
            api_url = base_url + discogs_release
            if access_token:
                api_url += "?token=" + access_token

            r = session.get(api_url)
            if r.status_code != 200:
                continue
            query_data = json.loads(r.text)

            if 'images' not in query_data:
                continue

            for image in query_data['images']:
                for art_type in art_types:
                    if 'type' in image and image['type'] == art_type and 'uri' in image:
                        url = image['uri']
                        if len(url):
                            r = session.head(url)
                            if r.status_code != 200:
                                continue
                            content_disposition =  r.headers.get("Content-Disposition")
                            if content_disposition:
                                basename = content_disposition.split("filename=")[1] 
                                basename = basename.replace('"', '')
                            else:
                                basename = hashlib.md5(url.encode("utf-8")).hexdigest()
                                basename += "." + url.split(".")[-1]
                            if len(art_types) > 1:
                                filename = prefix  + art_type + "." + basename
                            else:
                                filename = prefix + basename
                            if download(session, url, filename, cf['_overwrite_albumart']):
                                ret = True
                        else:
                            print("discogs albumart (%dx%d) is available but cannot be downloaded without an access token" % (image['width'], image['height']))
                            print("create a personal access token at https://www.discogs.com/settings/developers and use it as --discogs-albumart-token=your_token")

        return ret


def download(session, url, filename, overwrite):
    "fast chunked downloading of binary data with restoring modification date"

    different = False
    exists = False
    if os.path.exists(filename):
        exists = True
        stinfo = os.stat(filename)
        if overwrite == "conditional":
            r = session.head(url)
            if r.status_code == 200:
                remote_length = r.headers.get('Content-Length')
                if remote_length and int(remote_length) != stinfo.st_size:
                    different = True
                last_modified = r.headers.get('Last-Modified')
                if last_modified:
                    timestamp = datetime.datetime.timestamp(parsedate(last_modified))
                    if timestamp != stinfo.st_mtime:
                        different = True

    if exists and not different and overwrite != "always":
        return True

    r = session.get(url, stream=True)
    if r.status_code != 200:
        warning("could not download %s, status %d" % (filename, r.status_code))
        return False

    old_timestamp = datetime.datetime.now().timestamp()
    current_length = 0
    remote_length = r.headers.get('Content-Length')

    info(f"downloading {filename} ({remote_length=})")
    with tempfile.TemporaryFile() as tmpfd:
        for chunk in r.iter_content(chunk_size=32768):
            tmpfd.write(chunk)
            current_length += len(chunk)
            new_timestamp = datetime.datetime.now().timestamp()
            if cf['_download_progress_interval'] and new_timestamp - old_timestamp > cf['_download_progress_interval']:
                progress = "downloading %s: %d bytes" % (filename, current_length)
                if remote_length:
                    percent = 100 * current_length // int(remote_length)
                    progress = "downloading %s: %d/%s bytes (%d%%)" % (filename, current_length, remote_length, percent)
                info(progress)
                old_timestamp = new_timestamp

        tmpfd.seek(0)
        with open(filename, "wb") as fd:
            shutil.copyfileobj(tmpfd, fd)

    last_modified = r.headers.get('Last-Modified')
    if last_modified:
        timestamp = datetime.datetime.timestamp(parsedate(last_modified))
        stinfo = os.stat(filename)
        os.utime(filename, (stinfo.st_atime, timestamp))

    return True

def validate_itunes_country(country):
    itunes_countries = [
        "ae","ag","ai","al","am","ao","ar","at","au","az","bb","be","bf","bg","bh","bj","bm","bn","bo","br","bs","bt","bw","by",
        "bz","ca","cg","ch","cl","cn","co","cr","cv","cy","cz","de","dk","dm","do","dz","ec","ee","eg","es","fi","fj","fm","fr",
        "gb","gd","gh","gm","gr","gt","gw","gy","hk","hn","hr","hu","id","ie","il","in","is","it","jm","jo","jp","ke","kg","kh",
        "kn","kr","kw","ky","kz","la","lb","lc","lk","lr","lt","lu","lv","md","mg","mk","ml","mn","mo","mr","ms","mt","mu","mw",
        "mx","my","mz","na","ne","ng","ni","nl","np","no","nz","om","pa","pe","pg","ph","pk","pl","pt","pw","py","qa","ro","ru",
        "sa","sb","sc","se","sg","si","sk","sl","sn","sr","st","sv","sz","tc","td","th","tj","tm","tn","tr","tt","tw","tz","ua",
        "ug","us","uy","uz","vc","ve","vg","vn","ye","za","zw",
    ]

    if country in itunes_countries:
        return country
    country =  cf['_itunes_albumart_country']
    if country in itunes_countries:
        return country
    return "us"
