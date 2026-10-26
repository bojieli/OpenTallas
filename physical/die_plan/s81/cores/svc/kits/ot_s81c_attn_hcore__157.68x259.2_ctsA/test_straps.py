"""ID straps (OWNER DECISION 2026-10-25 07:01, option B): the flow gates accept a constant / false path / missing pin
register ONLY on declared strap_* ports; every other case stays fail-closed.
    python3 -m pytest -q tools/die_plan/test_straps.py"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import face_guard  # noqa: E402
import port_bind_gate  # noqa: E402
import reg_fanout_gate  # noqa: E402
import schema  # noqa: E402
import gen_phys  # noqa: E402
import sdc_lint  # noqa: E402
import straps  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _sdc():
    P = schema.Plan(TINY)
    tn = next(iter(t for t in P.types if not P.types[t].get("hard")))
    txt = gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))
    ctx = sdc_lint.kit_context(P, tn)
    ctx = dict(ctx, inputs=list(ctx["inputs"]) + ["strap_tid"],
               io_floor_ps=dict(ctx.get("io_floor_ps") or {}))
    return txt, ctx


def test_sdc_false_path_only_on_declared_straps():
    txt, ctx = _sdc()
    fp = "\nset_false_path -from [get_ports {strap_tid}]\n"
    other = next(p for p in ctx["inputs"] if p != "strap_tid")
    assert sdc_lint.lint(txt + fp, **ctx, straps=["strap_tid"]) == []
    assert sdc_lint.lint(txt + "\nset_false_path -from [get_ports strap_*]\n", **ctx, straps=["strap_tid"]) == []
    # undeclared: the exception is forbidden as before
    assert any("forbidden" in e for e in sdc_lint.lint(txt + fp, **ctx))
    # declared but no false path: required on every declared strap
    assert any("no set_false_path" in e for e in sdc_lint.lint(txt, **ctx, straps=["strap_tid"]))
    # false path on a non-strap port, or a -to / -through form: refused
    bad = f"\nset_false_path -from [get_ports {{strap_tid {other}}}]\n"
    assert any("non-strap" in e for e in sdc_lint.lint(txt + bad, **ctx, straps=["strap_tid"]))
    assert any("only 'set_false_path -from" in e
               for e in sdc_lint.lint(txt + fp + "set_false_path -to [get_ports {strap_tid}]\n", **ctx,
                                      straps=["strap_tid"]))
    # a strap must be a strap_* input
    assert any("strap_<id>" in e for e in sdc_lint.lint(txt, **ctx, straps=[other]))
    assert any("not an input" in e for e in sdc_lint.lint(txt, **ctx, straps=["strap_nope"]))


NET = r"""
module top(clk, a, strap_tid, o);
  input clk; input [1:0] a; input [1:0] strap_tid; output [1:0] o;
  wire _0_; wire _1_; wire [1:0] q; wire s;
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[0]$_DFF_P_  (.CLK(clk), .D(a[0]), .QN(q[0]));
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[1]$_DFF_P_  (.CLK(clk), .D(a[1]), .QN(q[1]));
  XOR2xp5_ASAP7_75t_R _9_ (.A(q[0]), .B(strap_tid[0]), .Y(s));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[0]$_DFF_P_  (.CLK(clk), .D(s), .QN(_0_));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[1]$_DFF_P_  (.CLK(clk), .D(q[1]), .QN(_1_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));
  INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));
endmodule
"""


def test_face_guard_exempts_declared_straps_only():
    assert face_guard.guard(NET)["verdict"] == "FAIL"                     # undeclared: unregistered input
    r = face_guard.guard(NET, straps=["strap_tid"])
    assert r["verdict"] == "PASS" and r["straps_exempt"] == ["strap_tid"], r
    with pytest.raises(ValueError):
        face_guard.guard(NET, straps=["a"])                              # only strap_* names
    assert face_guard.guard(NET.replace("input [1:0] strap_tid; output [1:0] o;",
                                        "input [1:0] strap_tid; output [1:0] o; output strap_x;")
                            .replace("module top(clk, a, strap_tid, o)", "module top(clk, a, strap_tid, o, strap_x)"),
                            straps=["strap_tid", "strap_x"])["verdict"] == "FAIL"   # a strap must be an input


def test_face_guard_reads_kit_straps(tmp_path):
    (tmp_path / "core.json").write_text(json.dumps(dict(report=dict(straps=[
        dict(port="strap_tid", kind="id_strap"), dict(port="cfg", kind="other")]))))
    assert face_guard.kit_strap_list(tmp_path) == ["strap_tid"]
    straps.write_kit(tmp_path, ["strap_tid"])
    assert straps.kit_straps(tmp_path) == ["strap_tid"] == face_guard.kit_strap_list(tmp_path)
    with pytest.raises(ValueError):
        straps.write_kit(tmp_path, ["tile_tid"])


def _fan(n, d="strap_tid[0]"):
    loads = "\n".join(f"  INVx1_ASAP7_75t_R l{i} (.A(q), .Y(y{i}));" for i in range(n))
    wires = " ".join(f"wire y{i};" for i in range(n))
    return (f"module top(clk, strap_tid, a);\n input clk; input [1:0] strap_tid; input a; wire q; {wires}\n"
            f"  DFFHQNx1_ASAP7_75t_R r (.CLK(clk), .D({d}), .QN(q));\n{loads}\nendmodule\n")


def test_reg_fanout_exempts_strap_landing_only():
    assert reg_fanout_gate.fanout(_fan(100))["verdict"] == "FAIL"
    r = reg_fanout_gate.fanout(_fan(100), straps=["strap_tid"])
    assert r["verdict"] == "PASS" and len(r["strap_landing"]) == 1, r
    assert reg_fanout_gate.fanout(_fan(100, d="a"), straps=["strap_tid"])["verdict"] == "FAIL"


def test_port_bind_gate_strap_must_be_input():
    text = "module t(a, strap_tid, o);\n  input a;\n  input [1:0] strap_tid;\n  output o;\nendmodule\n"
    pins = [dict(bus="a"), dict(bus="strap_tid", bit=0), dict(bus="strap_tid", bit=1), dict(bus="o")]
    assert port_bind_gate.check(text, "t", pins, ["strap_tid"])["verdict"] == "PASS"
    assert port_bind_gate.check(text, "t", pins, ["o"])["verdict"] == "FAIL"
    assert port_bind_gate.check(text, "t", pins, ["strap_o"])["verdict"] == "FAIL"


MAN = dict(types=dict(ta={"strap_u_b__tile_id": dict(leaf="u_b", port="tile_id", width=4)}))
TOP = """module tdie(input clk);
    bt_ta #(.P_x(4'b0001)) A0 (
        .clk(clk),
        .strap_u_b__tile_id(4'b0110),
        .d(w0)
    );
endmodule
"""


def test_top_tie_audit_accepts_declared_straps_only():
    r = straps.audit_top_ties(TOP, MAN)
    assert r["verdict"] == "PASS" and r["rows"] == [("A0", "strap_u_b__tile_id", "4'b0110")], r
    bad = straps.audit_top_ties(TOP.replace(".d(w0)", ".d(1'b0)"), MAN)
    assert bad["verdict"] == "FAIL" and bad["rejected"] == [("A0.d", "1'b0")], bad
    assert straps.audit_top_ties(TOP, dict(types={}))["verdict"] == "FAIL"           # undeclared tie
    assert straps.audit_top_ties(TOP.replace("4'b0110", "2'b10"), MAN)["verdict"] == "FAIL"   # width mismatch
    tcl = straps.tie_check_tcl(r["rows"], max_um=5)
    assert tcl.count("ot_strap_tie_check {A0}") == 4
    assert "{strap_u_b__tile_id[1]} 1" in tcl and "{strap_u_b__tile_id[0]} 0" in tcl
    assert "TIEHIx1_ASAP7_75t_R" in tcl and "TIELOx1_ASAP7_75t_R" in tcl
