"""KDIE5-RTL 10-22: the r2 group successors' calendar law (kv_static_die.GRP_R2_EDGES -> kv_static_programme)."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import kv_static_programme as P  # noqa: E402


class GrpR2(unittest.TestCase):
    def test_off_is_zero(self):
        with mock.patch.dict(os.environ, {'OT_KV_GRP_R2': '0'}):
            self.assertEqual(P.grp_r2_edges(), P.GRP_R2_ZERO)
            self.assertEqual(P.CAL_DELTAS_ZERO['grp_r2'], P.GRP_R2_ZERO)

    def test_on_law(self):
        ksd = mock.Mock(GRP_R2_EDGES=dict(fan=29, chain_hop=4, gather_own=3, gather_hop=4, gather_max=31, cf1_fault=2,
                                          est=2, tok_tep=2))
        with mock.patch.dict(os.environ, {'OT_KV_GRP_R2': '1'}):
            e = P.grp_r2_edges(ksd)
        self.assertEqual((e['fan'], e['gather_max']), (29, 31))
        self.assertEqual(e['fan'], 1 + e['chain_hop'] * 7)              # uniform local view = deepest group's entry
        self.assertEqual(e['gather_max'], e['gather_own'] + e['gather_hop'] * 7)

    def test_wrong_law_refused(self):
        ksd = mock.Mock(GRP_R2_EDGES=dict(fan=28, chain_hop=4, gather_own=3, gather_hop=4, gather_max=31, cf1_fault=2,
                                          est=2, tok_tep=2))
        with mock.patch.dict(os.environ, {'OT_KV_GRP_R2': '1'}), self.assertRaises(ValueError):
            P.grp_r2_edges(ksd)

    def test_rtl_constants_match(self):
        t = (HERE.parents[1] / 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_r2.sv').read_text()
        self.assertIn('localparam DL = 4 * (NT - 1);', t)                # 7 hops x 4 = 28 delay stages
        self.assertIn("3'd7: tap_of = 3'd7;", t)                       # slg 7 = depth 0 = longest local delay


if __name__ == '__main__':
    unittest.main()
