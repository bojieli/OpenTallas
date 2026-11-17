import importlib.util
from pathlib import Path
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
