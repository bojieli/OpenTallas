"""KV-GEN8 10-19: GEN7 real case 'qkd_astk_ep_s MY x has no legal origin' is caught and adapted in prep."""
import tempfile
import unittest
from pathlib import Path

import kv_place_orient as P


def ep_like(mixed=True):
    # zi face bus on both vertical layers, as the closed qkd_astk_ep_s view (M3 x%36==9, M5 x%48==12)
    pins = [dict(name='zi[0]', use='SIGNAL', rects=[('M3', (1620, 0, 1638, 38))])]
    if mixed:
        pins.append(dict(name='zi[1]', use='SIGNAL', rects=[('M5', (1716, 0, 1740, 38))]))
    return dict(name='ep', W=162000, H=345600, pins=pins)


LEF = '''MACRO ep
  CLASS BLOCK ;
  SIZE 162 BY 345.6 ;
  PIN zi[0]
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M3 ;
        RECT  1.62 0 1.638 0.038 ;
    END
  END zi[0]
  PIN zi[1]
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  1.716 0 1.74 0.038 ;
    END
  END zi[1]
END ep
'''


class PlaceOrientTest(unittest.TestCase):
    def test_mixed_m3_m5_x_mirror_adapted_keep_y(self):
        txt = 'ot_mts::place [$_blk findInst a] 1 2 MY\not_mts::place [$_blk findInst b] 3 4 R180\not_mts::place [$_blk findInst c] 5 6 MX'
        out, rep = P.adapt(txt, {'a': 'ep', 'b': 'ep', 'c': 'ep'}, {'ep': ep_like()})
        self.assertEqual(out.split('\n'), ['ot_mts::place [$_blk findInst a] 1 2 R0',
                                           'ot_mts::place [$_blk findInst b] 3 4 MX',
                                           'ot_mts::place [$_blk findInst c] 5 6 MX'])
        self.assertEqual(rep['verdict'], 'PASS')
        self.assertEqual(rep['per_master'], {'ep MY->R0': 1, 'ep R180->MX': 1})
        self.assertEqual(rep['changes'][0]['max_pin_x_displacement_um'], 162.0)

    def test_single_layer_mirror_kept(self):
        txt = 'ot_mts::place [$_blk findInst a] 1 2 MY'
        out, rep = P.adapt(txt, {'a': 'ep'}, {'ep': ep_like(False)})
        self.assertEqual(out, txt)
        self.assertEqual(rep['changes'], [])
        self.assertEqual(rep['checked'], 1)

    def test_offtrack_view_refused(self):
        m = ep_like()
        m['pins'][0]['rects'].append(('M3', (1621, 100, 1639, 138)))
        _, rep = P.adapt('ot_mts::place [$_blk findInst a] 1 2 R0', {'a': 'ep'}, {'ep': m})
        self.assertEqual(rep['verdict'], 'FAIL')
        self.assertEqual(rep['refused'][0]['instance'], 'a')

    def test_unknown_master_untouched(self):
        txt = 'ot_mts::place [$_blk findInst a] 1 2 MY'
        out, rep = P.adapt(txt, {'a': 'other'}, {'ep': ep_like()})
        self.assertEqual(out, txt)
        self.assertEqual(rep['checked'], 0)

    def test_case_cli_rewrites_and_backs_up(self):
        with tempfile.TemporaryDirectory() as t:
            c = Path(t)
            (c / 'place.tcl').write_text('ot_mts::place [$_blk findInst u_ep] 10 20 MY\n')
            (c / 'die.v').write_text('module d();\n  ep u_ep (.x(n));\nendmodule\n')
            (c / 'elements.lef').write_text(LEF)
            self.assertEqual(P.main(['--case', str(c)]), 0)
            self.assertIn('10 20 R0', (c / 'place.tcl').read_text())
            self.assertIn('10 20 MY', (c / 'place.tcl.preorient').read_text())
            self.assertTrue((c / 'place_orientations.json').exists())
            # check-only reports without rewriting
            (c / 'place.tcl').write_text('ot_mts::place [$_blk findInst u_ep] 10 20 MY\n')
            self.assertEqual(P.main(['--case', str(c), '--check-only', '--report', str(c / 'r.json')]), 0)
            self.assertIn('10 20 MY', (c / 'place.tcl').read_text())


if __name__ == '__main__':
    unittest.main()
