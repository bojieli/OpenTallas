"""HBM-COLLECT-1 11-09 (COORD class fix): the HBM asbuilt.param_regen hook and its inputs are repo bind inputs.

physical/die_plan/hbm/bind/hbm_param_regen.py imports hbm_lat_pads from its own ../r8 and reads
../r8/hbm_lat_contract.json.  Until now the three files lived only in one scratch tree, and hbm_lat_pads.py was
missing there on every host, so any HBM rebind off intel1 failed with PARAM_REGEN "No module named hbm_lat_pads".
This test copies the repo subset into an empty temp dir and loads the hook the way tools/die_plan/bind.py does
(importlib from a path), in a python3 -I process (no scratch path, no cwd on sys.path).  It then expands the
default contract.  The negative control drops hbm_lat_pads.py and must fail with the old error.
    python3 -m pytest tools/die_plan/test_hbm_param_regen_inputs.py
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = ["physical/die_plan/hbm/bind/hbm_param_regen.py",
         "physical/die_plan/hbm/r8/hbm_lat_pads.py",
         "physical/die_plan/hbm/r8/hbm_lat_contract.json",
         "tools/die_plan/r8.py", "tools/die_plan/schema.py",
         "tools/die_plan/latency_consumers.py", "tools/die_plan/bind_position_bank.py"]

PROBE = r"""
import importlib.util, json, sys
from pathlib import Path
f = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("bind_param_regen", f)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
legs = mod.legs_of(json.loads(mod.CONTRACT.read_text()))
import hbm_lat_pads
assert Path(hbm_lat_pads.__file__).resolve().parent == f.resolve().parent.parent / "r8", hbm_lat_pads.__file__
assert callable(mod.regen)
print("LEGS", len(legs))
"""


def run_probe(tmp):
    return subprocess.run([sys.executable, "-I", "-c", PROBE, str(tmp / FILES[0])], capture_output=True, text=True,
                          cwd=str(tmp), timeout=120)


class ParamRegenInputs(unittest.TestCase):
    def stage(self, drop=()):
        tmp = Path(tempfile.mkdtemp(prefix="pr_inputs_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        for f in FILES:
            if f in drop:
                continue
            (tmp / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / f, tmp / f)
        return tmp

    def test_files_in_repo(self):
        for f in FILES[:3]:
            self.assertTrue((ROOT / f).is_file(), f)

    def test_hook_imports_on_clean_tree(self):
        p = run_probe(self.stage())
        self.assertEqual(p.returncode, 0, p.stderr)
        n = int(p.stdout.split("LEGS", 1)[1].split()[0])
        self.assertGreater(n, 0)

    def test_control_without_lat_pads_fails(self):
        p = run_probe(self.stage(drop=("physical/die_plan/hbm/r8/hbm_lat_pads.py",)))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("No module named 'hbm_lat_pads'", p.stderr)


if __name__ == "__main__":
    unittest.main()
