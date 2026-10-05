"""Static checks of the b3r2 die source (no flow is launched)."""
import collections
import re
import tempfile
import unittest
from pathlib import Path

import qwen_rom_fulldie_b3r2 as R


def _case(band):
    v, m = R.selected(True, band=band[0], area_pins=band[1])
    d = Path(tempfile.mkdtemp())
    v.case_grt(m, d, 16, 't', 1)
    return v, m, d


class B3R2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {b: _case(b) for b in ((False, False), (True, False), (True, True))}

    def test_default_off(self):
        with self.assertRaises(ValueError):
            R.selected()

    def test_every_abstract_has_signal_pins(self):
        for band, (_, _, d) in self.cases.items():
            lef = (d / 'elements.lef').read_text()
            empty = [n for n, b in re.findall(r'MACRO (\S+)\n(.*?)END \1\n', lef, re.S) if 'USE SIGNAL' not in b]
            self.assertEqual(empty, [], band)

    def test_no_pin_has_two_nets(self):
        for band, (_, _, d) in self.cases.items():
            v = (d / 'die.v').read_text()
            for m in re.finditer(r'\n  (\S+) (\S+) \((.*?)\);', v):
                c = collections.Counter(re.findall(r'\.(\S+?)\(', m.group(3)))
                self.assertFalse([p for p, n in c.items() if n > 1], (band, m.group(2)))

    def test_every_port_group_mapped(self):
        for band, (_, m, _) in self.cases.items():
            gm = m['b3r2']['groups']
            self.assertEqual(sorted(gm['port']), list(range(96)))
            self.assertEqual(sorted(gm['scale']), list(range(96)))

    def test_widths_area_fifo(self):
        for band, (v, m, _) in self.cases.items():
            self.assertEqual(v.CORRIDOR_BITS, 388)
            self.assertEqual(v.TAP_BITS, 325)
            self.assertAlmostEqual(v.VCH, 260.064)
            self.assertLessEqual(m['die']['mm2'], 858)
            self.assertAlmostEqual(R.fifo_accounting(v, m)['total_mm2'], 2.53, places=2)

    def test_band_cut_below_b2(self):
        _, m, _ = self.cases[(True, True)]
        cut = R.spine_cut(m, [8800])['8800']['total']
        self.assertLess(cut, 35840 / 2)


if __name__ == '__main__':
    unittest.main()
