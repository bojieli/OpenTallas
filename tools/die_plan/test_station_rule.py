"""LOCKUP-STATION-1130: station_rule.py (count / site / first rank / lockup) + kit_zl_lockup register form + the GEN hook
(plan clock.zl_lockup), with an iverilog lock-step bench: the latched circuit is cycle-identical to the original."""
import json
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import kit_zl_lockup as zl  # noqa: E402
import schema as S  # noqa: E402
import station_rule as SR  # noqa: E402


# ------------------------------------------------------------------ 1 COUNT
def test_count_from_length():
    n = lambda L: SR.stations_needed(L, reach_um=300)      # tools/conftest.py pins the suite default to 405
    assert n(0) == 1 and n(299.9) == 1 and n(300) == 1 and n(300.1) == 2 and n(900) == 3 and n(901) == 4
    assert SR.stations_needed(800, reach_um=405) == 2


# ------------------------------------------------------------------ 2 SITE / 3 FIRST
def test_each_bit_on_its_own_line():
    a = [(0.0, 100.0 + 2 * i) for i in range(8)]          # W face, 8 bits
    b = [(900.0, 400.0 + 2 * i) for i in range(8)]        # E face, shifted window
    k = SR.stations_needed(900 + 300, reach_um=300)
    st = SR.lane_sites(a, b, k, "W")
    assert k == 4 and len(st) == 3 and all(len(s) == 8 for s in st)
    for s in st:                                          # a stage is a line across the bus: distinct points, no bank
        assert len({p for p in s}) == 8
    for i in range(8):                                    # bit i stays on its own pin -> pin route, equal pitch
        legs = SR.hop_lengths([a[i]], [[s[i]] for s in st], [b[i]])
        assert max(legs) - min(legs) < 1e-6 and abs(sum(legs) - (900 + 300)) < 1e-6
    assert max(SR.hop_lengths(a, st, b)) <= 300 + 1e-6


def test_slot_row_counts_seats_and_lockups():
    t = {"outline_um": [1000.0, 400.0]}
    s = {"name": "ft3", "in_face": "W", "out_face": "E", "width": 3, "stations": 2,
         "in_window_um": [100, 110], "out_window_um": [100, 110]}
    taps = [("clk", 150.0, 100.0), ("clk_t1", 850.0, 100.0)]
    r = SR.slot_row("T", t, s, taps=taps, reach_um=300)
    assert (r["stations_have"], r["stations_need"], r["delta_cycles"]) == (2, 4, 2)
    assert r["first_rank"] == "pin" and r["regs_um"][0] == [0.0, 105.0]          # stage 0 at the in pin
    assert len(r["regs_um"]) == 4 and len(r["bit_sites_um"]) == 3 and r["worst_hop_um"] <= 300
    assert r["site_form"] == "line"
    assert r["lockup_hops"] == [2]                       # stages x 0/250/500/750: only 500 -> 750 changes tap
    one = SR.slot_row("T", t, s, taps=[("clk", 500.0, 200.0)], reach_um=300)
    assert one["lockup_hops"] == []                      # one tap: nothing to latch


def test_cross_tap_unknown_sites_is_cross():
    taps = [("a", 0.0, 0.0), ("b", 100.0, 0.0)]
    assert SR.cross_tap_hops([[(0, 0)], [], [(1, 0)]], taps) == [0, 1]
    assert SR.cross_tap_hops([[(0, 0)], [(2, 0)]], taps) == []


def test_apply_rows_plan_copy():
    raw = {"clock": {"ft_hop_lockup": {"types": ["U"]}, "tap_max_sinks": 1000},
           "partition_types": {"T": {"ft_slots": [{"name": "ft3", "stations": 4}]}}, "lanes": {"x": 1}}
    rows = [dict(type="T", slot="ft3", width=3, stations_have=4, stations_need=4, delta_cycles=0, lockup_hops=[2, 0],
                 regs_um=[[0, 1], [2, 3], [4, 5], [6, 7]], bit_sites_um=[[[1, 1]], [[2, 2]], [[3, 3]]])]
    spec = {"guard": None, "hops": [{"inst": "u_ist_\\d+", "types": ["ot_dp_st"], "ports": ["d", "ea"]}], "regs": []}
    new, rec = SR.apply_rows(raw, rows, {"T": spec})
    lk = new["clock"]["ft_hop_lockup"]
    assert lk["types"] == ["T", "U"] and lk["hops"] == {"T": {"ft3": [0, 2]}}
    assert new["clock"]["zl_lockup"]["T"] == spec and new["partition_types"] == raw["partition_types"]
    assert rec["latch_hops"] == 2 and raw["clock"]["ft_hop_lockup"] == {"types": ["U"]}
    new2, rec2 = SR.apply_rows(raw, rows, None, sites=True)
    s = new2["partition_types"]["T"]["ft_slots"][0]
    assert s["explicit_stage0"] and s["keep_firm"] and s["regs_um"][0] == [0, 1] and rec2["sited_slots"] == 1
    with pytest.raises(ValueError):
        SR.apply_rows({"clock": {"ft_hop_lockup": {"all": True}}}, rows)


def test_schema_accepts_zl_lockup():
    clk = S.SCHEMA["properties"]["clock"]["properties"]
    assert "zl_lockup" in clk
    import jsonschema
    jsonschema.validate({"T": {"guard": None, "hops": [{"inst": "u_x", "ports": ["d"]}], "regs": [{"reg": "g_q"}]}},
                        clk["zl_lockup"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"T": {"hops": [{"ports": ["d"]}]}}, clk["zl_lockup"])


def test_gen_hook_key():
    raw = {"clock": {"zl_lockup": {"ot_s81sl_leaf__t3": {"hops": []}, "ot_s81sl_leaf*": {"regs": []}}}}
    assert gen_phys.zl_lockup_spec(raw, "ot_s81sl_leaf__t3") == {"hops": []}
    assert gen_phys.zl_lockup_spec(raw, "ot_s81sl_leaf__t39") == {"regs": []}      # exact name only, then 'prefix*'
    assert gen_phys.zl_lockup_spec(raw, "col_h9_r1") is None and gen_phys.zl_lockup_spec({}, "x") is None


# ------------------------------------------------------------------ 4 LOCKUP: measured derive + register form
BOUND = """module top_bound (
    input  wire clk,
    input  wire rst_n,
    input  wire [3:0] x_i,
    output wire [3:0] y_o,
    output wire [3:0] z_o
);
    wire [3:0] s0_q, s1_q;
    wire s0_e, s1_e;
    reg [3:0] g_u_lf1_u_cst_gd_s_0_u_src_9471b6ecb0af15f07fde_q;
    reg [3:0] g_u_lf1_u_cst_gd_s_1_u_src_9471b6ecb0af15f07fde_q;
    reg [3:0] g_logic_q;
    reg [3:0] g_port_q;
    ot_dp_st #(.W(4)) u_ft_ft1_o_0 (.clk(clk), .rst_n(rst_n), .d(x_i), .ea(1'b0), .q(s0_q), .eq(s0_e));
    ot_dp_st #(.W(4)) u_ft_ft1_o_1 (.clk(clk), .rst_n(rst_n), .d(s0_q), .ea(s0_e), .q(s1_q), .eq(s1_e));
    always @(posedge clk) g_port_q <= x_i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_u_lf1_u_cst_gd_s_0_u_src_9471b6ecb0af15f07fde_q <= 4'b0; else g_u_lf1_u_cst_gd_s_0_u_src_9471b6ecb0af15f07fde_q <= s1_q;
    always @(posedge clk) g_u_lf1_u_cst_gd_s_1_u_src_9471b6ecb0af15f07fde_q <= g_u_lf1_u_cst_gd_s_0_u_src_9471b6ecb0af15f07fde_q[3:0];
    always @(posedge clk) g_logic_q <= s1_q ^ g_port_q;
    assign y_o = g_u_lf1_u_cst_gd_s_1_u_src_9471b6ecb0af15f07fde_q;
    assign z_o = g_logic_q;
endmodule
"""
ST = """module ot_dp_st #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d, input wire ea,
    output reg [W-1:0] q, output reg eq);
    always @(posedge clk or negedge rst_n) if (!rst_n) begin q <= 0; eq <= 0; end else begin q <= d; eq <= ea; end
endmodule
"""


def test_register_form_latches_zero_logic_only():
    spec = {"guard": None, "regs": [{"reg": r"g_\w+_q"}]}
    txt, lat, sk = zl.apply(BOUND, spec)
    by = {l["capture"]: l for l in lat}
    s0 = "g_u_lf1_u_cst_gd_s_0_u_src_9471b6ecb0af15f07fde_q"
    s1 = "g_u_lf1_u_cst_gd_s_1_u_src_9471b6ecb0af15f07fde_q"
    assert set(by) == {s0, s1} and by[s0]["src"] == "s1_q" and by[s1]["width"] == 4 and by[s0]["clk"] == "clk"
    assert sk["logic"] == 1 and sk["port"] == 1               # g_logic_q (xor), g_port_q (module input)
    assert f"{s0} <= 4'b0; else {s0} <= fl_{s0};" in txt       # reset branch untouched, data branch latched
    assert "`ifdef" not in txt and f"ot_dp_lk #(.W(4)) u_fl_{s1} (.clk(clk), .d({s0}[3:0]), .q(fl_{s1}));" in txt


def test_apply_kit_adds_module_and_fails_closed(tmp_path):
    (tmp_path / "top_bound.sv").write_text(BOUND)
    (tmp_path / "ot_dp_st.sv").write_text(ST)
    spec = {"guard": None, "hops": [{"inst": r"u_ft_ft\d+_o_\d+", "types": ["ot_dp_st"], "ports": ["d", "ea"]}],
            "regs": [{"reg": r"g_u_lf\d+_u_cst_gd_s_\d+_u_src_[0-9a-f]+_q"}]}
    rec = zl.apply_kit(tmp_path, spec)
    assert rec["top_bound.sv"]["latches"] == 3 and rec["top_bound.sv"]["ot_dp_lk_module"]
    out = (tmp_path / "top_bound.sv").read_text()
    assert out.count("module ot_dp_lk") == 1 and "u_fl_ft_ft1_o_1" in out and "u_fl_ft_ft1_o_0" not in out
    assert (tmp_path / "ot_dp_st.sv").read_text() == ST
    with pytest.raises(zl.LkError):
        zl.apply_kit(tmp_path, {"guard": None, "regs": [{"reg": "nothing_q"}]})


def test_derive_spec_from_pairs(tmp_path):
    (tmp_path / "top_bound.sv").write_text(BOUND)
    s0 = "g_u_lf1_u_cst_gd_s_0_u_src_9471b6ecb0af15f07fde_q"
    pairs = [("u_bound.u_ft_ft1_o_0/q[0]$_DFF_P_", "u_bound.u_ft_ft1_o_1/q[0]$_DFF_P_", "clk", "clk_t1", 250.0, "DFF", "DFF"),
             ("u_bound.u_ft_ft1_o_1/q[1]$_DFF_P_", f"u_bound.{s0}[1]$_DFF_PN0_", "clk_t1", "clk_t2", 120.0, "DFF", "DFF"),
             ("u_bound.x/q$_DFF_P_", "u_bound.g_logic_q[0]$_DFF_P_", "clk", "clk", 10.0, "DFF", "DFF"),
             ("u_bound.x/q$_DFF_P_", "u_other.unknown_q[0]$_DFF_P_", "clk", "clk_t3", 10.0, "DFF", "DFF")]
    tsv = tmp_path / "p.tsv"
    tsv.write_text("".join("\t".join(map(str, r)) + "\n" for r in pairs))
    spec, rec = SR.derive_spec(SR.read_pairs(tsv), tmp_path, "top")
    assert spec["guard"] is None and [h["types"] for h in spec["hops"]] == [["ot_dp_st"]]
    assert spec["hops"][0]["ports"] == ["d", "ea"] and re.fullmatch(spec["hops"][0]["inst"], "u_ft_ft7_o_12")
    # flat registers go to the post-synth netlist form (generate-block registers need no RTL parser)
    assert len(spec["netlist"]) == 2
    assert re.fullmatch(spec["netlist"][0], "u_bound.g_u_lf2_u_cst_gd_s_3_u_src_0123456789abcdef01_q[7]$_DFF_PN0_")
    assert rec["cross_tap"] == 3 and rec["cross_tap_covered"] == 3
    ends = tmp_path / "ends.tsv"
    ends.write_text("slack\tclass\tstart\tend\n-50\tcross_tap\ta\tu_bound.u_ft_ft1_o_4/q[2]$_DFF_P_/D\n"
                    "-40\tport_in\tp\tu_bound.x/q$_DFF_P_/D\n-30\tsame_tap\ta\tu_bound.zz_q[1]$_DFF_P_/D\n")
    _s, rec = SR.derive_spec(SR.read_pairs(tsv), tmp_path, "top", hold_ends=SR.read_hold_ends(ends))
    assert rec["hold_ends"]["total"] == 3 and rec["hold_ends"]["covered"] == 1 and rec["hold_ends"]["by"]["port_in"] == 1
    assert SR._cell_obj("u_lpad_leafdn_i3.q[4]$_DFF_P_") == ("u_lpad_leafdn_i3", "q")


# ------------------------------------------------------------------ iverilog: latched == original, cycle for cycle
TB = """module tb;
    reg clk = 0, rst_n = 0; reg [3:0] x = 0;
    wire [3:0] ya, za, yb, zb;
    top_a a (.clk(clk), .rst_n(rst_n), .x_i(x), .y_o(ya), .z_o(za));
    top_b b (.clk(clk), .rst_n(rst_n), .x_i(x), .y_o(yb), .z_o(zb));
    integer i, bad = 0;
    always #5 clk = ~clk;
    initial begin
        #12 rst_n = 1;
        for (i = 0; i < 200; i = i + 1) begin
            @(negedge clk); x = $random;
            @(posedge clk); #1 if (ya !== yb || za !== zb) bad = bad + 1;
        end
        if (bad == 0) $display("LOCKSTEP_PASS"); else $display("LOCKSTEP_FAIL %0d", bad);
        $finish;
    end
endmodule
"""


@pytest.mark.skipif(not shutil.which("iverilog"), reason="no iverilog")
@pytest.mark.parametrize("mutant", [False, True])
def test_lockstep_bench(tmp_path, mutant):
    spec = {"guard": None, "hops": [{"inst": r"u_ft_ft\d+_o_\d+", "types": ["ot_dp_st"], "ports": ["d", "ea"]}],
            "regs": [{"reg": r"g_\w+_q"}]}
    b, lat, _ = zl.apply(BOUND, spec)
    assert len(lat) == 3
    lk = zl.LK_MODULE.replace("(* keep_hierarchy, keep *)", "")
    if mutant:                                            # a latch built as one more flop adds a cycle: caught
        lk = lk.replace("always @(*) if (!clk) q = d;", "always @(posedge clk) q <= d;")
    src = tmp_path / "all.v"
    src.write_text(ST + lk + BOUND.replace("module top_bound", "module top_a")
                   + b.replace("module top_bound", "module top_b") + TB)
    r = subprocess.run(["iverilog", "-g2012", "-o", str(tmp_path / "a.out"), str(src)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    o = subprocess.run(["vvp", str(tmp_path / "a.out")], capture_output=True, text=True).stdout
    assert ("LOCKSTEP_FAIL" in o) if mutant else ("LOCKSTEP_PASS" in o), o


SUB = """module ot_ctl (input wire clk, input wire [3:0] d_i, output reg [3:0] d_o);
    always @(posedge clk) d_o <= d_i;
endmodule
module ot_other (input wire clk, input wire [3:0] d_i, output reg [3:0] d_o);
    always @(posedge clk) d_o <= d_i;
endmodule
module top2 (input wire clk, input wire [3:0] x_i, output wire [3:0] y_o);
    wire [3:0] a;
    reg [3:0] r0;
    always @(posedge clk) r0 <= x_i;
    ot_ctl u_ctl (.clk(clk), .d_i(r0), .d_o(a));
`ifdef SLOW
    ot_other u_m(.clk(clk),
`else
    ot_other u_m(.clk(clk),
`endif
        .d_i(a), .d_o(y_o));
endmodule
"""


def test_module_scoped_register_and_ifdef_headers(tmp_path):
    (tmp_path / "lep.sv").write_text(SUB)
    pairs = [("u_core.r0[0]$_DFF_P_", "u_core.u_ctl/d_o[1]$_DFF_P_", "clk", "clk_t1", 90.0, "DFF", "DFF")]
    tsv = tmp_path / "p.tsv"
    tsv.write_text("".join("\t".join(map(str, r)) + "\n" for r in pairs))
    spec, rec = SR.derive_spec(SR.read_pairs(tsv), tmp_path, "top2")
    assert spec["netlist"] == [SR.generalize("u_core.u_ctl/d_o[1]$_DFF_P_")] and rec["cross_tap_covered"] == 1
    out = zl.apply_kit(tmp_path, {"guard": None, "regs": [{"reg": "d_o", "module": "ot_ctl", "allow_missing": True}]})
    txt = (tmp_path / "lep.sv").read_text()
    ctl, other = txt.split("module ot_other")
    assert "u_fl_d_o" in ctl and "u_fl_d_o" not in other and out["lep.sv"]["latches"] == 1
    assert txt.count("module ot_dp_lk") == 1


def test_parameter_width_register():
    src = """module ot_st #(parameter integer W = 552) (input wire clk, input wire [W-1:0] d_i, output reg [W-1:0] d_o);
    always @(posedge clk) d_o <= d_i;
endmodule
"""
    txt, lat, sk = zl.apply(src, {"guard": None, "regs": [{"reg": "d_o", "module": "ot_st"}]})
    assert len(lat) == 1 and lat[0]["width"] == "((W-1)-(0)+1)"
    assert "wire [((W-1)-(0)+1)-1:0] fl_d_o;" in txt and "ot_dp_lk #(.W(((W-1)-(0)+1))) u_fl_d_o (.clk(clk), .d(d_i), .q(fl_d_o));" in txt


def test_reset_cells_skipped_and_sram_wrappers_tap_grouped(tmp_path):
    (tmp_path / "top_bound.sv").write_text(BOUND)
    pairs = [("u_bound.x/q$_DFF_P_", "u_bound.u_rrl_3/q[0]$_DFF_P_", "clk", "clk_t1", 10.0, "DFF", "DFF"),
             ("u_bound.x/q$_DFF_P_", "u_bound.u_lf.u_sram_w2/wreg[4]$_DFF_P_", "clk", "clk_t1", 10.0, "DFF", "DFF")]
    tsv = tmp_path / "p.tsv"
    tsv.write_text("".join("\t".join(map(str, r)) + "\n" for r in pairs))
    spec, rec = SR.derive_spec(SR.read_pairs(tsv), tmp_path, "top")
    assert spec["netlist"] == [] and spec["hops"] == [] and rec["cross_tap_covered"] == 0
    assert rec["cross_tap_tap_group"] == 1 and re.match(rec["tap_group"]["re"], "u_bound.u_lf.u_sram_w7/wreg[1]")


def test_zl_netlist_hook(tmp_path):
    import gen_phys
    (tmp_path / "face_keep_release.tcl").write_text("puts x\n")
    assert not gen_phys.zl_netlist_files(tmp_path, {"hops": []}) and not gen_phys.zl_netlist_hook(tmp_path)
    assert (tmp_path / "face_keep_release.tcl").read_text() == "puts x\n"
    assert gen_phys.zl_netlist_files(tmp_path, {"netlist": [r"u_a\.q\d+"]}) and gen_phys.zl_netlist_hook(tmp_path)
    assert (tmp_path / "zl_netlist_lockup.tcl").exists() and "zl_netlist_lockup" in (tmp_path / "face_keep_release.tcl").read_text()
    assert not gen_phys.zl_netlist_hook(tmp_path)


def test_ends_only_latches_the_violating_cross_tap_ends(tmp_path):
    (tmp_path / "top_bound.sv").write_text(BOUND)
    s0 = "g_u_lf1_u_cst_gd_s_0_u_src_9471b6ecb0af15f07fde_q"
    pairs = [("u_bound.a/q$_DFF_P_", f"u_bound.{s0}[1]$_DFF_PN0_", "clk_t1", "clk_t2", 120.0, "DFF", "DFF"),
             ("u_bound.a/q$_DFF_P_", f"u_bound.{s0}[2]$_DFF_PN0_", "clk_t1", "clk_t2", 120.0, "DFF", "DFF"),
             ("u_bound.a/q$_DFF_P_", f"u_bound.{s0}[3]$_DFF_PN0_", "clk_t1", "clk_t1", 120.0, "DFF", "DFF")]
    tsv = tmp_path / "p.tsv"
    tsv.write_text("".join("\t".join(map(str, r)) + "\n" for r in pairs))
    ends = tmp_path / "ends.tsv"
    ends.write_text("slack\tclass\tstart\tend\n"
                    f"-50\tcross_tap\ta\tu_bound.{s0}[1]$_DFF_PN0_/D\n"      # violating, cross-tap pair: latched
                    f"3\tcross_tap\ta\tu_bound.{s0}[2]$_DFF_PN0_/D\n"        # meets hold: not latched
                    f"-9\tsame_tap\ta\tu_bound.{s0}[3]$_DFF_PN0_/D\n")       # same tap: not latched
    with pytest.raises(ValueError):
        SR.derive_spec(SR.read_pairs(tsv), tmp_path, "top", ends_only=True)
    spec, rec = SR.derive_spec(SR.read_pairs(tsv), tmp_path, "top", hold_ends=SR.read_hold_ends(ends), ends_only=True)
    assert spec["hops"] == [] and spec["netlist"] == [f"=u_bound.{s0}[1]$_DFF_PN0_"]
    assert rec["ends_only"] == {"violating_cross_tap": 1, "latched": 1}


def test_hop_latch_leaf_lines_and_hooks(tmp_path):
    import gen_phys
    assert gen_phys.hop_latch_leaf_lines(tmp_path, None) == [] and not (tmp_path / "hop_latch_leaf.tcl").exists()
    assert gen_phys.hop_latch_leaf_lines(tmp_path, {"netlist": ["=x"], "leaf": False}) == []
    assert gen_phys.hop_latch_leaf_lines(tmp_path, {"netlist": ["=x"]})[-1] == "export OT_HOP_LATCH_LEAF = 1"
    assert (tmp_path / "hop_latch_leaf.tcl").exists()
    here = Path(__file__).resolve().parent
    ct = (here / "clock_taps.tcl").read_text()
    assert "OT_HOP_LATCH_LEAF" in ct and "/work/hop_latch_leaf.tsv" in ct and "$ct_cit disconnect; incr ct_hl; continue" in ct
    cp = (here / "cts_post.tcl").read_text()
    assert cp.index("hop_latch_leaf cts") < cp.index("source [file join $cp_dir subtree_balance.tcl]") and "hop_latch_leaf after_leaf_affinity" in cp
    zn = (here / "zl_netlist_lockup.tcl").read_text()
    assert "dict set zn_exact" in zn and "^(DFFH|ASYNC_DFFH)" in zn


def test_seam_port_latch_text_and_lockstep(tmp_path):
    src = '''module top (
    input  wire clk,
    input  wire [3:0] a,
    output reg  [3:0] y,
    output wire z
);
    always @(posedge clk) y <= a;
    assign z = y[0];
endmodule
'''
    txt, lat, sk = zl.apply_ports(src, "top", ["y", "nope"])
    assert [l["port"] for l in lat] == ["y"] and sk == {"not_an_ansi_output": 1}
    assert "output wire [3:0] y" in txt and "reg [3:0] y__fl;" in txt and "y__fl <= a" in txt and "assign z = y__fl[0]" in txt
    assert "ot_dp_lk #(.W(4)) u_fl_po_y (.clk(clk), .d(y__fl), .q(y));" in txt
    assert zl.apply_ports(txt, "top", ["y"])[1] == []          # idempotent
    if not shutil.which("iverilog"):
        pytest.skip("iverilog")
    (tmp_path / "a.v").write_text(src.replace("module top", "module top_o") + txt.replace("module top", "module top_l") + zl.LK_MODULE)
    (tmp_path / "tb.v").write_text('''module tb; reg clk = 0; reg [3:0] a = 0; wire [3:0] yo, yl; wire zo, zl; integer i, bad = 0;
  top_o o(.clk(clk), .a(a), .y(yo), .z(zo)); top_l l(.clk(clk), .a(a), .y(yl), .z(zl));
  initial begin for (i = 0; i < 40; i = i + 1) begin #5 clk = 1; #1 a = $random; #4 clk = 0; end
    if (bad) $display("BAD %0d", bad); else $display("OK"); $finish; end
  always @(posedge clk) if (yo !== yl || zo !== zl) bad = bad + 1;
endmodule
''')
    r = subprocess.run(["iverilog", "-o", str(tmp_path / "s"), str(tmp_path / "a.v"), str(tmp_path / "tb.v")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "OK" in subprocess.run(["vvp", str(tmp_path / "s")], capture_output=True, text=True).stdout


def test_apply_seams_and_leaf_for_ft_lockup_types(tmp_path):
    import gen_phys
    raw = {"clock": {}, "partition_types": {"tA": {}, "tB": {}}, "die": {"x": 1}}
    new, rec = SR.apply_rows(raw, [], seams={"tA": {"ports": ["o1", "o0"]}, "tB": {"ports": []}, "tZ": {"ports": ["q"]}})
    assert new["clock"]["zl_lockup"] == {"tA": {"guard": None, "note": "LOCKUP-STATION-1130 station_rule.apply --seams",
                                                "ports": ["o0", "o1"]}}
    assert rec["seam_types"] == 1 and rec["seam_ports"] == 2 and raw["clock"] == {}
    assert gen_phys.hop_latch_leaf_lines(tmp_path, None, ft=True)[-1] == "export OT_HOP_LATCH_LEAF = 1"
