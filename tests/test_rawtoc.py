"""tests for the rawtoc line in the progress file

Run from the top of the source tree with:

    python3 -m unittest discover tests
"""

import os
import unittest

import jack.globals
import jack.functions
import jack.rawtoc

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "phoenix-alphabetical")


def read_toc(name):
    tracks, dummy, dummy = jack.functions.cdrdao_gettoc(os.path.join(FIXTURES, name), silent=True)
    return tracks


class RawToc(unittest.TestCase):

    def test_format_line(self):
        line = jack.rawtoc.format_line(1, 3, 10000, [(150, False), (2000, True), (5000, False)])
        self.assertEqual(line, "1 3 10000 150 2000d 5000")

    def test_from_the_old_toc(self):
        # the old toc still has the data track and the real lead-out behind it
        line = jack.rawtoc.from_tracks(read_toc("jack.toc"), data_tracks=(11,))
        self.assertEqual(line, "1 11 230657 150 13733 31019 42517 62385 80537 96577 102028 119828 135361 180720d")

    def test_from_a_libdiscid_toc(self):
        # a toc read with libdiscid ends 11400 frames before the data track
        line = jack.rawtoc.from_tracks(read_toc("jack.toc.rerip"))
        self.assertEqual(line, "1 10 169320 150 13733 31019 42517 62385 80537 96577 102028 119828 135361")


if __name__ == "__main__":
    unittest.main()
