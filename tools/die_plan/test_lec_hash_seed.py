"""LEC-DETERMINISM-1 (COORD 11-24, QC hc3 pvfd488b8f): one lec.py on one netlist failed different point sets per run
(u_xl3_5 17 points, u_xl3_1 85 points, u_xh3 b_emin 290 points).  Candidate discovery iterates sets of register-name
strings, and `python3 -I` randomises str hashing per process, so the proposal order moved between runs.  lec.py now
re-execs once with PYTHONHASHSEED=0 (same isolation: -s, scrubbed PYTHON* environment, -P where available).
    python3 -m pytest -q tools/die_plan/test_lec_hash_seed.py"""
import json
import os
import subprocess
import sys
from pathlib import Path

LEC = Path(__file__).resolve().parent / "lec.py"


def _probe(extra_env=None):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHASHSEED", "OT_LEC_HASHSEED_EXEC")}
    env.update(OT_LEC_HASHSEED_PROBE="1", **(extra_env or {}))
    out = subprocess.run([sys.executable, "-I", str(LEC)], env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_str_hash_order_is_identical_across_processes():
    runs = [_probe() for _ in range(3)]
    assert all(r["seed"] == "0" and r["randomized"] is False for r in runs)
    assert len({r["hash"] for r in runs}) == 1          # failed before the fix: -I randomised the seed per process


def test_reexec_keeps_isolation():
    r = _probe({"PYTHONPATH": "/nonexistent-ot-lec", "PYTHONSTARTUP": "/nonexistent-ot-lec.py"})
    assert r["no_user_site"] is True
    assert r["python_env"] == []                        # no PYTHON* variable but the seed reaches the child


def test_pinned_parent_is_not_reexecuted():
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env.update(PYTHONHASHSEED="0", OT_LEC_HASHSEED_PROBE="1")
    out = subprocess.run([sys.executable, "-s", str(LEC)], env=env, capture_output=True, text=True, check=True)
    r = json.loads(out.stdout.strip().splitlines()[-1])
    assert r["seed"] == "0" and r["randomized"] is False
