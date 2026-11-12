"""ot-autoclean DESIGN_EXPORT_1112 (OWNER 11-12 "export before cleanup"): no routed DB (6_final.odb or a routed / CTS
stage ODB) is deleted until its design-explorer cut is published, and the gate is ON by default.
    python3 -I tools/fleet/test_ot_autoclean_dx.py"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ot_autoclean_auto as T   # noqa: E402

ac = T.ac
ROUTED = ("6_final", "5_3_fillcell", "5_2_route", "5_1_grt", "5_route", "6_1_fill", "4_1_cts", "4_cts")


class Gate(T.Base):
    def setUp(self):
        super().setUp()
        self.dx = {"names": ["kv3_hgi", "d"], "ledger": [], "ledger_paths": []}

    def attempt(self, item, n, stage):
        d = os.path.join(self.root, f"kw-x/kit-wave/qkv/ev1/items/{item}/attempt_{n}")
        base = os.path.join(d, f"gen/{item}/run/results/asap7/dp_{item}/base")
        T.touch(os.path.join(base, "3_place.odb"))
        odb = T.touch(os.path.join(base, stage + ".odb"))
        T.age_tree(d)
        return d, odb

    def kw_for(self, fin, sup):
        h = "hx:"
        self.kw = {"attempts": {h + fin: {"active": False, "signed": False, "terminal": ["FAIL/None"]}},
                   "latest": {h + os.path.dirname(sup): 9}, "keep": []}

    def dxreq(self):
        return [ln.split("\t") for ln in self.out.splitlines() if ln.startswith("DXREQ\t")]

    def test_unsigned_routed_db_is_deleted_without_export(self):
        """OWNER 11-12: only SIGNED routed DBs are exported; an unsigned / failed / superseded attempt is deleted, no cut asked"""
        for stage in ROUTED:
            with self.subTest(stage=stage):
                fin, odb = self.attempt("kv3_hgi", 1, stage)
                sup, odb2 = self.attempt("kv3_hgi", 2, stage)
                self.kw_for(fin, sup)
                self.dx["ledger"] = []
                self.run_job("--classes", "a")
                self.assertFalse(os.path.exists(fin))
                self.assertFalse(os.path.exists(sup))
                self.assertEqual(self.dxreq(), [])

    def sign(self, k):
        T.touch(os.path.join(k, "signoff", "signoff.json"), 20)
        with open(os.path.join(k, "signoff", "signoff.json"), "w") as f:
            f.write('{"verdict": "SIGNED"}')
        T.age_tree(os.path.join(k, "signoff"))

    def test_signed_near_signed_vs_unsigned(self):
        k, b = self.kit_b("lane/kitsg")
        self.sign(k)
        k2, b2 = self.kit_b("lane/kitun")
        import types
        fake = types.SimpleNamespace(found={"record": []})
        self.assertTrue(ac.Job.signed_near(fake, b))
        self.assertFalse(ac.Job.signed_near(fake, b2))

    def test_class_b_trim_of_unsigned_kit_needs_no_cut(self):
        k, b = self.kit_b("lane/kitu")
        self.run_job("--classes", "b")
        self.assertFalse(os.path.exists(os.path.join(b, "5_route.odb")))
        self.assertEqual(self.dxreq(), [])

    def test_gate_down_does_not_hold_unsigned(self):
        k2, b2 = self.kit_b("lane/kitu2")
        self.dx = None                     # gate file missing
        self.run_job("--classes", "b")
        self.assertFalse(os.path.exists(os.path.join(b2, "5_route.odb")))
        fin, odb = self.attempt("not_a_current_design", 1, "6_final")
        sup, _ = self.attempt("not_a_current_design", 2, "3_place")
        self.kw_for(fin, sup)
        self.dx = {"all": True, "ledger": []}   # the drive's HOLD ALL file (snapshot failed)
        self.run_job("--classes", "a")
        self.assertFalse(os.path.exists(fin))

    def test_names_limit_and_explicit_off(self):
        fin, odb = self.attempt("old_design", 1, "6_final")
        sup, odb2 = self.attempt("old_design", 2, "6_final")
        self.kw_for(fin, sup)
        self.run_job("--classes", "a")                  # gate names only current designs: old_design is not one
        self.assertFalse(os.path.exists(fin))
        self.dx = None
        self.run_job("--classes", "a", "--design-export", "off")   # explicit off opens the gate
        self.assertFalse(os.path.exists(sup))

    def test_drive_writes_hold_all_when_hook_fails(self):
        import types
        out = os.path.join(self.t, "snapx")
        os.makedirs(out)
        bad = os.path.join(self.t, "hook.py")
        with open(bad, "w") as f:
            f.write("import sys; sys.exit(5)\n")
        for hook in (bad, os.path.join(self.t, "missing.py")):
            p = os.path.join(out, ac.DX_FILE)
            if os.path.exists(p):
                os.unlink(p)
            a = types.SimpleNamespace(design_export_hook=hook, design_export_args="")
            ac.Driver.dx_snapshot(types.SimpleNamespace(a=a), out)
            self.assertEqual(ac.jl(p)["all"], True)


if __name__ == "__main__":
    unittest.main()
