import json
from pathlib import Path
import tempfile
import unittest

from hbm_layer_vehicle.check_slice_run import check_run


class CompletenessTest(unittest.TestCase):
    def fixture(self, root, *, checks=1, serial=100, rec_cycle=100):
        # Stream drive at 5, serial record-0 comparison at 100.
        headers = [(1 << 62) | 5, (2 << 62) | (1 << 60) | (1 << 32) | 100, 3 << 62]
        (root / "hdr.mem").write_text("\n".join(f"{h:016x}" for h in headers))
        (root / "index.json").write_text(json.dumps(dict(events=2, drives=1, checks=1)))
        (root / "run.log").write_text(
            (f"SLICE_REC rec=0 cyc={rec_cycle} COMMIT_OK\n" if checks else "") +
            f"SLICE_SUMMARY drives=1 checks={checks} fails=0 rec_commit_ok={checks} rec_fail=0 stream_edges=150 serial_edges={serial} hbm_edges=200\nSLICE_PASS\n")

    def test_complete(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            self.assertTrue(check_run(p, p / "run.log")["passed"])

    def test_component_pass_cannot_qualify_native_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            result = check_run(p, p / "run.log", scope="native_chain")
            self.assertFalse(result["passed"])
            self.assertFalse(result["qualifies_native_layer"])
            self.assertFalse(result["qualifies_native_chain"])

    def test_old_tb_false_pass_before_serial_check(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p, checks=0, serial=90)
            result = check_run(p, p / "run.log")
            self.assertFalse(result["passed"])
            self.assertTrue(any("last scheduled event" in e for e in result["errors"]))

    def test_wrong_commit_edge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p, rec_cycle=99)
            self.assertFalse(check_run(p, p / "run.log")["passed"])

    def test_silent_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            with (p / "hdr.mem").open("a") as f:
                f.write(f"\n{(2 << 62) | (1 << 60) | (1 << 32) | 110:016x}\n")
            self.assertFalse(check_run(p, p / "run.log")["passed"])

    def test_missing_vm_preload(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            (p / "index.json").write_text(json.dumps(dict(events=2, drives=1, checks=1, vm_preload_words=1)))
            self.assertFalse(check_run(p, p / "run.log")["passed"])


if __name__ == "__main__":
    unittest.main()
