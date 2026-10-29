"""TOK-DS-8: lower_vpx placements of the shared collectives (router_allgather, substage_hop0, out_allreduce RS + AG)."""
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
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


    def test_xr7_config_slot_is_lov1_free(self):
        """TOK-DS-9: ot_s81sl_xr.sv:558 faults tg[4] && |lov1; every config decode edge must miss every packer pair edge"""
        leg = LV.leg_program(0, 'W', 14, LV.a_rows(0), t0=100)
        cfg = {c['cycle'] + LV.CFG_AT for c in leg['ctl'] if c['target'] == 4}
        lov1 = {c['cycle'] + LV.CFG_AT + LV.LO_AFTER_CTL + LV.LO_PACK + j for c in leg['ctl'] if c['target'] == 0
                for j in range(4)}
        self.assertFalse(cfg & lov1)
        pins = [c['cycle'] for c in leg['ctl']]
        self.assertEqual(len(pins), len(set(pins)))
        self.assertEqual(LV.beat_period(), 6)
    def test_later_substage_hop_uses_identical_abi(self):
        """Every numbered stage hop is the same rank-local static NEXT circuit, with its own issue dates."""
        class Die:
            def slices(self): return {'u_s_0N': {'sid': 1}}
        with patch('dv_layer_compile.ctl_path', return_value={'edges': 10}):
            first=LV.lower(Die(),{'op':'substage_hop0'},{'t_issue':100})
            second=LV.lower(Die(),{'op':'substage_hop1'},{'t_issue':1100})
        self.assertEqual(second['status'],'PARTIAL')  # producer/consumer row binding is still held
        self.assertEqual(len(second['templates']),320)
        self.assertEqual(first['templates'],second['templates'])
        self.assertEqual([r['issue']+1000 for r in first['rows']],[r['issue'] for r in second['rows']])
        self.assertEqual([r['cycle']+1000 for r in first['events']],[r['cycle'] for r in second['events']])

    def test_cross_operation_engine_reservation(self):
        """Two operations share one physical issuer; preserve each leg's payloads and relative event dates."""
        class Die:
            def slices(self):
                return {n: {'sid': k} for k, n in enumerate(
                    ('u_s_0S', 'u_s_7S', 'u_s_7N', 'u_s_0N'))}
        with patch('dv_layer_compile.ctl_path', return_value={'edges': 11.5}):
            first = LV.lower(Die(), {'op': 'attn.out_allreduce'}, {'t_issue': 100})
            occupied = {(r['eng'], r['issue']) for r in first['rows']}
            # Force the second operation's first command onto a real earlier command.
            edge = min(r['issue'] for r in first['rows'] if r['eng'] == 0)
            legacy = LV.lower(Die(), {'op': 'substage_hop0'}, {'t_issue': edge})
            fixed = LV.lower(Die(), {'op': 'substage_hop0'},
                             {'t_issue': edge, 'ctl_used': occupied})
        self.assertTrue(occupied & {(r['eng'], r['issue']) for r in legacy['rows']})  # lost-booking mutant
        self.assertFalse(occupied & {(r['eng'], r['issue']) for r in fixed['rows']})
        self.assertEqual(legacy['templates'], fixed['templates'])
        self.assertTrue(fixed['reservation_delays'])
        # Each segment moves intact: commands, CTL inputs, and outward RD events all follow the same delay.
        for lf in (1, 2):
            a = [e for e in legacy['events'] if e['kind'] == 'RD' and e['tag'].startswith(f'leaf {lf} ')]
            b = [e for e in fixed['events'] if e['kind'] == 'RD' and e['tag'].startswith(f'leaf {lf} ')]
            shifts = {y['cycle'] - x['cycle'] for x, y in zip(a, b)}
            self.assertEqual(len(shifts), 1)
            self.assertGreaterEqual(next(iter(shifts)), 0)
        self.assertTrue(all(type(r['issue']) is int for r in first['rows'] + fixed['rows']))

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
