"""FLOW-PROC-A 11-21 (COORD, FAM-QC-CB fp7 rc 22): the run_item pre-gen check lists EVERY absolute gen / kit-rtl input that does not
resolve on the gen host, with the host, before mkdir / gen (bind_out, prep_cmd, notes and revert records are not inputs here)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


class PreGenInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d / "plan.json").write_text("{}")
        (self.d / "base").mkdir()
        (self.d / "base" / "a.sv").write_text("")
        self.asb = self.d / "asbuilt_preview.json"
        self.asb.write_text(json.dumps({"base": str(self.d / "base"), "files": ["a.sv", "gone.sv"]}))
        self.sp = {"type_overlay": str(self.d / "overlay_missing.json"),
                   "gen_args": ["--clock-landing", str(self.d / "landing_missing.json")],
                   "gen_env": {"OT_SIGNED_VIEW_SHA": str(self.d / "sv_missing.json"), "OT_X": "1"}}
        self.kr = {"mode": "bind", "asbuilt": str(self.asb), "bind_out": str(self.d / "bind_elsewhere"),
                   "prep_cmd": f"python3 x.py > {self.d}/written_by_prep.json", "note": "/srv/old/path",
                   "prev_asbuilt": "/srv/old/asbuilt.json", "script": str(self.d / "kitrtl_missing.sh")}

    def items(self):
        return KW.pre_gen_inputs(self.sp, str(self.d / "plan.json"), self.kr)

    def test_inputs_audited_and_skips(self):
        roles = {p: r for r, p in self.items()}
        self.assertEqual(roles[str(self.d / "plan.json")], "plan")
        self.assertEqual(roles[str(self.asb)], "kit_rtl.asbuilt")
        self.assertEqual(roles[str(self.d / "kitrtl_missing.sh")], "kit_rtl.script")
        self.assertEqual(roles[str(self.d / "overlay_missing.json")], "type_overlay")
        self.assertEqual(roles[str(self.d / "landing_missing.json")], "gen_args")
        self.assertEqual(roles[str(self.d / "sv_missing.json")], "gen_env")
        for skipped in (str(self.d / "bind_elsewhere"), f"{self.d}/written_by_prep.json", "/srv/old/path", "/srv/old/asbuilt.json"):
            self.assertNotIn(skipped, roles)

    def run_probe(self):
        items = self.items()
        txt = subprocess.run(["bash", "-c", KW.pre_gen_probe_cmd(items)], capture_output=True, text=True, timeout=60).stdout
        return KW.pre_gen_verdict(items, "epyc7", txt)

    def test_every_missing_path_named_with_host(self):
        why = self.run_probe()
        self.assertTrue(why.startswith("KIT_INPUT_MISSING: pre-gen check on host epyc7: 5 absolute input(s)"), why)
        for p in ("kitrtl_missing.sh", "overlay_missing.json", "landing_missing.json", "sv_missing.json"):
            self.assertIn(str(self.d / p), why)
        self.assertIn(f"{self.d / 'base' / 'gone.sv'} (named by {self.asb})", why)
        self.assertNotIn(str(self.d / "plan.json") + ";", why)

    def test_all_present_is_clean(self):
        self.sp = {}
        self.kr = {"mode": "bind", "asbuilt": str(self.d / "plan.json")}
        self.assertEqual(self.run_probe(), "")

    def test_classified_flow_not_infra(self):
        cls, _ = KW.classify("abs_inputs", "KIT_INPUT_MISSING: pre-gen check on host epyc7: 1 absolute input(s) do not resolve before any work: kit_rtl.asbuilt /srv/x.json")
        self.assertEqual(cls, "FLOW")


if __name__ == "__main__":
    unittest.main()
