"""TOK-DS-8: lower_vpx placements of the shared collectives (router_allgather, substage_hop0, out_allreduce RS + AG)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lower_vpx as LV  # noqa: E402


class T(unittest.TestCase):
    def test_default_leg_unchanged(self):
        a = LV.leg_program(0, 'W', 14, LV.a_rows(0), t0=100)
        b = LV.leg_program(0, 'W', 14, LV.a_rows(0), t0=100, dst_leaf=0, dst_off=0)
        self.assertEqual([c['body'] for c in a['ctl']], [c['body'] for c in b['ctl']])
        self.assertEqual(len(a['sends']), 14)

    def test_dst_offset_in_config_and_send(self):
        leg = LV.leg_program(0, 'W', 14, list(range(320, 640)), leaf=4, dst_leaf=1, dst_off=320)
        cfg = [c for c in leg['ctl'] if c['target'] == 4]
        self.assertEqual((cfg[0]['body'] >> 28) & 7, 1)
        self.assertEqual((cfg[0]['body'] >> 31) & 0x3FF, 640)
        self.assertEqual(leg['sends'][0]['dst_row'], 640)
        self.assertEqual(len(leg['sends']), 40)

    def test_placements_fit_and_disjoint(self):
        """on one die (rank d): every rank's gathered a / router rows, the 4 partial quarters and d's 3 RS slots are
        disjoint leaf rows inside 5 leaves x 1024 rows"""
        for d in range(4):
            occ = set()
            def put(leaf, rows):
                for r in rows:
                    self.assertTrue(0 <= r < 1024 and 0 <= leaf < 5)
                    self.assertNotIn((leaf, r), occ)
                    occ.add((leaf, r))
            for rk in range(4):
                put(0, LV.a_rows(rk))
                put(0, LV.router_rows(rk))
                lf, r0 = LV.ar_quarter(rk)
                put(lf, range(r0, r0 + 320))
            slots = {LV.rs_slot(s_, d) for s_ in range(4) if s_ != d}
            self.assertEqual(len(slots), 3)
            for lf, r0 in slots:
                put(lf, range(r0, r0 + 320))
        self.assertEqual(sum(n for _, _, n in LV.STAGE_SEGS), 1280)

    def test_rs_quarters_cover_partial(self):
        rows = set()
        for q in range(4):
            lf, r0 = LV.ar_quarter(q)
            rows |= {(lf, r) for r in range(r0, r0 + 320)}
        self.assertEqual(len(rows), 1280)


if __name__ == '__main__':
    unittest.main()
