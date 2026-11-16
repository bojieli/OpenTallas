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
