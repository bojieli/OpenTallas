"""OWNER DECISION 13 (2026-10-24): reset wavefront -- one root synchroniser per die, every partition registers its
incoming reset and re-drives registered rst_o outs to its neighbours; per-partition release cycles published by
reset_tree.py offsets and checked here against a simulation of the generated die."""
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def wave(raw, **kw):
    raw = copy.deepcopy(raw)
    raw.setdefault("reset", {}).update(release="wavefront", **kw)
    assert schema.validate(raw) == []
    return raw


def test_offsets_follow_the_parent_tree():
    for raw in (TINY, PAIR):
        P = schema.Plan(wave(raw))
        W = RT.wf_plan(P)
        assert W["unreachable"] == [] and set(W["parts"]) == set(P.parts)
        assert W["max_die_hop_um"] <= RT.hop_um(P)
        roots = [p for p, r in W["parts"].items() if r["parent"] is None]
        assert roots == [W["root"]]
        for p, r in W["parts"].items():
            ty = W["types"][r["type"]]
            if r["parent"] is None:
                assert r["release"] == RT.sync_stages(P) + ty["depth_K"] and ty["entry"] == "sync"
            else:
                par = W["parts"][r["parent"]]
                assert r["release"] == par["release"] + ty["entry_stages"] + ty["depth_K"]
                k = int(r["source"].rsplit("_", 1)[1])
                assert r["source"].startswith(r["parent"] + ".rst_o_") and k < len(W["types"][par["type"]]["outs"])
        for tn in W["types"]:
            T = RT.for_type(P, tn)
            assert RT.verify(T) == [] and T["max_hop_um"] <= RT.relay_um(P)
            assert len(T["outs"]) == len(W["types"][tn]["outs"])
        e, w, info = RT.check(P)
        assert e == [] and info["max_release"] == W["max_release"]


def test_check_py_wavefront_and_supersedes_pipelined():
    import check
    R, summ = check.run(wave(TINY))
    assert R.errors() == [] and summ["reset"]["release"] == "wavefront"
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {})["release"] = "pipelined"
    R2, _ = check.run(raw)
    assert any(i["check"] == "reset" and "DECISION 13" in i["msg"] for i in R2.items)


def test_gen_rtl_ports_and_die_wiring():
    import gen_rtl
    raw = wave(TINY)
    P = schema.Plan(raw)
    W = RT.wf_plan(P)
    with tempfile.TemporaryDirectory() as d:
        gen_rtl.write_rtl(copy.deepcopy(raw), d)
        top = (Path(d) / "tiny_top.sv").read_text()
        for p, r in W["parts"].items():
            inst = re.search(rf"^    \w+ {p} \((.*?)\n    \);", top, re.S | re.M).group(1)
            if r["parent"] is None:
                assert ".arst_n(rst_n)" in inst
            else:
                net = "rstw_" + re.sub(r"\W", "_", r["source"])
                assert f".arst_n({net})" in inst
                assert re.search(rf"\.{r['source'].split('.')[1]}\({net}\)", top)
        for tn, ty in W["types"].items():
            v = (Path(d) / f"{P.types[tn]['module']}.sv").read_text()
            for n, _x, _y in ty["outs"]:
                assert f"output wire {n}" in v and f"assign {n} = rst_n_t" in v
            assert ("ot_dp_rsync_s2 u_rst_root" in v) == (ty["entry"] == "sync")


def test_tiny_die_wavefront_release_matches_offsets():
    """simulate the generated tiny die: every tap of partition p releases exactly W.parts[p].release clocks after the
    die rst_n deasserts (and is held in reset before)."""
    import gen_rtl
    if not shutil.which("iverilog"):
        return
    root = HERE.parent.parent
    raw = wave(TINY)
    P = schema.Plan(raw)
    W = RT.wf_plan(P)
    nets, want = [], []
    for part, p in P.parts.items():
        T = RT.for_type(P, p["type"])
        for i in range(len(T["taps"])):
            nets.append(f"u_top.{gen_rtl.sv_id(part)}.rst_n_t{i}")
            want.append(W["parts"][part]["release"])
    mx = W["max_release"]
    with tempfile.TemporaryDirectory() as d:
        files = [str(f) for f in gen_rtl.write_rtl(copy.deepcopy(raw), d, rtl_root=str(root))]
        tb = Path(d) / "tb.sv"
        chk = "\n".join(f"        if ({n} === 1'b1 && rel[{k}] < 0) rel[{k}] = cyc + 1;\n"
                        f"        if ({n} !== 1'b0 && cyc >= -19 && cyc < 0) bad = bad + 1;" for k, n in enumerate(nets))
        tb.write_text(f"""`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [31:0] din = 0;
    wire [31:0] dout;
    tiny_top u_top (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout));
    integer cyc = -{mx + 20}, bad = 0, k;
    integer rel [0:{len(nets) - 1}];
    initial for (k = 0; k < {len(nets)}; k = k + 1) rel[k] = -1;
    always @(posedge clk) begin
        #0.1;
{chk}
        if (cyc == -1) rst_n = 1;
        cyc = cyc + 1;
    end
    initial begin
        repeat ({2 * mx + 40}) @(posedge clk);
        for (k = 0; k < {len(nets)}; k = k + 1) $display("REL %0d %0d", k, rel[k]);
        $display("BAD %0d", bad);
        $finish;
    end
endmodule
""")
        exe = str(Path(d) / "a.out")
        src = files + [str(HERE / "examples" / "tiny_leaves.sv")]
        subprocess.run(["iverilog", "-g2012", "-o", exe, str(tb)] + src, check=True)
        out = subprocess.run(["vvp", "-n", exe], capture_output=True, text=True).stdout
        rel = [int(x) for x in re.findall(r"REL \d+ (-?\d+)", out)]
        assert rel == want, (rel, want, out[-2000:])
        assert "BAD 0" in out, out
        assert len(set(want)) > 1          # a wavefront: not every partition on one cycle
        if shutil.which("verilator"):
            r = subprocess.run(["verilator", "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED",
                                "-Wno-PINCONNECTEMPTY", "--top-module", "tiny_top"] + src,
                               capture_output=True, text=True)
            assert r.returncode == 0, r.stderr


def test_gen_phys_pins_lef_and_sdc_lint():
    import gen_phys
    import sdc_lint
    raw = wave(PAIR)
    P = schema.Plan(raw)
    for tn in RT.wf_plan(P)["types"]:
        outs = gen_phys.reset_out_pins(P, tn)
        io = gen_phys.io_tcl(P, tn, gen_phys.type_pins(P, tn))
        x, y = RT.in_pin(P, tn)
        assert re.search(rf"place_pin -pin_name arst_n -layer \w+ -location {{{x:.4f} {y:.4f}}}", io)
        for n, ox, oy in outs:
            assert f"place_pin -pin_name {n} " in io
        ctx = sdc_lint.kit_context(P, tn)
        assert all(n in ctx["outputs"] for n, _, _ in outs)
    with tempfile.TemporaryDirectory() as d:
        tn = next(t for t, ty in RT.wf_plan(P)["types"].items() if ty["outs"])
        kd = gen_phys.write_type_kit(P, tn, Path(d), [])
        tcl = (Path(kd) / "reset_tree.tcl").read_text()
        assert len(re.findall(r"^rtr_place ", tcl, re.M)) == len(RT.for_type(P, tn)["relays"]) + 1


def test_kit_rsync_adds_reset_outs_to_bound_and_wrapper():
    import kit_rsync
    raw = wave(PAIR)
    P = schema.Plan(raw)
    tn = next(t for t, ty in RT.wf_plan(P)["types"].items() if ty["outs"])
    outs = [n for n, _, _ in RT.out_pins(P, tn)]
    mod = P.types[tn]["module"]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "plan.json").write_text(json.dumps(raw))
        kd = d / "kit"
        kd.mkdir()
        w = kd / f"{mod}.sv"
        w.write_text(f"module {mod} (\n    input  wire clk,\n    input  wire arst_n,  // die reset\n    input  wire [3:0] x\n);\n"
                     f"    {mod}_bound u_bound (\n        .clk(clk),\n        .arst_n(arst_n),\n        .x(x)\n    );\n"
                     "endmodule\n")
        b = kd / f"{mod}_bound.sv"
        b.write_text(f"module {mod}_bound (\n    input  wire clk,\n    input  wire arst_n,\n    input  wire [3:0] x\n);\n"
                     "    wire rst_n;\n"
                     "    ot_reset_sync #(.ASYNC_STAGES(2)) u_rst_sync (.clk(clk), .async_rst_n(arst_n), .sync_rst_n(rst_n));\n"
                     "endmodule\n")
        c = kd / "bind_cells.sv"
        c.write_text("// cells\nmodule ot_dp_st #(parameter W = 1) (input wire clk);\nendmodule\n")
        (kd / "kit_rtl.json").write_text(json.dumps(dict(files=[str(w), str(b), str(c)], bound_module=f"{mod}_bound")))
        for _ in range(2):           # idempotent
            assert kit_rsync.main([str(d / "plan.json"), tn, str(kd)]) == 0
            vb, vw = b.read_text(), w.read_text()
            for n in outs:
                assert vb.count(f"output wire {n},") == 1 and vb.count(f"assign {n} = rst_n_t") == 1
                assert vw.count(f"output wire {n},") == 1 and vw.count(f".{n}({n}),") == 1
            man = json.loads((kd / "kit_rtl.json").read_text())
            assert man["kit_rsync"]["reset_outs"] == outs
        if shutil.which("iverilog"):
            cells = d / "cells.sv"
            import gen_rtl
            cells.write_text(gen_rtl.CELLS)
            r = subprocess.run(["iverilog", "-g2012", "-o", str(d / "x"), str(w), str(b), str(kd / "kit_cells.sv")],
                               capture_output=True, text=True)
            assert r.returncode == 0, r.stderr


def test_face_flops_leaves_reset_outs_to_reset_tree():
    """S81/KITS 10-24: face_flops.tcl placed the rst_o relay FIRM as an output pin register, then reset_tree.tcl moved
    it (ODB-0359 in GPL).  rst_o ports are skipped like arst_n; reset_tree.tcl places their relays."""
    ff = (HERE / "face_flops.tcl").read_text()
    m = re.search(r"set ff_skip_re \{(.*?)\}\s", ff)
    assert m and re.match(m.group(1), "rst_o_3") and re.match(m.group(1), "arst_n") and not re.match(m.group(1), "x_o")


def test_hard_core_reset_gets_equal_depth_local_relay_and_reach_gate():
    raw = wave(TINY)
    raw["partition_types"]["src"]["hard_cores"] = [dict(
        inst="u_core.g_h[0].u_hc", module="core", origin_um=[50, 50], outline_um=[200, 300],
        orient="MY", track_offset_um=[0.108, 0.012],
        pins=[dict(name="rst_n", layer="M4", xy=[0, 150])])]
    P = schema.Plan(raw)
    T = RT.for_type(P, "src")
    c, = T["core_resets"]
    assert c["pin_um"] == [250.108, 200.012]
    q = next(r for r in T["relays"] if r["q"] == f"rst_n_t{c['tap']}")
    assert q["depth"] == T["depth"] and RT.verify(T) == []
    assert RT._man(q["xy"], c["pin_um"]) <= RT.relay_um(P)
    assert RT._free(q["xy"], RT.blockages(P.types["src"]), (RT.CLEAR_UM, RT.CLEAR_UM, 859.68, 859.68))
    text = RT.tcl_text(T)
    assert "OT_RESET_CORE unresolved u_core.g_h[0].u_hc.rst_n" in text
    assert f"core:{c['tap']} rst_n_t{c['tap']}" in text
    offsets = RT.wf_plan(P)
    row = next(r for r in offsets["parts"].values() if r["type"] == "src")
    assert row["core_release"]["u_core.g_h[0].u_hc.rst_n"] == row["release"] + 1
    mutant = copy.deepcopy(T)
    next(r for r in mutant["relays"] if r["q"] == q["q"])["xy"] = [800, 800]
    assert any("hard-core reset" in e for e in RT.verify(mutant))


def test_core_reset_tcl_literal_hierarchy_with_brackets():
    # Tcl glob syntax must not interpret the generate-array brackets in a hard-core instance name.
    raw = wave(TINY)
    raw["partition_types"]["src"]["hard_cores"] = [dict(inst="u_hc[0]", origin_um=[50, 50],
        outline_um=[200, 300], pins=[dict(name="rst_n", layer="M4", xy=[0, 150])])]
    text = RT.tcl_text(RT.for_type(schema.Plan(raw), "src"))
    block = next(l for l in text.splitlines() if l.startswith("foreach i [$ff_blk getInsts]"))
    stub = """proc blk {method} {return {i1 i2 i3}}
proc i1 {method} {return {u_hc[0]}}
proc i2 {method} {return {u_bound/u_hc[0]}}
proc i3 {method} {return {u_hc0}}
set ff_blk blk
set rtr_ci {}
"""
    out = subprocess.run(["tclsh"], input=stub+block+'\nputs $rtr_ci\n', text=True, capture_output=True)
    assert out.returncode == 0 and not out.stderr
    assert out.stdout.strip() == "i1 i2"


def test_core_reset_rewire_refuses_a_private_pipeline_register():
    stub = '''
set rtr_terminal_qnets {terminal 1}
proc terminal {m} {if {$m eq "getName"} {return terminal}}
proc buffered {m} {if {$m eq "getName"} {return buffered}; return {bo}}
proc delayed {m} {if {$m eq "getName"} {return delayed}; return {fo}}
proc bo {m} {if {$m eq "getMTerm"} {return mout}; return buf}
proc fo {m} {if {$m eq "getMTerm"} {return mout}; return flop}
proc bi {m} {if {$m eq "getMTerm"} {return minput}; return terminal}
proc mout {m} {return OUTPUT}
proc minput {m} {return INPUT}
proc buf {m} {if {$m eq "getMaster"} {return mbuf};return {bo bi}}
proc flop {m} {if {$m eq "getMaster"} {return mflop};return {fo bi}}
proc mbuf {m} {return BUFx2_ASAP7_75t_R}
proc mflop {m} {return DFFHQNx1_ASAP7_75t_R}
'''
    script = stub + RT.CORE_RESET_EQ_TCL + '''
if {![rtr_reset_equiv buffered 0 {}]} {error "buffered same-depth reset refused"}
if {[rtr_reset_equiv delayed 0 {}]} {error "private reset pipeline bypassed"}
puts CORE_RESET_EQ_PASS
'''
    out = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert out.returncode == 0 and not out.stderr, out.stderr
    assert out.stdout.strip() == "CORE_RESET_EQ_PASS"
