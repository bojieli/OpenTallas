"""tests for the leaf-registered crossing opt-in (DIE-KV-64 11-03, option 2): plan lane `"registered": "leaves"`.

    python3 -m pytest tools/die_plan/test_bind_regleaf.py
  - schema: the key, lane_natural 0 cycles, shape rules, one type bus all-or-none;
  - gen_phys: half-period IO budget on the leaf-registered ports only, sdc_lint clean, no-key SDC unchanged;
  - leaf_pinreg.py (+ face_guard.py hook): both-flop crossing PASS, a combinational end FAILS closed;
  - bind.py (Yosys via $OT_BIND_YOSYS or docker, like test_bind.py): no station on either side, bind_verify PASS with a
    0-stage transport, every file the lanes do not touch byte-identical to the no-key bind, and fail-closed refusals.
"""
import copy
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import face_guard  # noqa: E402
import gen_phys  # noqa: E402
import leaf_pinreg as LP  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
CFG = ("cfg01", "cfg12", "cfg23")


def tiny(lanes=CFG, **kw):
    raw = copy.deepcopy(TINY)
    for ln in raw["lanes"]:
        if ln["id"] in lanes:
            ln["registered"] = "leaves"
            ln.update(kw)
    return raw


# ---- schema -------------------------------------------------------------------------------------------------------

def test_schema_key_and_zero_cycles():
    raw = tiny()
    assert schema.validate(raw) == []
    P = schema.Plan(raw)
    for lid in CFG:
        assert P.lane_latency(lid) == dict(cycles=0, stations=0, boundary=0, faces=1, fixed=0, natural=0, pad=0)
    # untouched lanes keep their R2 boundary flops
    assert P.lane_latency("x") == schema.Plan(TINY).lane_latency("x")
    assert schema.registered_buses(P, "mid") == {"cfg_i": "in", "cfg_o": "out"}
    assert schema.registered_buses(P, "src") == {"cfg_o": "out"} and schema.registered_buses(P, "sink") == {"cfg_i": "in"}
    assert schema.registered_buses(schema.Plan(TINY), "mid") == {}


def test_schema_refusals():
    assert any("unknown" in e or "registered" in e for e in schema.validate(tiny(lanes=("cfg01",), registered="flops")))
    assert any("exactly one port" in e for e in schema.validate(tiny(lanes=("x",))))
    assert any("partition ends" in e for e in schema.validate(tiny(lanes=("din",))))
    assert any("fixed_cycles" in e for e in schema.validate(tiny(lanes=CFG, fixed_cycles=1)))
    # one type bus = one hardened pin: mid.cfg_o is registered on cfg12 but stationed on cfg23
    e = schema.validate(tiny(lanes=("cfg01", "cfg12")))
    assert any("type mid bus cfg_o" in x and "all or none" in x for x in e), e
    assert schema.registered_buses(schema.Plan(tiny(lanes=("cfg01", "cfg12"))), "mid") == {"cfg_i": "in"}


# ---- kit SDC ------------------------------------------------------------------------------------------------------

def test_half_period_io_budget():
    P0, P1 = schema.Plan(copy.deepcopy(TINY)), schema.Plan(tiny())
    for tn in ("src", "mid", "sink"):
        s0 = gen_phys.sdc(P0, tn, gen_phys.type_pins(P0, tn))
        s1 = gen_phys.sdc(P1, tn, gen_phys.type_pins(P1, tn))
        assert "leaf-registered" not in s0
        half = 0.5 * gen_phys.t_lib(P1.die["period_ps"])
        rb = schema.registered_buses(P1, tn)
        for b, d in rb.items():
            if d == "in":
                assert re.search(rf"set_input_delay -max {half:.4f} -clock vclk \[get_ports \{{{b}\[\*\]\}}\]", s1), s1
            else:
                assert f"set_output_delay -max {half:.4f} -clock vclk [get_ports {{{b}[*]}}]" in s1
        # only the leaf-registered lines are added (the min / hold lines are unchanged)
        extra = [x for x in s1.splitlines() if x not in s0.splitlines()]
        assert len(extra) == 1 + len(set(rb.values())), extra
        assert sdc_lint.lint(s1, **sdc_lint.kit_context(P1, tn)) == []
    rl = gen_phys.regleaf_buses(P1, "mid")
    assert sorted(rl) == ["cfg_i", "cfg_o"] and rl["cfg_i"]["dir"] == "in" and rl["cfg_o"]["dir"] == "out"
    assert all(v["data_bits"] == int(next(b["width"] for b in P1.types["mid"]["buses"] if b["name"] == n))
               for n, v in rl.items())
    assert gen_phys.regleaf_buses(P0, "mid") == {}


# ---- leaf_pinreg on synthesized netlists --------------------------------------------------------------------------

DFF = "DFFHQNx1_ASAP7_75t_R"
INV = "INVx1_ASAP7_75t_R"
NAND = "NAND2xp5_ASAP7_75t_R"


def netlist(in_comb=False, out_comb=False, epoch_float=True):
    """kt: rin[2:0] (2 data + epoch) -> leaf flops, leaf flops -> rout[2:0]; ASAP7 DFFHQN outputs QN (INV after)."""
    v = ["module kt (clk, rin, rout);", "  input clk;", "  input [2:0] rin;", "  output [2:0] rout;",
         "  wire n0, n1, q0, q1, qn0, qn1, x0, ia;"]
    # input bit 0: port -> INV -> D; bit 1: port -> D (or through a NAND = combinational end)
    v.append(f"  {INV} ui0 (.A(rin[0]), .Y(n0));")
    v.append(f"  {DFF} f0 (.CLK(clk), .D(n0), .QN(qn0));")
    if in_comb:
        v.append(f"  {NAND} ug (.A(rin[1]), .B(qn0), .Y(n1));")
        v.append(f"  {DFF} f1 (.CLK(clk), .D(n1), .QN(qn1));")
    else:
        v.append(f"  {DFF} f1 (.CLK(clk), .D(rin[1]), .QN(qn1));")
    # output bits: flop QN -> INV -> port (the flop also feeds internal logic: allowed)
    v.append(f"  {INV} uo0 (.A(qn0), .Y(q0));")
    v.append(f"  {NAND} uint (.A(qn0), .B(qn1), .Y(ia));")
    v.append(f"  {DFF} f2 (.CLK(clk), .D(ia), .QN(x0));")
    if out_comb:
        v.append(f"  {NAND} uo1 (.A(qn1), .B(qn0), .Y(q1));")
    else:
        v.append(f"  {INV} uo1 (.A(qn1), .Y(q1));")
    v += ["  assign rout[0] = q0;", "  assign rout[1] = q1;", "  assign rout[2] = clk;" if not epoch_float else
          "  assign rout[2] = 1'b1;", "endmodule", ""]
    return "\n".join(v)


DECL = {"rin": dict(dir="in", data_bits=2, epoch=True), "rout": dict(dir="out", data_bits=2, epoch=True)}


def test_leaf_pinreg_both_flop_pass():
    r = LP.check(netlist(), DECL)
    assert r["verdict"] == "PASS" and r["checked"] == 4 and r["ok"] == 4, r
    assert r["ends"]["flop"] == 4 and not r["fails"]


def test_leaf_pinreg_comb_end_fails_closed():
    r = LP.check(netlist(in_comb=True), DECL)
    assert r["verdict"] == "FAIL" and "comb_end" in r["fails"] and "rin[1]" in r["fails"]["comb_end"][0], r
    r = LP.check(netlist(out_comb=True), DECL)
    assert r["verdict"] == "FAIL" and "comb_end" in r["fails"] and "rout[1]" in r["fails"]["comb_end"][0], r
    # a declaration that does not match the netlist port fails too (never silently skipped)
    r = LP.check(netlist(), {"rin": dict(dir="in", data_bits=3, epoch=True)})
    assert r["verdict"] == "FAIL" and "port" in r["fails"]
    r = LP.check(netlist(), {"rout": dict(dir="in", data_bits=2, epoch=True)})
    assert r["verdict"] == "FAIL" and "port" in r["fails"]



def test_leaf_pinreg_declaration_fails_closed(tmp_path):
    p = tmp_path / "leaf_pinreg.json"
    for doc in (dict(schema="x", buses=DECL), dict(schema=LP.SCHEMA, buses={}),
                dict(schema=LP.SCHEMA, buses={"rin": dict(dir="in", data_bits=0, epoch=True)}),
                dict(schema=LP.SCHEMA, buses={"rin[0]": dict(dir="in", data_bits=1, epoch=False)})):
        p.write_text(json.dumps(doc))
        with pytest.raises(ValueError):
            LP.load_decl(p)
    p.write_text(json.dumps(dict(schema=LP.SCHEMA, buses=DECL)))
    assert LP.load_decl(p) == DECL


def test_leaf_pinreg_feedthrough_clock_pin_and_spare():
    ft = netlist().replace("  assign rout[0] = q0;", "  assign rout[0] = rin[0];")
    r = LP.check(ft, DECL)
    assert r["verdict"] == "FAIL" and "feedthrough" in r["fails"], r
    ck = netlist().replace(f"{DFF} f1 (.CLK(clk), .D(rin[1])", f"{DFF} f1 (.CLK(rin[1]), .D(clk)")
    assert "flop_pin" in LP.check(ck, DECL)["fails"]
    tie = netlist().replace("  assign rout[1] = q1;", "  assign rout[1] = 1'b0;")
    assert "const" in LP.check(tie, DECL)["fails"]
    assert LP.check(tie, DECL, spare=["rout[1]"])["verdict"] == "PASS"


def lib_text(cell="hm", reg=True):
    def tim(kind):
        return f'      timing () {{\n        related_pin : "clk";\n        timing_type : {kind};\n      }}\n'
    return (f"library (hm_tt) {{\n  cell ({cell}) {{\n    pin (clk) {{\n      direction : input;\n      clock : true;\n    }}\n"
            f"    pin (a) {{\n      direction : input;\n{tim('setup_rising') + tim('hold_rising') if reg else ''}    }}\n"
            f"    pin (z) {{\n      direction : output;\n{tim('rising_edge') if reg else tim('combinational')}    }}\n"
            "  }\n}\n")


def test_leaf_pinreg_hard_macro_ends(tmp_path):
    t = ("module kt (clk, rin, rout);\n  input clk;\n  input [1:0] rin;\n  output [1:0] rout;\n  wire z;\n"
         "  hm u_hm (.clk(clk), .a(rin[0]), .z(z));\n  assign rout[0] = z;\nendmodule\n")
    d = {"rin": dict(dir="in", data_bits=1, epoch=True), "rout": dict(dir="out", data_bits=1, epoch=True)}
    good, bad = tmp_path / "hm_tt.lib", tmp_path / "hmb_tt.lib"
    good.write_text(lib_text())
    bad.write_text(lib_text(reg=False))
    r = LP.check(t, d, libs=[good])
    assert r["verdict"] == "PASS" and r["ends"]["macro"] == 2, r
    r = LP.check(t, d, libs=[bad])
    assert r["verdict"] == "FAIL" and len(r["fails"]["macro"]) == 2, r
    r = LP.check(t, d)                                   # no liberty view: unknown macro pin, fail closed
    assert r["verdict"] == "FAIL" and "macro" in r["fails"]


def test_face_guard_runs_leaf_pinreg(tmp_path):
    """face_guard (run_kit.sh, after synth) exempts the declared buses from the dedicated-face-flop rule and runs
    leaf_pinreg on them; a kit without leaf_pinreg.json is unchanged."""
    kd = tmp_path / "kit"
    kd.mkdir()
    pins = [dict(bus=b, bit=i, layer="M4", x=0, y=0, face="W") for b in ("rin", "rout") for i in range(3)]
    (kd / "pins.json").write_text(json.dumps(pins))
    (kd / "leaf_pinreg.json").write_text(json.dumps(dict(schema=LP.SCHEMA, period_ps=833, io_budget_ps=416.5,
                                                         buses=DECL)))
    for tag, text, want in (("ok", netlist(), 0), ("comb", netlist(in_comb=True), 1)):
        f = tmp_path / f"{tag}.v"
        f.write_text(text)
        out = tmp_path / f"{tag}.json"
        assert face_guard.main([str(f), "--pins", str(kd / "pins.json"), "--out", str(out)]) == want
        r = json.loads(out.read_text())
        assert r["leaf_pinreg"]["verdict"] == ("PASS" if want == 0 else "FAIL"), r
    (kd / "leaf_pinreg.json").unlink()
    f = tmp_path / "ok.v"
    out = tmp_path / "plain.json"
    assert face_guard.main([str(f), "--pins", str(kd / "pins.json"), "--out", str(out)]) == 1   # shared leaf flops
    assert "leaf_pinreg" not in json.loads(out.read_text())


# ---- bind ---------------------------------------------------------------------------------------------------------

def run(plan, out, *cmds):
    for c in cmds:
        rc = bind.main([c, str(plan), "--out", str(out), "--mem", "4"])
        if rc:
            return rc
    return 0


def lanes_plan(tmp_path, tag, reg=("a0s", "a1s"), cycles=0, edit=None):
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    for ln in p["lanes"]:
        if ln["id"] in reg:
            ln["registered"] = "leaves"
            p["latency"]["lanes"][ln["id"]].update(cycles=cycles, boundary=0)
    if edit:
        edit(p)
    p["asbuilt"]["base"] = str(EX)
    f = tmp_path / f"die_plan_lanes_{tag}.json"
    f.write_text(json.dumps(p))
    return f


def rep(o):
    return json.loads((o / "bind_report.json").read_text())


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
def test_bind_registered_leaves(tmp_path):
    """a0s / a1s (A0/A1 ys_o -> S d0_i / d1_i, single-port lanes) marked registered "leaves": no ot_dp_st on either
    side, bind_verify PASS with the 0-stage transport, bound_stages 0, the other lanes' stations untouched."""
    o0, o1 = tmp_path / "o0", tmp_path / "o1"
    assert run(lanes_plan(tmp_path, "plain", reg=()), o0, "elab", "bind", "verify") == 0, rep(o0)["errors"][:5]
    assert run(lanes_plan(tmp_path, "reg"), o1, "elab", "bind", "verify") == 0, rep(o1)["errors"][:5]
    r = rep(o1)
    v = json.loads((o1 / "verify_report.json").read_text())
    assert r["n_errors"] == 0 and v["verdict"] == "PASS", (r["errors"][:3], v["counts"], v["mismatches"][:3])
    ta0, ta1 = ((o / "rtl" / "bt_ta.sv").read_text() for o in (o0, o1))
    ts0, ts1 = ((o / "rtl" / "bt_ts.sv").read_text() for o in (o0, o1))
    assert "u_bout_ys_o" in ta0 and "u_bout_ys_o" not in ta1 and "u_bout_y_o" in ta1 and "u_bin_x_i" in ta1
    assert re.search(r"assign ys_o = \{rst_n, w_\w+\[[\d:]+\]\};", ta1), ta1
    assert "u_bin_d0_i" in ts0 and "u_bin_d0_i" not in ts1 and "u_bin_d1_i" not in ts1 and "u_bin_f0_i" in ts1
    assert re.search(r"assign d0_i_q = d0_i\[7:0\];", ts1), ts1
    lat = {b["lane"]: b for b in json.loads((o1 / "bind_latency.json").read_text())["buses"]}
    assert lat["a0s"]["bound_stages"] == 0 == lat["a0s"]["plan_cycles"] and lat["a1s"]["bound_stages"] == 0
    assert lat["a0y"]["bound_stages"] == 3 and lat["a0f"]["bound_stages"] == 2
    s0, s1 = (json.loads((o / "bind_sinks.json").read_text()) for o in (o0, o1))
    assert s0["snk.d0[0]"][2] == 2 and s1["snk.d0[0]"][2] == 0 and s1["snk.flt[0]"] == s0["snk.flt[0]"]
    # every generated file the registered lanes do not touch is byte-identical to the no-key bind
    for f0 in sorted((o0 / "rtl").glob("*.sv")):
        if f0.name not in ("bt_ta.sv", "bt_ts.sv"):
            assert f0.read_text() == (o1 / "rtl" / f0.name).read_text(), f0.name


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
def test_bind_no_key_byte_identical(tmp_path):
    """no `registered` key anywhere: the bind output equals the example plan's bind file for file (the opt-in code
    paths are dead), and no leaf-registered text appears."""
    o0, o1 = tmp_path / "o0", tmp_path / "o1"
    assert run(EX / "die_plan_lanes.json", o0, "elab", "bind") == 0
    assert run(lanes_plan(tmp_path, "nokey", reg=()), o1, "elab", "bind") == 0
    f0 = sorted(p.relative_to(o0) for p in (o0 / "rtl").rglob("*") if p.is_file())
    assert f0 == sorted(p.relative_to(o1) for p in (o1 / "rtl").rglob("*") if p.is_file())
    for rel in f0:
        a, b = (o0 / rel).read_text(), (o1 / rel).read_text()
        assert a == b, rel
        assert "leaf-registered" not in a
    la, lb = (json.loads((o / "bind_latency.json").read_text()) for o in (o0, o1))
    assert la["buses"] == lb["buses"]


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
def test_bind_registered_fails_closed(tmp_path):
    # the latency table still prices the R2 stations (2 cycles): the lane would need flops it does not have
    o = tmp_path / "o2"
    run(lanes_plan(tmp_path, "cyc2", cycles=2), o, "elab", "bind")       # bind records EMIT errors in its report
    assert any("registered leaves lane" in e and "needs flops" in e for e in rep(o)["errors"]), rep(o)["errors"][:3]

    # a forwarded bit (A0 -> A1 -> S through A1's in bus) on a registered out bus = a 0-cycle feedthrough
    def fwd(p):
        p["ports"] = [x for x in p["ports"] if x["id"] != "a0s__0"]
        p["lanes"] = [x for x in p["lanes"] if x["id"] != "a0s"]
        p["latency"]["lanes"].pop("a0s")
        for x in p["ports"]:
            if x["id"] == "a1s__0":
                x["width"] = 16
        for t, b in (("ta", "ys_o"), ("ts", "d1_i")):
            for bb in p["partition_types"][t]["buses"]:
                if bb["name"] == b:
                    bb["width"] = 16
    o = tmp_path / "o3"
    run(lanes_plan(tmp_path, "fwd", reg=("a1s",), edit=fwd), o, "elab", "bind")
    assert any("registered leaves lane a1s" in e and "forwarded" in e for e in rep(o)["errors"]), rep(o)["errors"][:3]
