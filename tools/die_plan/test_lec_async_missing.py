"""KIT-OPS-1 11-13 (COORD): a kit runner with async LEC on (OT_LEC_ASYNC default 1, or lec_async.on / .identity) whose kit
has lec.py but no lec_async.sh fails fast (exit 13, LEC_ASYNC KIT ERROR) instead of silently running the blocking inline LEC
after synthesis.  Kits that have lec_async.sh, kits without lec.py and OT_LEC_ASYNC=0 behave as before.
    python3 -m pytest -q tools/die_plan/test_lec_async_missing.py"""
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SH_RUNNERS = ("physical/die_plan/hbm_arch_cores/run_kit_hbm.sh", "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh",
              "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py")
BLOCK = re.compile(r"^LECA=\n.*?\n  exit 13\nfi\n", re.S | re.M)


def _runner_texts():
    sys.path.insert(0, str(HERE))
    import gen_phys
    out = {"gen_phys": gen_phys.RUN_KIT}
    for f in SH_RUNNERS:
        out[f] = (ROOT / f).read_text()
    leg = ROOT / "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"
    for node in ast.parse(leg.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "LECA_START" for t in node.targets):
            out["legacy"] = eval(compile(ast.Expression(node.value), str(leg), "eval"), {})
    return out


TEXTS = _runner_texts()


def _block(name):
    m = BLOCK.search(TEXTS[name])
    assert m, f"{name}: LECA start block with the fail-fast check not found"
    return m.group(0)


def _run(tmp_path, name, lec_py=True, lec_async=False, env_async=None, flag=None):
    k = tmp_path / "kit"
    k.mkdir()
    if lec_py:
        (k / "lec.py").write_text("")
    if lec_async:
        (k / "lec_async.sh").write_text('echo started > "$2/started"\n')
    if flag:
        (k / flag).write_text("")
    script = (f'K={k}; NAME=n; IMAGE=i; MEM=1; CPUS=1; DOCKER=docker; DK=docker; GOAL=route\n'
              + _block(name) + 'echo "AFTER LECA=$LECA"\n')
    env = {kk: v for kk, v in os.environ.items() if kk != "OT_LEC_ASYNC"}
    if env_async is not None:
        env["OT_LEC_ASYNC"] = env_async
    p = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=30)
    return p, k


NAMES = sorted(TEXTS)


def test_all_five_runners_carry_the_check():
    assert set(NAMES) == {"gen_phys", "legacy", *SH_RUNNERS}


@pytest.mark.parametrize("name", NAMES)
def test_missing_lec_async_fails_fast(tmp_path, name):
    p, k = _run(tmp_path, name)
    assert p.returncode == 13
    assert "LEC_ASYNC KIT ERROR" in p.stderr and "lec_async.sh is missing" in p.stderr
    assert "AFTER" not in p.stdout


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("flag", ["lec_async.on", "lec_async.identity"])
def test_flag_file_with_async_off_still_fails_fast(tmp_path, name, flag):
    p, _ = _run(tmp_path, name, env_async="0", flag=flag)
    assert p.returncode == 13 and "LEC_ASYNC KIT ERROR" in p.stderr


@pytest.mark.parametrize("name", NAMES)
def test_kit_with_lec_async_unchanged(tmp_path, name):
    p, k = _run(tmp_path, name, lec_async=True)
    assert p.returncode == 0, p.stderr
    assert "AFTER LECA=1" in p.stdout and (k / "started").exists() and "KIT ERROR" not in p.stderr


@pytest.mark.parametrize("name", NAMES)
def test_inline_on_purpose_and_no_lec_unchanged(tmp_path, name):
    p, _ = _run(tmp_path, name, env_async="0")                  # OT_LEC_ASYNC=0: the inline LEC, as before
    assert p.returncode == 0 and "AFTER LECA=" in p.stdout and "KIT ERROR" not in p.stderr
    (tmp_path / "b").mkdir()
    p, _ = _run(tmp_path / "b", name, lec_py=False)
    assert p.returncode == 0 and "AFTER LECA=" in p.stdout     # no lec.py: no LEC at all, as before
