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


def test_parameter_hook_does_not_shadow_the_bound_reset_generator(tmp_path, monkeypatch):
    stale = tmp_path / "reset_replicate.py"
    stale.write_text("raise RuntimeError('loaded the source-tree reset generator')\n")
    hook = tmp_path / "param_hook.py"
    hook.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(tmp_path)!r})\n"
        "def regen(ctx): return {'params': {}}\n"
    )
    monkeypatch.delitem(sys.modules, "reset_replicate", raising=False)
    # Give pytest a fresh list so even a failing assertion cannot leak paths.
    monkeypatch.setattr(sys, "path", sys.path[:])
    b = bind.Binder.__new__(bind.Binder)
    b.ab, b.errors = {"param_regen": {"file": str(hook)}}, []
    b.regen_params()
    assert b.errors == []
    import reset_replicate
    assert Path(reset_replicate.__file__).resolve() == Path(RR.__file__).resolve()


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


def test_rsync_lockups_group_by_connected_hard_core():
    txt = rs_mod(6)
    lockups = (
        '    ot_dp_lk #(.W(1)) u_lk_nk_short_a (.clk(clk), .d(glue_rst), .q(lock_a));\n'
        '    ot_dp_lk #(.W(1)) u_lk_nk_short_b (.clk(clk), .d(ri_pv_rst_n_q[0]), .q(lock_b));\n'
    )
    txt = txt.replace('    // as-built pvg0.p0', lockups + '    // as-built pvg0.p0')
    txt = txt.replace('.s0__rst_n(ri_pv_rst_n_q[0])', '.s0__rst_n(lock_a)', 1)
    start = txt.index('    rcore u_pvg0_p1 (')
    txt = txt[:start] + txt[start:].replace('.s0__rst_n(ri_pv_rst_n_q[0])', '.s0__rst_n(lock_b)', 1)
    pos = {"u_pvg0_p0": (0, 0), "u_pvg0_p1": (400, 0), "u_pvg3_p2": (800, 0)}
    spec = {**RS_SPEC[0], "lockup_regions": True}

    old, old_report = RR.apply(txt, RS_SPEC, pos)
    new, report = RR.apply(txt, [spec], pos)
    assert re.search(r"u_lk_nk_short_a .*\.d\(glue_rst\)", old)
    assert re.search(r"u_lk_nk_short_b .*\.d\(rs_ri_pv_rst_n_r0\[0\]\)", old)
    assert report[0]["loads"] == old_report[0]["loads"]
    assert report[0]["loads_per_region"] == {"rest": 0, "u_pvg0_p0": 2, "u_pvg0_p1": 2, "u_pvg3_p2": 2}
    assert report[0]["depth"] == 6 and report[0]["copy_depth"] == 4
    assert re.search(r"u_lk_nk_short_a .*\.d\(glue_rst_rs_ri_pv_rst_n_r1\)", new)
    assert re.search(r"u_lk_nk_short_b .*\.d\(rs_ri_pv_rst_n_r2\[0\]\)", new)


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



RS_SYNC_SPEC = [dict(RS_SPEC[0], tail_clear="sync")]


def test_rsync_sync_tail_text_and_errors():
    new, rep = RR.apply(rs_mod(6), RS_SYNC_SPEC)
    tails = re.findall(r"ot_dp_rtail #\(\.D\((\d+)\)\) \w+ \(\.clk\(clk\), \.a\(([^()]*)\), ", new)
    assert tails and {a for _d, a in tails} == {"1'b1"} and {d for d, _a in tails} == {"4"}
    assert "synchronous copy: assert +4 clk, release unchanged" in new
    assert rep[0]["tail_clear"] == "sync" and rep[0]["assert_delay_clk"] == 4
    old, _ = RR.apply(rs_mod(6), RS_SPEC)
    assert old == RR.apply(rs_mod(6), [dict(RS_SPEC[0], tail_clear="async")])[0]        # async = the form before the key
    with pytest.raises(RR.ReplicateError):
        RR.apply(rs_mod(6), [dict(RS_SPEC[0], tail_clear="maybe")])
    with pytest.raises(RR.ReplicateError):
        RR.apply(mod(7), [dict(SPEC[0], tail_clear="sync")])


def test_rsync_async_tail_clears_from_the_sync_output():
    spec = [dict(RS_SPEC[0], tail_clear="sync_output")]
    ref, _ = RR.apply(rs_mod(6), RS_SPEC)
    assert ref.count(".a(ri_pv_rst_n), .d(ri_pv_rst_n_q[0])") == 4
    new, report = RR.apply(rs_mod(6), spec)
    assert ref.replace(".a(ri_pv_rst_n), .d(ri_pv_rst_n_q[0])",
                       ".a(ri_pv_rst_n_q[0]), .d(ri_pv_rst_n_q[0])") == new
    assert report[0]["copy_depth"] == 4
    assert report[0]["tail_clear"] == "sync_output" and report[0]["assert_delay_clk"] == 0
    with pytest.raises(RR.ReplicateError, match="sync_output needs form rsync"):
        RR.apply(mod(7), [dict(SPEC[0], tail_clear="sync_output")])


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog")
def test_rsync_sync_tail_bench_iverilog(tmp_path):
    """BENCH (COORD approval of the sync-tail form): one 6-stage synchroniser (all stages spine-cleared) vs synchroniser + per-core
    SYNCHRONOUS 4-stage copies.  Spine asserted between edges and released at random, with long and short pulses.
    Checked at every half step: (1) every core's copy carries the same level (all cores assert and release on the same edge);
    (2) every release (0->1) of a copy happens on the SAME clock edge as the old load; (3) every assert (1->0) of the copies
    comes exactly 4 clocks after the old (asynchronous) assert, and the copies never stay high while the old load is low for
    more than 4 edges.  Stimulus: each spine level held >= 8 clocks.  Outside that contract the forms differ: a re-assert
    within the n-clock release sequence clears the old load at once but lets the synchronous copies emit the part of the
    release already shifted in (a short high pulse) before they assert; the reset spine is a held level (boot >= 64 clk)."""
    new, _ = RR.apply(rs_mod(6), RS_SYNC_SPEC)
    (tmp_path / "old.v").write_text(RS_CELLS + rs_mod(6).replace("module top", "module top_old"))
    (tmp_path / "new.v").write_text(RR.TAIL_CELL + new.replace("module top", "module top_new"))
    tb = """module tb; reg clk=0; reg a=0; wire [6:0] x, y; integer i, e=0, ec=0, bad_eq=0, bad_rel=0, bad_as=0, rel=0, as_n=0, la=-1, ly=1, lx=0;
      integer sx[0:9999]; reg [31:0] r = 32'h13579bd;
      top_old o(.clk(clk), .ri_pv_rst_n(a), .o(x)); top_new n(.clk(clk), .ri_pv_rst_n(a), .o(y));
      always @(posedge clk) begin e = e + 1; end
      initial begin for (i = 0; i < 8000; i = i + 1) begin r = r * 1103515245 + 12345;
          // the spine moves between clock edges and holds each level >= 8 clocks (reset contract: rst_n is a level held for
          // many clocks, boot >= 64; a re-assert inside the n-clock release sequence is outside the contract, see the docstring)
          #1 if (e - ec >= 8 && r[20:16] == 0) begin a = ~a; ec = e; end
          #1 if (y !== {7{y[0]}}) bad_eq = bad_eq + 1;
          if (x[0] === 1'b0 && lx === 1) la = e;               // old load asserted (async) during edge count e
          if (y[0] === 1'b1 && ly === 0) begin rel = rel + 1; if (x[0] !== 1'b1) bad_rel = bad_rel + 1; end
          if (x[0] === 1'b1 && lx === 0 && y[0] !== 1'b1) bad_rel = bad_rel + 1;
          if (y[0] === 1'b0 && ly === 1) begin as_n = as_n + 1; if (e - la != 4 && la >= 0) bad_as = bad_as + 1; end
          if (x[0] === 1'b0 && y[0] === 1'b1 && la >= 0 && e - la > 4) bad_as = bad_as + 1;
          lx = x[0]; ly = y[0];
          #1 if (i % 2) clk = ~clk; end
        $display("EQ=%0d REL=%0d/%0d AS=%0d/%0d", bad_eq, bad_rel, rel, bad_as, as_n); $finish; end endmodule"""
    (tmp_path / "tb.v").write_text(tb)
    subprocess.run(["iverilog", "-o", str(tmp_path / "s"), str(tmp_path / "old.v"), str(tmp_path / "new.v"), str(tmp_path / "tb.v")], check=True)
    out = subprocess.run(["vvp", str(tmp_path / "s")], capture_output=True, text=True, check=True).stdout
    m = re.search(r"EQ=(\d+) REL=(\d+)/(\d+) AS=(\d+)/(\d+)", out)
    assert m and m.group(1) == "0" and m.group(2) == "0" and int(m.group(3)) > 10 and m.group(4) == "0" and int(m.group(5)) > 10, out


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
