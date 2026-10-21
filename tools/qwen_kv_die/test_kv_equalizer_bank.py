"""Long equalizer row-bank physical and latency invariants."""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_bundle_eq as E


def inst(name, master, x, y, w, h, orient, **kw):
    return NS(name=name, master=master, x=x, y=y, w=w, h=h, orient=orient, **kw)


class RowBank(unittest.TestCase):
    def setUp(self):
        self.K = NS(GX=.432, GY=2.16, SHAVE=.02,
                    up=lambda x, g: math.ceil((x - 1e-9) / g) * g, F=NS(Inst=inst))
        self.m = dict(die=dict(w=1200, h=1200), insts=[], keepouts=[])

    def test_39_stage_bank_physical(self):
        source, sink = (400, 500), (600, 500)
        out = E._place_pad_bank(self.K, self.m, [], source, sink, 39, 12.98, 12.98, 400)
        self.assertEqual(len(out), 39)
        self.assertIn('MY', {i.orient for i in out})
        pt = source
        for j, i in enumerate(out):
            self.assertAlmostEqual(i.x / self.K.GX, round(i.x / self.K.GX))
            self.assertAlmostEqual(i.y / self.K.GY, round(i.y / self.K.GY))
            a = (i.x + (i.w if i.orient == 'MY' else 0), i.y + i.h / 2)
            b = (i.x + (0 if i.orient == 'MY' else i.w), i.y + i.h / 2)
            self.assertLessEqual(abs(a[0] - pt[0]) + abs(a[1] - pt[1]), 400)
            self.assertTrue(E._free(self.m, out[:j], i.x, i.y, i.w, i.h))
            pt = b
        self.assertLessEqual(abs(pt[0] - sink[0]) + abs(pt[1] - sink[1]), 400)
    def test_no_bank_inside_block_or_keepout(self):
        self.m['keepouts'] = [('closed', 0, 0, 1200, 1200)]
        self.assertIsNone(E._place_pad_bank(self.K, self.m, [], (400, 500), (600, 500),
                                          39, 12.98, 12.98, 400))

    def test_unreachable_endpoints_are_refused(self):
        self.assertIsNone(E._place_pad_bank(self.K, self.m, [], (0, 0), (1100, 1100),
                                          39, 12.98, 12.98, 50))


if __name__ == '__main__':
    unittest.main()
