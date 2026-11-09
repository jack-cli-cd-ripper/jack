"""tests for the iTunes album art urls

Run from the top of the source tree with:

    python3 -m unittest discover tests
"""

import unittest

import jack.globals
import jack.albumart

# artworkUrl100 of a search result, as the iTunes search API hands them out
ARTWORK_URL100 = "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/bb/91/1b/bb911b04-47ca-663a-2fd5-7bd7e4303a0f/26UMGIM57737.rgb.jpg/100x100bb.jpg"
BASE = "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/bb/91/1b/bb911b04-47ca-663a-2fd5-7bd7e4303a0f/26UMGIM57737.rgb.jpg"


class ItunesArtUrls(unittest.TestCase):

    def test_sizes(self):
        urls = jack.albumart.itunes_art_urls(ARTWORK_URL100)
        self.assertEqual(urls['thumb'], ARTWORK_URL100)
        self.assertEqual(urls['standard'], BASE + "/600x600bb.jpg")
        self.assertEqual(urls['high'], BASE + "/10000x10000bb.png")

    def test_only_the_rendering_spec_changes(self):
        for url in jack.albumart.itunes_art_urls(ARTWORK_URL100).values():
            self.assertTrue(url.startswith(BASE + "/"))
            self.assertEqual(url.count("/"), ARTWORK_URL100.count("/"))

    def test_png_source(self):
        "the source file's own extension stays, the rendering spec picks the output format"
        url = ARTWORK_URL100.replace("26UMGIM57737.rgb.jpg", "cover.png")
        urls = jack.albumart.itunes_art_urls(url)
        self.assertEqual(urls['standard'], BASE.replace("26UMGIM57737.rgb.jpg", "cover.png") + "/600x600bb.jpg")
        self.assertEqual(urls['high'], BASE.replace("26UMGIM57737.rgb.jpg", "cover.png") + "/10000x10000bb.png")

    def test_files_match_the_search_pattern(self):
        "the downloaded files must be found by the default albumart_search patterns"
        import re
        urls = jack.albumart.itunes_art_urls(ARTWORK_URL100)
        patterns = [re.compile(p) for p in jack.globals.cf['_albumart_search']]
        for size, url in urls.items():
            filename = "jack.itunes.Artist - Album." + size + "." + url.rsplit('.', 1)[1]
            self.assertTrue(any(p.match(filename) for p in patterns), filename)

    def test_every_configured_size_has_a_url(self):
        urls = jack.albumart.itunes_art_urls(ARTWORK_URL100)
        for size in jack.globals.cf['_itunes_albumart_sizes']:
            self.assertIn(size, urls)
        self.assertEqual(set(urls), {'thumb', 'standard', 'high'})


if __name__ == '__main__':
    unittest.main()
