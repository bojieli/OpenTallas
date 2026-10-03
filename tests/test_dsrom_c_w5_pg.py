import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('w5', ROOT / 'tools/dsrom_c_w5_pg.py')
w5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w5)


class W5ModelTest(unittest.TestCase):
    def test_missing_wake_is_unknown(self):
        self.assertIsNone(w5.wake_price({'lead_cycles': 8000})['added_cycles'])

    def test_serial_cost_and_late_wake(self):
        c = dict(prewake_route_cycles=1, inrush_wait_cycles=3, powergood_cycles=2,
                 relock_cycles=4, guard_cycles=2, release_cycles=1, lead_cycles=12)
        self.assertEqual(w5.wake_price(c)['added_cycles'], 1)
        c['lead_cycles'] = 13
        self.assertEqual(w5.wake_price(c)['added_cycles'], 0)
        c['powergood_cycles'] = None
        self.assertIsNone(w5.wake_price(c)['added_cycles'])

    def test_invalid_cycles(self):
        for value in (-1, 0.5, True):
            with self.assertRaises(ValueError):
                w5.wake_price({'lead_cycles': value})

    def test_actual_successor_and_debt_union(self):
        mapping = {'domains': [{'id': 'A', 'kind': 'stage'}, {'id': 'Z', 'kind': 'stage'},
                               {'id': 'B', 'kind': 'stage'}, {'id': 'E', 'kind': 'engram'},
                               {'id': 'AZ', 'kind': 'link', 'endpoints': ['A', 'Z']}],
                   'successors': {'A': 'Z', 'Z': 'B', 'B': 'A'}}
        ticks = [{'busy': ['A'], 'live_debt': ['B']}, {'busy': [], 'live_debt': ['Z']}]
        r = w5.occupancy(mapping, ticks)
        self.assertEqual(r['A']['awake_cycles'], 1)
        self.assertEqual(r['Z']['awake_cycles'], 2)
        self.assertEqual(r['AZ']['awake_cycles'], 2)
        self.assertEqual(r['B']['awake_cycles'], 1)
        self.assertEqual(r['E']['awake_cycles'], 2)
        # The simplistic batch+one formula misses the retained B debt.
        self.assertEqual(sum(v['awake_cycles'] for k, v in r.items() if k in ('A', 'Z', 'B')), 4)

    def test_invalid_map(self):
        with self.assertRaises(ValueError):
            w5.occupancy({'domains': [{'id': 'A', 'kind': 'stage'}], 'successors': {'A': 'missing'}}, [{}])

    def test_liberty_units_states_and_no_off_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'fixture_SS.lib'
            p.write_text('library(x){leakage_power_unit:"1nW"; cell(DFF){area:291600; '
                         'cell_leakage_power:2; leakage_power(){when:"A";value:5;} '
                         'leakage_power(){when:"!A";value:3;}}}')
            palette = w5.liberty_palette([p])
            self.assertAlmostEqual(palette['cells']['DFF/SS']['on_rail_max_state_W'], 5e-9)
            self.assertIsNone(palette['cells']['DFF/SS']['off_rail_W'])
            p.write_text('library(x){cell(DFF){cell_leakage_power:2;}}')
            with self.assertRaises(ValueError):
                w5.liberty_palette([p])

    def test_baseline_preserved_and_savings_not_qualified(self):
        path = ROOT / 'results/uarch/dsrom_return_storage_hbm_20261003/model.json'
        before = path.read_bytes()
        model = w5.compose(json.loads(before), json.loads((ROOT / 'configs/hardware/dsrom_c_w5_pg.json').read_text()))
        self.assertFalse(model['gates']['adopted'])
        self.assertIsNone(model['leakage']['qualified_static_kw'])
        self.assertIsNone(model['per_context']['1048576']['AR_tok_s_conditional'])
        self.assertFalse(model['leakage']['legacy_10pct_adopted'])
        self.assertEqual(model['leakage']['Engram_always_on_W_model'], 3324.4)
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
