"""FLOW-PROC-A 11-21 (COORD, FAM-QC-CB fp5/fp6): a kit whose kit_rtl.json names a bind_out that exists on another host only
reads the bind sidecars from its own kit copy (bind.py kit-rtl stages them); a miss names every path tried and the host."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_r8_straps as B  # noqa: E402
import count_strap_evidence as CSE  # noqa: E402


class KitBindSidecars(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.bind = root / "producer_host_only" / "bind"
        self.kd = root / "kit" / "rtl"
        self.bind.mkdir(parents=True)
        self.kd.mkdir(parents=True)
        self.m = dict(types={"T": {"strap_r8pad_x": dict(width=4, kind="r8pad_strap")}},
                      instances={"a": {"strap_r8pad_x": dict(width=4, value=2, kind="r8pad_strap")}})
        (self.bind / "bind_parent_id_straps.json").write_text(json.dumps(self.m))
        (self.bind / "bind_r8pad_strap_audit.json").write_text(json.dumps(dict(verdict="PASS", checked_bits=4, errors=[])))
        (self.bind / "bind_tie_audit.json").write_text(json.dumps({"ties": []}))
        (self.bind / "asbuilt.json").write_text("{}")
        self.kr = dict(plan_type="T", bound_type="T", bind_out=str(self.bind), instances=["a"],
                       bound_only_pins=[dict(port="strap_r8pad_x", dir="input", width=4)])

    def write_kr(self):
        (self.kd / "kit_rtl.json").write_text(json.dumps(self.kr))
        return self.kd / "kit_rtl.json"

    def gone(self):
        """the kit is now on a host without the producer's bind_out"""
        for p in self.bind.iterdir():
            p.rename(self.bind.parent / ("moved_" + p.name))

    def test_stage_copies_only_named_sidecars_with_sha(self):
        side = B.stage_kit_sidecars(self.bind, self.kd)
        self.assertEqual(side["dir"], "bind_sidecars")
        self.assertEqual(sorted(side["files"]), ["bind_parent_id_straps.json", "bind_r8pad_strap_audit.json", "bind_tie_audit.json"])
        self.assertFalse((self.kd / "bind_sidecars" / "asbuilt.json").exists())

    def test_kit_copy_used_when_bind_out_absent_on_this_host(self):
        self.kr["bind_sidecars"] = B.stage_kit_sidecars(self.bind, self.kd)
        kj = self.write_kr()
        self.gone()
        self.assertEqual(B.declared(kj), [dict(name="strap_r8pad_x", width=4)])
        self.assertEqual(CSE.Path, Path)
        self.assertEqual(B.bind_file(kj, self.kr, "bind_tie_audit.json"), self.kd / "bind_sidecars" / "bind_tie_audit.json")

    def test_kit_copy_wins_over_bind_out(self):
        self.kr["bind_sidecars"] = B.stage_kit_sidecars(self.bind, self.kd)
        kj = self.write_kr()
        self.assertEqual(B.bind_file(kj, self.kr, "bind_parent_id_straps.json").parent, self.kd / "bind_sidecars")

    def test_miss_names_paths_and_host(self):
        kj = self.write_kr()
        self.gone()
        with self.assertRaises(ValueError) as cm:
            B.declared(kj)
        msg = str(cm.exception)
        self.assertIn("lack their bind manifest", msg)
        self.assertIn(str(self.bind / "bind_parent_id_straps.json"), msg)
        self.assertIn(str(self.kd / "bind_sidecars" / "bind_parent_id_straps.json"), msg)
        self.assertIn("on host ", msg)

    def test_tampered_kit_copy_refused(self):
        self.kr["bind_sidecars"] = B.stage_kit_sidecars(self.bind, self.kd)
        kj = self.write_kr()
        (self.kd / "bind_sidecars" / "bind_parent_id_straps.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "sha256 differs"):
            B.declared(kj)

    def test_missing_audit_names_path(self):
        (self.bind / "bind_r8pad_strap_audit.json").unlink()
        kj = self.write_kr()
        with self.assertRaisesRegex(FileNotFoundError, "bind_r8pad_strap_audit.json not found on host .*tried"):
            B.declared(kj)

    def test_asbuilt_leaf_kit_copy_when_preview_absent_on_host(self):
        ab = self.bind.parent / "asbuilt_n46r4_final_preview.json"
        ab.write_text(json.dumps({"sub_core_leaf": {"u_q": "u_q.map_lane"}, "hard_core_leaf": {"h": "x"}, "big": [1] * 10}))
        self.kr["asbuilt_manifest"] = str(ab)
        self.kr["bind_sidecars"] = B.stage_asbuilt_leaf(str(ab), self.kd, B.stage_kit_sidecars(self.bind, self.kd))
        kj = self.write_kr()
        ab.rename(ab.with_suffix(".moved"))
        leaf = B.asbuilt_leaf(kj, self.kr)
        self.assertEqual(leaf["sub_core_leaf"], {"u_q": "u_q.map_lane"})
        self.assertEqual(leaf["sub_core_leaf_variants"], {})
        self.assertNotIn("big", leaf)

    def test_asbuilt_leaf_miss_names_paths_and_host(self):
        self.kr["asbuilt_manifest"] = str(self.bind.parent / "asbuilt_epyc9_only.json")
        kj = self.write_kr()
        with self.assertRaisesRegex(FileNotFoundError, r"on host \S+; tried .*asbuilt_leaf.json, .*asbuilt_epyc9_only.json"):
            B.asbuilt_leaf(kj, self.kr)

    def test_asbuilt_leaf_none_named(self):
        self.assertEqual(B.asbuilt_leaf(self.write_kr(), self.kr), {})


if __name__ == "__main__":
    unittest.main()
