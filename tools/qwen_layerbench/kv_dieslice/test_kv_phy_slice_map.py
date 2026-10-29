#!/usr/bin/env python3
"""TOK-KV-2 10-28: kv_phy_slice_map.py fail-closed checks (synthetic bind)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_phy_slice_map as m  # noqa: E402

SL = 'module qkd_hbm3e_phy_pc_s8 ();\n' + ''.join(
    f'    qkd_hbm3e_phy_pc4 u_s{k} (.clk(clk), ' + ', '.join(f'.pi{i}(pi{4 * k + i}), .po{i}(po{4 * k + i})'
                                                         for i in range(4)) + ');\n' for k in range(8)) + 'endmodule\n'


def names(swap=None):
    d = {f'phy_{s}_{k}.u_core': f'phy_{s}.u_sub.u_s{k}' for s in m.STACKS for k in range(8)}
    d['hub_C.u_ahub'] = 'ahub'
    if swap:
        a, b = swap
        d[a], d[b] = d[b], d[a]
    return d


class T(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)
        (self.d / 'kv3_phy_part.sv').write_text('module kv3_phy_part(); qkd_hbm3e_phy_pc4 u_core (); endmodule\n')
        self.top = ''.join(f'    kv3_phy_part phy_{s}_{k} (\n' for s in m.STACKS for k in range(8))

    def tearDown(self):
        self.td.cleanup()

    def test_pass_identity(self):
        p, a, e = m.build(names(), self.top, self.d, SL)
        self.assertEqual(e, [])
        self.assertEqual(len(p), 32)
        self.assertEqual(p['phy_WS.u_s3'], 'phy_WS_3')
        self.assertEqual(a['phy_WS.u_s3'], 'phy_WS.u_sub.u_s3')

    def test_swap_followed(self):
        p, _, e = m.build(names(('phy_WS_0.u_core', 'phy_WS_5.u_core')), self.top, self.d, SL)
        self.assertEqual(e, [])
        self.assertEqual(p['phy_WS.u_s0'], 'phy_WS_5')

    def test_missing_slice_fails(self):
        d = names()
        del d['phy_EN_7.u_core']
        self.assertTrue(m.build(d, self.top, self.d, SL)[2])

    def test_not_in_top_fails(self):
        self.assertTrue(m.build(names(), self.top.replace('phy_ES_2 ', 'phy_ESx2 '), self.d, SL)[2])

    def test_slice_pc_law_fails(self):
        self.assertTrue(m.build(names(), self.top, self.d, SL.replace('.pi0(pi4)', '.pi0(pi8)'))[2])

    def test_type_without_core_fails(self):
        (self.d / 'kv3_phy_part.sv').write_text('module kv3_phy_part(); endmodule\n')
        self.assertTrue(m.build(names(), self.top, self.d, SL)[2])


if __name__ == '__main__':
    unittest.main()
