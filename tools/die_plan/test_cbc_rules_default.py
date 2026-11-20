"""OWNER 11-20 #6: the generator placed-hop cap is 300 um on every die; the check rule stays 405 (cbc_rules)."""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _probe(env_extra):
    env = {k: v for k, v in os.environ.items() if k != "OT_CBC_REACH_UM"}
    env.update(env_extra)
    code = ("import sys; sys.path.insert(0, %r); import cbc_rules as C, relay_depth as R, s81_hi_corridor as H, "
            "istation_clear as I, collector_reach as Q; print(C.REACH_UM_PER_HOP, C.REACH_GATE_UM, R.LIMIT, H.LIMIT, I.LIMIT, Q.REACH_UM)") % str(HERE)
    return subprocess.run([sys.executable, "-I", "-c", code], env=env, capture_output=True, text=True, check=True).stdout.split()


def test_generator_default_is_300_and_gate_stays_405():
    assert _probe({}) == ["300.0", "405.0", "300.0", "295.0", "295.0", "405.0"]


def test_env_override_reaches_every_generator():
    assert _probe({"OT_CBC_REACH_UM": "405"}) == ["405.0", "405.0", "405.0", "400.0", "400.0", "405.0"]
