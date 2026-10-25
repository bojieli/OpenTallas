"""OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): one root synchroniser per die region, synchronous relays every
<= 405 um, equal depth to every tap.   python3 -m pytest -q tools/die_plan/test_reset_tree.py"""
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


def piped(raw, **kw):
    raw = copy.deepcopy(raw)
    raw.setdefault("reset", {}).update(release="pipelined", **kw)
    assert schema.validate(raw) == []
    return raw


def _hops_ok(T, reach=405.0):
    xy = {r["q"]: r["xy"] for r in T["relays"]}
    root_net = next(r["d"] for r in T["relays"] if r["d"].endswith("rst_root_n"))
    xy[root_net] = T["root"]
    return max(RT._man(xy[r["d"]], r["xy"]) for r in T["relays"]) <= reach


def test_build_equal_depth_reach_and_shared_pads():
    taps = [(f"t{i}", 200.0 + 400.0 * (i % 5), 200.0 + 400.0 * (i // 5)) for i in range(25)]
    T = RT.build(taps, (10.0, 10.0))
    assert RT.verify(T) == [] and _hops_ok(T)
    assert T["depth"] == T["own_depth"] and T["max_hop_um"] <= 405.0 - RT.MARGIN_UM + 1e-6
    # padded to a deeper contract: every tap still at exactly that depth, pads shared high in the tree
    T2 = RT.build(taps, (10.0, 10.0), depth=T["depth"] + 4)
    assert RT.verify(T2) == [] and T2["depth"] == T["depth"] + 4
    per_leaf = sum(T2["depth"] - d for d in T2["tap_depth"].values())
    assert T2["n_pad"] < per_leaf


def test_build_routes_relays_around_a_macro():
    """a 900 um macro on the straight line: no relay inside it, every hop <= 405 um (grid fallback)."""
    boxes = [(150.0, -10.0, 1050.0, 900.0)]
    taps = [("a", 50.0, 400.0), ("b", 1150.0, 400.0)]
    T = RT.build(taps, (50.0, 380.0), boxes=boxes, box_out=(0.0, 0.0, 1200.0, 1000.0))
    assert RT.verify(T) == [] and _hops_ok(T)
    for r in T["relays"]:
        x, y = r["xy"]
        assert not (150.0 < x < 1050.0 and -10.0 < y < 900.0), r
    assert T["topology"] == "grid"


def test_build_routes_hops_around_a_wall():
    """CLOCK-RESET 10-25 (S81 col_h9_r1 u_rrl_73 -> 74, TT -247.6 in the PROTO probe): a core closed through the top
    signal layer (a WALL) on the straight root -> tap line.  Without walls the planned hop crosses it (the kit then
    detours ~2x); with walls every hop has a wall-free L route, at the same reach."""
    wall = (100.0, 150.0, 500.0, 300.0)
    boxes = [(wall[0] - RT.CLEAR_UM, wall[1] - RT.CLEAR_UM, wall[2] + RT.CLEAR_UM, wall[3] + RT.CLEAR_UM)]
    taps = [("a", 300.0, 340.0)]
    box_out = (0.0, 0.0, 700.0, 500.0)
    T0 = RT.build(taps, (300.0, 50.0), boxes=boxes, box_out=box_out)
    xy0 = dict({r["q"]: r["xy"] for r in T0["relays"]}, **{"rst_root_n": T0["root"]})
    assert any(not RT._lfree(xy0[r["d"]], r["xy"], [wall]) for r in T0["relays"])     # the old plan crosses the wall
    T = RT.build(taps, (300.0, 50.0), boxes=boxes, box_out=box_out, walls=[wall])
    assert RT.verify(T) == [] and _hops_ok(T) and T["topology"] == "grid"
    xy = dict({r["q"]: r["xy"] for r in T["relays"]}, **{"rst_root_n": T["root"]})
    assert all(RT._lfree(xy[r["d"]], r["xy"], [wall]) for r in T["relays"])
    # a wall with no way around inside the outline fails closed
    try:
        RT.build(taps, (300.0, 50.0), boxes=[(-5.0, 145.0, 705.0, 305.0)], box_out=box_out,
                 walls=[(-10.0, 150.0, 710.0, 300.0)])
    except RT.ResetError:
        pass
    else:
        raise AssertionError("walled hop accepted")


def test_plan_trees_and_g0():
    P = schema.Plan(piped(PAIR))
    K = RT.part_depth(P)
    for tn in P.types:
        T = RT.for_type(P, tn)
        assert T["entry"] == "relayed" and T["depth"] == K and RT.verify(T) == []
        assert RT.release_clocks(T) == 1 + K
    e, w, info = RT.check(P)
    assert e == [] and len(w) == 1 and "DECISION 13" in w[0] and info["part_depth_K"] == K   # superseded mode
    r = info["regions"][0]
    assert r["members"] == 2 and r["release_clocks"] == 2 + r["die_depth_E"] + 1 + K
    # a counted plan is flagged (warning) but not failed
    e, w, info = RT.check(schema.Plan(copy.deepcopy(PAIR)))
    assert e == [] and len(w) == 1 and "OWNER RESET RULE" in w[0]
    # an impossible contract is an error
    e, _, _ = RT.check(schema.Plan(piped(PAIR, part_depth=1)))
    assert e and "part_depth" in e[0]


def test_g0_check_reports_reset_rule():
    import check
    R, summ = check.run(piped(TINY))
    assert not [i for i in R.errors() if i["check"] == "reset"]
    assert summ["reset"]["release"] == "pipelined" and summ["reset"]["part_depth_K"] >= 1
    R, summ = check.run(copy.deepcopy(TINY))
    assert any(i["check"] == "reset" for i in R.items) and not [i for i in R.errors() if i["check"] == "reset"]


def test_gen_rtl_pipelined_partition_and_die_top():
    import gen_rtl
    raw = piped(PAIR)
    P = schema.Plan(raw)
    with tempfile.TemporaryDirectory() as d:
        gen_rtl.write_rtl(copy.deepcopy(raw), d)
        v = (Path(d) / f"{P.types['fa']['module']}.sv").read_text()
        assert "ot_dp_rsync" not in v and "u_rst_sync" not in v and "u_rst_root" not in v
        assert "ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));" in v
        n = len(schema.tap_grid(P, "fa"))
        assert all(re.search(rf"\.q\(rst_n_t{i}\)\);", v) for i in range(n))
        assert f"wire rst_n = rst_n_t{RT.leaf_tap(P, 'fa')};" in v
        top = (Path(d) / f"{P.name}_top.sv").read_text()
        assert top.count("ot_dp_rsync_s2 die0_u_rst_root (.clk(clk), .async_rst_n(rst_n)") == 1
        assert re.search(r"\.arst_n\(die0_rst_n_t\d+\)", top) and ".arst_n(rst_n)" not in top
        cells = Path(d) / "ot_dp_cells.sv"
        if shutil.which("yosys"):
            t = Path(d) / "t.sv"
            t.write_text("module t(input wire clk, input wire a, output wire y0, output wire y1);\n"
                         "  ot_dp_rrelay u0(.clk(clk), .d(a), .q(y0));\n"
                         "  ot_dp_rrelay u1(.clk(clk), .d(a), .q(y1));\nendmodule\n")
            r = subprocess.run(["yosys", "-p", f"read_verilog -sv {cells} {t}; synth -top t; stat"],
                               capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            assert re.search(r"(?m)^\s*(?:ot_dp_rrelay\s+2|2\s+ot_dp_rrelay)\s*$", r.stdout), r.stdout        # identical relays are NOT merged


def test_tiny_die_releases_every_tap_on_one_cycle():
    """simulate the generated tiny die: every tap of every partition releases on cycle N + E + 1 + K after rst_n, and
    asserts (synchronously) by the same depth."""
    import gen_rtl
    if not shutil.which("iverilog"):
        return
    root = HERE.parent.parent
    raw = piped(TINY)
    P = schema.Plan(raw)
    info = RT.die_summary(P)
    want = info["regions"][0]["release_clocks"]
    nets = []
    for part, p in P.parts.items():
        for i in range(len(schema.tap_grid(P, p["type"]))):
            nets.append(f"u_top.{gen_rtl.sv_id(part)}.rst_n_t{i}")
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
    integer cyc = -{want + 20}, bad = 0, k;
    integer rel [0:{len(nets) - 1}];
    initial for (k = 0; k < {len(nets)}; k = k + 1) rel[k] = -1;
    always @(posedge clk) begin
        #0.1;
{chk}
        if (cyc == -1) rst_n = 1;
        cyc = cyc + 1;
    end
    initial begin
        repeat ({2 * want + 40}) @(posedge clk);
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
        assert len(rel) == len(nets) and set(rel) == {want}, out
        assert "BAD 0" in out, out
        if shutil.which("verilator"):
            r = subprocess.run(["verilator", "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED",
                                "--top-module", "tiny_top"] + src, capture_output=True, text=True)
            assert r.returncode == 0, r.stderr


def test_kit_rsync_converts_bound_and_old_kits():
    import kit_rsync
    raw = piped(PAIR)
    P = schema.Plan(raw)
    n = len(schema.tap_grid(P, "fa"))
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "plan.json").write_text(json.dumps(raw))
        kd = d / "kit"
        kd.mkdir()
        mod = P.types["fa"]["module"]
        b = kd / f"{mod}.sv"
        b.write_text(f"module {mod} (input wire clk, input wire arst_n, input wire [3:0] x, output wire [3:0] y);\n"
                     "    wire rst_n;\n"
                     "    ot_reset_sync #(.ASYNC_STAGES(2)) u_rst_sync (.clk(clk), .async_rst_n(arst_n), .sync_rst_n(rst_n));\n"
                     "    ot_dp_st #(.W(4)) u_bin_x (.clk(clk), .rst_n(rst_n), .d(x), .ea(rst_n), .q(y), .eq());\n"
                     "endmodule\n")
        c = kd / "bind_cells.sv"
        c.write_text("// cells\nmodule ot_dp_st #(parameter W = 1) (input wire clk);\nendmodule\n"
                     "module other_cell (input wire a);\nendmodule\n")
        (kd / "kit_rtl.json").write_text(json.dumps(dict(files=[str(b), str(c)], bound_module=mod)))
        for _ in range(2):          # the second run re-plans an already converted kit (idempotent)
            assert kit_rsync.main([str(d / "plan.json"), "fa", str(kd)]) == 0
            v = b.read_text()
            assert "u_rst_sync" not in v and v.count("ot_dp_rrelay u_rst_in ") == 1
            assert all(f"wire rst_n_t{i};" in v for i in range(n)) and v.count("wire rst_n_t0;") == 1
            assert re.search(r"ot_dp_ste #\(\.W\(4\)\) u_bin_x \(\.clk\(clk\), \.rst_n\(rst_n_t\d+\)", v)
            man = json.loads((kd / "kit_rtl.json").read_text())
            assert man["kit_rsync"]["reset_tree"]["entry"] == "relayed"
            assert man["kit_rsync"]["reset_tree"]["depth"] == RT.part_depth(P)
            tcl = (kd / "reset_tree.tcl").read_text()
            assert "rtr_place rst_root_n {*u_rst_in[./]*}" in tcl and len(re.findall(r"^rtr_place ", tcl, re.M)) >= n + 1
            assert "ot_dp_rrelay" in (kd / "kit_cells.sv").read_text()
        # an older per-tap kit_rsync kit converts too; a counted plan gives the interim per-partition root
        (d / "c.json").write_text(json.dumps(PAIR))
        b.write_text(f"module {mod} (input wire clk, input wire arst_n);\n    wire rst_n;\n" +
                     "".join(f"    wire rst_n_t{i};\n    ot_dp_rsync_s2 u_rsync_t{i} (.clk(clk), .async_rst_n(arst_n), "
                             f".sync_rst_n(rst_n_t{i}));  // kit_rsync: tap clk\n" for i in range(n)) +
                     "    assign rst_n = rst_n_t0;\nendmodule\n")
        (kd / "kit_rtl.json").write_text(json.dumps(dict(files=[str(b), str(c)], bound_module=mod)))
        assert kit_rsync.main([str(d / "c.json"), "fa", str(kd)]) == 0
        v = b.read_text()
        assert "u_rsync_t" not in v and v.count("ot_dp_rsync_s2 u_rst_root (.clk(clk), .async_rst_n(arst_n)") == 1
        assert json.loads((kd / "kit_rtl.json").read_text())["kit_rsync"]["converted_from"] == "per-tap"


def test_gen_phys_kit_gets_reset_tree_tcl():
    import gen_phys
    raw = piped(PAIR)
    P = schema.Plan(raw)
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(P, "fa", Path(d), [])
        tcl = (Path(kd) / "reset_tree.tcl").read_text()
        T = RT.for_type(P, "fa")
        assert len(re.findall(r"^rtr_place ", tcl, re.M)) == len(T["relays"]) + 1 and "OT_RESET_TREE entry relayed" in tcl
    ff = (HERE / "face_flops.tcl").read_text()
    assert ff.index("source /work/reset_tree.tcl") < ff.index("source /work/reset_taps.tcl")


def test_interior_pins_clear_kit_pdn_m7_straps():
    """S81-HEAD 10-25: hd_st_m rst_o_1 (1434.272) shorted the kit M7 VDD strap; interior pins clear the strap pair."""
    import gen_phys as G
    import schema as S
    raw = json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())
    P = S.Plan(raw)
    for v in (8.304, 8.608, 8.976, 1434.272, 17.312, 812.0):
        c, y = G._snap_tap(P, v, 153.376)
        ph = (c - 8.304) % 8.64
        assert 0.672 + 0.116 <= ph + 1e-9 <= 8.64 - 0.116 + 1e-9, (v, c, ph)
        assert abs(c - v) < 1.0
        assert G._snap_tap(P, c, y) == (c, y)
