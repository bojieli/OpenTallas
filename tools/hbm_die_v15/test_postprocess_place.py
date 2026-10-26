import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('postprocess_place', Path(__file__).with_name('postprocess_place.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ActualPinAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        lef = self.root / 'hbfd_rly_test.lef'
        lef.write_text('''MACRO hbfd_rly_test
 SIZE 10 BY 10 ;
 PIN i
 DIRECTION INPUT ;
 PORT
 RECT 0 4 1 6 ;
 END
 END i
 PIN o
 DIRECTION OUTPUT ;
 PORT
 RECT 9 4 10 6 ;
 END
 END o
END hbfd_rly_test
''')
        self.contract = dict(instances={n: dict(master='hbfd_rly_test', ports=dict(i=dict(bits=1), o=dict(bits=1)))
                                        for n in ('a', 'b')},
                             edges=[dict(source=['a', 'o', 0, 1], sink=['b', 'i', 0, 1], bits=1)], clock_resets=[])
        self.man = dict(placement={n: dict(m='hbfd_rly_test', x=x, y=0, w=10, h=10, o='R0')
                                   for n, x in [('a', 0), ('b', 450)]},
                        excluded_instances=[], consumed_view_sha256={lef.name: p.sha(lef)}, die_um=[1000,1000])

    def test_positive_and_displaced_mutant(self):
        good = p.audit(self.man, self.contract, self.root, 500)
        self.assertEqual(good['worst']['max_pin_manhattan_um'], 441)
        bad = copy.deepcopy(self.man)
        bad['placement']['b']['x'] += 100
        self.assertEqual(p.audit(bad, self.contract, self.root, 500)['counts']['over_limit_edges'], 1)

    def test_missing_relay_never_excluded(self):
        del self.man['placement']['b']
        self.man['excluded_instances'] = ['b']
        with self.assertRaisesRegex(ValueError, 'relay_missing'):
            p.audit(self.man, self.contract, self.root, 500)

    def test_consumed_lef_drift_refused(self):
        with (self.root/'hbfd_rly_test.lef').open('a') as f:
            f.write('# changed\n')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            p.audit(self.man, self.contract, self.root, 500)

    def test_mirror_changes_physical_pin_reach(self):
        self.man['placement']['b']['o'] = 'MY'
        self.assertEqual(p.audit(self.man, self.contract, self.root, 500)['worst']['max_pin_manhattan_um'], 450)

    def test_literal_clock_bus_and_real_root(self):
        self.contract['clock_resets'] = [dict(instance='b', port='ckv', bits=2, kind='clock', source=['a', 'pll_stream'])]
        p.export_def(self.man, self.contract, self.root)
        text = (self.root/'place_only.def').read_text()
        self.assertIn('( a pll_stream )', text)
        self.assertIn('( b ckv[1] )', text)
        self.assertEqual(json.loads((self.root/'literal_clocks.json').read_text())['clock_entries'], 2)
        self.contract['clock_resets'].append(self.contract['clock_resets'][0])
        with self.assertRaisesRegex(ValueError, 'assigned twice'):
            p.export_def(self.man, self.contract, self.root)


if __name__ == '__main__':
    unittest.main()
