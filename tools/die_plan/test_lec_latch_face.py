"""lec.py phase-aware face latches (LATCH-FACE, COORD 11-03 08:25; S81 RF-1 out-face lockup latch, CLK table row 1:
face flop -> ONE transparent-low latch -> port; gunit_l1c / l4, XCHECK TX ot_dp_lk).

The gold RTL registers y and drives it through always_latch if (!clk) (port class 'low': it changes at the falling
edge and holds in the high phase).  ok: DFF -> DLL -> y is EQUIVALENT.  Mutants are each caught (NOT EQUIVALENT):
  WRONG_PHASE  DFF -> DHL -> y (transparent-high: the port changes at the rising edge, class 'edge');
  DROP         DFF -> BUF -> y (latch dropped: class 'edge'; the cycle function alone is equal);
  SWAP         the two face latches read each other's flop (swapped D).
A gold transparent-high face latch against a DHL gate is EQUIVALENT (both 'edge'); a port that mixes a latch-held
and a rising-edge path is UNPROVEN (no cycle model holds its high-phase value)."""
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

RTL = """module lec_fl_t (input clk, input [1:0] a, output [1:0] y);
  reg [1:0] r;
  reg [1:0] l;
  always @(posedge clk) r <= a;
  always_latch if (!clk) l = r;
  assign y = l;
endmodule
"""
RTL_HI = RTL.replace("if (!clk)", "if (clk)")
# the gen_rtl TX-face ot_dp_lk form (Verilog-2001, ROOT-MERGE 867e693fa67): `always @(*) if (!clk) q = d;` in a module
RTL_DPLK = """module ot_dp_lk #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
  always @(*) if (!clk) q = d;
endmodule
module lec_fl_t (input clk, input [1:0] a, output [1:0] y);
  reg [1:0] r;
  always @(posedge clk) r <= a;
  ot_dp_lk #(.W(2)) u_blk_y (.clk(clk), .d(r), .q(y));
endmodule
"""


def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


needs_image = pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")


def _netlist(v):
    s = ["module lec_fl_t(clk, a, y);", "  input clk; input [1:0] a; output [1:0] y;",
         "  wire [1:0] qn, q;"]
    for i in range(2):
        s += [f"  DFFHQNx1_ASAP7_75t_R \\r[{i}]$_DFF_P_ (.CLK(clk), .D(a[{i}]), .QN(qn[{i}]));",
              f"  INVx1_ASAP7_75t_R iq_{i} (.A(qn[{i}]), .Y(q[{i}]));"]
        d = f"q[{1 - i}]" if v == "SWAP" else f"q[{i}]"
        if v == "DROP":
            s += [f"  BUFx2_ASAP7_75t_R lk_{i} (.A({d}), .Y(y[{i}]));"]
        else:
            lat = "DHLx1_ASAP7_75t_R" if v in ("WRONG_PHASE", "HI") else "DLLx1_ASAP7_75t_R"
            s += [f"  {lat} lk_{i} (.CLK(clk), .D({d}), .Q(y[{i}]));"]
    s += ["endmodule", ""]
    return "\n".join(s)


def _kit(tmp_path, v, rtl=RTL):
    k = tmp_path / v
    (k / "rtl").mkdir(parents=True)
    (k / "rtl" / "lec_fl_t.sv").write_text(rtl)
    n = k / "run" / "results" / "asap7" / "lec_fl_t" / "base"
    n.mkdir(parents=True)
    (n / "1_2_yosys.v").write_text(_netlist(v))
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_fl_t\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/rtl/lec_fl_t.sv\n"
        "export VERILOG_INCLUDE_DIRS = /work/rtl\nexport VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\n")
    return k


def _run(kit, **env):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900, env=dict(os.environ, **env))
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


@needs_image
def test_face_latch_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "ok"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    lk = r["lockup_latches"]
    assert lk["gold"]["to_wire"] == 2 and lk["gate"]["to_wire"] == 2, lk
    assert lk["gold"]["port_phase_counts"] == {"low": 2} == lk["gate"]["port_phase_counts"], lk
    assert r["latch_phase"]["n_differ"] == 0, r


@needs_image
@pytest.mark.parametrize("mut,phase", [("WRONG_PHASE", True), ("DROP", True), ("SWAP", False)])
def test_face_latch_mutants_are_caught(tmp_path, mut, phase):
    rc, r = _run(_kit(tmp_path, mut))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r
    if phase:                             # cycle-equal: only the port phase tells them apart
        assert r["counts"]["differs"] == 0 and r["latch_phase"]["n_differ"] == 2, r
        assert {(e["gold"], e["gate"]) for e in r["latch_phase"]["differ"]} == {("low", "edge")}, r
    else:
        assert r["counts"]["differs"] == 2 and r["latch_phase"]["n_differ"] == 0, r


@needs_image
def test_transparent_high_face_latch_both_sides_is_equivalent(tmp_path):
    rc, r = _run(_kit(tmp_path, "HI", RTL_HI))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["lockup_latches"]["gold"]["phases"] == {"high": 2} == r["lockup_latches"]["gate"]["phases"], r


@needs_image
def test_gold_face_latch_against_gate_low_latch_wrong_gold_phase(tmp_path):
    # gold transparent-high (class edge) against the DLL gate (class low): caught from the gold side too
    rc, r = _run(_kit(tmp_path, "ok", RTL_HI))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT" and "latch phase" in r["reason"], r


# ------------------------------------------------------------------ JSON-level (no docker): port phase classes
def _po_json(path, mix=False, hi=False):
    """r0 (clk) -> latch lk (transparent-low, or high) -> [AND with r0 when mix] -> lec_po_y capture flop."""
    io = {"A": "input", "B": "input", "C": "input", "D": "input", "E": "input", "Q": "output", "Y": "output"}
    cells = {
        "r0": {"type": "$_DFF_P_", "port_directions": io, "connections": {"C": [2], "D": [3], "Q": [10]}},
        "lk": {"type": "$_DLATCH_P_" if hi else "$_DLATCH_N_", "port_directions": io,
               "connections": {"E": [2], "D": [10], "Q": [11]}},
        "po": {"type": "$_DFF_P_", "port_directions": io, "connections": {"C": [5], "D": [12 if mix else 11], "Q": [13]}},
    }
    if mix:
        cells["a"] = {"type": "$_AND_", "port_directions": io, "connections": {"A": [11], "B": [10], "Y": [12]}}
    d = {"modules": {"lec_top": {"attributes": {"top": "00000000000000000000000000000001"},
                                 "ports": {"clk": {"direction": "input", "bits": [2]},
                                           "a": {"direction": "input", "bits": [3]}},
                                 "cells": cells,
                                 "netnames": {"clk": {"bits": [2]}, "a": {"bits": [3]}, "lec_clk": {"bits": [5]},
                                              "lec_po_y": {"bits": [13]}}}}}
    path.write_text(json.dumps(d))
    return path


@pytest.mark.parametrize("hi,cls", [(False, "low"), (True, "edge")])
def test_latch_to_output_port_class(tmp_path, hi, cls):
    st = lec.latch_to_wire(_po_json(tmp_path / "s.json", hi=hi), tmp_path / "d.json", "gate")
    assert st["to_wire"] == 1 and st["per_latch"]["lk"]["ports"] == 1, st
    assert st["port_phase_counts"] == {cls: 1} and st["port_phase"] == ({"po": "low"} if cls == "low" else {}), st


def test_mixed_latch_and_edge_port_is_refused(tmp_path):
    with pytest.raises(lec.Unproven, match="mixes"):
        lec.latch_to_wire(_po_json(tmp_path / "s.json", mix=True), tmp_path / "d.json", "gate")


def test_latch_phase_diff_const_matches_any():
    lk = {"gold": {"port_phase": {"p0": "low", "p1": "low", "p2": "const"}},
          "gate": {"port_phase": {"p0": "low", "p2": "low", "p3": "low"}}}
    assert lec.latch_phase_diff(lk) == [("p1", "low", "edge"), ("p3", "edge", "low")]


def test_rtl_latch_detects_verilog2001_and_ot_dp_lk_forms():
    assert lec.RTL_LATCH.search(RTL_DPLK) and lec.RTL_LATCH.search("always @* if (!clk) q = d;")
    assert lec.RTL_LATCH.search("ot_dp_lk #(.W(4)) u (.clk(clk), .d(x), .q(y));")
    assert not lec.RTL_LATCH.search("always @(posedge clk) r <= a;")


@needs_image
def test_ot_dp_lk_gold_against_dll_gate_is_equivalent(tmp_path):
    """FLOW-LATCH-1: the merged xcheck TX-face wrapper form (ot_dp_lk, Verilog-2001 latch) against its DLL netlist."""
    rc, r = _run(_kit(tmp_path, "ok", RTL_DPLK))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["lockup_latches"]["gold"]["port_phase_counts"] == {"low": 2}, r


@needs_image
def test_ot_dp_lk_gold_against_missing_latch_is_not_equivalent(tmp_path):
    """MISSING LATCH: the golden has the ot_dp_lk latch, the netlist has a buffer -> NOT EQUIVALENT (not UNPROVEN)."""
    rc, r = _run(_kit(tmp_path, "DROP", RTL_DPLK))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT" and "latch phase" in r["reason"], r


@pytest.mark.parametrize("literal", ["0", "1"])
def test_constant_capture_data_has_constant_phase(tmp_path, literal):
    src = _po_json(tmp_path / "s.json")
    d = json.loads(src.read_text())
    d["modules"]["lec_top"]["cells"]["po"]["connections"]["D"] = [literal]
    src.write_text(json.dumps(d))
    st = lec.latch_to_wire(src, tmp_path / "d.json", "gate")
    assert st["port_phase_counts"] == {"const": 1}
    assert st["port_phase"] == {"po": "const"}
    assert json.loads((tmp_path / "d.json").read_text())["modules"]["lec_top"]["cells"]["po"]["connections"]["D"] == [literal]
