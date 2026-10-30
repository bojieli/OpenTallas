"""FLOW-KITFAIL-3 (S81 CRS4 ra2 RSZ-0060 'Max buffer count reached', fixed kit-local in ra3): core kits' FF-only GRT
hold repair runs repair_timing at OpenROAD's default 20 % buffer cap.  core_flow.apply's grt_pre_core.tcl now raises the
cap like hold_repair_pre.tcl does (OT_MAX_BUFFER_PERCENT, default 100) and changes nothing else."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _kit(tmp_path):
    import core_flow
    core_flow.apply(tmp_path, core_flow.binding(250.0, 202.5), "t_kit", rc_cal=False, grt_pre_extra=("/work/drv.tcl",))
    return (tmp_path / "grt_pre_core.tcl").read_text()


def test_grt_pre_core_raises_buffer_cap(tmp_path):
    txt = _kit(tmp_path)
    assert "-max_buffer_percent $::ot_grt_mbp" in txt
    # main hook and the kit's own hook still come first, in order
    lines = txt.splitlines()
    assert lines.index("source /work/grt_pre.tcl") < lines.index("source /work/drv.tcl")


MOCK = r"""
set ::got {}
proc repair_timing_helper {args} { set ::got $args }
%s
repair_timing_helper -hold
puts "ARGS $::got"
"""


def _args(tmp_path, env):
    body = "\n".join(l for l in _kit(tmp_path).splitlines() if not l.startswith("source "))
    out = subprocess.run(["tclsh"], input=MOCK % (body + "\n" + body), capture_output=True, text=True, env=env,
                         check=True).stdout
    return out.split("ARGS ", 1)[1].split()


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_cap_default_100_wrapped_once(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "OT_MAX_BUFFER_PERCENT"}
    # sourcing the hook twice must not stack wrappers (one -max_buffer_percent only)
    assert _args(tmp_path, env) == ["-hold", "-max_buffer_percent", "100"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_cap_env_override(tmp_path):
    assert _args(tmp_path, dict(os.environ, OT_MAX_BUFFER_PERCENT="20")) == ["-hold", "-max_buffer_percent", "20"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_plan_demand_wrapper_not_doubled(tmp_path):
    """a kit whose PRE_GLOBAL_ROUTE already went through hold_repair_pre.tcl keeps that single wrapper"""
    body = "\n".join(l for l in _kit(tmp_path).splitlines() if not l.startswith("source "))
    pre = 'proc ::ot_hr_rth_orig {args} {}\n'
    out = subprocess.run(["tclsh"], input=MOCK % (pre + body), capture_output=True, text=True, check=True).stdout
    assert out.split("ARGS ", 1)[1].split() == ["-hold"]
