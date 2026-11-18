"""KV-D24-HUBC 11-18: ot_dp_dly as a param_wrap base (hard delay-line child cores of kv3_hub_Wo / kv3_hub_C).
The port table must equal the header of the module bind.py emits, and wrap_bound must rename exactly the planned instance.
    python3 -m pytest -q tools/die_plan/test_param_wrap_dly.py"""
import re
from pathlib import Path

import pytest

import param_wrap

BIND = (Path(__file__).resolve().parent / "bind.py").read_text()


def test_port_table_equals_bind_header():
    m = re.search(r"module ot_dp_dly #\(parameter integer W = 1, parameter integer D = 1\) \((.*?)\);", BIND, re.S)
    assert m, "bind.py no longer emits the ot_dp_dly header this table was written for"
    hdr = re.findall(r"(input|output)\s+wire\s+(?:\[W-1:0\]\s+)?(\w+)", m.group(1))
    assert hdr == [(d, n) for d, n, _ in param_wrap.PORTS["ot_dp_dly"]]
    wide = set(re.findall(r"wire\s+\[W-1:0\]\s+(\w+)", m.group(1)))
    assert wide == {n for _, n, w in param_wrap.PORTS["ot_dp_dly"] if w({"W": 7, "D": 3}) == 7}


def test_wrapper_and_wrap_bound():
    hc = dict(inst="dly_x", module="kv_dly_w512_d46_x", physical_master="kv_dly_w512_d46_x", physical_inst="u_bound.u_d46_x",
              param_wrap=dict(base="ot_dp_dly", params={"W": 512, "D": 46}))
    bound = ("    ot_dp_dly #(.W(512), .D(46)) u_d46_x (.clk(clk), .d(a), .q(b));\n"
             "    ot_dp_dly #(.W(16), .D(46)) u_d46_y (.clk(clk), .d(c), .q(e));\n")
    out, receipt, srcs = param_wrap.wrap_bound(bound, [hc])
    assert "    kv_dly_w512_d46_x u_d46_x (.clk(clk), .d(a), .q(b));" in out and "ot_dp_dly #(.W(16), .D(46)) u_d46_y" in out
    assert receipt[0]["cycles_changed"] == 0
    sv = srcs["kv_dly_w512_d46_x"]
    assert "input  wire clk" in sv and "input  wire [511:0] d" in sv and "output wire [511:0] q" in sv
    assert "ot_dp_dly #(.W(512), .D(46)) u_w (.clk(clk), .d(d), .q(q));" in sv


def test_wrong_depth_fails_closed():
    hc = dict(inst="dly_x", module="m", physical_inst="u_bound.u_d46_x", param_wrap=dict(base="ot_dp_dly", params={"W": 512, "D": 44}))
    with pytest.raises(ValueError):
        param_wrap.wrap_bound("    ot_dp_dly #(.W(512), .D(46)) u_d46_x (.clk(clk), .d(a), .q(b));\n", [hc])
