"""KV-BIND12 10-20: the OT_KV_QKH_SAFE32 head plans (results/arch/qwen_kv_die/head_safe32) against the real nc32c LEFs.

Every leaf the safe32 head RTL instantiates has a home of exactly its closed-view size, inside the slot outline, with no
overlap (kv_expand's 'overlapping closed leaves' / 'outside contract frame' checks); the near head's feed-through stages
fit their channel; the lane -> slot assignment is a permutation; the plans' own reach record is what they claim.
Run from the repo root:  python3 -m unittest tools/qwen_kv_die/test_head_safe32_plan.py
"""
import itertools
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLANS = ROOT / 'results/arch/qwen_kv_die/head_safe32'
RT = ROOT / 'physical/ref_tile'
LEF = dict(lane='ot_qkh_lane8_nc32c/views/ot_qkh_lane8_nc32c/ot_qkh_lane8_nc32c.lef',
           ktree='ot_qkh_ktree_lk_nc32c/views/ot_qkh_ktree_lk_nc32c/ot_qkh_ktree_lk_nc32c.lef',
           stin='qkh_r3_stin_1014/views/ot_qkh_head_stin_native/ot_qkh_head_stin_native.lef',
           stk='qkh_r3_stk_1014/views/ot_qkh_head_stk_native/ot_qkh_head_stk_native.lef',
           front='qkh_r4_frontq_1014/views/ot_qkh_head_frontq_native/ot_qkh_head_frontq_native.lef',
           score='qkh_r4_score4_1014/views/ot_qkh_head_score4_native/ot_qkh_head_score4_native.lef',
           ftg='qkh_head_gather_stage/views/qkh_head_gather_stage/qkh_head_gather_stage.lef',
           fts='qkh_head_sstage/views/qkh_head_sstage/qkh_head_sstage.lef')
RTL = ROOT / 'rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4_s_lk_nc32c.sv'


def size(rel):
    for line in (RT / rel).open():
        t = line.split()
        if t[:1] == ['SIZE']:
            return float(t[1]), float(t[3])
    raise ValueError(rel)


def kind(name):
    return re.sub(r'\d+$', '', name)


def overlap(a, b):
    return min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]) > 1e-3 and min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]) > 1e-3


class Safe32HeadPlans(unittest.TestCase):
    def check(self, ft, sub=''):
        plan = json.loads((PLANS / sub / ('head_ft_plan.json' if ft else 'head_r4_plan.json')).read_text())
        W, H = plan['slot_outline_um']
        for v in (W, H):
            self.assertAlmostEqual(v / 43.2, round(v / 43.2), 6, 'slot outline off the 43.2 lattice')
        ch = dict(plan['children'])
        # the RTL's leaves: 4 front quarters, ktree, score4, 16 x (stin, stk, lane8_nc32c); no nb relays (static heads)
        want = {f'front{g}' for g in range(4)} | {'ktree', 'score'} | {f'{k}{t}' for k in ('stin', 'stk', 'lane') for t in range(16)}
        self.assertEqual(set(ch), want)
        rtl = RTL.read_text()
        self.assertIn('ot_qkh_lane8_nc32c u_l8', rtl)
        self.assertIn('ot_qkh_ktree_lk_nc32c u_kt', rtl)
        self.assertNotIn('ot_qkh_head_nb_native', rtl)
        if ft:
            st = plan['feedthrough_channel']['stage_xy_um']
            ch['ftg'], ch['fts'] = [*st['ftg'], *size(LEF['ftg'])], [*st['fts'], *size(LEF['fts'])]
        for n, r in ch.items():
            self.assertEqual(tuple(r[2:]), size(LEF[kind(n)]), f'{n}: home size is not the closed view size')
            self.assertTrue(r[0] >= 0 and r[1] >= 0 and r[0] + r[2] <= W + 1e-6 and r[1] + r[3] <= H + 1e-6, f'{n} outside')
        for a, b in itertools.combinations(ch, 2):
            self.assertFalse(overlap(ch[a], ch[b]), f'{a} / {b} overlap')
        for t in range(16):     # lanes on the 43.2-um x lattice (v1.1 rule)
            x = ch[f'lane{t}'][0]
            self.assertAlmostEqual(x / 43.2, round(x / 43.2), 6)
        perm = plan['lane_slot_perm']
        self.assertEqual(len(perm), 16)
        self.assertEqual(len(set(perm)), 16)
        self.assertFalse(plan['overlaps'])
        self.assertFalse(plan['outside'])
        hops = [h for h in plan['hops'] if not h['name'].startswith(('die_ti', 'die_e'))]
        self.assertEqual(plan['internal_worst_hop']['um'], max(h['um'] for h in hops))
        return plan

    def test_r4(self):
        self.check(False)

    def test_ft(self):
        ft, r4 = self.check(True), self.check(False)
        self.assertEqual(ft['slot_outline_um'][0], r4['slot_outline_um'][0], 'near / far heads share the column width')

    def test_alt_5x4(self):     # the reach-400 comparison pair (OT_KV_QKH_SAFE32_PLANS)
        ft, r4 = self.check(True, 'alt_5x4'), self.check(False, 'alt_5x4')
        self.assertEqual(ft['slot_outline_um'][0], r4['slot_outline_um'][0])


if __name__ == '__main__':
    unittest.main()
