"""OWNER 10-20 ~09:05 pin-register / reset rules in textbook_lint (ROOT8-RULES).

  * pin registers are required only at region crossings (landing rings) and on wires over the 405 um reach: an
    unregistered input / output with logic between the pin and its flop (a same-region direct connection) is a WARN
    finding, never a boundary REFUSE, unless the strict form (bnd_strict_pin_regs=1) is asked for;
  * a combinational input -> output feed-through stays a REFUSE (safe-design item 4), and a stage beyond the wire reach
    without a register stays a wire_reach REFUSE;
  * reset is control / valid only by default: unreset datapath flops are never a finding and the reset fan-out metric
    counts the control flops the reset actually reaches."""
import json

import textbook_lint as TL

HDR = "module top (clk, {ports});\n  input clk;\n"


def netlist(body, ports):
    decl = "".join(f"  {d} {p};\n" for d, p in ports)
    return HDR.format(ports=", ".join(p for _, p in ports)) + decl + body + "endmodule\n"


def lint(tmp_path, text, dump=None, th=None, checks=("boundary", "wire_reach", "high_fanout")):
    f = tmp_path / "n.v"
    f.write_text(text)
    d = None
    if dump is not None:
        d = tmp_path / "d.json"
        d.write_text(json.dumps(dump))
    return TL.run(str(f), str(d) if d else None, th, "top", "refuse", refuse_checks=checks)


def chain(src, n, dst, b="e"):
    """n AND levels from src to the wire dst"""
    s, prev = [], src
    for i in range(n):
        out = dst if i == n - 1 else f"c{i}"
        if i < n - 1:
            s.append(f"  wire c{i};\n")
        s.append(f"  AND2x2_ASAP7_75t_R g{i} (.A({prev}), .B({b}), .Y({out}));\n")
        prev = out
    return "".join(s)


# input d -> 10 logic levels -> flop (over bnd_in_levels_refuse 9): an unregistered input pin
DEEP_IN = netlist("  wire dd;\n" + chain("d", 10, "dd")
                  + "  DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk), .D(dd), .QN(q));\n",
                  [("input", "d"), ("input", "e"), ("output", "q")])
# flop -> 4 logic levels -> output (over bnd_out_levels_refuse 3): an unregistered output pin
DEEP_OUT = netlist("  wire qn;\n  DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk), .D(d), .QN(qn));\n" + chain("qn", 4, "q", b="qn"),
                   [("input", "d"), ("output", "q")])
# combinational input -> output
FEED = netlist("  AND2x2_ASAP7_75t_R g0 (.A(d), .B(e), .Y(q));\n", [("input", "d"), ("input", "e"), ("output", "q")])
# one register between two fixed pins 1,200 um apart (> the reach: a relay is owed)
FAR = netlist("  DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk), .D(d), .QN(q));\n", [("input", "d"), ("output", "q")])
FAR_DUMP = {"core": [0, 0, 1210, 20], "die": [0, 0, 1210, 20], "bterms": [["d", "d", "SIGNAL", "INPUT", [["M4", [0, 0, 1, 1]]]],
                       ["q", "q", "SIGNAL", "OUTPUT", [["M4", [1200, 0, 1201, 1]]]]]}


def test_unregistered_pins_warn_not_refuse(tmp_path):
    for text in (DEEP_IN, DEEP_OUT):
        r = lint(tmp_path, text)
        assert "boundary" in r["findings"], r["findings"]                 # still reported (WARN)
        assert "boundary" not in r["refuse"], r["refuse"]                 # never a REFUSE by default
        assert "same-region direct connection" in " ".join(r["findings"]["boundary"])


def test_strict_form_refuses_unregistered_pins(tmp_path):
    for text in (DEEP_IN, DEEP_OUT):
        r = lint(tmp_path, text, th={"bnd_strict_pin_regs": 1})
        assert "boundary" in r["refuse"], r


def test_combinational_feedthrough_still_refused(tmp_path):
    r = lint(tmp_path, FEED)
    assert any("combinational input->output" in x for x in r["refuse"].get("boundary", [])), r["refuse"]


def test_unregistered_wire_beyond_reach_still_refused(tmp_path):
    r = lint(tmp_path, FAR, FAR_DUMP)
    assert "wire_reach" in r["refuse"], r
    assert r["metrics"]["reach_worst_um"] > 405


def test_control_only_reset_datapath_unreset(tmp_path):
    # 3 control flops on a synchronous reset (AND in front of D) + 40 unreset datapath flops on the same clock
    ctl = "".join(f"  wire a{i}, n{i};\n  AND2x2_ASAP7_75t_R r{i} (.A(rst_n), .B(v), .Y(a{i}));\n"
                  f"  DFFHQNx1_ASAP7_75t_R vf{i} (.CLK(clk), .D(a{i}), .QN(n{i}));\n" for i in range(3))
    dp = "".join(f"  wire m{i};\n  DFFHQNx1_ASAP7_75t_R df{i} (.CLK(clk), .D(x), .QN(m{i}));\n" for i in range(40))
    text = netlist(ctl + dp + "  BUFx2_ASAP7_75t_R ob (.A(n0), .Y(q));\n",
                   [("input", "rst_n"), ("input", "v"), ("input", "x"), ("output", "q")])
    r = lint(tmp_path, text, checks=("boundary", "wire_reach", "high_fanout", "reset_landing"))
    blob = json.dumps(r["findings"]) + json.dumps(r["refuse"])
    assert not any(f"df{i}" in blob for i in range(40)), blob        # unreset datapath flops are never flagged
    land = {p["port"]: p for p in r["metrics"]["reset_landing"]}
    assert land["rst_n"]["sinks"] == 3, land                          # the reset reaches the control flops only
    assert "high_fanout" not in r["refuse"]
