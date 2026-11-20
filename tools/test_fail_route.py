import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("fr", Path(__file__).with_name("fail_route.py"))
fr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fr)


class ExactOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.coord = Path(self.temp.name)
        (self.coord / "autopilot").mkdir()
        self.path = self.coord / "autopilot/COORD-ROUTED-OWNERS.tsv"

    def rows(self, text):
        self.path.write_text(text)

    def test_exact_owner_beats_newer_mentions(self):
        self.rows("qwen_kvsys\tkv3_hgi_v8\tKV-R\tr410\n")
        self.assertEqual(fr.explicit_owner(self.coord, "qwen_kvsys", {"kv3_hgi_v8": 1}, {"KV-R": 10, "KV-CLK-R2": 20}), "KV-R")

    def test_mixed_class_goes_coordinator(self):
        self.rows("qwen_kvsys\ta\tKV-R\nx\ta\tOTHER\nqwen_kvsys\tb\tKV-CLK-R2\n")
        self.assertEqual(fr.explicit_owner(self.coord, "qwen_kvsys", {"a": 1, "b": 2}, {"KV-R": 10, "KV-CLK-R2": 20}), "COORD")

    def test_exact_die_no_prefix_and_no_partial_override(self):
        self.rows("qwen_kvsys\titem*\tKV-R\nhead\titem1\tKV-R\nqwen_kvsys\titem1\tKV-R\n")
        self.assertEqual(fr.explicit_owner(self.coord, "qwen_kvsys", {"item12": 1}, {"KV-R": 10}), "")
        self.assertEqual(fr.explicit_owner(self.coord, "qwen_kvsys", {"item1": 1, "item2": 2}, {"KV-R": 10}), "")
        self.assertEqual(fr.explicit_owner(self.coord, "s81", {"item1": 1}, {"KV-R": 10}), "")

    def test_retired_mapping_keeps_liveness_fallback(self):
        self.rows("qwen_kvsys\ta\tKV-OLD\n")
        self.assertEqual(fr.explicit_owner(self.coord, "qwen_kvsys", {"a": 1}, {"KV-R": 10}), "")

    def test_last_exact_assignment_wins(self):
        self.rows("qwen_kvsys\ta\tKV-CLK-R2\nqwen_kvsys\ta\tKV-R\n")
        self.assertEqual(fr.explicit_owner(self.coord, "qwen_kvsys", {"a": 1}, {"KV-R": 10, "KV-CLK-R2": 20}), "KV-R")


class CoordinatorSummaryTests(unittest.TestCase):
    def test_only_exact_codex_coordinator_is_excluded(self):
        posts = [
            {"lane": "CODEX", "tag": "RESULT", "t": 100, "text": "HEAD proof FAIL preserved", "stamp": "2026-11-16 19:46"},
            {"lane": "CODEX-TOKEN", "tag": "RESULT", "t": 100, "text": "QC component FAIL actual", "stamp": "2026-11-16 19:46"},
        ]
        classes = fr.build_classes(Path("/nonexistent"), {}, posts, 101, 1, 3)
        self.assertEqual(len(classes), 1)
        cls = next(iter(classes.values()))
        self.assertEqual(cls["die"], "qwen_compute")
        self.assertEqual(set(cls["items"]), {"CODEX-TOKEN@19:46"})
        self.assertNotIn("CODEX", fr.live_lanes(posts, 101, 3))
        self.assertIn("CODEX-TOKEN", fr.live_lanes(posts, 101, 3))


class ResetEvidenceTests(unittest.TestCase):
    def test_only_exact_gen_failure_receives_the_runtime_evidence(self):
        state = {"fail_sigs": {"s81|col": {"reason": "physical collector_tree differs from captured bound reset identity"}}}
        cls = {"kind": "kit", "die": "s81", "items": {"old": 10, "col": 20}}
        with tempfile.TemporaryDirectory() as td:
            helper = Path(td) / "runtime.py"
            with patch.object(fr, "RUNTIME_FAIL_ROUTE", helper):
                self.assertEqual(fr.reset_note(state, cls), "")
                helper.write_text("def reset_evidence(state, die, item): return f' {die}/{item}'")
                self.assertEqual(fr.reset_note(state, cls), " s81/col")
                self.assertEqual(fr.reset_note(state, dict(cls, kind="waiter")), "")
                self.assertEqual(fr.reset_note({}, cls), "")


if __name__ == "__main__":
    unittest.main()
