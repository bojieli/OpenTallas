"""Evidence and A/B qualification checks; no RTL or numerical golden runs."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collect", ROOT / "tools/qwen_rom_realmem_collect.py")
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "results/rtl/qwen_rom_real_memory_20261003/runs_attempt2_srcdrift/real_p255.json"
        self.real = json.loads(path.read_text())
        self.ideal = copy.deepcopy(self.real)
        self.ideal["configuration"] = "KV_IDEAL A/B reference (HBM bypassed, slices preloaded)"

    def test_historical_exact_but_unstable_failure_is_not_a_baseline(self):
        self.assertTrue(all(c["mismatches"] == 0 for c in self.real["layer_x_checks"].values()))
        self.assertFalse(collect.comparable(self.real, self.ideal))
        self.real["status"] = self.ideal["status"] = "pass"
        self.assertFalse(collect.comparable(self.real, self.ideal))

    def test_passing_pair_requires_identical_provenance(self):
        self.real.update(status="pass", source_stable=True)
        self.ideal.update(status="pass", source_stable=True)
        self.assertTrue(collect.comparable(self.real, self.ideal))
        for key in ("position", "token", "source_sha256", "binary_sha256", "generated_core_sha256",
                    "stage_image_sha256", "kv_history_sha256", "oracle_json_sha256", "design_point", "stages_run"):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.ideal)
                bad[key] = "different"
                self.assertFalse(collect.comparable(self.real, bad))
                bad[key] = None
                self.assertFalse(collect.comparable(self.real, bad))

    def test_cannot_replace_failure_with_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            failure = b'{"status":"fail"}\n'
            collect.preserve(path, failure)
            collect.preserve(path, failure)
            with self.assertRaises(ValueError):
                collect.preserve(path, b'{"status":"pass"}\n')
            self.assertEqual(path.read_bytes(), failure)


if __name__ == "__main__":
    unittest.main()
