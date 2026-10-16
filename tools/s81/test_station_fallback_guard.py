"""Chains.run progress guard (ROOT 2026-10-16): the opt-in station fallback may serve a stop once; a second fallback at
the same stop (S-DIE v3i3/v3i4: one station re-placed >4,000 times, drifting 10 mm) fails fast naming the station."""
import os
import sys
import unittest
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as D


class FarOnlyPlacer:
    """No spot near the path; the unanchored 600-um fallback finds one far away (blocked street)."""
    def __init__(self, m):
        self.m, self.n, self.calls = m, defaultdict(int), 0

    def near(self, cx, cy, w, h, allowed, prev=None, span=72.0, **k):
        self.calls += 1
        if self.calls > 5000:
            raise AssertionError('unbounded re-placement')
        if prev is None and span >= 600.0:
            return (cx + 9000.0, cy)
        return None

    def add(self, it):
        self.m['insts'].append(it)
        return it


class OkPlacer(FarOnlyPlacer):
    def near(self, cx, cy, w, h, allowed, prev=None, span=72.0, **k):
        return (cx - w / 2, cy - h / 2)


class Guard(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.get('OT_S81_STATION_FALLBACK')
        os.environ['OT_S81_STATION_FALLBACK'] = '1'

    def tearDown(self):
        if self.env is None:
            os.environ.pop('OT_S81_STATION_FALLBACK', None)
        else:
            os.environ['OT_S81_STATION_FALLBACK'] = self.env

    def chains(self, placer, blocker=True):
        m = dict(buses=[], insts=[])
        if blocker:
            m['insts'].append(D.Inst('hstn_blocker', 'dsfd_hstn_2048', 300.0, 0.0, 80.0, 40.0, kind='stn'))
        return D.Chains(m, placer(m)), m

    def test_repeated_fallback_fails_fast_with_station_and_cause(self):
        c, m = self.chains(FarOnlyPlacer)
        with self.assertRaises(RuntimeError) as e:
            c.run('hb_su_s_wq_d_vm', [64], [(0.0, 20.0), (432.0, 20.0)], [(0.0, 0.0, 1e5, 1e5)], (0.0, 20.0))
        msg = str(e.exception)
        self.assertIn('OT_STATION_FALLBACK_NO_PROGRESS station hb_su_s_wq_d_vm', msg)
        self.assertIn('hstn_blocker', msg)
        self.assertIn("'stn': 1", msg)
        self.assertLess(c.P.calls, 100)
        self.assertEqual(len(m['station_fallback']), 3)   # s=400, then the end stop twice

    def test_normal_chain_unchanged(self):
        c, m = self.chains(OkPlacer, blocker=False)
        out = c.run('ok_chain', [64], [(0.0, 20.0), (2000.0, 20.0)], [(0.0, 0.0, 1e5, 1e5)], (0.0, 20.0))
        self.assertTrue(1 <= len(out) <= 8)
        self.assertNotIn('station_fallback', m)


if __name__ == '__main__':
    unittest.main()
