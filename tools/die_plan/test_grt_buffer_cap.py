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


def test_core_kits_pad_grt_hold_with_hb4(tmp_path):
    """KIT-TRIAGE-1/G5 11-01 (COORD 05:0x): the HBM-CORES-KITS-40 HB4 hook (b26a827db45) is the class form for the S81 /
    KV / QC core kits too -- core_flow.apply ships hold_pad_hb4.tcl and sources it from grt_pre_core.tcl, after main's
    grt_pre.tcl and the kit's own hooks, before the buffer-cap wrapper."""
    import core_flow
    lines = _kit(tmp_path).splitlines()
    assert lines.count("source /work/hold_pad_hb4.tcl") == 1
    assert lines.index("source /work/drv.tcl") < lines.index("source /work/hold_pad_hb4.tcl")
    assert (tmp_path / "hold_pad_hb4.tcl").read_text() == core_flow.HOLD_PAD_HB4.read_text()
    assert "unset_dont_use" in core_flow.HOLD_PAD_HB4.read_text()


def test_s81_kv_qc_core_generators_go_through_core_flow():
    """the three core-kit generators get the HB4 hook only through core_flow.apply's override PRE_GLOBAL_ROUTE hook"""
    root = HERE.parents[1] / "physical" / "die_plan"
    for rel in ("s81/cores/legacy/gen_core_kit_legacy.py", "qwen_kvsys/cores/harden/gen_core_kit_kv.py",
                "qwen_compute/cores/legacy/gen_core_kit_qc.py"):
        src = (root / rel).read_text()
        assert "core_flow.apply(" in src and "grt_pre_extra=" in src, rel
        assert "override export PRE_GLOBAL_ROUTE_TCL" not in src, rel   # nothing outranks grt_pre_core.tcl


MOCK_HB4 = r"""
proc get_lib_cells {args} { return {HB4} }
proc unset_dont_use {c} { lappend ::log unset }
proc set_dont_use {c} { lappend ::log set }
proc get_cells {args} { return {} }
proc get_property {args} { return {} }
proc repair_timing {args} { lappend ::log [list rt {*}$args] }
proc repair_timing_helper {args} { lappend ::log [list rth {*}$args] }
set ::log {}
%s
repair_timing -hold -hold_margin 10
repair_timing -setup
repair_timing_helper -hold
puts "LOG $::log"
"""


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_core_grt_pre_hb4_only_inside_hold_and_cap_kept(tmp_path):
    """sourced as generated (twice, idempotent): HB4 dont_use lifted only around repair_timing -hold, setup untouched,
    buffer-cap wrapper still single"""
    import core_flow
    _kit(tmp_path)
    hb4 = core_flow.HOLD_PAD_HB4.read_text()
    body = "\n".join(hb4 if l == "source /work/hold_pad_hb4.tcl" else l
                     for l in (tmp_path / "grt_pre_core.tcl").read_text().splitlines()
                     if not l.startswith("source ") or l == "source /work/hold_pad_hb4.tcl")
    env = {k: v for k, v in os.environ.items() if k != "OT_MAX_BUFFER_PERCENT"}
    out = subprocess.run(["tclsh"], input=MOCK_HB4 % (body + "\n" + body), capture_output=True, text=True, env=env,
                         check=True).stdout
    log = out.split("LOG ", 1)[1].strip()
    assert log == ("unset {rt -hold -hold_margin 10} set {rt -setup} "
                   "{rth -hold -max_buffer_percent 100}"), log
