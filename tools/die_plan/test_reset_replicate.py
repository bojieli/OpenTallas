"""S81-COLGEN-1 11-14: reset_replicate (FABLE-TYPES-S81-COL C2) -- region copies of a reset / flush driver, equal latency."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import reset_replicate as RR
import schema
from test_bind_wavefront import emitter, plan

CELLS = """module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1]; integer i;
    always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    assign q = r[D-1];
endmodule
module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
module core (input wire clk, input wire rs, output reg o);
    always @(posedge clk) o <= rs;
endmodule
"""


def mod(depth, extra_assign=True):
    return f"""module top (input wire clk, input wire s, output wire [5:0] o);
    wire [0:0] w_6_Y;
    wire [0:0] d{depth}_6_Y;
    wire [0:0] w_14_Y;
    assign w_6_Y = s;
    ot_dp_dly #(.W(1), .D({depth})) u_d{depth}_6_Y (.clk(clk), .d(w_6_Y), .q(d{depth}_6_Y));
{"    assign w_14_Y = d%d_6_Y[0];" % depth if extra_assign else "    assign w_14_Y = 1'b0;"}
    // as-built u_bn10
    core u_u_bn10 (
        .clk(clk),
        .rs(d{depth}_6_Y[0]),
        .o(o[0])
    );
    core u_u_bn11 (
        .clk(clk),
        .rs(d{depth}_6_Y[0]),
        .o(o[1])
    );
    core u_u_y_rt_24a_0 (
        .clk(clk),
        .rs(d{depth}_6_Y[0]),
        .o(o[2])
    );
    core u_u_y_rt_24a_1 (
        .clk(clk),
        .rs(d{depth}_6_Y[0]),
        .o(o[3])
    );
    core u_u_y_rt_24b_0 (
        .clk(clk),
        .rs(w_14_Y[0]),
        .o(o[4])
    );
    assign o[5] = w_14_Y[0];
endmodule
"""


SPEC = [dict(driver="u_d7_6_Y")]


def test_regions_and_equal_depth_text():
    new, rep = RR.apply(mod(7), SPEC)
    r = rep[0]
    assert r["depth"] == 7 and r["common_depth"] == 6 and r["copy_depth"] == 1
    # bn10, bn11, y_rt_24a (2 legs share), y_rt_24b (through assign w_14_Y), rest (w_14_Y also feeds an output port)
    assert r["regions"] == 5 and r["loads"] == 5
    assert r["loads_per_region"]["u_u_y_rt_24a"] == 2 and r["loads_per_region"]["u_u_y_rt_24b"] == 1
    assert ".D(6)) u_d7_6_Y" in new and new.count("ot_dp_rrelay u_d7_6_Y_r") == 5
    assert "d7_6_Y[0]" in new                # only the common wire feeding the copies is left on the old name
    assert len(re.findall(r"\.rs\(d7_6_Y_r\d\[0\]\)", new)) == 4


def test_depth_one_replaces_driver():
    new, rep = RR.apply(mod(7).replace("7", "1"), [dict(driver="u_d1_6_Y")])
    assert rep[0]["common_depth"] == 0
    assert "ot_dp_dly" not in new and new.count("ot_dp_rrelay u_d1_6_Y_r") == 5
    assert "(.clk(clk), .d(w_6_Y), .q(" in new


def test_single_region_unchanged():
    txt = mod(7)
    one = re.sub(r"    core u_u_bn11 \(.*?\n    \);\n", "", txt, flags=re.S)
    one = re.sub(r"    core u_u_y_rt_24a_\d \(.*?\n    \);\n", "", one, flags=re.S).replace("assign w_14_Y = d7_6_Y[0];", "assign w_14_Y = 1'b0;")
    new, rep = RR.apply(one, SPEC)
    assert new == one and rep[0]["copies"] == 0


def test_errors():
    with pytest.raises(RR.ReplicateError, match="no ot_dp_dly"):
        RR.apply(mod(7), [dict(driver="u_nope")])
    with pytest.raises(RR.ReplicateError, match="only a 1-bit"):
        RR.apply(mod(7).replace(".W(1), .D(7)", ".W(2), .D(7)"), SPEC)
    with pytest.raises(RR.ReplicateError, match="driver or driver_re"):
        RR.apply(mod(7), [{}])


def test_grid_regions_from_positions():
    pos = {"u_u_bn10": (10, 10), "u_u_bn11": (50, 60), "u_u_y_rt_24a_0": (700, 10), "u_u_y_rt_24a_1": (710, 20)}
    new, rep = RR.apply(mod(7), [dict(driver_re=r"u_d\d_6_Y", grid_um=300)], pos)
    assert set(rep[0]["region_names"]) == {"g0_0", "g2_0", "u_u_y_rt_24b", "rest"}
    assert rep[0]["loads_per_region"]["g0_0"] == 2 and rep[0]["loads_per_region"]["g2_0"] == 2


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog")
def test_cycle_equivalence_iverilog(tmp_path):
    """every sink sees the source exactly 7 flops late before and after (random stimulus, compare cycle by cycle)"""
    new, _ = RR.apply(mod(7), SPEC)
    for tag, text in (("old", mod(7)), ("new", new)):
        (tmp_path / f"{tag}.v").write_text((CELLS if tag == "old" else "") + text.replace("module top", f"module top_{tag}").replace("`default_nettype", ""))
    tb = """module tb; reg clk=0, s=0; wire [5:0] a, b; integer i, bad=0; reg [31:0] x = 32'h1234567;
      top_old o(.clk(clk), .s(s), .o(a)); top_new n(.clk(clk), .s(s), .o(b));
      initial begin for (i = 0; i < 400; i = i + 1) begin x = x * 1103515245 + 12345; s = x[17];
          #1 clk = 1; #1 clk = 0; if (i > 12 && a !== b) bad = bad + 1; end
        $display("BAD=%0d", bad); $finish; end endmodule"""
    (tmp_path / "tb.v").write_text(tb)
    subprocess.run(["iverilog", "-o", str(tmp_path / "s"), str(tmp_path / "old.v"), str(tmp_path / "new.v"), str(tmp_path / "tb.v")], check=True)
    out = subprocess.run(["vvp", str(tmp_path / "s")], capture_output=True, text=True, check=True).stdout
    assert "BAD=0" in out


def test_schema_key_declared_and_validates():
    raw = plan()
    t = raw["partition_types"]["src"]
    t["reset_replicate"] = [dict(driver="u_x", grid_um=300)]
    assert "reset_replicate" in schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]


def test_bind_wires_key_and_fails_closed_on_missing_driver():
    raw = plan()
    raw["partition_types"]["src"]["reset_replicate"] = [dict(driver="u_absent")]
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]["type"] == "src")
    with pytest.raises(bind.BindError, match="reset_replicate src: .*no ot_dp_dly"):
        b.emit_type("src", part)


def mod_assign(depth):
    """the 'element pair' shape: assign x = q; x feeds cores of TWO regions (and w_s feeds one region only)"""
    return f"""module top (input wire clk, input wire s, output wire [3:0] o);
    wire [0:0] w_6_Y;
    wire [0:0] d{depth}_6_Y;
    wire [0:0] x_pair;
    wire [0:0] w_one;
    assign w_6_Y = s;
    ot_dp_dly #(.W(1), .D({depth})) u_d{depth}_6_Y (.clk(clk), .d(w_6_Y), .q(d{depth}_6_Y));
    assign x_pair = d{depth}_6_Y[0];
    assign w_one = d{depth}_6_Y[0];
    core u_u_bn10 (
        .clk(clk),
        .rs(x_pair[0]),
        .o(o[0])
    );
    core u_u_bn11 (
        .clk(clk),
        .rs(x_pair[0]),
        .o(o[1])
    );
    core u_u_bs12 (
        .clk(clk),
        .rs(w_one[0]),
        .o(o[2])
    );
    core u_u_bs13 (
        .clk(clk),
        .rs(d{depth}_6_Y[0]),
        .o(o[3])
    );
endmodule
"""


def test_assign_loads_fan_out_per_region():
    new, rep = RR.apply(mod_assign(7), SPEC)
    r = rep[0]
    assert r["assign_splits"] == 2 and "rest" not in r["region_names"]          # no partition-wide shared copy
    assert set(r["region_names"]) == {"u_u_bn10", "u_u_bn11", "u_u_bs12", "u_u_bs13"}
    assert "assign x_pair = " not in new                                        # original assign gone, one per region
    assert new.count("assign x_pair_") == 2
    assert not re.search(r"\.rs\(x_pair\[0\]\)", new)
    # every sink reads a region-private copy: no two cores share a driver wire
    drv = re.findall(r"\.rs\((\w+)\[0\]\)", new)
    assert len(drv) == 4 and len(set(drv)) == 4


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog")
def test_assign_fanout_cycle_equivalence(tmp_path):
    new, _ = RR.apply(mod_assign(7), SPEC)
    for tag, text in (("old", mod_assign(7)), ("new", new)):
        (tmp_path / f"{tag}.v").write_text((CELLS if tag == "old" else "") + text.replace("module top", f"module top_{tag}").replace("`default_nettype", "").replace("[3:0] o", "[3:0] o"))
    tb = """module tb; reg clk=0, s=0; wire [3:0] a, b; integer i, bad=0; reg [31:0] x = 32'h7654321;
      top_old o(.clk(clk), .s(s), .o(a)); top_new n(.clk(clk), .s(s), .o(b));
      initial begin for (i = 0; i < 400; i = i + 1) begin x = x * 1103515245 + 12345; s = x[17];
          #1 clk = 1; #1 clk = 0; if (i > 12 && a !== b) bad = bad + 1; end
        $display("BAD=%0d", bad); $finish; end endmodule"""
    (tmp_path / "tb.v").write_text(tb)
    subprocess.run(["iverilog", "-o", str(tmp_path / "s"), str(tmp_path / "old.v"), str(tmp_path / "new.v"), str(tmp_path / "tb.v")], check=True)
    assert "BAD=0" in subprocess.run(["vvp", str(tmp_path / "s")], capture_output=True, text=True, check=True).stdout


def test_min_loads_leaves_small_drivers_alone():
    new, rep = RR.apply(mod(7), [dict(driver="u_d7_6_Y", min_loads=50)])
    assert new == mod(7) and rep[0]["copies"] == 0 and "min_loads" in rep[0]["note"]
    new, rep = RR.apply(mod(7), [dict(driver="u_d7_6_Y", min_loads=3)])
    assert rep[0]["copies"] > 1


def test_copy_depth_chain_text_and_report():
    """FABLE-DIE-S81 11-16: copy_depth 3 = common D(4) + a private 3-flop chain per region, 7 stages in total"""
    new, rep = RR.apply(mod(7), [dict(driver="u_d7_6_Y", copy_depth=3)])
    r = rep[0]
    assert r["depth"] == 7 and r["common_depth"] == 4 and r["copy_depth"] == 3 and r["chain_flops"] == 15
    assert ".D(4)) u_d7_6_Y" in new
    assert new.count("ot_dp_rrelay u_d7_6_Y_r") == 15 and len(re.findall(r"ot_dp_rrelay u_d7_6_Y_r\d_s[01] ", new)) == 10
    assert len(re.findall(r"u_d7_6_Y_r\d_s0 \(\.clk\(clk\), \.d\(d7_6_Y\[0\]\)", new)) == 5      # chain heads on the common flop
    assert len(re.findall(r"u_d7_6_Y_r\d \(\.clk\(clk\), \.d\(d7_6_Y_r\d_s1\)", new)) == 5        # last stage keeps the old name
    same, _ = RR.apply(mod(7), [dict(driver="u_d7_6_Y", copy_depth=1)])
    assert same == RR.apply(mod(7), SPEC)[0]                                                          # 1 = byte-identical


def test_copy_depth_capped_keeps_one_common_stage():
    new, rep = RR.apply(mod(7).replace("7", "2"), [dict(driver="u_d2_6_Y", copy_depth=5)])
    assert rep[0]["copy_depth"] == 1 and rep[0]["common_depth"] == 1 and ".D(1)) u_d2_6_Y" in new
    new, rep = RR.apply(mod(7).replace("7", "3"), [dict(driver="u_d3_6_Y", copy_depth=5)])
    assert rep[0]["copy_depth"] == 2 and rep[0]["common_depth"] == 1
    with pytest.raises(RR.ReplicateError, match="copy_depth"):
        RR.apply(mod(7), [dict(driver="u_d7_6_Y", copy_depth=0)])


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog")
def test_copy_depth_cycle_equivalence_iverilog(tmp_path):
    """every sink still sees the source exactly 7 flops late with the 3-flop chains"""
    new, _ = RR.apply(mod(7), [dict(driver="u_d7_6_Y", copy_depth=3, region_re="^(.*)$")])
    for tag, text in (("old", mod(7)), ("new", new)):
        (tmp_path / f"{tag}.v").write_text((CELLS if tag == "old" else "") + text.replace("module top", f"module top_{tag}"))
    tb = """module tb; reg clk=0, s=0; wire [5:0] a, b; integer i, bad=0; reg [31:0] x = 32'h1234567;
      top_old o(.clk(clk), .s(s), .o(a)); top_new n(.clk(clk), .s(s), .o(b));
      initial begin for (i = 0; i < 400; i = i + 1) begin x = x * 1103515245 + 12345; s = x[17];
          #1 clk = 1; #1 clk = 0; if (i > 12 && a !== b) bad = bad + 1; end
        $display("BAD=%0d", bad); $finish; end endmodule"""
    (tmp_path / "tb.v").write_text(tb)
    subprocess.run(["iverilog", "-o", str(tmp_path / "s"), str(tmp_path / "old.v"), str(tmp_path / "new.v"), str(tmp_path / "tb.v")], check=True)
    out = subprocess.run(["vvp", str(tmp_path / "s")], capture_output=True, text=True, check=True).stdout
    assert "BAD=0" in out


def test_copy_depth_schema():
    props = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["reset_replicate"]["items"]["properties"]
    assert props["copy_depth"] == {"type": "integer", "minimum": 1}


# ---- KV-D23-REACH 11-18: reset spine landing driver (form rsync) -------------------------------------------------------------
RS_CELLS = """module ot_dp_rsync #(parameter integer W = 1, parameter integer S = 2) (input wire clk, input wire [W-1:0] a, output wire [W-1:0] q);
    genvar g;
    generate for (g = 0; g < W; g = g + 1) begin : b
        reg [S-1:0] r;
        always @(posedge clk or negedge a[g]) if (!a[g]) r <= {S{1'b0}}; else r <= {r[S-2:0], 1'b1};
        assign q[g] = r[S-1];
    end endgenerate
endmodule
module rcore (input wire clk, input wire s0__rst_n, input wire s1__rst_n, output wire [1:0] o);
    assign o = {s1__rst_n, s0__rst_n};
endmodule
"""


def rs_mod(S):
    return f"""module top (input wire clk, input wire [0:0] ri_pv_rst_n, output wire [6:0] o);
    wire [0:0] ri_pv_rst_n_q;
    wire glue_rst;
    ot_dp_rsync #(.W(1), .S({S})) u_rs_ri_pv_rst_n (.clk(clk), .a(ri_pv_rst_n), .q(ri_pv_rst_n_q));
    assign glue_rst = ri_pv_rst_n_q[0];
    // as-built pvg0.p0
    rcore u_pvg0_p0 (
        .clk(clk),
        .s0__rst_n(ri_pv_rst_n_q[0]),
        .s1__rst_n(ri_pv_rst_n_q[0]),
        .o(o[1:0])
    );
    rcore u_pvg0_p1 (
        .clk(clk),
        .s0__rst_n(ri_pv_rst_n_q[0]),
        .s1__rst_n(ri_pv_rst_n_q[0]),
        .o(o[3:2])
    );
    rcore u_pvg3_p2 (
        .clk(clk),
        .s0__rst_n(ri_pv_rst_n_q[0]),
        .s1__rst_n(ri_pv_rst_n_q[0]),
        .o(o[5:4])
    );
    assign o[6] = glue_rst;
endmodule
"""


RS_SPEC = [dict(form="rsync", driver_re=r"u_rs_ri_.*rst_n", region_re="^(.*)$", copy_depth=4)]


def test_rsync_s2_has_no_relay_stage_and_is_unchanged():
    """the default landing is the two synchroniser flops: nothing to copy, the row says so (stages come from sink_stages)"""
    new, rep = RR.apply(rs_mod(2), RS_SPEC)
    assert new == rs_mod(2) and rep[0]["copies"] == 0 and rep[0]["form"] == "rsync" and "S = 2" in rep[0]["note"]


def test_rsync_copies_only_the_post_sync_stages():
    new, rep = RR.apply(rs_mod(6), RS_SPEC)
    r = rep[0]
    assert r["depth"] == 6 and r["common_depth"] == 2 and r["copy_depth"] == 4 and r["form"] == "rsync"
    assert r["region_names"] == ["rest", "u_pvg0_p0", "u_pvg0_p1", "u_pvg3_p2"] and r["chain_flops"] == 16
    # the synchroniser stays ONE 2-stage ot_dp_rsync on the spine; every copy is cleared by the same async spine
    assert "ot_dp_rsync #(.W(1), .S(2)) u_rs_ri_pv_rst_n (.clk(clk), .a(ri_pv_rst_n), .q(ri_pv_rst_n_q));" in new
    cp = re.findall(r"ot_dp_rtail #\(\.D\((\d+)\)\) (u_rs_ri_pv_rst_n_r\d) \(\.clk\(clk\), \.a\((\w+)\), \.d\(([^()]+)\), \.q\(([^()]+)\)\);"
                    r"  // landing pad tail copy for core (\S+?):", new)
    assert len(cp) == 4 and {c[0] for c in cp} == {"4"} and {c[2] for c in cp} == {"ri_pv_rst_n"}
    assert {c[3] for c in cp} == {"ri_pv_rst_n_q[0]"} and {c[5] for c in cp} == set(r["region_names"])
    # both pins of one core read that core's copy; the glue assign reads the rest copy; nothing but the copies reads the sync q
    for inst, w in (("u_pvg0_p0", "rs_ri_pv_rst_n_r1"), ("u_pvg0_p1", "rs_ri_pv_rst_n_r2"), ("u_pvg3_p2", "rs_ri_pv_rst_n_r3")):
        blk = re.search(r"rcore " + inst + r" \((.*?)\n    \);", new, re.S).group(1)
        assert blk.count(f"({w}[0])") == 2 and "ri_pv_rst_n_q" not in blk
    assert "assign glue_rst = rs_ri_pv_rst_n_r0[0];" in new
    assert new.count("ri_pv_rst_n_q[0]") == 4


def test_rsync_copy_depth_capped_at_the_relay_stages():
    new, rep = RR.apply(rs_mod(3), RS_SPEC)                 # S = 3: one relay stage, the 2 sync flops are never taken
    assert rep[0]["copy_depth"] == 1 and rep[0]["common_depth"] == 2
    assert ".S(2)) u_rs_ri_pv_rst_n" in new and new.count("ot_dp_rtail #(.D(1))") == 4


def test_rsync_driver_needs_the_form_and_form_is_checked():
    with pytest.raises(RR.ReplicateError, match="no ot_dp_dly"):
        RR.apply(rs_mod(6), [dict(driver_re=r"u_rs_ri_.*rst_n")])           # no form: the ot_dp_dly rule, as before
    with pytest.raises(RR.ReplicateError, match="no ot_dp_rsync"):
        RR.apply(mod(7), [dict(form="rsync", driver="u_d7_6_Y")])
    with pytest.raises(RR.ReplicateError, match="expected"):
        RR.apply(rs_mod(6), [dict(form="x", driver_re=r"u_rs_.*")])
    new, rep = RR.apply(rs_mod(6), [dict(form="rsync", driver="u_nope", optional=True)])
    assert new == rs_mod(6) and rep[0]["copies"] == 0


def test_rtail_cell_schema_and_plan_switch():
    assert "module ot_dp_rtail" in RR.TAIL_CELL and "(* keep *) reg [D-1:0] r;" in RR.TAIL_CELL
    assert "posedge clk or negedge a" in RR.TAIL_CELL
    props = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["reset_replicate"]["items"]["properties"]
    assert props["form"] == {"enum": ["rsync"]}
    assert RR.uses_rtail({"partition_types": {"a": {"reset_replicate": RS_SPEC}}})
    assert not RR.uses_rtail({"partition_types": {"a": {"reset_replicate": SPEC}, "b": {}}})
    import bind_verify
    rule = [x for x in bind_verify.VERIFY_RULES["transport"] if x["module"] == "ot_dp_rtail"]
    assert rule == [{"module": "ot_dp_rtail", "map": {"q": "d"}, "drop_in": ["clk", "a"], "stages": 1, "stages_param": "D"}]
    assert "ot_dp_rtail" in bind_verify.BIND_CELLS


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog")
def test_rsync_copies_same_function_async_assert_iverilog(tmp_path):
    """one 6-stage synchroniser vs synchroniser + per-core relay copies: every load sees the same level at every half step,
    with the spine asserted between clock edges (asynchronous assert) and released at random"""
    new, _ = RR.apply(rs_mod(6), RS_SPEC)
    (tmp_path / "old.v").write_text(RS_CELLS + rs_mod(6).replace("module top", "module top_old"))
    (tmp_path / "new.v").write_text(RR.TAIL_CELL + new.replace("module top", "module top_new"))
    tb = """module tb; reg clk=0; reg a=0; wire [6:0] x, y; integer i, bad=0, low=0, high=0; reg [31:0] r = 32'h2468ace;
      top_old o(.clk(clk), .ri_pv_rst_n(a), .o(x)); top_new n(.clk(clk), .ri_pv_rst_n(a), .o(y));
      initial begin for (i = 0; i < 4000; i = i + 1) begin r = r * 1103515245 + 12345;
          if (r[20:16] == 0) a = 0; else if (r[19:16] == 1) a = 1;
          #1 if (x !== y) bad = bad + 1; if (&y) high = high + 1; if (~|y) low = low + 1;
          if (i % 2) clk = ~clk; end
        $display("BAD=%0d HIGH=%0d LOW=%0d", bad, high, low); $finish; end endmodule"""
    (tmp_path / "tb.v").write_text(tb)
    subprocess.run(["iverilog", "-o", str(tmp_path / "s"), str(tmp_path / "old.v"), str(tmp_path / "new.v"), str(tmp_path / "tb.v")], check=True)
    out = subprocess.run(["vvp", str(tmp_path / "s")], capture_output=True, text=True, check=True).stdout
    m = re.search(r"BAD=(\d+) HIGH=(\d+) LOW=(\d+)", out)
    assert m and m.group(1) == "0" and int(m.group(2)) > 50 and int(m.group(3)) > 50, out


def _spine_plan(tmp_path, tag, sink_stages=None, row=None):
    """bind_tiny with a sink partition of two leaves (u_s0 / u_s1) whose flt pins hang directly on the reset spine p1.u_b.flt"""
    import json
    import test_bind_pad_tail_split as TT
    src = tmp_path / "srcs"
    if not src.exists():
        shutil.copytree(TT.EX, src)
        die = (src / "die.v").read_text()
        die = die.replace("wire [8:0] sq;", "wire [8:0] sq; wire [8:0] sq1;")
        die = die.replace("lf_sink snk (.clk(ck), .flt(fo), .d0(y0), .d1(y1), .q(sq));",
                          "spar snk (.ck(ck), .flt(f1), .a(y0), .b(y1), .q0(sq), .q1(sq1));")
        assert "spar snk" in die
        (src / "die.v").write_text(die)
        (src / "spar.sv").write_text(TT.SPAR)
    p = json.loads((TT.EX / "die_plan_lanes.json").read_text())
    ab = p["asbuilt"]
    ab.update(base=str(src), files=ab["files"] + ["spar.sv"], dissolve=ab["dissolve"] + ["spar"])
    p["ports"] = [x for x in p["ports"] if x["id"] not in ("a1f__0", "a0f__0")]
    p["lanes"] = [x for x in p["lanes"] if x["id"] not in ("a1f", "a0f")]
    for x in p["ports"]:
        if x["id"] == "a1s__0":
            x["width"] = 16
    for b in p["partition_types"]["ta"]["buses"]:
        if b["name"] == "ys_o":
            b["width"] = 16
    ts = p["partition_types"]["ts"]
    ts["buses"] = [b for b in ts["buses"] if b["name"] not in ("f0_i", "f1_i")]
    for b in ts["buses"]:
        if b["name"] == "d1_i":
            b["width"] = 16
        b["leaf"] = b["leaf"].replace("core.", "u_s0.")
    ab["reset_spines"] = [{"pin": r"p1\.u_b\.flt", "sync_stages": 2}]
    if sink_stages:
        ab["reset_spines"][0]["sink_stages"] = sink_stages
    if row:
        ts["reset_replicate"] = [row]
    f = tmp_path / f"plan_{tag}.json"
    f.write_text(json.dumps(p))
    return f


def test_bind_spine_sink_stages_and_per_core_relay_copies(tmp_path, monkeypatch):
    """asbuilt.reset_spines[].sink_stages raises the landing depth on the listed sink types only; the rsync row then hands the
    stages past the two synchroniser flops out per consumer core.  Absent keys = byte-identical bind output."""
    import json
    import test_bind_pad_tail_split as TT
    if not TT.HAVE_YOSYS:
        pytest.skip("no Yosys")
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    row = dict(form="rsync", driver_re="u_rs_.*", region_re="^(.*)$", copy_depth=2)
    base, norow, other, on = (tmp_path / x for x in ("base", "norow", "other", "on"))
    assert TT._bind(_spine_plan(tmp_path, "b"), base, "elab", "bind", "verify") == 0
    assert TT._bind(_spine_plan(tmp_path, "r", row=row), norow, "elab", "bind") == 0
    assert TT._bind(_spine_plan(tmp_path, "o", [{"types": ["ta"], "sync_stages": 4}]), other, "elab", "bind") == 0
    assert TT._bind(_spine_plan(tmp_path, "n", [{"types": ["t[s]"], "sync_stages": 4}], row), on, "elab", "bind", "verify") == 0
    rb = (base / "rtl" / "bt_ts.sv").read_text()
    m = re.search(r"ot_dp_rsync #\(\.W\(1\), \.S\(2\)\) (u_rs_\w+) \(\.clk\(clk\), \.a\((\w+)\), \.q\((\w+)\)\);", rb)
    assert m and rb.count(f"({m.group(3)}[0])") == 2                      # one landing, both cores read its q
    # S = 2: the row alone changes no RTL (no post-sync stage); stages listed for another sink type change nothing here
    assert (norow / "rtl" / "bt_ts.sv").read_text() == rb and (other / "rtl" / "bt_ts.sv").read_text() == rb
    assert "ot_dp_rtail" not in (base / "rtl" / "bind_cells.sv").read_text()
    ro = (on / "rtl" / "bt_ts.sv").read_text()
    assert f"ot_dp_rsync #(.W(1), .S(2)) {m.group(1)} (.clk(clk), .a({m.group(2)}), .q({m.group(3)}));" in ro
    cp = re.findall(r"ot_dp_rtail #\(\.D\(2\)\) (\w+) \(\.clk\(clk\), \.a\((\w+)\), \.d\(([^()]+)\), \.q\(([^()]+)\)\);"
                    r"  // landing pad tail copy for core (\w+):", ro)
    assert len(cp) == 2 and {c[1] for c in cp} == {m.group(2)} and {c[2] for c in cp} == {f"{m.group(3)}[0]"}
    assert {c[4] for c in cp} == {"u_u_s0", "u_u_s1"}
    for _i, _a, _d, q, core in cp:
        blk = re.search(r"lf_sink " + core + r" \((.*?)\n    \);", ro, re.S).group(1)
        assert f".flt({q})" in blk
    assert "module ot_dp_rtail" in (on / "rtl" / "bind_cells.sv").read_text()
    assert "released after 4 clocks" in ro and "released after 2 clocks" in rb
    assert json.loads((base / "verify_report.json").read_text())["verdict"] == "PASS"
    assert json.loads((on / "verify_report.json").read_text())["verdict"] == "PASS"
    import gen_phys
    assert sorted(r[3] for r in gen_phys.tail_copy_rows(on / "rtl")) == ["u_u_s0", "u_u_s1"]
