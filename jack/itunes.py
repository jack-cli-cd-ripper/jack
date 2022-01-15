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

import requests
import json
import os
import datetime
import dateparser
from urllib.parse import urlparse
from jack.globals import *
import jack.version

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
                warning("Could not download %s, status %d" % (filename, status))
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
