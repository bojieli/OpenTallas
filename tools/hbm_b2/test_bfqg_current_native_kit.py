import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bfqg_current_native_kit as B


class CurrentBFQG(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.readset = json.loads((B.ROOT / B.READSET).read_text())
        self.views = self.root / "views.json"
        self.views.write_text(json.dumps(dict(plan_sha256=self.readset["plan_sha256"],
            view_list=[dict(view=v, module=B.MODULE) for v in self.readset["views"]])))

    def test_exact_current_source_and_all_twenty_clocks(self):
        recipe, profile = B.prepare(B.ROOT, self.readset["views"][0], self.views)
        self.assertEqual(recipe["params"], {})
        self.assertFalse(recipe["read_at_commit"])
        self.assertNotIn("files_at_commit", recipe)
        self.assertEqual(len(profile["clock_ports"]), 20)
        self.assertEqual(len(set(profile["clock_ports"])), 20)
        self.assertEqual(profile["native_capacity"]["macros"],
                         {"ot_sram_1r1w_128x256_m1_r2c2": 8})
        self.assertEqual(profile["added_face_cycles"], 0)

    def test_foreign_view_cannot_replace_current_interface(self):
        with self.assertRaisesRegex(ValueError, "not the current native BFQG"):
            B.prepare(B.ROOT, "ot_hgi_sm_xload_cl2_bfqg@old", self.views)

    def test_source_mutation_stops_before_generation(self):
        p = self.root / B.READSET
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(self.readset))
        for row in self.readset["files"]:
            dest = self.root / row["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(B.ROOT / row["file"], dest)
        changed = self.root / self.readset["files"][0]["file"]
        changed.write_bytes(changed.read_bytes() + b"\n// changed\n")
        with self.assertRaisesRegex(ValueError, "selected current C source changed"):
            B.prepare(self.root, self.readset["views"][0], self.views)

    def test_generic_shell_cannot_be_added(self):
        with self.assertRaisesRegex(ValueError, "--face-shell must be off"):
            B.main(["--views", str(self.views), "--view", self.readset["views"][0],
                    "--face-shell", "on", "--prepare-only"])


if __name__ == "__main__":
    unittest.main()
