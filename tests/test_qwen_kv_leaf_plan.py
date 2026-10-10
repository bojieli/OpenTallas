"""The leaf candidate must never own the CDC's landing or fault fields."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('kv_leaf_plan', ROOT / 'tools/qwen_kv_die/kv_die.py')
K = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(K)


class LeafPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = K.build()
        cls.plan = K.build(kv_wq_leaves=True)

    def test_cdc_pin_shapes_preserved_and_ownership_split(self):
        baseline, candidate = K.masters(self.base), K.masters(self.plan)
        widths0, widths1 = K.port_widths(self.base), K.port_widths(self.plan)
        def pins(master, widths, prefixes):
            rects = K.F.pin_rects(master, 1, {p: w for (m,p),w in widths.items() if m == master.name})
            return [(layer, rect) for p,layer,rect in rects if p.startswith(prefixes)]
        a = pins(baseline['qkd_cdc'], widths0, ('ci[',))
        b = pins(candidate['qkd_cdc_wleaf'], widths1, ('wi[', 'wr[', 'cf['))
        self.assertEqual(len(a), 302)
        self.assertEqual(len(b), 302)
        for (la, ra), (lb, rb) in zip(a, b):
            self.assertEqual(la, lb)
            for x,y in zip(ra,rb):
                self.assertAlmostEqual(x,y,places=9)
        for st in K.STACKS:
            for pc in range(32):
                ports = {p:w for _,_,w,eps in self.plan['buses'] for i,p in eps if i == f'cdc_{st}_{pc}'}
                self.assertEqual({p:ports[p] for p in ('wi','wr','cf','co')}, dict(wi=290,wr=11,cf=1,co=283))

    def test_all_leaves_chain_and_strap(self):
        self.assertEqual(sum(i.master == 'qkd_kvwq_leaf' for i in self.plan['insts']),128)
        for st in K.STACKS:
            for pc in range(32):
                self.assertEqual(self.plan['wq_straps'][f'wlane_{st}_{pc}'], pc%8)
        self.assertEqual(K.check(self.plan)['overlaps'],0)
        self.assertTrue(K.strict_ports(K.masters(self.plan))['ok'])

    def test_binary_feed_retains_eight_physical_lane_pins(self):
        plan = K.build(kv_wq_binary=True)
        widths = K.port_widths(plan)
        self.assertFalse(any(i.master == 'qkd_kvwq_lane_encoder' for i in plan['insts']))
        for group in range(4):
            self.assertEqual(widths[('qkd_kvwq_ctl_bin', f'f{group}')],298)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'die.v'
            K.write_netlist(plan,1,path)
            text = path.read_text()
            for st in K.STACKS:
                for group in range(4):
                    net=f'n_wencoded_{st}_{group}'
                    self.assertIn(f'.f{group}({{{net}[292:284], ctl_lane_high5_unused_{st}_{group}, {net}[283:0]}})',text)
            self.assertFalse((Path(tmp)/'kv_wq_lane_encoder.sv').exists())

    def test_south_face_leaf_and_actual_cdc_geometry_fit(self):
        plan=K.build(kv_wq_leaf_s=True)
        self.assertEqual(K.check(plan)['overlaps'],0)
        self.assertEqual(K.check(plan)['outside'],0)
        by={i.name:i for i in plan['insts']}
        for st in K.STACKS:
            for pc in range(32):
                cdc=by[f'cdc_{st}_{pc}']; leaf=by[f'wleaf_{st}_{pc}']
                self.assertEqual((cdc.w,cdc.h),(183.72,183.72))
                self.assertAlmostEqual(cdc.y-(leaf.y+leaf.h),K.GY)
                self.assertIn(leaf.orient,('MX','R180'))
        rows,status=K.real_pin_bindings(plan)
        self.assertEqual(status['qkd_cdc_wleaf']['size_um'],[183.72,183.72])
        self.assertEqual(status['qkd_cdc_wleaf']['mapped_shapes'],1202)

    def test_head_capture_wide_slots_preserve_exact_feed_binding(self):
        plan=K.build(kv_wq_head=True,kv_wq_wide=True)
        self.assertEqual(K.check(plan)['overlaps'],0)
        self.assertEqual(K.check(plan)['outside'],0)
        by={i.name:i for i in plan['insts']}
        for st in K.STACKS:
            ctl=by[f'wctl_{st}']
            self.assertEqual(ctl.master,'qkd_kvwq_ctl_bin_h')
            self.assertAlmostEqual(ctl.w+K.SHAVE,216.0)
            self.assertAlmostEqual(ctl.h+K.SHAVE,648.0)
            for pc in range(32):
                self.assertEqual(by[f'wleaf_{st}_{pc}'].w,129.6)
        self.assertEqual(K.BINDINGS['qkd_kvwq_ctl_bin_h']['parameters'],dict(FLANE_BINARY=1,HEAD_PIPE=1))
        self.assertEqual(K.port_widths(plan)[('qkd_kvwq_ctl_bin_h','f0')],298)
        self.assertEqual(plan['geo']['edge_channel'],K.CHAN)
        self.assertEqual(max(plan['relay_stages'][f'kvn_{st}'] for st in K.STACKS),42)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'die.v'
            K.write_netlist(plan,1,path)
            self.assertIn('ctl_lane_high5_unused_WS_0',path.read_text())

    def test_candidate_cannot_launch_physical_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'plan-only'):
                K.case(self.plan, Path(tmp))
            self.assertFalse(any(Path(tmp).iterdir()))


if __name__ == '__main__':
    unittest.main()
