"""DIE-S81-10 (COORD 2026-10-28 06:47; METHODOLOGY 12.3 v5.0 lifted the 12.8d early-tap ban): plan clock.tap_window on
a type with CP2 early core taps.  Grid / edge ports keep the [-W, 0] window; each core tap port keeps its own early
latency e (TT golden SDC, FF core_taps_ff.sdc) as its late value and gets early -(e + W).  Same-tap pairs keep the
CRPR credit (OpenSTA probe), cross-tap pairs see the full W; lint, pre-CTS zero / restore and the TT corner replay agree."""
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_phys as G
import schema as S
import sdc_lint
from test_corelat import pair_with_core

W = 80.0


def _plan(window=W):
    raw = pair_with_core(430.0, 350.0)          # core tap clk_c0: early TT 180 / FF 147.5
    raw["partition_types"]["fa"]["hard_cores"] = [{"inst": "u_c", "origin_um": [200.0, 800.0], "outline_um": [200.0, 200.0]}]
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    if window is not None:
        raw["clock"]["tap_window"] = dict(window_ps=window, note="test")
    return S.Plan(raw)


def _sdc(P, tn="fa"):
    return G.sdc(P, tn, G.type_pins(P, tn))


def test_window_and_core_tap_sdc_lines():
    P = _plan()
    s = _sdc(P)
    grid = " ".join(n for n, _x, _y in G.clock_pins(P, "fa"))
    assert f"set_clock_latency -source -early -clock clk -80.0000 [get_ports {{{grid}}}]" in s
    assert f"set_clock_latency -source -late -clock clk 0.0000 [get_ports {{{grid}}}]" in s
    base = "set_clock_latency -source -clock clk -180.0000 [get_ports clk_c0]"
    win = "set_clock_latency -source -early -clock clk -260.0000 [get_ports clk_c0]"
    assert s.count(base) == 1 and s.count(win) == 1
    assert s.index(base) < s.index(win)                  # the window line must not be overwritten by the base line
    assert "clk_c0" not in grid                          # core tap port is not in the [-W, 0] grid window
    ff = G.core_tap_ff_sdc(P, "fa")
    fbase = "set_clock_latency -source -clock clk -147.5000 [get_ports clk_c0]"
    fwin = "set_clock_latency -source -early -clock clk -227.5000 [get_ports clk_c0]"
    assert fbase in ff and fwin in ff and ff.index(fbase) < ff.index(fwin) and "-late" not in ff
    # no window: core-tap SDC and FF overlay byte-identical to the pre-change form
    P0 = _plan(window=None)
    assert "-early" not in _sdc(P0) and "-early" not in G.core_tap_ff_sdc(P0, "fa")


def test_lint_core_tap_window():
    P = _plan()
    s, ctx = _sdc(P), sdc_lint.kit_context(P, "fa")
    assert ctx["tap_window_ps"] == W and ctx["port_latency_ps"] == {"clk_c0": -180.0}
    assert sdc_lint.lint(s, **ctx) == []
    win = "set_clock_latency -source -early -clock clk -260.0000 [get_ports clk_c0]"
    assert any("core tap clk_c0 window" in e for e in sdc_lint.lint(s.replace("-260.0000", "-250.0000"), **ctx))
    assert any("no clock.tap_window early line" in e for e in sdc_lint.lint(s.replace(win + "\n", ""), **ctx))
    late = s.replace(win, win + "\nset_clock_latency -source -late -clock clk -180.0000 [get_ports clk_c0]")
    assert any("no -late line" in e for e in sdc_lint.lint(late, **ctx))


def test_prects_zero_and_restore_core_taps():
    P = _plan()
    pre, cts = G.clock_phase_tcl(P, "fa"), G.clock_phase_tcl(P, "fa", before_cts=True)
    assert "set_clock_latency -source -early -clock clk -180.0000 [get_ports clk_c0]" in pre   # zeroed = own early
    assert "-0.0000" not in pre
    assert "set_clock_latency -source -early -clock clk -260.0000 [get_ports clk_c0]" in cts
    assert cts.index("unset_clock_latency") < cts.index("-260.0000") < cts.index("source /work/clock_taps.tcl")


def test_tt_corner_replay_keeps_window(tmp_path):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    P = _plan()
    (tmp_path / "vclk_corner.tcl").write_text(Path(G.__file__).with_name("vclk_corner.tcl").read_text())
    (tmp_path / "constraint.sdc").write_text(_sdc(P))
    (tmp_path / "core_taps_ff.sdc").write_text(G.core_tap_ff_sdc(P, "fa"))
    fixture = ("proc get_ports {p} {return $p}\nproc set_clock_latency {args} {puts \"LATENCY [join $args { }]\"}\n"
               "proc read_sdc {p} {uplevel #0 [list source $p]}\nsource vclk_corner.tcl\n"
               "puts FF\not_core_tap_bind ff\nputs TT\not_core_tap_bind tt\n")
    out = subprocess.run(["tclsh"], input=fixture, text=True, cwd=tmp_path, capture_output=True, check=True).stdout
    ff, tt = out.split("\nTT\n")
    assert ff.index("-clock clk -147.5000 clk_c0") < ff.index("-early -clock clk -227.5000 clk_c0")
    assert tt.index("-clock clk -180.0000 clk_c0") < tt.index("-early -clock clk -260.0000 clk_c0")


def _libdir():
    for d in ["/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM", "~/.cache/opentallas/asap7_nldm",
              "~/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM"]:
        p = Path(d).expanduser() / "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
        if p.is_file():
            return p
    return None


def _sta_hold(tmp_path, lines):
    lib = _libdir()
    (tmp_path / "n.v").write_text(
        "module top(clk_c0, clk_g0, d, q1, q2);\ninput clk_c0, clk_g0, d; output q1, q2; wire n1;\n"
        "DFFHQNx1_ASAP7_75t_R a(.CLK(clk_c0), .D(d), .QN(n1));\n"
        "DFFHQNx1_ASAP7_75t_R b(.CLK(clk_c0), .D(n1), .QN(q1));\n"
        "DFFHQNx1_ASAP7_75t_R c(.CLK(clk_g0), .D(n1), .QN(q2));\nendmodule\n")
    tcl = (f"read_liberty {lib}\nread_verilog n.v\nlink_design top\n"
           "create_clock -name clk -period 833 [get_ports {clk_c0 clk_g0}]\n" + "".join(lines) +
           "set_propagated_clock [all_clocks]\n"
           "foreach {f t} {a/CLK b/D a/CLK c/D} {\n"
           "  set p [lindex [find_timing_paths -path_delay min -from [get_pins $f] -to [get_pins $t]] 0]\n"
           "  puts \"HOLD $f $t [get_property $p slack]\"\n}\n")
    (tmp_path / "s.tcl").write_text(tcl)
    sta = shutil.which("sta") or str(Path("~/.local/opentallas-tools/bin/sta").expanduser())
    out = subprocess.run([sta, "-no_splash", "-exit", "s.tcl"], cwd=tmp_path, text=True, capture_output=True).stdout
    return {tuple(l.split()[1:3]): float(l.split()[3]) for l in out.splitlines() if l.startswith("HOLD ")}


@pytest.mark.skipif(not (shutil.which("sta") or Path("~/.local/opentallas-tools/bin/sta").expanduser().is_file())
                    or _libdir() is None, reason="OpenSTA or ASAP7 SEQ lib not installed")
def test_crpr_same_core_tap_and_cross_tap(tmp_path):
    """The generated window lines (ps library units here, tiny_plan time unit 1 ps in t_lib) under OpenSTA: hold on
    a same-core-tap pair is unchanged by W (CRPR at the common port), a core -> grid-tap pair loses exactly W."""
    P = _plan()
    if G.LIB_TIME_UNIT_PS != 1.0:
        pytest.skip("fixture assumes ps library units")
    grid_ports = " ".join(n for n, _x, _y in G.clock_pins(P, "fa"))

    def lines(sdc):
        out = []
        for l in sdc.splitlines():
            if l.startswith("set_clock_latency -source") and "[get_ports" in l and "vclk" not in l:
                out.append(l.replace(grid_ports, "clk_g0") + "\n")
        return out
    win = lines(_sdc(P))
    nowin = lines(_sdc(_plan(window=None)))
    assert any("clk_c0" in l and "-early" in l for l in win) and any("clk_g0" in l for l in win)
    h1, h0 = _sta_hold(tmp_path, win), _sta_hold(tmp_path, nowin)
    assert abs(h1[("a/CLK", "b/D")] - h0[("a/CLK", "b/D")]) < 0.01                  # same tap: CRPR credit
    assert h1[("a/CLK", "c/D")] - h0[("a/CLK", "c/D")] == pytest.approx(-W, abs=0.01)  # cross tap: full W
