"""tests for the track order used by the reorder option

Run from the top of the source tree with:

    python3 -m unittest discover tests
"""

import os
import unittest

import jack.globals
import jack.functions
import jack.utils
from jack.constants import NUM, LEN

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "phoenix-alphabetical")


class Reorder(unittest.TestCase):

    def test_track_len_orders_by_length(self):
        tracks, dummy, dummy = jack.functions.cdrdao_gettoc(os.path.join(FIXTURES, "jack.toc"), silent=True)
        by_len = sorted(tracks, key=jack.utils.track_len)
        self.assertEqual([t[LEN] for t in by_len], sorted(t[LEN] for t in tracks))
        # the fixture's shortest and longest tracks, as a guard against a key on the wrong field
        self.assertEqual(by_len[0][NUM], 7)
        self.assertEqual(by_len[-1][NUM], 11)

    def test_reverse_puts_longest_first(self):
        tracks, dummy, dummy = jack.functions.cdrdao_gettoc(os.path.join(FIXTURES, "jack.toc"), silent=True)
        tracks.sort(key=jack.utils.track_len)
        tracks.reverse()
        self.assertEqual(tracks[0][NUM], 11)


if __name__ == "__main__":
    unittest.main()
