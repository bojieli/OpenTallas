#!/usr/bin/env python3
"""Q-COLLCAL3 10-18: the compiled collective calendar (lane_groups.collective_calendar) and the strict-bind period check
(lane_latency_audit (d)).  Real-lane TP8 bench (Verilator 5.050, results/rtl/qcollcal_rl_1018): GEN dv2f14bq LX 10/0/9
FAILS at LS 376 and PASSES at 377; the formula must give exactly 377 there."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import lane_groups as LG  # noqa: E402

RL = ROOT / 'results/rtl/qcollcal_rl_1018'


class CollectiveCalendar(unittest.TestCase):
    def test_rtl_defaults(self):
        d = LG.coll_rtl_defaults()
        self.assertEqual((d['PS'], d['LS'], d['LU'], d['RU'], d['RS0'], d['RS1'], d['RS2'], d['KC'], d['KW']),
                         (339, 376, 53, 5, 0, 0, 5, 4, 2))

    def test_no_lanes_matches_r5_lmin(self):
        c = LG.collective_calendar([0, 0, 0], dict(RS0=0, RS1=0, RS2=0, RU=0))
        self.assertEqual(c['LS'], 4 + 2 + 17 + 339)          # r5 L_min = KC + KW + 17 + PHY (bench --tight)
        self.assertEqual(c['LU'], 4 + 2 + 17 + 20)

    def test_production_lu(self):
        self.assertEqual(LG.collective_calendar([0, 0, 0])['LU'], 53)

    def test_dv2f14bq_needs_377(self):
        cll = json.loads((RL / 'gen_dv2f14bq/coll_lane_latency.json').read_text())
        c = LG.collective_calendar(cll['LX'])
        self.assertEqual((c['LS'], c['binding_port'], c['delta_vs_default']), (377, 0, 1))

    def test_dv2f14bi_needs_378(self):
        cll = json.loads((RL / 'gen_dv2f14bi/coll_lane_latency.json').read_text())
        self.assertEqual(LG.collective_calendar(cll['LX'])['LS'], 378)

    def test_gen_emits_ls_param(self):
        rec = LG.coll_lane_latency([], [], source='t')
        self.assertIn('LS', rec['params'])
        self.assertEqual(rec['params']['LS'], rec['calendar']['LS'])

    def test_strict_bind_witnesses(self):
        """committed lane_latency_audit runs on the dv2f14bq / dv2f14bi netlists: period < need FAILS (negative at 376)."""
        A = RL / 'calendar_audit'
        want = {('bq', 'asbuilt'): 'FAIL', ('bq', '376'): 'FAIL', ('bq', '377'): 'PASS', ('bq', '378'): 'PASS',
                ('bi', 'asbuilt'): 'FAIL', ('bi', '376'): 'FAIL', ('bi', '377'): 'FAIL', ('bi', '378'): 'PASS'}
        for (g, ls), v in want.items():
            r = json.loads((A / f'dv2f14{g}_ls{ls}.json').read_text())
            self.assertEqual(r['verdict'], v, (g, ls))
            if v == 'FAIL':
                self.assertTrue(any('calendar period' in f for f in r['fails']), r['fails'])


if __name__ == '__main__':
    unittest.main()
