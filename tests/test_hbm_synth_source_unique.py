"""Exercise the exact synth script generator without running synthesis."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SourceUniqueTest(unittest.TestCase):
    def test_scoped_extra_is_read_once_and_conflicts_remain_visible(self):
        script = (ROOT / "tools/hbm_die_v15/synth_master.sh").read_text()
        generator = script.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            inp, ys = td / "files.json", td / "out.ys"
            inp.write_text(json.dumps({"files": ["rtl/scoped.sv", "rtl/other.sv", "rtl/./scoped.sv"], "macros": []}))
            args = [str(inp), str(ys), "top", "-", "-", "sample", "0", "1", "", "v16w/wrap.sv,rtl/scoped.sv", "0", "wrap", ""]
            subprocess.run([sys.executable, "-", *args], input=generator, text=True, cwd=td, check=True)
            reads = [x for x in ys.read_text().splitlines() if x.startswith("read_verilog")]
            self.assertEqual(reads, ["read_verilog -sv -DSYNTHESIS rtl/scoped.sv", "read_verilog -sv -DSYNTHESIS v16w/wrap.sv", "read_verilog -sv -DSYNTHESIS rtl/other.sv"])
            self.assertIn("hierarchy -check -top wrap", ys.read_text())

if __name__ == "__main__":
    unittest.main()
