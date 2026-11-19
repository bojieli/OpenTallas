"""CBC-RULES-1119 11-19: zero-wire logic delay rule (COORD amends r713 rule 3)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbc_rules as RULES
import zero_wire as ZW

NET = """module sub (a, y);
  input a;
  output y;
  INVx1_ASAP7_75t_R _1_ (
    .A(a),
    .Y(y)
  );
endmodule
module top (clk, d, q);
  input clk;
  input d;
  output q;
  wire n0;
""" + "".join(f"""  INVx1_ASAP7_75t_R _i{k}_ (
    .A(n0),
    .Y(o{k})
  );
""" for k in range(20)) + """  DFFHQNx1_ASAP7_75t_R _f_ (
    .CLK(clk),
    .D(d),
    .QN(n0)
  );
  sub u_s (.a(n0), .y(q));
endmodule
"""


def test_rule_constants():
    assert RULES.LOGIC_PS_MAX == 600.0 and RULES.FANOUT_BOUND == 8 and RULES.PERIOD_PS == 833.0
    assert RULES.DEPTH_LEVELS_MAX == 13        # pre-screen only


def test_bound_fanout_tree_and_untouched_other_sinks():
    out, st = ZW.bound_fanout(NET, bound=8)
    assert st == dict(nets_bounded=1, buffers_added=3)        # 20 sinks -> 3 buffers of <= 8, all on n0
    loads = {}
    for m in re.finditer(r"\.A\(([^)]*)\)", out):
        loads[m.group(1)] = loads.get(m.group(1), 0) + 1
    assert max(loads.values()) <= 8
    assert loads["n0"] == 3                                    # the driver now sees 3 buffers (+ the submodule port)
    assert "sub u_s (.a(n0), .y(q));" in out                   # a submodule sink stays on the net
    assert ".D(d)" in out and ".QN(n0)" in out                 # outputs and other inputs untouched
    assert ZW.bound_fanout(NET, bound=32)[1] == dict(nets_bounded=0, buffers_added=0)


def test_deep_tree_recurses():
    big = NET.replace("range(20)", "")
    text = "module t (x);\n  input x;\n" + "".join(
        f"  INVx1_ASAP7_75t_R _i{k}_ (\n    .A(x),\n    .Y(o{k})\n  );\n" for k in range(100)) + "endmodule\n"
    out, st = ZW.bound_fanout(text, bound=8)
    assert st["buffers_added"] == 13 + 2                       # 100 -> 13 -> 2 buffers; x drives 2
    assert len(re.findall(r"\.A\(x\)", out)) == 2


def test_top_module_and_tcl_and_parse():
    assert ZW.top_module(NET) == "top"
    tcl = ZW.sta_tcl("/zw/zw.v", "top", 600.0, 50)
    assert "-period 600.0" in tcl and "RVT_TT" in tcl and "set_load" not in tcl and "parasitics" not in tcl
    log = "ZW WNS -215.3 NV 2\nEndpoint  Required Arrival Slack\n" \
          "u_a/D (DFFHQNx1_ASAP7_75t_R)   590.1  805.4 -215.3 (VIOLATED)\nq (output)  600.0  611.0 -11.0 (VIOLATED)\n"
    r = ZW.parse(log, 600.0)
    assert r["endpoints_over"] == 2 and r["worst_ps"] == 815.3
    assert r["ends"][0] == ["u_a/D", 815.3]


def test_escaped_net_keeps_its_terminating_space():
    text = "module t (x);\n  input x;\n" + "".join(
        f"  INVx1_ASAP7_75t_R _i{k}_ (\n    .A(\\r_oh[2] ),\n    .Y(o{k})\n  );\n" for k in range(9)) + "endmodule\n"
    out, st = ZW.bound_fanout(text, bound=8)
    assert st["buffers_added"] == 2 and out.count("(.A(\\r_oh[2] ), ") == 2
