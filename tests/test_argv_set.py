"""tests for the --set option

Run from the top of the source tree with:

    python3 -m unittest discover tests
"""

import unittest

import jack.globals
import jack.argv
from jack.config import cf


def parse(*args):
    dummy, argv_cf, dummy = jack.argv.parse_argv(cf, ["jack", *args])
    return {key: entry['val'] for key, entry in argv_cf.items()}


class Set(unittest.TestCase):

    def test_set_is_the_long_option(self):
        self.assertEqual(parse("--set", "bitrate", "192"), parse("--bitrate", "192"))

    def test_set_with_equal_sign(self):
        self.assertEqual(parse("--set", "bitrate=192"), {'bitrate': 192})

    def test_set_bool_takes_the_next_argument(self):
        self.assertEqual(parse("--set", "vbr", "no", "--bitrate", "128"), {'vbr': False, 'bitrate': 128})

    def test_set_bool_with_equal_sign_leaves_the_next_argument_alone(self):
        self.assertEqual(parse("--set", "vbr=no", "--bitrate", "128"), {'vbr': False, 'bitrate': 128})


if __name__ == "__main__":
    unittest.main()
