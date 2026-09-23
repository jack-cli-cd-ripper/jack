"""tests for the discogs album art helpers

Run from the top of the source tree with:

    python3 -m unittest discover tests
"""

import base64
import os
import tempfile
import unittest

import jack.globals
import jack.albumart


def imgproxy_url(source_path, fmt="jpeg"):
    "a signed discogs image url as the api hands them out, with a fake signature"
    blob = base64.urlsafe_b64encode(source_path.encode()).decode().rstrip("=")
    segments = [blob[i:i + 16] for i in range(0, len(blob), 16)]
    return "https://i.discogs.com/bZhQ7h7OQKQf--BIogfaKeSiGnAtUrE/rs:fit/g:sm/q:90/h:600/w:600/" + "/".join(segments) + "." + fmt


class DiscogsImageId(unittest.TestCase):

    def test_id_from_signed_url(self):
        url = imgproxy_url("s3://discogs-database-images/R-261718-1449656596-1124.jpeg")
        self.assertEqual(jack.albumart.discogs_image_id(url), "R-261718-1449656596-1124")

    def test_output_format_does_not_matter(self):
        url = imgproxy_url("s3://discogs-database-images/R-261718-1449656596-1124.jpeg", fmt="webp")
        self.assertEqual(jack.albumart.discogs_image_id(url), "R-261718-1449656596-1124")

    def test_other_urls_give_none(self):
        self.assertIsNone(jack.albumart.discogs_image_id("https://coverartarchive.org/release/d8add909/22042063020.jpg"))
        self.assertIsNone(jack.albumart.discogs_image_id("https://i.discogs.com/R-261718-1449656596-1124.jpeg"))
        self.assertIsNone(jack.albumart.discogs_image_id("https://i.discogs.com/"))


class ExistingFiles(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)
        for name in ("jack.discogs.primary.R-261718-1449656596-1124.jpg",
                     "jack.discogs.secondary.R-261718-1449656583-2643.jpg",
                     "jack.discogs.R-99-1-1.png",
                     "jack.saved.0123456789abcdef0123456789abcdef.jpeg",
                     "jack.caa.front.large.jpg"):
            open(name, "w").close()

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def test_stem_match_with_and_without_type(self):
        self.assertEqual(jack.albumart.existing_file_with_stem("jack.discogs.", "R-261718-1449656596-1124"),
                         "jack.discogs.primary.R-261718-1449656596-1124.jpg")
        self.assertEqual(jack.albumart.existing_file_with_stem("jack.discogs.", "R-99-1-1"), "jack.discogs.R-99-1-1.png")

    def test_stem_match_ignores_other_ids_and_prefixes(self):
        self.assertIsNone(jack.albumart.existing_file_with_stem("jack.discogs.", "R-261718-1449656596-1125"))
        self.assertIsNone(jack.albumart.existing_file_with_stem("jack.discogs.", "0123456789abcdef0123456789abcdef"))

    def test_files_for_release(self):
        self.assertEqual(jack.albumart.discogs_files_for_release("jack.discogs.", "261718"),
                         ["jack.discogs.primary.R-261718-1449656596-1124.jpg",
                          "jack.discogs.secondary.R-261718-1449656583-2643.jpg"])
        self.assertEqual(jack.albumart.discogs_files_for_release("jack.discogs.", "2617"), [])
        self.assertEqual(jack.albumart.discogs_files_for_release("jack.discogs.", "99"), ["jack.discogs.R-99-1-1.png"])


if __name__ == "__main__":
    unittest.main()
