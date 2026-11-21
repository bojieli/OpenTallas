"""PLACE-SLEW (CORE-LIB-LIMITS-1330): gen_phys.place_max_transition + the PRE_RESIZE hook's set_max_transition."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402


def test_default_320_every_die(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_PLACE_MAX_TRANSITION", raising=False)
    for rf in (None, "0"):
        if rf is None:
            monkeypatch.delenv("OT_RFLOW", raising=False)
        else:
            monkeypatch.setenv("OT_RFLOW", rf)
        for die in ("s81", "s81_head", "qwen_kvsys", "qwen_compute", "hbm", None):
            assert "export OT_PLACE_MAX_TRANSITION = 320" in gen_phys.install_gp_noconverge_gate(tmp_path, [], die)


def test_env_wins_and_zero_is_off(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PLACE_MAX_TRANSITION", "250")
    assert "export OT_PLACE_MAX_TRANSITION = 250" in gen_phys.install_gp_noconverge_gate(tmp_path, [], "hbm")
    monkeypatch.setenv("OT_PLACE_MAX_TRANSITION", "0")
    assert not any("OT_PLACE_MAX_TRANSITION" in c for c in gen_phys.install_gp_noconverge_gate(tmp_path, [], "s81"))


def test_own_hook_kept(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PLACE_MAX_TRANSITION", "320")
    assert gen_phys.install_gp_noconverge_gate(tmp_path, ["export PRE_RESIZE_TCL = /work/x.tcl"]) == []


@pytest.mark.parametrize("bad", ["x", "-4", "5", "5000"])
def test_bad_values(monkeypatch, bad):
    monkeypatch.setenv("OT_PLACE_MAX_TRANSITION", bad)
    with pytest.raises(ValueError):
        gen_phys.place_max_transition("s81")


STUBS = r"""
proc current_design {} { return "dp_top" }
proc set_max_fanout {v objs} { puts "STUB set_max_fanout $v $objs" }
proc set_max_transition {v objs} { puts "STUB set_max_transition $v $objs" }
"""


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")
@pytest.mark.parametrize("val,applied", [("320", True), ("0", False), ("", True), (None, True)])   # unset = 320 (older kits)
def test_hook_applies_limit_before_repair(tmp_path, val, applied):
    kit = tmp_path / "kit"
    kit.mkdir()
    shutil.copyfile(HERE / "gp_noconverge_gate.tcl", kit / "gp_noconverge_gate.tcl")
    drv = kit / "drv.tcl"
    drv.write_text(STUBS + f"source {kit}/gp_noconverge_gate.tcl\nputs HOOK_DONE\n")
    env = dict(os.environ, LOG_DIR=str(kit / "no_logs"))
    env.pop("OT_GPL_NOCONV", None)
    env.pop("OT_PLACE_MAX_FANOUT", None)
    env.pop("OT_PLACE_MAX_TRANSITION", None)
    if val is not None:
        env["OT_PLACE_MAX_TRANSITION"] = val
    r = subprocess.run(["tclsh", str(drv)], text=True, capture_output=True, env=env)
    out = r.stdout + r.stderr
    assert "HOOK_DONE" in out, out
    assert ("STUB set_max_transition 320 dp_top" in out) == applied, out
    assert ("PLACE-SLEW set_max_transition 320 on design dp_top" in out) == applied, out
