"""KITPACK-CLOSE-1115 (COORD r221 F3): the adoption preflight refuses with the COMPLETE named list of missing kit inputs."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adopt_guard as AG  # noqa: E402
import kit_input_preflight as KP  # noqa: E402


def local_run(argv, timeout=900):
    import subprocess
    r = subprocess.run(argv[:3] if argv[0] == "bash" else argv, capture_output=True, text=True)
    return r.returncode, r.stdout


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.views = t / "views"
        for name, ok in (("good", True), ("cland_a", False), ("stub", True)):
            v = self.views / name
            v.mkdir(parents=True)
            (v / f"{name}.lef").write_text("x")
            export = {"signoff": "/gone/signoff.json"} if name != "stub" else {}
            (v / "provenance.json").write_text(json.dumps({"export": export}))
            if ok:
                (v / "signoff.json").write_text("{}")
        (self.views / "good" / "good.lef").write_text("x")
        self.plan = t / "plan.json"
        self.plan.write_text(json.dumps({"partition_types": {"T": {"cores": [str(self.views / n / f"{n}.lef") for n in ("good", "cland_a", "stub")]
                                                                   + ["/nowhere/ghost/ghost.lef"]}}}))
        self.cfg = {"dies": {"d": {"plan": str(self.plan), "src": str(t / "src"),
                                   "prov_view_sources": {"modx": [{"host": "epyc4", "dir": "/x"}, {"host": "epyc7", "dir": "/y"}]}}}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_list_not_first_miss(self):
        extra = [str(Path(self.tmp.name) / f"src/rtl/f{i}.sv") for i in range(3)]      # three missing src inputs
        ents = KP.preflight(self.cfg, "d", ["localhost"], run=local_run, src_files=extra)
        paths = {e["path"] for e in ents}
        for f in extra:
            self.assertIn(f, paths)                                                 # every src miss, not the first
        v = str(self.views)
        self.assertIn(f"{v}/cland_a/signoff.json", paths)                           # view lacks its closed signoff copy
        self.assertIn(f"{v}/cland_a/landing_evidence/manifest.json", paths)        # landing child without evidence
        self.assertIn(f"{v}/stub/provenance.json", paths)                           # stub provenance
        self.assertIn("/nowhere/ghost/ghost.lef", paths)                            # unresolved view
        self.assertIn("epyc4:/x", paths)                                            # terminated host candidate
        self.assertNotIn("epyc7:/y", paths)
        self.assertNotIn(f"{v}/good/signoff.json", paths)
        text = KP.refusal("d", ents)
        self.assertIn("REFUSED", text)
        self.assertEqual(sum(1 for ln in text.splitlines() if "src/rtl/f" in ln), 3)

    def test_ok_when_everything_resolves(self):
        cfg = {"dies": {"d": {"plan": str(self.plan), "src": "", "prov_view_sources": {}}}}
        v = self.views
        for n in ("cland_a", "stub"):
            (v / n / "signoff.json").write_text("{}")
        (v / "cland_a" / "landing_evidence").mkdir()
        (v / "cland_a" / "landing_evidence" / "manifest.json").write_text("{}")
        (v / "stub" / "provenance.json").write_text(json.dumps({"export": {"signoff": "/a"}}))
        plan = json.loads(self.plan.read_text())
        plan["partition_types"]["T"]["cores"].pop()
        self.plan.write_text(json.dumps(plan))
        self.assertEqual(KP.preflight(cfg, "d", ["localhost"], run=local_run), [])

    def test_adopt_guard_refuses_and_logs_the_list(self):
        logs = []
        ok = AG.preflight_all(self.cfg, "d", ["localhost"], [], local_run, logs.append)
        self.assertFalse(ok)
        self.assertTrue(any("cland_a/landing_evidence/manifest.json" in l for l in logs))
        self.assertTrue(any("preflight d: FAIL closed" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
