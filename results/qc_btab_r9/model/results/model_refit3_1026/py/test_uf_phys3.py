#!/usr/bin/env python3
"""MODEL-REFIT-3 tests.  Library-dependent tests need OT_INVBUF_LIBDIR (invbuf_tt/ff.lib) and skip otherwise."""
import hashlib, json, os, subprocess, sys, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import uf_phys3 as V  # noqa: E402
import points as PT  # noqa: E402
from uf_phys3 import U  # noqa: E402
LIBDIR = os.environ.get("OT_INVBUF_LIBDIR", "/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor")
HAVE_LIB = (Path(LIBDIR) / "invbuf_tt.lib").exists()
R3 = HERE.parent


class Registry(unittest.TestCase):
    def test_points_exist(self):
        for b, p in PT.POINTS.items():
            for k in ("spec", "geo", "seg", "vias_rcx"):
                if p.get(k):
                    self.assertTrue(Path(p[k]).exists() or Path(p[k] + ".gz").exists(), (b, k, p[k]))
            for f in list(p["grt"]) + list(p.get("rcx") or ()):
                self.assertTrue(Path(f).exists() or Path(f + ".gz").exists(), (b, f))

    def test_fit_provenance_matches_files(self):
        F = json.load(open(R3 / "fit3_grt.json"))
        root = PT.RES.parent
        for rel, h in F["provenance"]["sha256"].items():
            p = root / rel if not rel.startswith("/") else Path(rel)
            if not p.exists():
                p = Path(str(p) + ".gz")
            if p.suffix == ".py":
                continue                       # code may be edited after the fit (tests, comments); data must not
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), h, rel)

    def test_model_file_reproduces(self):
        out = Path(os.environ.get("TMPDIR", "/tmp")) / "uf_phys3_v1.repro.json"
        subprocess.run([sys.executable, str(HERE / "make_model.py"), str(R3 / "fit3_grt.json"), str(out)], check=True, capture_output=True)
        a, b = json.load(open(out)), json.load(open(R3 / "uf_phys3_v1.json"))
        for k in ("PMAX", "PMIN", "LOO_MAX", "LOO_maxabs"):
            self.assertEqual(a[k], b[k], k)
        self.assertEqual(b["model"], "uf_phys3")


@unittest.skipUnless(HAVE_LIB, "invbuf libs not present (set OT_INVBUF_LIBDIR)")
class Kernel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = U.load_libs(LIBDIR)
        p = PT.POINTS["prog_r1"]
        cls.P = V.load_plan(p["spec"], p["geo"], p["seg"])
        cls.Pv = V.load_plan(PT.POINTS["vmr_f4a"]["spec"], PT.POINTS["vmr_f4a"]["geo"], None)

    def test_reduces_to_uf_phys(self):
        q = dict(alpha=0.2, beta=0.5, gslew=5.0, kleaf=1.2955)
        for e in ("rise", "fall"):
            a, _ = U.predict(self.P, self.L, "TT", edge=e, **q)
            b, _ = V.predict3(self.P, self.L, "TT", edge=e, **q)
            for k in a:
                self.assertAlmostEqual(a[k], b[k], places=9)

    def test_kstage_is_per_stage(self):
        q = dict(alpha=0.2, beta=0.5, gslew=5.0, kleaf=1.2955)
        a, _ = V.predict3(self.P, self.L, "TT", **q)
        b, _ = V.predict3(self.P, self.L, "TT", kstage=1.5, **q)
        d = V.depth(self.P)
        for k in a:
            self.assertAlmostEqual(b[k] - a[k], 1.5 * d[k], places=6)

    def test_bleaf_scales_leaf_wire_only(self):
        q = dict(alpha=0.0, beta=0.5, gslew=5.0, kleaf=1.2955)
        a, A = V.predict3(self.P, self.L, "TT", **q)
        b, B = V.predict3(self.P, self.L, "TT", bleaf=0.25, **q)
        for k in a:
            self.assertEqual(A[k], B[k])           # leaf input arrival unchanged
            self.assertLess(b[k], a[k])

    def test_vias_rcx_only(self):
        q = dict(alpha=0.2, beta=0.5, gslew=5.0, kleaf=1.2955)
        vias = {V.net_name(d): 80 for d in self.Pv.kids}
        g0, _ = V.predict3(self.Pv, self.L, "TT", **q)
        g1, _ = V.predict3(self.Pv, self.L, "TT", vias=vias, **q)
        r1, _ = V.predict3(self.Pv, self.L, "TT", basis="RCX", vias=vias, **q)
        self.assertEqual(g0, g1)                    # GRT basis ignores vias
        self.assertTrue(all(r1[k] > g0[k] for k in g0))

    def test_plan_vias_flags_unplanned_long_legs(self):
        v, risk = V.plan_vias(self.Pv, {})
        self.assertTrue(risk)
        v2, risk2 = V.plan_vias(self.Pv, {n: 4 for n, _ in risk})
        self.assertFalse(risk2)

    def test_phys_gate_default_unchanged_and_opt_in(self):
        pg = PT.RES / "qc_su_prog_l1_1026" / "phys_gate.py"
        p = PT.POINTS["btab_r4"]
        code = ("import sys,json; sys.path.insert(0,%r); import phys_gate as G; o=G.predict_file(%r,%r,%r,%r); "
                "print(json.dumps([o['TT_rise']['mean'], o['FF_early']['mean'], G.WMAX, o['params']['fit']]))") % (
            str(pg.parent), p["spec"], p["seg"], p["geo"], LIBDIR)
        env = dict(os.environ); env.pop("OT_PHYS_FIT", None)
        d0 = json.loads(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1])
        env["OT_PHYS_FIT"] = str(R3 / "uf_phys3_v1.json")
        d1 = json.loads(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1])
        self.assertIn("model-refit2", d0[3])
        self.assertEqual(d0[2], 20.0)
        self.assertIn("uf_phys3", d1[3])
        self.assertEqual(d1[2], 14.0)
        self.assertNotAlmostEqual(d0[0], d1[0], places=2)


if __name__ == "__main__":
    unittest.main()
