"""Selected pair-image start offsets survive the native target-11 rebuild."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static_programme as C


class LinkCalendarOffset(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, 'image.svh')
            p.write_text(text)
            return C.image_calendar_offset(p)

    def test_historical_image_omits_offset(self):
        self.assertEqual(self.read('localparam integer D2D_ADM_OFS = 72;'), 0)

    def test_signed_clock_anchor_difference(self):
        self.assertEqual(self.read('localparam integer D2D_CAL_OFS = -2;'), -2)
        self.assertEqual(self.read('localparam integer D2D_CAL_OFS = +3;'), 3)

    def test_explicit_unknown_offset_fails(self):
        with self.assertRaises(SystemExit):
            self.read('localparam integer D2D_CAL_OFS = unknown;')

    def test_native_rebuild_uses_selected_image_offset(self):
        self.assertEqual(C.LINK_ARGS[C.LINK_ARGS.index('--ofs') + 1], str(C.image_calendar_offset()))


if __name__ == '__main__':
    unittest.main()
