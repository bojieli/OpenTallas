"""DIE-S81-LEAD 10-19: hop-0 forward cell follows the real data launch pins (case_p4l3_rv fclk FAIL: dsdv_bk_col's
vo_n pins 3.9 mm from the plan link point -> fclk 2 repeaters vs data 27)."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_rvcase as RV  # noqa: E402

LEF = '''VERSION 5.8 ;
MACRO blk
  SIZE 100.000 BY 50.000 ;
  PIN vo[1]
    DIRECTION OUTPUT ;
    PORT
      LAYER M4 ;
        RECT 40.000 49.900 40.100 50.000 ;
    END
  END vo[1]
  PIN vo[0]
    DIRECTION OUTPUT ;
    PORT
      LAYER M4 ;
        RECT 60.000 49.900 60.100 50.000 ;
    END
  END vo[0]
  PIN vi
    DIRECTION INPUT ;
    PORT
      LAYER M4 ;
        RECT 0.000 10.000 0.100 10.100 ;
    END
  END vi
END blk
END LIBRARY
'''


class Hop0(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'views').mkdir()
        (self.d / 'views' / 'blk.lef').write_text(LEF)

    def test_lef_pins(self):
        size, pins = RV.lef_pins(self.d / 'views' / 'blk.lef')
        self.assertEqual(size, (100.0, 50.0))
        self.assertEqual(pins['vo[1]'][2], 'OUTPUT')
        self.assertAlmostEqual(pins['vo[0]'][0], 60.05)

    def _case(self):
        insts = [('blk', 'u_b', {}, {}), ('BUFx8_ASAP7_75t_R', 'fwd_ln', {}, {}), ('dsfd_dvrlyh_2_SN', 'st_ln_0', {}, {})]
        ibits = {'u_b': {'vo': [('w_ln_src', 1), ('w_ln_src', 0)], 'vi': [('x', 0)]},
                 'fwd_ln': {'A': [('ck_r', 0)], 'Y': [('nln_fck', 0)]},
                 'st_ln_0': {'i': [('w_ln_src', 1), ('w_ln_src', 0)], 'ck': [('nln_fck', 0)]}}
        touch = {'w_ln_src': {'u_b', 'st_ln_0'}, 'nln_fck': {'fwd_ln', 'st_ln_0'}}
        # block at (1000, 1000); the plan link point (old forward cell) 3 mm above it
        loc = {'u_b': (1000.0, 1000.0, 100.0, 50.0, 'FIRM'), 'fwd_ln': (1050.0, 4000.0, 1.2, 0.6, 'PLACED'),
               'st_ln_0': (1040.0, 4010.0, 20.0, 20.0, 'FIRM')}
        placer = RV.Placer(40000.0, 40000.0)
        placer.add((1000.0, 1000.0, 1100.0, 1050.0))
        return insts, ibits, touch, loc, placer

    def test_forward_cell_moves_to_launch_pins(self):
        insts, ibits, touch, loc, placer = self._case()
        mv = RV.fwd_relocate(self.d, insts, ibits, touch, loc, placer, {'u_b': 'closed'}, {})
        x, y = loc['fwd_ln'][0] + 0.6, loc['fwd_ln'][1] + 0.3
        self.assertAlmostEqual(x, 1050.05, delta=1.0)          # centroid of vo[1] (1040) and vo[0] (1060)
        self.assertTrue(1050.0 < y < 1060.0)                    # just outside the N face, not 3 mm away
        self.assertGreater(mv['ln'][0], 2900)
        self.assertEqual(mv['ln'][1], 2)

    def test_untraceable_source_keeps_plan_point(self):
        insts, ibits, touch, loc, placer = self._case()
        (self.d / 'views' / 'blk.lef').unlink()
        mv = RV.fwd_relocate(self.d, insts, ibits, touch, loc, placer, {'u_b': 'closed'}, {})
        self.assertEqual(mv, {})
        self.assertEqual(loc['fwd_ln'][1], 4000.0)


if __name__ == '__main__':
    unittest.main()
