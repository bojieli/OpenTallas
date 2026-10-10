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

    def test_candidate_cannot_launch_physical_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'plan-only'):
                K.case(self.plan, Path(tmp))
            self.assertFalse(any(Path(tmp).iterdir()))


if __name__ == '__main__':
    unittest.main()
