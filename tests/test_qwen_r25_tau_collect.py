import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("tau_collect", Path(__file__).parents[1] / "tools/qwen_r25_tau_collect.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class TauCollectionTest(unittest.TestCase):
    def fixture(self, directory):
        for shard, (cls, first, count) in collector.SHARDS.items():
            rec = dict(collector.EXPECTED_PINS)
            rec["schema"] = "opentallas.qwen-rom-dspark-tau.v1"
            rec["prompts_jsonl"] = {"sha256": rec.pop("prompts_sha256"), "class_map": {}}
            rec["samples"] = [{"class": cls, "prompt_index": i,
                               collector.KEY: 2 + list(collector.COUNTS).index(cls)/10,
                               "fast_path_equals_reference_at_first_step": True}
                              for i in range(first, first+count)]
            (directory / (shard + ".json")).write_text(json.dumps(rec))

    def test_complete_equal_class_blend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            result = collector.collect(root)
            self.assertEqual(result["status"], "COMPLETE_CHARACTERIZATION")
            self.assertAlmostEqual(result["blend_owner6"], 6/sum(1/(2+i/10) for i in range(6)))
            self.assertFalse(result["deployment_qualified"])
            self.assertIsNone(result["classes"]["agentic"]["pooled_tau"])

    def test_partial_shard_cannot_publish_blend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            p = root / "ag5.json"
            rec = json.loads(p.read_text())
            rec["samples"].pop()
            p.write_text(json.dumps(rec))
            self.assertIsNone(collector.collect(root)["blend_owner6"])

    def test_corrupt_identity_pins_exactness_and_ratio_rejected(self):
        mutations = [lambda r: r["samples"][0].update(prompt_index=99),
                     lambda r: r.update(tool_sha256="unregistered"),
                     lambda r: r["samples"][0].update(fast_path_equals_reference_at_first_step=False),
                     lambda r: r["samples"][0].update({collector.KEY: float("nan")}),
                     lambda r: r["samples"].append(r["samples"][0])]
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.fixture(root)
                p = root / "cr0.json"
                rec = json.loads(p.read_text())
                mutation(rec)
                p.write_text(json.dumps(rec))
                result = collector.collect(root)
                self.assertTrue(result["errors"])
                self.assertIsNone(result["blend_owner6"])


if __name__ == "__main__":
    unittest.main()
