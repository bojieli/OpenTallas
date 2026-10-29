"""DIE-KV-18 10-28: the static attention RESULT slot follows the service need (kv_static_programme.service_slot_pad)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static_programme as C  # noqa: E402

TS = sorted(set(range(1, C.T_MAX + 1, 61)) | {1, 2, 128, 129, 4097, 8191, C.T_MAX})


class ServiceSlotPad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pr = C.profile('die', json.loads((C.ROOT / C.AGES).read_text()))
        cls.base = C.service_end_of(dict(cls.pr, attn_service_pad=0))

    def test_committed_die_needs_no_pad(self):
        # default-preserving: the committed die ages fit the unpadded slot over EVERY context -> pad 0, images unchanged
        r = C.service_slot_pad(self.pr)
        self.assertEqual(r['pad'], 0)
        self.assertLessEqual(r['need'], r['base_service_end'])

    def test_pad_moves_the_slot_edge_for_edge(self):
        self.assertEqual(C.service_end_of(dict(self.pr, attn_service_pad=8)), self.base + 8)

    def test_need_is_the_calendar_law(self):
        n = C.service_need(self.pr, TS)
        c = C.attention_calendar(n['T'], self.pr, None)
        self.assertEqual(n['need'], c['PV_START'] + c['R'] + 48 + self.pr.get('f_dly', 1))
        C.attention_calendar(n['T'], self.pr, n['need'])                 # the need is exactly enough
        with self.assertRaises(ValueError):
            C.attention_calendar(n['T'], self.pr, n['need'] - 1)

    def test_deeper_seams_get_exactly_the_missing_edges(self):
        # one rule for every context: grow the PV word latency until the worst context misses the unpadded slot; the
        # derived pad makes every context fit and one edge less fails at the worst context
        n0 = C.service_need(self.pr, TS)['need']
        deep = dict(self.pr, d_rl=self.pr['d_rl'] + (self.base - n0) + 40)
        r = C.service_slot_pad(deep, TS)
        self.assertGreater(r['pad'], 0)
        se = r['base_service_end'] + r['pad']
        for T in TS:
            C.attention_calendar(T, deep, se)
        with self.assertRaises(ValueError):
            C.attention_calendar(r['worst_T'], deep, se - 1)


if __name__ == '__main__':
    unittest.main()
