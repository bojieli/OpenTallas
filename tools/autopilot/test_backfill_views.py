"""KITPACK-CLOSE-1115: backfill_views closes the views the current plans reference, and counts what stays open."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import backfill_views as BV  # noqa: E402
import hard_landing as HL  # noqa: E402


def sha(p):
    return HL.digest(p)


class TestBackfill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.t = Path(self.tmp.name)
        self.so = t / "build" / "signoff.json"
        self.so.parent.mkdir()
        self.so.write_text(json.dumps(dict(verdict="SIGNED")))
        kit = self.kit = t / "build"
        (kit / "face_guard.json").write_text(json.dumps(dict(top="m", verdict="PASS", land_mux_bits=2, netlist=str(kit / "netlist.v"))))
        (kit / "face_guard.py").write_text("# tool\n")
        (kit / "land_slots.json").write_text(json.dumps(dict(buses=dict(d=dict(D=4, form="hold_mux")))))
        (kit / "netlist.v").write_text("module m(); endmodule\n")
        self.views = {}
        for name, kind in (("cland_ok", "landing"), ("plain_core", "plain"), ("cland_gone", "gone"), ("stub_core", "stub"), ("cland_stub", "stub")):
            v = t / "views" / name
            v.mkdir(parents=True)
            (v / f"{name}.lef").write_text("l")
            (v / f"{name}_tt.lib").write_text("b")
            exp = {} if kind == "stub" else dict(signoff=str(self.so), signoff_sha256=sha(self.so))
            src = str(kit if kind in ("landing", "plain") else t / "deleted_build")
            (v / "provenance.json").write_text(json.dumps(dict(src=src, kit=dict(module=name), export=exp)))
            self.views[name] = v
        # plain_core is not a landing child: its build dir has no face_guard receipt
        self.plain_kit = t / "plain_build"
        self.plain_kit.mkdir()
        p = json.loads((self.views["plain_core"] / "provenance.json").read_text())
        p["src"] = str(self.plain_kit)
        (self.views["plain_core"] / "provenance.json").write_text(json.dumps(p))
        cores = [str(v / f"{n}.lef") for n, v in self.views.items()] + [str(t / "views" / "missing" / "missing.lef")]
        self.plan = t / "plan.json"
        self.plan.write_text(json.dumps(dict(partition_types=dict(T=dict(cores=cores)))))
        self.cfg = dict(dies=dict(d=dict(plan=str(self.plan), src=str(t / "src"))))

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_changes_nothing_and_counts(self):
        r = BV.run(self.cfg, ["d"], apply=False)
        self.assertEqual((r["closed"], r["already"], r["absent"]), (0, 0, 1))
        self.assertEqual((r["would"], r["open"], r["nonlanding"]), (2, 2, 1))
        self.assertFalse((self.views["cland_ok"] / "signoff.json").exists())

    def test_apply_closes_what_can_be_closed_and_reports_the_rest_open(self):
        r = BV.run(self.cfg, ["d"], apply=True)
        self.assertEqual((r["closed"], r["open"], r["absent"]), (2, 2, 1))
        self.assertEqual(r["nonlanding"], 1)
        ok = self.views["cland_ok"]
        self.assertTrue((ok / "signoff.json").is_file())
        man = json.loads((ok / "landing_evidence" / "manifest.json").read_text())
        for name, h in man["sha256"].items():
            self.assertEqual(sha(ok / "landing_evidence" / name), h)
        self.assertTrue((self.views["plain_core"] / "signoff.json").is_file())
        self.assertFalse((self.views["plain_core"] / "landing_evidence").exists())
        why = {i["view"].split("/")[-1]: i["why"] for i in r["items"] if i["status"] == "open"}
        self.assertIn("no longer holds", why["cland_gone"])
        self.assertIn("stub provenance", why["cland_stub"])
        # the original build dir may now vanish: the closed view still proves its own evidence
        import shutil
        shutil.rmtree(self.kit)
        self.assertEqual(BV.close_one(ok, True)[0], "already")

    def test_second_run_is_idempotent_and_provenance_is_untouched(self):
        before = (self.views["cland_ok"] / "provenance.json").read_bytes()
        BV.run(self.cfg, ["d"], apply=True)
        r2 = BV.run(self.cfg, ["d"], apply=True)
        self.assertEqual((r2["closed"], r2["already"]), (0, 2))
        self.assertEqual((self.views["cland_ok"] / "provenance.json").read_bytes(), before)

    def test_dir_without_provenance_is_a_plain_macro_not_a_view(self):
        v = self.t / "views" / "sram_macro"
        v.mkdir()
        (v / "sram_macro.lef").write_text("l")
        self.assertEqual(BV.close_one(v, True)[0], "plain")

    def test_receipt_sha_mismatch_stays_open(self):
        self.so.write_text("tampered")
        st, why = BV.close_one(self.views["cland_ok"], True)
        self.assertEqual(st, "open")
        self.assertIn("sha", why)


    def test_propagate_copies_a_closed_view_to_hosts_that_lost_the_build_dir(self):
        cmds = []

        class R:
            returncode = 0
            stderr = stdout = ""
        orig = BV.subprocess.run
        BV.subprocess.run = lambda argv, **k: cmds.append(argv[-1]) or R()
        try:
            tot = dict(hosts=dict(intel1=dict(items=[dict(status="closed", view="/v/cland_a")]),
                                  epyc7=dict(items=[dict(status="open", view="/v/cland_a"), dict(status="open", view="/v/other")])))
            n = BV.propagate(tot, log=lambda m: None)
        finally:
            BV.subprocess.run = orig
        self.assertEqual(n, 1)
        self.assertEqual(len(cmds), 1)
        self.assertIn("intel1", cmds[0])
        self.assertIn("epyc7", cmds[0])
        self.assertIn("landing_evidence", cmds[0])


if __name__ == "__main__":
    unittest.main()
