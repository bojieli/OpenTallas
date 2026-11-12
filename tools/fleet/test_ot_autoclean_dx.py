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

    def test_every_routed_stage_held_until_published(self):
        for stage in ROUTED:
            with self.subTest(stage=stage):
                fin, odb = self.attempt("kv3_hgi", 1, stage)
                sup, odb2 = self.attempt("kv3_hgi", 2, stage)
                self.kw_for(fin, sup)
                self.dx["ledger"] = []
                self.run_job("--classes", "a")
                for d, f in ((fin, odb), (sup, odb2)):
                    self.assertTrue(os.path.exists(f), (stage, f))
                    self.assertEqual(self.row(d)[3], "SKIP")
                    self.assertIn("design-export pending", self.row(d)[4])
                req = {r[1]: r for r in self.dxreq()}
                self.assertEqual(req["hx:" + odb][2:], ["kv3_hgi", stage, "newest"])
                self.assertEqual(req["hx:" + odb2][4], "superseded")
                # cut published (ledger has both labels): the next run deletes
                self.dx["ledger"] = ["hx:" + odb, "hx:" + odb2]
                self.run_job("--classes", "a")
                self.assertFalse(os.path.exists(fin))
                self.assertFalse(os.path.exists(sup))
                self.assertEqual(self.dxreq(), [])

    def test_class_b_trim_waits_for_6_final_cut(self):
        k, b = self.kit_b("lane/kitb")
        self.run_job("--classes", "b")
        for n in ("5_route.odb", "5_3_fillcell.odb", "6_1_fill.odb", "6_final.odb"):
            self.assertTrue(os.path.exists(os.path.join(b, n)), n)
        self.assertIn("design-export pending", self.row(b)[4])
        self.dx["ledger_paths"] = [os.path.join(b, "6_final.odb")]
        self.run_job("--classes", "b")
        self.assertFalse(os.path.exists(os.path.join(b, "5_route.odb")))
        self.assertTrue(os.path.exists(os.path.join(b, "6_final.odb")))

    def test_default_on_without_gate_file_holds_everything(self):
        fin, odb = self.attempt("not_a_current_design", 1, "6_final")
        sup, _ = self.attempt("not_a_current_design", 2, "3_place")   # no routed ODB beyond 3_place: free to go
        self.kw_for(fin, sup)
        self.dx = None                     # gate file missing
        self.run_job("--classes", "a")
        self.assertTrue(os.path.exists(odb))
        self.assertIn("design-export pending", self.row(fin)[4])
        self.dx = {"all": True, "ledger": []}   # the drive's HOLD ALL file (snapshot failed)
        self.run_job("--classes", "a")
        self.assertTrue(os.path.exists(odb))

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
