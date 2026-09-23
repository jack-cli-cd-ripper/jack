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
# the kernel's view of the same disc: 11 tracks, the last one data
KERNEL = (1, 11, 230657, [(150, False), (13733, False), (31019, False), (42517, False), (62385, False),
                          (80537, False), (96577, False), (102028, False), (119828, False), (135361, False),
                          (180720, True)])


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

    def test_the_kernel_toc_gives_the_same_line(self):
        self.assertEqual(jack.rawtoc.format_line(*KERNEL),
                         jack.rawtoc.from_tracks(read_toc("jack.toc"), data_tracks=(11,)))

    def test_decode_entry(self):
        # cdte_adr 1 in the low nibble, cdte_ctrl 4 (data) in the high one
        buf = jack.rawtoc.TOCENTRY.pack(11, 0x41, jack.rawtoc.CDROM_LBA, 180570, 0)
        self.assertEqual(jack.rawtoc.decode_entry(buf), (180720, True))
        buf = jack.rawtoc.TOCENTRY.pack(1, 0x01, jack.rawtoc.CDROM_LBA, 0, 0)
        self.assertEqual(jack.rawtoc.decode_entry(buf), (150, False))
        self.assertEqual(jack.rawtoc.TOCENTRY.size, 12)

    def test_agrees_with_a_plain_audio_cd(self):
        tracks = read_toc("jack.toc.rerip")
        first, last, leadout, offsets = KERNEL
        audio = (1, 10, 169320, offsets[:-1])
        self.assertTrue(jack.rawtoc.agrees_with(audio, tracks))

    def test_disagrees_on_a_data_track(self):
        self.assertFalse(jack.rawtoc.agrees_with(KERNEL, read_toc("jack.toc.rerip")))

    def test_disagrees_on_the_lead_out(self):
        first, last, leadout, offsets = KERNEL
        self.assertFalse(jack.rawtoc.agrees_with((1, 10, 169321, offsets[:-1]), read_toc("jack.toc.rerip")))

    def test_disagrees_on_an_offset(self):
        first, last, leadout, offsets = KERNEL
        offsets = [(150, False), (13734, False)] + offsets[2:-1]
        self.assertFalse(jack.rawtoc.agrees_with((1, 10, 169320, offsets), read_toc("jack.toc.rerip")))

    def test_read_kernel_toc_is_none_without_a_drive(self):
        # not a cdrom device, and no such file: both are simply "no raw TOC"
        self.assertIsNone(jack.rawtoc.read_kernel_toc(os.devnull))
        self.assertIsNone(jack.rawtoc.read_kernel_toc(os.path.join(FIXTURES, "no-such-device")))


if __name__ == "__main__":
    unittest.main()
