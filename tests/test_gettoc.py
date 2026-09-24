"""tests for the TOC reader cache

Run from the top of the source tree with:

    python3 -m unittest discover tests
"""

import unittest

import jack.globals
import jack.functions
import jack.helpers

TRACK = [1, 100, 0, 0, 0, 2, 1, 0, "x", None, None]


class GetTocCache(unittest.TestCase):
    """two fake readers stand in for libdiscid and cdparanoia -Q"""

    def setUp(self):
        self.reads = []
        jack.functions.test_reads = self.reads
        jack.helpers.helpers["fake-reader"] = {
            "type": "toc-reader",
            "toc_fkt": "test_reads.append('fake-reader'); erg.append(list(TRACK))",
        }
        jack.helpers.helpers["fake-ripper"] = {
            "type": "ripper",
            "toc_cmd": "true",
            "toc_fkt": "test_reads.append('fake-ripper')",
        }
        jack.functions.TRACK = TRACK
        jack.functions.cached_erg.clear()

    def tearDown(self):
        del jack.helpers.helpers["fake-reader"]
        del jack.helpers.helpers["fake-ripper"]
        jack.functions.cached_erg.clear()

    def test_reads_each_reader_once(self):
        "the order of a fresh rip: reader, ripper, reader again in check_cd"
        first = jack.functions.gettoc("fake-reader")
        jack.functions.gettoc("fake-ripper")
        again = jack.functions.gettoc("fake-reader")
        self.assertEqual(self.reads, ["fake-reader", "fake-ripper"])
        self.assertIs(again, first)

    def test_returns_the_track_list(self):
        self.assertEqual(jack.functions.gettoc("fake-reader"), [TRACK])


if __name__ == "__main__":
    unittest.main()
