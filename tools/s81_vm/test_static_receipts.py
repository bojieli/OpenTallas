import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from check_static_receipts import verify


class Receipt(unittest.TestCase):
    def fixture(self, root):
        for name, text in (("rtl.sv", "module rtl;endmodule\n"),
                           ("run_base.log", "RESULT reads17 bad0\nPASS\n"),
                           ("run_mutant.log", "RESULT reads17 bad3\nFAIL\n")):
            (root / name).write_text(text)
        record = {"source_sha256": {"rtl.sv": hashlib.sha256((root / "rtl.sv").read_bytes()).hexdigest()},
                  "log_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
                                 for p in ("run_base.log", "run_mutant.log")}}
        (root / "receipt.json").write_text(json.dumps({"gates": {"g": record}}))
        return record

    def test_positive_and_observed_mutant(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);self.fixture(root)
            self.assertEqual(verify(root, "receipt.json", "g", ["rtl.sv"])["minimum_positive_observations"], 17)

    def test_changed_source_or_log_refused(self):
        for changed in ("rtl.sv", "run_base.log", "run_mutant.log"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as td:
                root = Path(td);self.fixture(root)
                with (root / changed).open("a") as f:f.write("changed\n")
                with self.assertRaises(ValueError):verify(root, "receipt.json", "g")

    def test_missing_mutant_and_empty_positive_refused(self):
        for mutation in ("missing", "empty"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as td:
                root = Path(td);record = self.fixture(root)
                if mutation == "missing":record["log_sha256"].pop("run_mutant.log")
                else:
                    (root / "run_base.log").write_text("RESULT reads0 bad0\nPASS\n")
                    record["log_sha256"]["run_base.log"] = hashlib.sha256((root / "run_base.log").read_bytes()).hexdigest()
                (root / "receipt.json").write_text(json.dumps({"gates": {"g": record}}))
                with self.assertRaises(ValueError):verify(root, "receipt.json", "g")

    def test_wrong_source_binding_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);self.fixture(root)
            with self.assertRaises(ValueError):verify(root, "receipt.json", "g", ["other.sv"])


if __name__ == "__main__":unittest.main()
