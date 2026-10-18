"""cts_native_probe.py --from-dir --relative-to (owner 10-17 0dq) on the synthetic ETM of test_pinreg_audit.py."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "hier_contract"))
import test_pinreg_audit as T  # noqa: E402


class RelativeProbe(unittest.TestCase):
    def run_probe(self, td, ins, *extra):
        kit, out = Path(td) / "kit", Path(td) / "out"
        kit.mkdir(exist_ok=True)
        out.mkdir(exist_ok=True)
        (kit / "gate_result.json").write_text(json.dumps({"kit": "k", "source_binding": {"remote_host": "h", "remote_run": "/r"}}))
        (out / "probe_tt.lib").write_text(T.lib())
        (out / "insertion.json").write_text(json.dumps(ins))
        subprocess.run([sys.executable, str(HERE.parent / "cts_native_probe.py"), str(kit), "--out", str(out), "--from-dir", *extra],
                       capture_output=True, text=True)
        return json.loads((out / "native_audit.json").read_text())

    def test_relative_and_ff_spread(self):
        ins = {"tt": {"boundary": {"mean": 160.0, "min": 150.0, "max": 170.0, "n": 4}},
               "ff": {"boundary": {"mean": 120.0, "min": 70.0, "max": 160.0, "n": 4}}}
        with tempfile.TemporaryDirectory() as td:
            r = self.run_probe(td, ins)
            self.assertEqual(r["ff_spread_ps"], 90.0)
            self.assertFalse(r["diagnostic_pass"])
            r = self.run_probe(td, ins, "--relative-to", "tt=100,ff=100")
            self.assertEqual(r["launch"]["ps"], 300.0)                   # O - C, not O - R
            self.assertEqual(r["relative"]["tt"]["mismatch_ps"], 70.0)
            self.assertEqual(r["relative"]["ff"]["mismatch_ps"], 60.0)


if __name__ == "__main__":
    unittest.main()
