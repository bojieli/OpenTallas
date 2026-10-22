"""QK3-PHYCLK: boundary R 0 only for a pin-referenced Liberty boundary; mutants refused."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import boundary_targets as B   # noqa: E402

REPO = HERE.parents[1]
KPHY = 'ot_qkvd_ucie_x64_phy'
KDIR = REPO / 'physical/qwen_kv_die_phy' / KPHY
ELEM = '''library (qfd_elements_%s) {
  cell (qkd_frame) { area : 0;
    bus (ck) { bus_type : b1; direction : input; clock : true; capacitance : 2.0; }
    bus (d) { bus_type : b1; direction : input; capacitance : 0.7; timing () { related_pin : "ck[0]"; timing_type : setup_rising; } }
    bus (q) { bus_type : b1; direction : output; timing () { related_pin : "ck[0]"; timing_type : rising_edge; } }
  }
}
'''


class BoundaryTargets(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.libs = Path(t.name)
        for c in ('tt', 'ff', 'ss'):
            shutil.copy(KDIR / f'{KPHY}_{c}.lib', self.libs / f'qfd_etm_{KPHY}_{c}.lib')
            (self.libs / f'qfd_elements_{c}.lib').write_text(ELEM % c)
        self.clocks = dict(assumed_ideal=[KPHY, 'qkd_frame'], measured={})

    def run_complete(self):
        t = dict(schema='opentallas.die_clock.targets.v1', masters={'m': {'insertion_per_clock_pin_ps': {'ck[0]': [1, 2, 3]}}})
        return t, B.complete(self.clocks, self.libs, t)

    def test_kphy_and_element_admitted_at_r0_labelled(self):
        t, added = self.run_complete()
        self.assertEqual(added, {KPHY: B.PHY_CLASS, 'qkd_frame': B.ELEM_CLASS})
        self.assertEqual(t['masters'][KPHY]['insertion_per_clock_pin_ps'], {'clk': [0.0, 0.0, 0.0]})
        self.assertEqual(t['masters']['qkd_frame']['insertion_per_clock_pin_ps'], {'ck[0]': [0.0, 0.0, 0.0]})
        self.assertEqual(t['assumed'], [KPHY, 'qkd_frame'])
        self.assertEqual(t['masters']['m']['insertion_per_clock_pin_ps'], {'ck[0]': [1, 2, 3]})   # measured untouched
        self.assertEqual(json.loads((KDIR / f'{KPHY}.json').read_text())['views'][f'{KPHY}_tt.lib'],
                         t['masters'][KPHY]['liberty']['tt']['sha256'])

    def test_build_lookup_accepts_completed_targets(self):
        t, _ = self.run_complete()
        p = self.libs / 'targets.json'; p.write_text(json.dumps(t))
        import importlib.util
        src = (HERE / 'build.py').read_text()
        fn = src[src.index('def load_targets'):src.index('\ndef build(')]
        g = {'json': json, 'Path': Path, 'math': __import__('math')}
        exec(fn, g)
        v = g['load_targets'](str(p))
        self.assertEqual(v(KPHY, 'clk'), [0.0, 0.0, 0.0])
        self.assertEqual(v('qkd_frame', 'ck'), [0.0, 0.0, 0.0])

    def test_tree_path_refused(self):
        f = self.libs / f'qfd_etm_{KPHY}_ff.lib'
        f.write_text(f.read_text().replace('clock : true;', 'clock : true; max_clock_tree_path (rise) { }', 1))
        with self.assertRaisesRegex(ValueError, 'clock_tree_path'):
            self.run_complete()

    def test_arc_on_non_clock_pin_refused(self):
        f = self.libs / 'qfd_elements_tt.lib'
        f.write_text(f.read_text().replace('related_pin : "ck[0]"; timing_type : rising_edge', 'related_pin : "d[0]"; timing_type : rising_edge'))
        with self.assertRaisesRegex(ValueError, 'non-clock'):
            self.run_complete()

    def test_missing_corner_refused(self):
        (self.libs / f'qfd_etm_{KPHY}_ss.lib').unlink()
        with self.assertRaisesRegex(ValueError, 'ss cell in 0 libs'):
            self.run_complete()


class ComputeKphy(unittest.TestCase):
    def test_opt_in_exact_profile(self):
        sys.path.insert(0, str(REPO / 'tools/qwen_tp8'))
        import die_sta_libs as D
        libs = {c: f'physical/qwen_kv_die_phy/{KPHY}/{KPHY}_{c}.lib' for c in ('tt', 'ff', 'ss')}
        with patch.dict(os.environ, {'OT_KPHY_BOUNDARY_MODEL': '0'}):
            self.assertIsNone(D.kphy_boundary_model(KPHY, REPO, KDIR, libs))
        with patch.dict(os.environ, {'OT_KPHY_BOUNDARY_MODEL': '1'}):
            r = D.kphy_boundary_model(KPHY, REPO, KDIR, libs)
            self.assertEqual(r['reference_kind'], 'LIBERTY_ARCS_PIN_REFERENCED')
            self.assertIsNone(D.kphy_boundary_model('other', REPO, KDIR, libs))
            t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
            v = Path(t.name)
            for f in KDIR.iterdir():
                shutil.copy(f, v / f.name)
            (v / f'{KPHY}_tt.lib').write_text((v / f'{KPHY}_tt.lib').read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'approved'):
                D.kphy_boundary_model(KPHY, REPO, v, libs)


if __name__ == '__main__':
    unittest.main()
