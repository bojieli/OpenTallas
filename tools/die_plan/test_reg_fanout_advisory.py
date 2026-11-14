"""WF-1 11-14 (OWNER: no procedural gates, R-MINIMAL is the only blocker): the pre-floorplan reg_fanout check logs and continues in every kit generator."""
import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _legacy_step():
    src = (ROOT / "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py").read_text()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "REG_FANOUT_STEP" for t in node.targets):
            return eval(compile(ast.Expression(node.value), "legacy", "eval"), {})
    raise AssertionError("REG_FANOUT_STEP not found")


def test_s81_core_kit_reg_fanout_step_never_fails_the_kit():
    step = _legacy_step()
    assert "FAIL_PREFLOOR" not in step and "rc=7" not in step and "ADVISORY" in step


def test_s81_core_kit_step_runs_the_gate_but_continues_in_bash(tmp_path):
    step = _legacy_step().replace("\\$", "$").replace("$TOP", "top").replace("/work/", str(tmp_path) + "/")
    (tmp_path / "reg_fanout_gate.py").write_text("import sys; print('FAIL 74 loads'); sys.exit(1)\n")
    r = subprocess.run(["bash", "-c", "rc=0; N=x; " + step + 'echo "FINAL rc=$rc"'], capture_output=True, text=True, timeout=30)
    assert "FINAL rc=0" in r.stdout and "ADVISORY" in r.stdout and not (tmp_path / "FAIL_PREFLOOR").exists(), r.stdout + r.stderr


def test_type_kit_runner_reg_fanout_is_advisory_too():
    t = (ROOT / "tools/die_plan/gen_phys.py").read_text()
    m = re.search(r"reg_fanout_gate\.py[^\n]*\n?", t[t.index("python3 -I /work/reg_fanout_gate.py"):])
    seg = t[t.index("python3 -I /work/reg_fanout_gate.py"):][:600]
    assert "ADVISORY" in seg and "rc=0" in seg and "FAIL_PREFLOOR reg_fanout" not in seg
