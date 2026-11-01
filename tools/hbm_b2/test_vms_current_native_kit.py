"""The native bank profile must not reintroduce the observed source confounds."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vms_current_native_kit as V


class NativeVMSContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.readset = json.loads((V.ROOT / V.READSET).read_text())
        self.views = self.root / "views.json"
        self.views.write_text(json.dumps(dict(
            plan_sha256=self.readset["plan_sha256"],
            view_list=[dict(view=v, module=V.MODULE) for v in self.readset["views"]])))

    def test_actual_c_bundle_has_no_generic_shell_or_old_file_commit(self):
        recipe, profile = V.prepare(V.ROOT, self.readset["views"][0], self.views)
        self.assertEqual(recipe["top"], "hfd_vms_bank_native_q0_faces")
        self.assertEqual(recipe["params"], {})
        self.assertFalse(recipe["read_at_commit"])
        self.assertNotIn("files_at_commit", recipe)
        self.assertEqual(profile["added_face_cycles"], 0)
        self.assertEqual(profile["native_capacity"]["macros"],
                         {"ot_sram_1r1w_1024x256_m2_r2c2": 3})

    def test_four_sram_adapter_cannot_alias_current_bank(self):
        with self.assertRaisesRegex(ValueError, "no vec6293/r2048 alias"):
            V.prepare(V.ROOT, "hnx_vms_bank_q0_faces__vec6293@d2ac2d17712e", self.views)

    def test_changed_selected_source_stops_before_generation(self):
        target = self.root / V.READSET
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(self.readset))
        for row in self.readset["files"]:
            dest = self.root / row["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(V.ROOT / row["file"], dest)
        first = self.root / self.readset["files"][0]["file"]
        first.write_bytes(first.read_bytes() + b"\n// changed\n")
        with self.assertRaisesRegex(ValueError, "selected current C source changed"):
            V.prepare(self.root, self.readset["views"][0], self.views)

    def test_generic_shell_cannot_be_reenabled(self):
        with self.assertRaisesRegex(ValueError, "--face-shell must be off"):
            V.main(["--repo", str(V.ROOT), "--views", str(self.views),
                    "--view", self.readset["views"][0], "--face-shell", "on",
                    "--prepare-only"])

    def test_shared_backend_can_import_its_sibling_contract(self):
        d = self.root / "physical/die_plan/hbm_arch_cores"
        d.mkdir(parents=True)
        (d / "vms_test_sibling_contract.py").write_text("VALUE = 'native-source'\n")
        (d / "gen_core_kit_hbm.py").write_text(
            "from vms_test_sibling_contract import VALUE\n")
        self.assertEqual(V.load_backend(self.root).VALUE, "native-source")


if __name__ == "__main__":
    unittest.main()
