"""KV-PLAN-ECTL 10-17 (coordinator decision 2): OT_KV_ECTL_PAIR=1 puts each logical engine / K issuer in the ECTL frame
level with its landing group (same row-pair = the group's V-port slot pair) without touching the logical graph."""
import os
import unittest
from unittest import mock

import kv_static_die as D

FLAG = 'OT_KV_ECTL_PAIR'


def row(f):
    return f % 4                     # kv_die: ectl_<st>_<f> at ey = gy + (f % 4) * (RENG_H + GY)


def col(f):
    return f // 4                    # 0 = the landing side (W stacks: e // 4; E stacks mirrored, same index)


class EctlPair(unittest.TestCase):
    def test_default_is_identity(self):
        with mock.patch.dict(os.environ, {FLAG: '0'}):
            self.assertEqual([D.ectl_frame(g) for g in range(8)], list(range(8)))
            self.assertEqual(D.cluster_of('ectl_a_WN_5')[0], 'ectl_WN_5')

    def test_pair_is_a_bijection_and_inverse(self):
        with mock.patch.dict(os.environ, {FLAG: '1'}):
            fr = [D.ectl_frame(g) for g in range(8)]
            self.assertEqual(sorted(fr), list(range(8)))
            self.assertEqual([D.frame_engine(f) for f in fr], list(range(8)))

    def test_every_k_link_pairs_an_ectl_with_a_group_in_its_row_pair(self):
        """krq_<st>_<g> / krs_<st>_<g> join ki_<st>_<g> (folded in the frame cluster_of names) and slg_<st>_<g>, which
        sits at strip slot ORDER.index(g): its slot pair (= its V port vport_<st>_<g // 2>) must be the frame's row."""
        with mock.patch.dict(os.environ, {FLAG: '1'}):
            for st in D.STACKS:
                for g in range(8):
                    for n in (f'ectl_a_{st}_{g}', f'ki_{st}_{g}'):
                        die, kind, _ = D.cluster_of(n)
                        self.assertEqual(kind, 'ectl')
                        f = int(die.split('_')[2])
                        self.assertEqual(row(f), D.ORDER.index(g) // 2, (n, die))
                        self.assertEqual(D.ORDER.index(g) // 2, D.ORDER.index(g ^ 1) // 2)   # V-port pair {2k, 2k + 1}
                        # the astk's own leaf column of engine g (astk_plan eng = 2 r + c)
                        self.assertEqual(col(f), g % 2, (n, die))
        with mock.patch.dict(os.environ, {FLAG: '0'}):
            off = sum(row(D.ectl_frame(g)) != D.ORDER.index(g) // 2 for g in range(8))
            self.assertEqual(off, 4)     # the default binding: engines 0, 3, 5, 6 sit off their group's slot pair

    def test_logical_graph_unchanged(self):
        """bit-exactness: the join (engine g <-> group g, cfg word index 8 s + g, astk port g) is flag-independent"""
        with mock.patch.dict(os.environ, {FLAG: '1'}):
            g = D.graph()
            a = {i['name']: i['inputs'] for i in g['instances'] if i['role'] in ('ectla', 'k_issuer')}
        for s, st in enumerate(D.STACKS):
            for e in range(8):
                self.assertEqual(a[f'ectl_a_{st}_{e}']['cfg'],
                                 [dict(instance='diecfg', port='ectl_a_cfg', lo=5 * (8 * s + e), width=5)])
                self.assertEqual(a[f'ectl_a_{st}_{e}']['rs'][0]['instance'], f'ki_{st}_{e}')
                self.assertEqual({it['instance'] for it in a[f'ki_{st}_{e}']['rsp_data']}, {f'slg_{st}_{e}'})

    def test_response_lat_keys_follow_the_frame(self):
        m = dict(relay_stages={'krq_WS_4': 1, 'krs_WS_4': 3})
        with mock.patch.dict(os.environ, {FLAG: '1'}):
            out = D.response_lat(m)
            self.assertEqual(out[f'ectl_WS_{D.ectl_frame(4)}']['RESPONSE_LAT'], 12)
            self.assertEqual(len(out), 32)


if __name__ == '__main__':
    unittest.main()
