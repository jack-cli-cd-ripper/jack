"""tests for --repair-toc

Run from the top of the source tree with:

    python3 -m unittest discover tests

The fixture is a real pair: the toc and progress file of a rip made
before jack used libdiscid, and the toc of a fresh rip of the same disc.
"""

import os
import tempfile
import unittest

import jack.globals
import jack.functions
import jack.metadata
import jack.prepare
from jack.constants import ISRC, MCN

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "phoenix-alphabetical")
SEP = "/|\\"
# the disc as the drive reports it, taken from the old toc: 11 tracks, the
# last one data, and the real lead-out behind it
RAWTOC = "1 11 230657 150 13733 31019 42517 62385 80537 96577 102028 119828 135361 180720d"


def read_toc(name):
    tracks, dummy, dummy = jack.functions.cdrdao_gettoc(os.path.join(FIXTURES, name), silent=True)
    return tracks


def read_lines(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read().splitlines()


class RepairDatatrackToc(unittest.TestCase):

    def setUp(self):
        self.tracks = read_toc("jack.toc")
        self.lines = read_lines("jack.progress")

    def repair(self, tracks=None, lines=None):
        return jack.prepare.repair_datatrack_toc(tracks or self.tracks, lines or self.lines, SEP)

    def test_repaired_toc_matches_the_rerip(self):
        tracks, dummy = self.repair()
        expected = read_toc("jack.toc.rerip")
        for track in expected:
            track[ISRC] = None  # ISRCs cannot be recovered without the disc
        self.assertEqual(tracks, expected)

    def test_disc_ids_match_the_rerip(self):
        tracks, dummy = self.repair()
        cd_id = jack.metadata.metadata_id(tracks)
        self.assertEqual(cd_id['musicbrainzngs'], "AQ3JU.INC2Lq5ZJE.yC4lVNjcdM-")
        self.assertEqual(cd_id['cddb'], "7d08cf0a")

    def test_only_the_correction_lines_are_removed(self):
        dummy, lines = self.repair()
        expected = [l for l in self.lines
                    if not l.startswith("11" + SEP + "off" + SEP)
                    and not l.startswith("10" + SEP + "patch" + SEP)]
        self.assertEqual(lines[:-1], expected)
        self.assertLess(len(lines), len(self.lines))

    def test_the_old_toc_is_kept_as_a_rawtoc_line(self):
        dummy, lines = self.repair()
        self.assertEqual(lines[-1], "all" + SEP + "rawtoc" + SEP + RAWTOC)
        self.assertEqual(len([l for l in lines if SEP + "rawtoc" + SEP in l]), 1)

    def test_written_toc_reads_back(self):
        tracks, dummy = self.repair()
        with tempfile.TemporaryDirectory() as dir:
            path = os.path.join(dir, "jack.toc")
            jack.functions.cdrdao_puttoc(path, tracks, jack.metadata.metadata_id(tracks))
            again, dummy, dummy = jack.functions.cdrdao_gettoc(path, silent=True)
            self.assertEqual(again, tracks)
            with open(path) as f:
                self.assertIn("// DB-ID=7d08cf0a\n", f.read())

    def test_isrcs_and_mcn_are_preserved(self):
        # old tocs have none, but a toc that has them must keep them
        for num, track in enumerate(self.tracks):
            track[ISRC] = "FRS6303000%02d" % num
        self.tracks[0][MCN] = "0724359863528"
        tracks, dummy = self.repair()
        with tempfile.TemporaryDirectory() as dir:
            path = os.path.join(dir, "jack.toc")
            jack.functions.cdrdao_puttoc(path, tracks, jack.metadata.metadata_id(tracks))
            again, dummy, dummy = jack.functions.cdrdao_gettoc(path, silent=True)
        self.assertEqual([t[ISRC] for t in again], [t[ISRC] for t in self.tracks[:-1]])
        self.assertEqual(again[0][MCN], "0724359863528")

    def test_the_input_is_not_modified(self):
        before = [t[:] for t in self.tracks]
        self.repair()
        self.assertEqual(self.tracks, before)

    def refuses(self, tracks=None, lines=None):
        with self.assertRaises(ValueError):
            self.repair(tracks, lines)

    def test_refuses_without_a_non_audio_track(self):
        self.refuses(lines=[l for l in self.lines if SEP + "off" + SEP not in l])

    def test_refuses_a_data_track_that_is_not_last(self):
        self.refuses(lines=[l.replace("11" + SEP + "off", "05" + SEP + "off") for l in self.lines])

    def test_refuses_a_second_non_audio_track(self):
        self.refuses(lines=self.lines + ["05" + SEP + "off" + SEP + "non-audio"])

    def test_refuses_without_a_length_correction(self):
        self.refuses(lines=[l for l in self.lines if SEP + "patch" + SEP not in l])

    def test_refuses_an_unexpected_length_correction(self):
        self.refuses(lines=[l.replace("-> 33959", "-> 33958") for l in self.lines])

    def test_refuses_any_other_patch(self):
        self.refuses(lines=self.lines + ["03" + SEP + "patch" + SEP + "START 100 -> 101"])


if __name__ == "__main__":
    unittest.main()
