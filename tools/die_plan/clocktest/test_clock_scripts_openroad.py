"""KIT-OPS-6 lever 7 (FABLE-METHOD): known-answer regression tests for the clock Tcl scripts, run in OpenROAD (docker openroad/orfs:asap7lock
or `openroad` on PATH; skipped where neither exists, run by ot-run from the merge-queue suite with OT_CLOCKTEST_OTRUN=1).
    python3 -m pytest -q tools/die_plan/clocktest/test_clock_scripts_openroad.py
subtree_balance.tcl STB-EDGE-1: ONE clock port -> BUF -> {2 flops, INV -> 1 flop}.  Every sink must be measured from the same source edge, so
the tree spread is a few ps.  The pre-STB-EDGE-1 script read arrival_max_rise on the inverted sink and measured T/2 + a few ps (424 ps here)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RUN = HERE / "run_openroad.sh"
HAVE = shutil.which("openroad") is not None or shutil.which("docker") is not None
needs_or = pytest.mark.skipif(not HAVE, reason="no openroad / docker")


def run(script, *env):
    r = subprocess.run(["bash", str(RUN), script, *env], capture_output=True, text=True, timeout=1500)
    if r.returncode == 77:
        pytest.skip("no openroad")
    return r.stdout + r.stderr


@needs_or
def test_stb_inverted_sink_is_measured_on_the_same_source_edge():
    out = run("stb_known.tcl")
    m = re.search(r"OT_STB before clk \(placement RC\): (\d+) tree nodes, sinks (\d+) .*\(spread (\d+),", out)
    assert m, out[-800:]
    nodes, sinks, spread = map(int, m.groups())
    assert (nodes, sinks) == (2, 3)
    assert spread <= 20, f"spread {spread} ps: the inverted sink is read on the wrong edge (T/2 artefact ~ 416 ps)"
    assert "OT_KNOWN_DONE" in out


def test_harness_files_exist():
    for f in ("stb_known.tcl", "stb_known.v", "ps_known.tcl", "ps_known.v", "ct_known.tcl", "ct_known.v", "vm_known.tcl", "vm_known.v", "run_openroad.sh"):
        assert (HERE / f).is_file()
    assert "source /tools/subtree_balance.tcl" in (HERE / "stb_known.tcl").read_text()


@needs_or
def test_pair_skew_raw_pair_matches_the_measured_clock_arrival_difference():
    """pair_skew.tcl: launch flop on tap n0, capture flop two buffers later.  The related pair (ff_l -> ff_c) is found (2 regs, 1 pair, no
    missing clock arrival) and its raw hold damage (capture late - launch early) is the CK arrival difference n1 - n0 within 1.5 ps; the raw setup
    damage has the opposite sign (late capture does not hurt setup)."""
    out = run("ps_known.tcl")
    assert "PS_COUNTS regs=2 pairs=1 inter=0 data=2 noarr=0" in out, out[-600:]
    pair = re.search(r"PS_PAIR ff_l ff_c ff_c/D (\S+) (\S+) ff_c", out)
    arr = re.search(r"PS_ARR launch (\S+) capture (\S+) diff (\S+)", out)
    assert pair and arr, out[-600:]
    setup, hold, diff = float(pair.group(1)), float(pair.group(2)), float(arr.group(3))
    assert 15.0 < diff < 40.0
    assert abs(hold - diff) <= 1.5 and setup < 0 and abs(setup + hold) <= 3.0


@needs_or
def test_clock_taps_early_core_tap_and_nearest_grid_tap_split():
    """clock_taps.tcl (CP2 early core taps + the nearest-tap split): fcore's clock pin leaves clk for the core tap clk_c0 (OT_CORE_TAPS), fc (next to
    clk_t1) moves to clk_t1, fa and fb stay on clk; no flop is ever moved onto the core tap."""
    out = run("ct_known.tcl")
    assert "OT_CLOCK_TAPS core tap clk_c0 <- fcore/CLK: 1 clock pin(s)" in out, out[-700:]
    nets = dict(re.findall(r"CT_NET (\w+) \S+ (\w+)", out))
    assert nets == {"fa": "clk", "fb": "clk", "fc": "clk_t1", "fcore": "clk_c0"}, nets
    assert "OT_CLOCK_TAPS 2 taps, 1 sinks moved off clk" in out


@needs_or
def test_vclk_measured_hold_pinreg_mean_is_the_mean_of_the_boundary_register_arrivals():
    """vclk_measured_hold.tcl ot_vmh_pinreg_mean: two flops fed from the input d (IO-boundary registers) on taps two buffers apart: the returned
    {mean n bad nclocks} is the mean of their measured CK arrivals (within 0.5 ps), n=2, no bad register, one clock."""
    out = run("vm_known.tcl")
    m = re.search(r"VM_MEAN (\S+) (\d+) (\d+) (\d+)", out)
    a = re.search(r"VM_ARR (\S+) (\S+) (\S+)", out)
    assert m and a, out[-600:]
    mean, n, bad, ncl = float(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    assert (n, bad, ncl) == (2, 0, 1)
    assert abs(mean - float(a.group(3))) <= 0.5 and float(a.group(2)) - float(a.group(1)) > 15
