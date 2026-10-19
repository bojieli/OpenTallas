"""KVR-PLACE2 10-19: a bound view whose boundary reference is the NATIVE-REF child_flop mean (a parent with hard
children: the expanded ASTK qkd_astk_ep_s) is a MEASURED reference for die STA; a lib midrange never is."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from qwen_tp8.die_sta_libs import measured_clock_refs   # noqa: E402

VD = ROOT / 'physical/ref_tile/qkd_astk_ep_s/views/qkd_astk_ep_s'


@unittest.skipUnless((VD / 'insertion.json').is_file(), 'qkd_astk_ep_s view not checked out')
class MeasuredRefs(unittest.TestCase):
    def test_child_flop_boundary_mean_is_measured(self):
        for c in ('tt', 'ff'):
            refs = measured_clock_refs(VD / f'qkd_astk_ep_s_{c}.lib', VD / 'insertion.json', c)
            self.assertIn('ck', refs)
            self.assertGreater(refs['ck'], 100.0)

    def test_missing_insertion_refuses(self):
        with self.assertRaises(ValueError):
            measured_clock_refs(VD / 'qkd_astk_ep_s_tt.lib', VD / 'no_such_insertion.json', 'tt')


if __name__ == '__main__':
    unittest.main()
