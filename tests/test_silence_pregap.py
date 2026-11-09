"""tests for reading the pregap of track 1 from a toc file

Run from the top of the source tree with:

    python3 -m unittest discover tests

jack 1.3 wrote the pregap of track 1 as a SILENCE statement and nothing
else. jack 2.99 switched to cdrdao's way, the pregap inside the FILE
length with a START statement, but its reader ignored SILENCE, so the
old rips kept their pregap only in "patch" progress lines from the
ripper. Both forms, and cdrdao's own SILENCE plus START, must read the
same.
"""

import os
import tempfile
import unittest

import jack.globals
import jack.functions
import jack.prepare
from jack.constants import NUM, LEN, START

HEAD = """CD_DA

// DB-ID=d30a5710

// Track 1
TRACK AUDIO
NO COPY
NO PRE_EMPHASIS
TWO_CHANNEL_AUDIO
"""

TAIL = """
// Track 2
TRACK AUDIO
NO COPY
NO PRE_EMPHASIS
TWO_CHANNEL_AUDIO
FILE "track_02.wav" 0 03:28:37

// Track 3
TRACK AUDIO
NO COPY
NO PRE_EMPHASIS
TWO_CHANNEL_AUDIO
FILE "track_03.wav" 0 02:46:53
"""

# the same disc, as jack 1.3, jack 2.99 and later, and cdrdao write it
JACK_1_3 = HEAD + 'SILENCE 00:00:33\nFILE "track_01.wav" 0 03:27:30\n' + TAIL
JACK_2_99 = HEAD + 'FILE "track_01.wav" 0 03:27:63\nSTART 00:00:33\n' + TAIL
CDRDAO = HEAD + 'SILENCE 00:00:33\nFILE "track_01.wav" 0 03:27:30\nSTART 00:00:33\n' + TAIL
NO_PREGAP = HEAD + 'SILENCE 00:00:00\nFILE "track_01.wav" 0 03:27:30\n' + TAIL

# "NUM LEN START" of the disc: track 1 starts 33 blocks in
TRACKS = [(1, 15555, 33), (2, 15637, 15588), (3, 12503, 31225)]


class ReadTrack1Pregap(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.silence_before = jack.globals.cf['_track_1_pregap_silence']

    def tearDown(self):
        self.tmpdir.cleanup()
        jack.globals.cf['_track_1_pregap_silence'] = self.silence_before

    def write(self, text):
        path = os.path.join(self.tmpdir.name, "jack.toc")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def read(self, text):
        jack.globals.cf['_track_1_pregap_silence'] = None
        tracks, dummy, pregap = jack.functions.cdrdao_gettoc(self.write(text), silent=True)
        return [(t[NUM], t[LEN], t[START]) for t in tracks], pregap

    def test_jack_1_3_silence_is_the_pregap(self):
        self.assertEqual(self.read(JACK_1_3), (TRACKS, 33))

    def test_jack_2_99_start(self):
        self.assertEqual(self.read(JACK_2_99), (TRACKS, 33))

    def test_cdrdao_silence_and_start(self):
        self.assertEqual(self.read(CDRDAO), (TRACKS, 33))

    def test_silence_of_zero_blocks(self):
        tracks = [(num, length, start - 33) for num, length, start in TRACKS]
        self.assertEqual(self.read(NO_PREGAP), (tracks, 0))

    def test_silence_is_remembered_for_image_files(self):
        "the image of a cdrdao SILENCE toc lacks the silent blocks"
        for text in (JACK_1_3, CDRDAO):
            self.read(text)
            self.assertEqual(jack.globals.cf['_track_1_pregap_silence'], 33)

    def test_jack_1_3_toc_round_trips_as_jack_2_99(self):
        tracks, dummy, dummy = jack.functions.cdrdao_gettoc(self.write(JACK_1_3), silent=True)
        path = os.path.join(self.tmpdir.name, "rewritten.toc")
        jack.functions.cdrdao_puttoc(path, tracks, {'cddb': "d30a5710"})
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), JACK_2_99 + "\n")


class ApplyPatch(unittest.TestCase):
    """"patch" progress lines against a track read from the toc"""

    def test_patch_corrects_the_track(self):
        track = [2, 15637, 15555, 0, 0, 2, 1, 0, "track_02", None, None]
        self.assertTrue(jack.prepare.apply_patch(track, "START 15555 -> 15588"))
        self.assertEqual(track[START], 15588)

    def test_patch_already_in_the_toc_is_accepted(self):
        track = [2, 15637, 15588, 0, 0, 2, 1, 0, "track_02", None, None]
        self.assertTrue(jack.prepare.apply_patch(track, "START 15555 -> 15588"))
        self.assertEqual(track[START], 15588)

    def test_patch_for_another_disc_is_refused(self):
        track = [2, 15637, 15000, 0, 0, 2, 1, 0, "track_02", None, None]
        self.assertFalse(jack.prepare.apply_patch(track, "START 15555 -> 15588"))
        self.assertEqual(track[START], 15000)


if __name__ == "__main__":
    unittest.main()
