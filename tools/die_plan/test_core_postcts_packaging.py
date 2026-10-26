"""Core kit packaging must ship the shared procedure called by its insertion gate."""
import ast
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = [
    "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py",
    "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py",
]


@pytest.mark.parametrize("generator", GENERATORS)
def test_packaged_postcts_pinreg_runtime(tmp_path, generator):
    tree = ast.parse((ROOT / generator).read_text())
    # Execute the production copy loop without building a physical design.
    loops = [n for n in ast.walk(tree) if isinstance(n, ast.For)
             and any(isinstance(c, ast.Constant) and c.value == "postcts_gate.tcl"
                     for c in ast.walk(n.iter))]
    assert len(loops) == 1
    unit = ast.fix_missing_locations(ast.Module(body=loops, type_ignores=[]))
    exec(compile(unit, generator, "exec"),
         dict(shutil=shutil, TOOL=ROOT / "tools/die_plan", kd=tmp_path, modern=True))
    gate = (tmp_path / "postcts_gate.tcl").read_text()
    assert "ot_pinreg_set" in gate and "ot_pinreg_arr" in gate
    helper = tmp_path / "pinreg_measure.tcl"
    assert helper.is_file(), "insertion gate dependency missing from generated core kit"
    script = f'''source {{{helper}}}
foreach p {{ot_pinreg_set ot_pinreg_arr}} {{
  if {{![llength [info commands $p]]}} {{error "missing $p"}}
}}
'''
    p = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
