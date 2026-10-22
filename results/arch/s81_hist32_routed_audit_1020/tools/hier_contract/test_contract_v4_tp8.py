#!/usr/bin/env python3
"""contract_v4_tp8: the committed qwen_rom_tp8 contract is the v4 fixed point and passes its own checks"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract_v4_tp8 as V4  # noqa: E402

D = HERE.parent.parent / 'results/arch/hier_contract_1012'


class TestV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.C = json.load(open(D / 'qwen_rom_tp8.json'))
        cls.R = json.load(open(D / 'qwen_rom_tp8_v4_regen.json'))

    def test_fixed_point(self):
        self.assertGreaterEqual(self.C['version'], 4)
        import contract_v4b_tp8 as V4B   # addendum b (T12 / T13) is applied on top of the v4 patch
        again = V4B.apply(V4.apply(json.loads(json.dumps(self.C)), self.C['updated'], self.R))
        self.assertEqual(again, self.C)

    def test_checks(self):
        res = V4.check(self.C)
        for k in ('schema', 'overlap', 'span', 'seam'):
            self.assertEqual(res[k], [], k)

    def test_station_pairs(self):
        s = next(x for x in self.C['slots'] if x['cell'] == 'qfd_chead_e')
        names = {V4.base(p['name']): V4.bits(p) for p in s['pins']}
        self.assertEqual(names, {'e_d': 508, 'e_r': 1, 'w_d': 508, 'w_r': 1, 'n_d': 508, 'n_r': 1, 's_d': 508, 's_r': 1,
                                 'rst_n': 1})

    def test_seam_mutant(self):
        C = json.loads(json.dumps(self.C))
        for s in C['slots']:
            if s['cell'] == 'qfd_chead_w':
                for p in s['pins']:
                    if p['name'].startswith('s_d'):
                        p['name'] = 's_d[321:0]'
        self.assertTrue(V4.seams(C)[0])

    def test_overlap_mutant(self):
        C = json.loads(json.dumps(self.C))
        a = next(x for x in C['slots'] if x['cell'] == 'qkd_rhead')
        a['origin']['x'] += 300.0 if a['origin']['orient'] in ('R0', 'MX') else -300.0
        self.assertTrue(V4.overlaps(C))


if __name__ == '__main__':
    unittest.main()
