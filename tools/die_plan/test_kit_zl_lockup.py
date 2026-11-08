"""DIE-HEAD-86/SPN 11-08: kit_zl_lockup.py (zero-logic hop lockup latches, kit RTL post-pass, opt-in)."""
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_zl_lockup as zl  # noqa: E402

RTL = """`timescale 1ns/1ps
`default_nettype none
module top (
    input  wire clk,
    input  wire [4:0] x_i,  // 4 data + epoch
    input  wire rst_in,
    output wire [3:0] x_o
);
    wire rst_n;
    wire [3:0] a_q, b_q;
    wire a_eq, b_eq, r1, r2;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_in), .q(r1));
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(r1), .q(r2));
    ot_dp_st #(.W(4)) u_bin_x_i (.clk(clk), .rst_n(rst_n), .d(x_i[3:0]), .ea(x_i[4]), .q(a_q), .eq(a_eq));
    ot_dp_st #(.W(4)) u_ist_x_0 (.clk(clk), .rst_n(rst_n), .d(a_q), .ea(a_eq), .q(b_q), .eq(b_eq));
    ot_dp_st #(.W(4)) u_bout_x_o (.clk(clk), .rst_n(rst_n), .d(b_q), .ea(rst_n), .q(x_o), .eq());
    leaf u_leaf (
        .ck(clk),
        .i(b_q),
        .j({b_eq, a_q[1:0]})
    );
endmodule
"""

SPEC = {"hops": [
    {"inst": "u_bin_x_i", "ports": ["d", "ea"]},
    {"inst": "u_ist_\\w+", "ports": ["d", "ea"]},
    {"inst": "u_bout_x_o", "ports": ["d", "ea"]},
    {"inst": "u_leaf", "groups": [["i"], ["j"]]},
    {"inst": "u_rrl_\\d+", "types": ["ot_dp_rrelay"], "ports": ["d"]},
]}


def test_never_run_is_identity_and_guard_off_is_wires():
    txt, lat, sk = zl.apply(RTL, SPEC)
    assert RTL != txt
    # every latch has the plain-wire twin in the `else branch: no define = the original circuit
    on = txt.split("`ifdef OT_ZL_LOCKUP")[1].split("`else")[0]
    off = txt.split("`else")[1].split("`endif")[0]
    assert len(re.findall(r"^\s*ot_dp_lk\b", on, re.M)) == len(lat) == len(re.findall(r"\bassign\b", off))


def test_hops_ports_and_skips():
    txt, lat, sk = zl.apply(RTL, SPEC)
    by = {l["inst"]: l for l in lat}
    # a port-fed face flop and a port-fed relay are never latched (the pin loads its face flop directly)
    assert "u_fl_bin_x_i" not in by and "u_fl_rrl_1" not in by and sk["port"] == 3
    # station hop: data + epoch in one latch, epoch in the MSB
    assert by["u_fl_ist_x_0"]["width"] == 5 and by["u_fl_ist_x_0"]["src"] == "{a_eq, a_q}"
    assert ".d(fl_ist_x_0[3:0]), .ea(fl_ist_x_0[4])" in txt
    # out face: only d (ea is a reset net), the face flop q -> port is untouched
    assert by["u_fl_bout_x_o"]["width"] == 4 and ".q(x_o)" in txt and sk["reset"] == 1
    # one latch per port group of a multi-input leaf, widths from declarations / slices / concatenations
    assert by["u_fl_leaf_i"]["width"] == 4 and by["u_fl_leaf_j"]["width"] == 3
    assert by["u_fl_rrl_2"]["width"] == 1 and ".d(fl_rrl_2)" in txt
    # declarations sit after the module header, before any use
    assert txt.index("wire [4:0] fl_ist_x_0;") < txt.index("u_ist_x_0 (")


def test_unmatched_spec_fails_closed():
    with pytest.raises(zl.LkError):
        zl.apply(RTL, {"hops": [{"inst": "u_nothing", "ports": ["d"]}]})
    with pytest.raises(zl.LkError):
        zl.apply(RTL, {"hops": [{"inst": "u_ist_x_0", "ports": ["dd"]}]})


def test_cli(tmp_path):
    r = tmp_path / "top.sv"
    r.write_text(RTL)
    s = tmp_path / "spec.json"
    s.write_text(json.dumps(SPEC))
    assert zl.main([str(r), str(s), "--out", str(tmp_path / "o.sv"), "--report", str(tmp_path / "r.json")]) == 0
    rep = json.loads((tmp_path / "r.json").read_text())
    assert rep["latches"] == 5 and rep["bits"] == 5 + 4 + 4 + 3 + 1
    assert r.read_text() == RTL
