"""Execute each core generator's standalone signoff packaging call without P&R."""
import ast
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = [
    "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py",
    "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py",
    "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py",
    "physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py",
]


@pytest.mark.parametrize("generator", GENERATORS)
def test_core_runtime_signoff_bundle(tmp_path, generator):
    tree = ast.parse((ROOT / generator).read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Expr)
             and isinstance(n.value, ast.Call)
             and any(isinstance(c, ast.Constant) and c.value == "bundle"
                     for c in ast.walk(n))]
    assert len(calls) == 1, "core kit must use canonical complete bundle API"
    unit = ast.fix_missing_locations(ast.Module(body=calls, type_ignores=[]))
    tool = ROOT / "tools/die_plan"
    exec(compile(unit, generator, "exec"),
         dict(subprocess=subprocess, sys=sys, TOOL=tool, Path=Path,
              a=SimpleNamespace(tool=str(tool)), kd=tmp_path))
    # These are runtime dependencies, not merely generation-time imports.
    for name in ("signoff.py", "sdc_lint.py", "face_guard.py", "io_hold_qualification.py",
                 "pair_skew.tcl", "clock_family.tcl"):
        assert (tmp_path / name).is_file(), name
    p = subprocess.run([sys.executable, "-I", str(tmp_path / "signoff.py"), "--help"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
