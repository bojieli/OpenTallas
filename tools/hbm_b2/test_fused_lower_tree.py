#!/usr/bin/env python3
"""HBM-BIND-6: opt-in lower FUSED tree in current_native_top (default output byte-identical)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from current_native_top import compose
from test_current_native_top import fixture
import fused_lower_tree as F

# sha256 of every output file of compose() on the test fixture, produced by current_native_top.py of
# claude/hbm-bind-5-1029@ca420a278f (before the opt-in existed)
BASE_SHA = json.loads(Path(__file__).with_name('fused_lower_tree_base_sha.json').read_text())


def run(lower):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'original.v').write_text(fixture())
        (root / 'base.v').write_text('module base (clk);\ninput clk;\nendmodule\n')
        report = compose(root / 'original.v', root / 'base.v', {'transport': []}, root / 'out', False, fused_lower_tree=lower)
        files = {p.name: p.read_bytes() for p in sorted((root / 'out').iterdir())}
        return report, files


class LowerTreeTest(unittest.TestCase):
    def test_default_byte_identical(self):
        _, files = run(False)
        self.assertEqual({k: hashlib.sha256(v).hexdigest() for k, v in files.items()}, BASE_SHA)

    def test_lower_tree(self):
        report, files = run(True)
        inst = json.loads(files['native_instance_manifest.json'])
        lanes = [n for n, o in inst.items() if o['master'] == 'ot_hnx_fused_lane']
        nodes = [n for n, o in inst.items() if o['master'] == 'ot_hnx_fused_tnode']
        self.assertEqual((len(lanes), len(nodes)), (32, 30))
        for side in F.SIDES:
            n4 = inst[f'u_mu_fused_n4_{side}']['ports']
            self.assertEqual(n4['ua']['segments'], [['n', f'u_mu_fused_n3_q0_{side}__uo', 0, 270]])
            self.assertEqual(n4['ub']['segments'], [['n', f'u_mu_fused_n3_q1_{side}__uo', 0, 270]])
            for L in range(16):
                self.assertEqual(inst[F.lane(side, L)]['ports']['lid']['segments'], [['c', 5, 16 * F.SIDES.index(side) + L]])
        nets = {o['net'] for o in report['obligations']}
        self.assertNotIn('native_required__u_mu_fused_n4_nw__ua', nets)
        self.assertIn('native_required__u_mu_fused_n1_q0_0_nw__pad_k', nets)
        self.assertIn('native_required__u_mu_fused_7_ne__rr_d', nets)
        rtl = files['hbm_current_native_top.sv'].decode()
        self.assertIn('ot_hnx_fused_lane #(.D(5120), .KX(4), .RR(10)) u_mu_fused_15_ne', rtl)
        self.assertNotIn('output wire [172:0] u_mu_fused_n4_nw__da;', rtl)
        self.assertEqual(sorted(F.plan_map('ne').values())[0][0], 'NE_hub')

    def test_mutant_changes_wiring(self):
        a, _ = F.compose_side('nw', [('n', 'c', 0, 0)], lambda *x: None, lambda n, p, w: None)
        b, _ = F.compose_side('nw', [('n', 'c', 0, 0)], lambda *x: None, lambda n, p, w: None, mutant='swap_2_4')
        self.assertNotEqual(a['u_mu_fused_n1_q0_1_nw']['ports']['ua'], b['u_mu_fused_n1_q0_1_nw']['ports']['ua'])


if __name__ == '__main__':
    unittest.main()
