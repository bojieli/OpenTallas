"""lec.py lockup-latch abstraction (latch_to_wire, LEC-FPREG-3 2026-10-27): a transparent-low ASAP7 DLL latch
between rising-edge flops is a wire in the cycle model.  ok: r0 -> DLL -> r1 is EQUIVALENT to the RTL r0 -> r1;
mutants (the latch reads the input instead of r0, the latch dropped and r1 reads r0's input) are NOT EQUIVALENT;
topologies outside the abstraction (transparent-high DHL, a latch clocked by an inverted clock or by a data input,
Q to a falling-edge flop, Q to a module output) are UNPROVEN, never EQUIVALENT; OT_LEC_LATCH=0 refuses latches."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

RTL = """module lec_lk_t (input clk, input [1:0] a, input b, output [1:0] y, output z);
  reg [1:0] r0, r1;
  reg n0, n1;
  always @(posedge clk) begin r0 <= a; r1 <= r0; n0 <= b; end
  always @(negedge clk) n1 <= n0;
  assign y = r1;
  assign z = n1;
endmodule
"""


def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


needs_image = pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")


def _netlist(v):
    lat = {"DHL": "DHLx1_ASAP7_75t_R"}.get(v, "DLLx1_ASAP7_75t_R")
    s = ["module lec_lk_t(clk, a, b, y, z);", "  input clk; input [1:0] a; input b; output [1:0] y; output z;",
         "  wire [1:0] q0n, q0, l, yn; wire nclk, n0n, n0, ln, n1n;",
         "  INVx1_ASAP7_75t_R ick (.A(clk), .Y(nclk));"]
    for i in range(2):
        lclk = "nclk" if v == "INV" else ("b" if v == "DATACLK" else "clk")
        ld = f"a[{i}]" if v == "MUT_SKIP" else f"q0[{i}]"
        s += [f"  DFFHQNx1_ASAP7_75t_R \\r0[{i}]$_DFF_P_ (.CLK(clk), .D(a[{i}]), .QN(q0n[{i}]));",
              f"  INVx1_ASAP7_75t_R i0_{i} (.A(q0n[{i}]), .Y(q0[{i}]));"]
        if v == "MUT_DROP":
            s += [f"  BUFx2_ASAP7_75t_R lk_{i} (.A(a[{i}]), .Y(l[{i}]));"]
        else:
            s += [f"  {lat} lk_{i} (.CLK({lclk}), .D({ld}), .Q(l[{i}]));"]
        if v == "PO" and i == 1:
            s += [f"  BUFx2_ASAP7_75t_R o_{i} (.A(l[{i}]), .Y(y[{i}]));",
                  f"  DFFHQNx1_ASAP7_75t_R \\r1[{i}]$_DFF_P_ (.CLK(clk), .D(q0[{i}]), .QN(yn[{i}]));"]
        else:
            s += [f"  DFFHQNx1_ASAP7_75t_R \\r1[{i}]$_DFF_P_ (.CLK(clk), .D(l[{i}]), .QN(yn[{i}]));",
                  f"  INVx1_ASAP7_75t_R i1_{i} (.A(yn[{i}]), .Y(y[{i}]));"]
    s += ["  DFFHQNx1_ASAP7_75t_R \\n0$_DFF_P_ (.CLK(clk), .D(b), .QN(n0n));",
          "  INVx1_ASAP7_75t_R in0 (.A(n0n), .Y(n0));"]
    if v == "NEG":                     # a latch into the falling-edge flop
        s += ["  DLLx1_ASAP7_75t_R lkn (.CLK(clk), .D(n0), .Q(ln));"]
    else:
        s += ["  BUFx2_ASAP7_75t_R bn (.A(n0), .Y(ln));"]
    s += ["  DFFLQNx1_ASAP7_75t_R \\n1$_DFF_N_ (.CLK(clk), .D(ln), .QN(n1n));",
          "  INVx1_ASAP7_75t_R in1 (.A(n1n), .Y(z));", "endmodule", ""]
    return "\n".join(s)


# Gold-side RTL lockup latch (S81 R21b u_view c_lk, LEC-FPREG-4 10-27): always_latch if (!clk) elaborates to a
# $_DLATCH_P_ whose enable is the unoptimised constant-data $_MUX_ (clk ? 0 : 1); RTL_LAT_HI (if (clk)) is a
# transparent-high latch and must stay UNPROVEN.
RTL_LAT = RTL.replace("always @(posedge clk) begin r0 <= a; r1 <= r0; n0 <= b; end",
                      "reg [1:0] lk;\n  always_latch if (!clk) lk = r0;\n"
                      "  always @(posedge clk) begin r0 <= a; r1 <= lk; n0 <= b; end")
RTL_LAT_HI = RTL_LAT.replace("if (!clk)", "if (clk)")


def _kit(tmp_path, v, rtl=RTL):
    k = tmp_path / v
    (k / "rtl").mkdir(parents=True)
    (k / "rtl" / "lec_lk_t.sv").write_text(rtl)
    n = k / "run" / "results" / "asap7" / "lec_lk_t" / "base"
    n.mkdir(parents=True)
    (n / "1_2_yosys.v").write_text(_netlist(v))
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_lk_t\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/rtl/lec_lk_t.sv\n"
        "export VERILOG_INCLUDE_DIRS = /work/rtl\nexport VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\n")
    return k


def _run(kit, **env):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900, env=dict(os.environ, **env))
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


def test_lockup_cells():
    assert lec.LOCKUP_CELLS.match("DLLx1_ASAP7_75t_R") and lec.LOCKUP_CELLS.match("DLLx3_ASAP7_75t_SL")
    assert not lec.LOCKUP_CELLS.match("DHLx1_ASAP7_75t_R") and lec.UNSUPPORTED_CELLS.match("DHLx1_ASAP7_75t_R")


@needs_image
def test_lockup_latch_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["lockup_latches"]["gate"]["to_wire"] == 2 and r["lockup_latches"]["gold"]["latches"] == 0, r


@needs_image
@pytest.mark.parametrize("mut", ["MUT_SKIP", "MUT_DROP"])
def test_lockup_mutants_are_not_equivalent(tmp_path, mut):
    rc, r = _run(_kit(tmp_path, mut))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r


@needs_image
@pytest.mark.parametrize("ref,why", [("DHL", "does not model"), ("INV", "transparent-low"),
                                     ("DATACLK", "transparent-low"), ("NEG", "Q reaches"),
                                     ("PO", "lec_po_y")])
def test_latch_topologies_outside_the_model_are_refused(tmp_path, ref, why):
    rc, r = _run(_kit(tmp_path, ref))
    assert rc == 2 and r["verdict"] == "UNPROVEN" and why in r["reason"], r


@needs_image
def test_latch_switch_off_refuses(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok"), OT_LEC_LATCH="0")
    assert rc == 2 and r["verdict"] == "UNPROVEN" and "does not model" in r["reason"], r


@needs_image
def test_rtl_lockup_latch_both_sides_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok", RTL_LAT))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["lockup_latches"]["gold"]["to_wire"] == 2 and r["lockup_latches"]["gate"]["to_wire"] == 2, r


@needs_image
def test_rtl_lockup_latch_mutant_is_not_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "MUT_SKIP", RTL_LAT))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r


@needs_image
def test_rtl_transparent_high_latch_is_refused(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok", RTL_LAT_HI))
    assert rc == 2 and r["verdict"] == "UNPROVEN" and "transparent-low" in r["reason"], r


def _mux_json(path, a, b, mtype="$_MUX_"):
    """r0 ($_DFF_P_ on clk) -> $_DLATCH_P_ (E = mtype(S = clk, A = a, B = b)) -> r1 ($_DFF_P_ on clk), the shape the
    RTL frontend leaves for always_latch if (!clk) (S81 R21b u_view c_lk, LEC-FPREG-4 10-27)."""
    io = lambda d: {"A": "input", "B": "input", "S": "input", "C": "input", "D": "input", "E": "input",
                    "Q": "output", "Y": "output"}
    cells = {
        "r0": {"type": "$_DFF_P_", "port_directions": io(0), "connections": {"C": [2], "D": [3], "Q": [10]}},
        "m": {"type": mtype, "port_directions": io(0), "connections": {"A": [a], "B": [b], "S": [2], "Y": [11]}},
        "lk": {"type": "$_DLATCH_P_", "port_directions": io(0), "connections": {"E": [11], "D": [10], "Q": [12]}},
        "r1": {"type": "$_DFF_P_", "port_directions": io(0), "connections": {"C": [2], "D": [12], "Q": [4]}},
    }
    d = {"modules": {"t": {"attributes": {"top": "00000000000000000000000000000001"},
                           "ports": {"clk": {"direction": "input", "bits": [2]}, "a": {"direction": "input", "bits": [3]},
                                     "y": {"direction": "output", "bits": [4]}},
                           "cells": cells,
                           "netnames": {"clk": {"bits": [2]}, "a": {"bits": [3]}, "y": {"bits": [4]},
                                        "r0q": {"bits": [10]}, "en": {"bits": [11]}, "lq": {"bits": [12]}}}}}
    path.write_text(json.dumps(d))
    return path


@pytest.mark.parametrize("a,b,mtype", [("1", "0", "$_MUX_"), ("0", "1", "$_NMUX_")])
def test_constant_mux_inverted_clock_enable_is_a_lockup_latch(tmp_path, a, b, mtype):
    st = lec.latch_to_wire(_mux_json(tmp_path / "s.json", a, b, mtype), tmp_path / "d.json", "gold")
    assert st["to_wire"] == 1 and st["per_latch"]["lk"]["clk"] == "clk", st
    cells = json.loads((tmp_path / "d.json").read_text())["modules"]["t"]["cells"]
    assert cells["lk"]["type"] == "$_BUF_" and cells["lk"]["connections"] == {"A": [10], "Y": [12]}


@pytest.mark.parametrize("a,b,mtype", [("0", "1", "$_MUX_"), ("1", "0", "$_NMUX_"), ("1", "1", "$_MUX_"),
                                       ("0", 3, "$_MUX_")])
def test_constant_mux_enable_mutants_are_refused(tmp_path, a, b, mtype):
    # transparent-high (MUX 0/1 = clk; NMUX 1/0 = clk), a constant enable, a data-dependent mux: never a wire
    with pytest.raises(lec.Unproven):
        lec.latch_to_wire(_mux_json(tmp_path / "s.json", a, b, mtype), tmp_path / "d.json", "gold")


def _dmux_json(path, dmux):
    """r0 -> $_DLATCH_N_ (E = clk) whose D is a $_MUX_ (the frontend's always_latch form) -> r1.  dmux = (S, A, B)
    with net 10 = r0.Q, 2 = clk, 3 = a, 13 = NOT(clk)."""
    io = {"A": "input", "B": "input", "S": "input", "C": "input", "D": "input", "E": "input", "Q": "output", "Y": "output"}
    S, A, B = dmux
    cells = {
        "r0": {"type": "$_DFF_P_", "port_directions": io, "connections": {"C": [2], "D": [3], "Q": [10]}},
        "n": {"type": "$_NOT_", "port_directions": io, "connections": {"A": [2], "Y": [13]}},
        "dm": {"type": "$_MUX_", "port_directions": io, "connections": {"A": [A], "B": [B], "S": [S], "Y": [11]}},
        "lk": {"type": "$_DLATCH_N_", "port_directions": io, "connections": {"E": [2], "D": [11], "Q": [12]}},
        "r1": {"type": "$_DFF_P_", "port_directions": io, "connections": {"C": [2], "D": [12], "Q": [4]}},
    }
    d = {"modules": {"t": {"attributes": {"top": "00000000000000000000000000000001"},
                           "ports": {"clk": {"direction": "input", "bits": [2]}, "a": {"direction": "input", "bits": [3]},
                                     "y": {"direction": "output", "bits": [4]}},
                           "cells": cells, "netnames": {"clk": {"bits": [2]}, "a": {"bits": [3]}, "y": {"bits": [4]}}}}}
    path.write_text(json.dumps(d))
    return path


@pytest.mark.parametrize("dmux", [(2, 10, "x"), (13, "x", 10)])
def test_latch_data_phase_mux_takes_the_transparent_branch(tmp_path, dmux):
    st = lec.latch_to_wire(_dmux_json(tmp_path / "s.json", dmux), tmp_path / "d.json", "gold")
    assert st["to_wire"] == 1 and st["per_latch"]["lk"]["phase_mux"], st
    lk = json.loads((tmp_path / "d.json").read_text())["modules"]["t"]["cells"]["lk"]
    assert lk["connections"] == {"A": [10], "Y": [12]}, lk


def test_latch_data_mux_on_a_data_select_is_kept(tmp_path):
    st = lec.latch_to_wire(_dmux_json(tmp_path / "s.json", (3, 10, "x")), tmp_path / "d.json", "gold")
    lk = json.loads((tmp_path / "d.json").read_text())["modules"]["t"]["cells"]["lk"]
    assert not st["per_latch"]["lk"]["phase_mux"] and lk["connections"] == {"A": [11], "Y": [12]}, (st, lk)


def test_latch_data_reading_the_clock_elsewhere_is_refused(tmp_path):
    # the clock in the data cone outside the phase mux select (here: the opaque-phase branch is the clock itself
    # behind a data-select mux) stays a clock read -> Unproven
    with pytest.raises(lec.Unproven):
        lec.latch_to_wire(_dmux_json(tmp_path / "s.json", (3, 10, 2)), tmp_path / "d.json", "gold")


def _chain_json(path, loop=False):
    """r0 (clk) -> L1 ($_DLATCH_N_ on clk) -> NOT -> L2 ($_DLATCH_N_ on ck2, D = phase mux) -> r1 (ck2): the R21b
    io_clk go latch -> core -> ck seam latch chain.  loop: L2's Q also feeds L1's data (AND), a latch loop."""
    io = {"A": "input", "B": "input", "S": "input", "C": "input", "D": "input", "E": "input", "Q": "output", "Y": "output"}
    cells = {
        "r0": {"type": "$_DFF_P_", "port_directions": io, "connections": {"C": [2], "D": [3], "Q": [10]}},
        "L1": {"type": "$_DLATCH_N_", "port_directions": io, "connections": {"E": [2], "D": [15 if loop else 10], "Q": [11]}},
        "n": {"type": "$_NOT_", "port_directions": io, "connections": {"A": [11], "Y": [12]}},
        "pm": {"type": "$_MUX_", "port_directions": io, "connections": {"A": [12], "B": ["x"], "S": [5], "Y": [13]}},
        "L2": {"type": "$_DLATCH_N_", "port_directions": io, "connections": {"E": [5], "D": [13], "Q": [14]}},
        "r1": {"type": "$_DFF_P_", "port_directions": io, "connections": {"C": [5], "D": [14], "Q": [4]}},
    }
    if loop:
        cells["a"] = {"type": "$_AND_", "port_directions": io, "connections": {"A": [10], "B": [14], "Y": [15]}}
    d = {"modules": {"t": {"attributes": {"top": "00000000000000000000000000000001"},
                           "ports": {"clk": {"direction": "input", "bits": [2]}, "a": {"direction": "input", "bits": [3]},
                                     "ck2": {"direction": "input", "bits": [5]}, "y": {"direction": "output", "bits": [4]}},
                           "cells": cells, "netnames": {"clk": {"bits": [2]}, "a": {"bits": [3]}, "ck2": {"bits": [5]},
                                                        "y": {"bits": [4]}}}}}
    path.write_text(json.dumps(d))
    return path


def test_latch_chain_is_a_wire(tmp_path):
    st = lec.latch_to_wire(_chain_json(tmp_path / "s.json"), tmp_path / "d.json", "gold")
    assert st["to_wire"] == 2 and st["phase_mux"] == 1, st
    assert st["per_latch"]["L1"]["sinks"] == 1 and st["per_latch"]["L2"]["data_sources"] == 1, st
    c = json.loads((tmp_path / "d.json").read_text())["modules"]["t"]["cells"]
    assert c["L1"]["connections"] == {"A": [10], "Y": [11]} and c["L2"]["connections"] == {"A": [12], "Y": [14]}, c


def test_latch_loop_is_refused(tmp_path):
    with pytest.raises(lec.Unproven, match="latch loop"):
        lec.latch_to_wire(_chain_json(tmp_path / "s.json", loop=True), tmp_path / "d.json", "gold")
