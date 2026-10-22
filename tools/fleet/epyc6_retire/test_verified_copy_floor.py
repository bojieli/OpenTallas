"""A final byte-exact archive can satisfy a skipped redundant copy; actual loss cannot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent

class VerifiedCopyFloor(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("retire_floor", HERE / "epyc6_retire.py")
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m.DEST = self.tmp.name
        self.root = "/root"
        self.dst = Path(self.tmp.name) / "root"
        self.dst.mkdir()
        (self.dst / "source.sv").write_bytes(b"old")
        (self.dst / "link").symlink_to("source.sv")
        self.items = [["source.sv", 3, hashlib.sha256(b"old").hexdigest()],
                      ["link", "L", hashlib.sha256(b"source.sv").hexdigest()]]
        self.summ = {self.root: dict(files=1, links=1, exists=True)}
        self.errs = {self.root: "AGIdock /archive free 408 GB < floor + 90 GB (copy held)"}

    def verify(self):
        result = subprocess.run([sys.executable, str(HERE / "remote_verify.py"), "list"],
            input=json.dumps({str(self.dst): self.items}), text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_complete_regular_and_symlink_bytes_remove_only_estimate(self):
        self.assertEqual(self.m.retain_copy_errors(self.errs, self.summ, self.verify(), self.m.AGI_FLOOR), {})

    def test_actual_space_below_floor_or_unknown_keeps_hold(self):
        proof = self.verify()
        for free in [self.m.AGI_FLOOR - 1, None, True]:
            with self.subTest(free=free):
                self.assertEqual(self.m.retain_copy_errors(self.errs, self.summ, proof, free), self.errs)

    def test_same_size_corruption_keeps_hold(self):
        (self.dst / "source.sv").write_bytes(b"new")
        self.assertEqual(self.m.retain_copy_errors(self.errs, self.summ, self.verify(), self.m.AGI_FLOOR), self.errs)

    def test_missing_file_keeps_hold(self):
        (self.dst / "source.sv").unlink()
        self.assertEqual(self.m.retain_copy_errors(self.errs, self.summ, self.verify(), self.m.AGI_FLOOR), self.errs)

    def test_changed_symlink_keeps_hold(self):
        (self.dst / "link").unlink()
        (self.dst / "link").symlink_to("other.sv")
        self.assertEqual(self.m.retain_copy_errors(self.errs, self.summ, self.verify(), self.m.AGI_FLOOR), self.errs)

    def test_rsync_failure_never_cleared(self):
        errs = {self.root: "rsync rc 23: unreadable file"}
        self.assertEqual(self.m.retain_copy_errors(errs, self.summ, self.verify(), self.m.AGI_FLOOR), errs)

    def test_missing_or_incomplete_receipt_keeps_hold(self):
        for proof in [{}, {str(self.dst): dict(ok=True)},
                      {str(self.dst): dict(ok=True,n=1,missing=0,size_mismatch=0,hash_mismatch=0)}]:
            with self.subTest(proof=proof):
                self.assertEqual(self.m.retain_copy_errors(self.errs, self.summ, proof, self.m.AGI_FLOOR), self.errs)

if __name__ == "__main__":
    unittest.main()
