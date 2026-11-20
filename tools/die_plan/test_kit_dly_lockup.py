"""FABLE-FIX-KV-PV XTAP-C 11-20: kit_dly_lockup.py (delay-line split + lockup latches, kit RTL post-pass, opt-in)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_dly_lockup as dl  # noqa: E402

CELLS = """
module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    assign q = r[D-1];
endmodule
module ot_dp_dly_keep #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    assign q = r[D-1];
endmodule
module ot_dp_lk #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(*) if (!clk) q = d;
endmodule
module core (input wire clk, input wire [1:0] a, input wire b, output reg [2:0] y);
    always @(posedge clk) y <= {b, a};
endmodule
"""

RTL = """module top (
    input  wire clk,
    input  wire [1:0] x_i,
    output wire [2:0] y_o,
    output wire z_o
);
    wire [0:0] pd20_x_0_t_25;
    wire [0:0] pd20_x_1_t_25;
    wire [0:0] pd4_x_0_t_29;
    wire [0:0] pd5_x_0_pvg0_p1_25;
    wire [0:0] pd5_x_1_pvg0_p1_25;
    wire [0:0] pd5_x_0_pvg0_p1_29;
    wire [3:0] d17_w;
    wire [0:0] other_q;
    ot_dp_dly #(.W(1), .D(20)) u_pd20_x_0_t_25 (.clk(clk), .d(x_i[0]), .q(pd20_x_0_t_25));  // trunk
    ot_dp_dly #(.W(1), .D(20)) u_pd20_x_1_t_25 (.clk(clk), .d(x_i[1]), .q(pd20_x_1_t_25));
    ot_dp_dly_keep #(.W(1), .D(4)) u_pd4_x_0_t_29 (.clk(clk), .d(pd20_x_0_t_25[0]), .q(pd4_x_0_t_29));
    ot_dp_dly_keep #(.W(1), .D(5)) u_pd5_x_0_pvg0_p1_25 (.clk(clk), .d(pd20_x_0_t_25[0]), .q(pd5_x_0_pvg0_p1_25));  // landing pad tail copy for core pvg0_p1: as-built relative timing
    ot_dp_dly_keep #(.W(1), .D(5)) u_pd5_x_1_pvg0_p1_25 (.clk(clk), .d(pd20_x_1_t_25[0]), .q(pd5_x_1_pvg0_p1_25));
    ot_dp_dly_keep #(.W(1), .D(5)) u_pd5_x_0_pvg0_p1_29 (.clk(clk), .d(pd4_x_0_t_29[0]), .q(pd5_x_0_pvg0_p1_29));
    ot_dp_dly #(.W(4), .D(17)) u_d17_w (.clk(clk), .d({x_i, x_i}), .q(d17_w));
    ot_dp_dly #(.W(1), .D(30)) u_other (.clk(clk), .d(x_i[0]), .q(other_q));
    core u_pvg0_p1 (
        .clk(clk),
        .a({pd5_x_1_pvg0_p1_25, pd5_x_0_pvg0_p1_25}),
        .b(pd5_x_0_pvg0_p1_29),
        .y(y_o)
    );
    assign z_o = ^d17_w ^ other_q;
endmodule
"""


def run(**kw):
    kw.setdefault("cores", ["u_pvg0_p1"])
    kw.setdefault("tail_groups", 2)
    return dl.apply(RTL, **kw)


def test_seg_sizes():
    assert dl.seg_sizes(20, 8) == [7, 7, 6] and dl.seg_sizes(8, 8) == [8] and dl.seg_sizes(9, 8) == [5, 4]
    assert dl.seg_sizes(1, 8) == [1] and sum(dl.seg_sizes(139, 8)) == 139 and max(dl.seg_sizes(139, 8)) <= 8


def test_split_keeps_stage_count_and_module():
    txt, lat, st = run()
    for nm, mod, d in (("u_pd20_x_0_t_25", "ot_dp_dly", 20), ("u_d17_w", "ot_dp_dly", 17)):
        segs = re.findall(r"(\w+) #\(\.W\((\d+)\), \.D\((\d+)\)\) %s_sg\d+ " % nm, txt)
        assert segs and {s[0] for s in segs} == {mod} and sum(int(s[2]) for s in segs) == d and max(int(s[2]) for s in segs) <= 8
        assert not re.search(r"\b%s \(" % nm, txt)
    # an unselected instance and a short one keep their text
    assert "ot_dp_dly #(.W(1), .D(30)) u_other (.clk(clk), .d(x_i[0]), .q(other_q));" in txt
    assert st["split"] == 4 and st["segments"] == 11 and st["selected"] == 7


def test_tail_copy_two_groups_and_bound_record():
    sys.path.insert(0, str(HERE))
    import gen_phys
    txt, lat, st = run()
    # the marked tail copy: K 5 -> groups 3 + 2, one latch between; the unmarked K 5 copies stay one instance
    assert "ot_dp_dly_keep #(.W(1), .D(3)) u_pd5_x_0_pvg0_p1_25_sg0 " in txt and "ot_dp_dly_keep #(.W(1), .D(2)) u_pd5_x_0_pvg0_p1_25_sg1 " in txt
    assert "u_fl_pd5_x_0_pvg0_p1_25_sg1" in {l["inst"] for l in lat} and " u_pd5_x_1_pvg0_p1_25 (" in txt
    # gen_phys still lists the copy under its bound name, K and d source, once
    rows = [(m.group(2), int(m.group(1)), m.group(3).strip()) for m in gen_phys._TAIL_COPY_RE.finditer(txt)]
    assert rows == [("u_pd5_x_0_pvg0_p1_25", 5, "pd20_x_0_t_25[0]")]
    assert rows == [(m.group(2), int(m.group(1)), m.group(3).strip()) for m in gen_phys._TAIL_COPY_RE.finditer(RTL)]


def test_latch_rules():
    txt, lat, st = run()
    by = {l["inst"]: l for l in lat}
    # segment boundaries
    assert {"u_fl_pd20_x_0_t_25_sg1", "u_fl_pd20_x_0_t_25_sg2", "u_fl_d17_w_sg1", "u_fl_d17_w_sg2"} <= set(by)
    assert by["u_fl_d17_w_sg1"]["W"] == 4
    # input latch: fed by another selected delay instance; never when fed by a port
    assert by["u_fl_pd5_x_0_pvg0_p1_25_i"]["d"] == "pd20_x_0_t_25[0]" and "u_fl_pd4_x_0_t_29_i" in by
    assert "u_fl_pd20_x_0_t_25_i" not in by and "u_fl_d17_w_i" not in by
    # output latch: read by a hard core; the consumers keep the original net name
    assert by["u_fl_pd5_x_0_pvg0_p1_25_o"]["q"] == "pd5_x_0_pvg0_p1_25" and ".q(pd5_x_0_pvg0_p1_25__pl)" in txt
    assert ".a({pd5_x_1_pvg0_p1_25, pd5_x_0_pvg0_p1_25})" in txt
    # read only by logic: no output latch
    assert "u_fl_d17_w_o" not in by
    assert st["by_kind"] == {"seg": 2 + 2 + 2 * 4 + 1, "in": 4, "out": 3}


def test_no_cores_no_out_latch_and_guard():
    txt, lat, st = run(cores=[])
    assert not [l for l in lat if l["kind"] == "out"]
    txt, lat, st = run(guard="OT_DLY_LOCKUP")
    on = txt.split("`ifdef OT_DLY_LOCKUP")[1].split("`else")[0]
    off = txt.split("`else")[1].split("`endif")[0]
    assert len(re.findall(r"^\s*ot_dp_lk\b", on, re.M)) == len(lat) == len(re.findall(r"\bassign\b", off))


def test_out_latched_driver_feeds_no_input_latch():
    rtl = RTL.replace(".b(pd5_x_0_pvg0_p1_29),", ".b(pd4_x_0_t_29),")
    txt, lat, st = dl.apply(rtl, cores=["u_pvg0_p1"])
    # default: one group per stage of a marked tail copy (K 5 -> 5 instances, 4 latches)
    assert len(re.findall(r"u_pd5_x_0_pvg0_p1_25_sg\d+ \(", txt)) == 5 and len([l for l in lat if l["inst"].startswith("u_fl_pd5_x_0_pvg0_p1_25_sg")]) == 4
    by = {l["inst"] for l in lat}
    assert "u_fl_pd4_x_0_t_29_o" in by and "u_fl_pd5_x_0_pvg0_p1_29_i" not in by


def test_nothing_selected_is_identity():
    txt, lat, st = dl.apply(RTL, inst_re="u_nomatch")
    assert txt == RTL and not lat


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_same_outputs_iverilog(tmp_path):
    txt, lat, st = run()
    tb = """`timescale 1ps/1ps
module tb;
    reg clk = 0; reg [1:0] x = 0; wire [2:0] ya, yb; wire za, zb; integer n, bad = 0;
    top_a a (.clk(clk), .x_i(x), .y_o(ya), .z_o(za));
    top_b b (.clk(clk), .x_i(x), .y_o(yb), .z_o(zb));
    always #416 clk = ~clk;
    initial begin
        for (n = 0; n < 400; n = n + 1) begin
            @(negedge clk); x = $random;
            @(posedge clk); #1;
            if (n > 60 && (ya !== yb || za !== zb)) bad = bad + 1;
        end
        if (bad == 0) $display("DLK_EQ PASS"); else $display("DLK_EQ FAIL %0d", bad);
        $finish;
    end
endmodule
"""
    (tmp_path / "a.v").write_text(CELLS + RTL.replace("module top", "module top_a") + txt.replace("module top", "module top_b") + tb)
    subprocess.run(["iverilog", "-g2005", "-o", str(tmp_path / "a.out"), str(tmp_path / "a.v")], check=True)
    out = subprocess.run(["vvp", str(tmp_path / "a.out")], check=True, capture_output=True, text=True).stdout
    assert "DLK_EQ PASS" in out, out


def test_plan_key_and_kit_entry(tmp_path):
    import gen_phys
    import schema
    c = gen_phys.dly_lockup_cfg
    assert c({}, "kv3_pv_v8") is None and c({"r_dly_lockup": {"kv3_pv": {}}}, "kv3_hub_C") is None
    assert c({"r_dly_lockup": {"kv3_pv": {}, "kv3_pv_v8": {"seg": 6, "tail_groups": 3}}}, "kv3_pv_v8__x") == dict(seg=6, tail_groups=3)
    assert c({"r_dly_lockup": {"kv3_pv": {}}}, "kv3_pv_v1") == dict(seg=8, tail_groups=0)
    b = {"r_dly_lockup": {"kv3_pv": {}}, "r_dly_spread": ["kv3_pv"]}
    ex = gen_phys.dly_lockup_exports(b, "kv3_pv_v8", {"clock": {}})
    assert "export OT_DLY_SPREAD_SEG = 1" in ex and "export OT_TAP_CAP_RECHECK = 0" in ex and "export OT_TAP_CHAIN_AFFINITY = 1" in ex
    assert "export OT_TAP_CHAIN_AFFINITY = 1" not in gen_phys.dly_lockup_exports(b, "kv3_pv_v8", {"clock": {"tap_chain_affinity": {}}})
    assert gen_phys.dly_lockup_exports({}, "kv3_pv_v8", {}) == []
    assert not [x for x in ex if "R2R_MARGIN" in x or "OT_HOLD_FF_MARGIN" in x]
    b2 = {"r_dly_lockup": {"kv3_pv": {"r2r_margin_ps": 25}}, "r_dly_spread": ["kv3_pv"]}
    ex2 = gen_phys.dly_lockup_exports(b2, "kv3_pv_v8", {"clock": {}})
    assert "export OT_PREGRT_HOLD_R2R_MARGIN = 25" in ex2 and "export OT_HOLD_FF_MARGIN = 25" in ex2
    assert c(b2, "kv3_pv_v8") == dict(seg=8, tail_groups=0) and gen_phys.dly_lockup_r2r_margin(b2, "kv3_hub_C") is None
    with pytest.raises(ValueError):
        gen_phys.dly_lockup_exports({"r_dly_lockup": {"kv3_pv": {}}}, "kv3_pv_v8", {})
    assert schema.SCHEMA["properties"]["budgets"]["properties"]["r_dly_lockup"]["type"] == "object"
    # kit entry: hard cores by module type, only *_bound.sv, in place
    (tmp_path / "top_bound.sv").write_text(RTL)
    (tmp_path / "other.sv").write_text(RTL)
    rec = dl.apply_kit(tmp_path, core_types={"core"})
    assert list(rec) == ["top_bound.sv"] and rec["top_bound.sv"]["by_kind"]["out"] == 3
    assert (tmp_path / "other.sv").read_text() == RTL and "u_fl_pd5_x_0_pvg0_p1_25_o" in (tmp_path / "top_bound.sv").read_text()


RTL_CH = RTL.replace("    wire [0:0] other_q;\n", "    wire [0:0] other_q;\n    wire [0:0] pd2_x_0_t_27;\n    wire [0:0] pd3_x_0_pvg0_p1_27;\n") \
    .replace("(.clk(clk), .d(x_i[0]), .q(pd20_x_0_t_25));  // trunk", "(.clk(clk), .d(x_i[0]), .q(pd20_x_0_t_25));  // landing pad trunk: shared stages of pad 25 (tail split)") \
    .replace("    core u_pvg0_p1 (", "    ot_dp_dly_keep #(.W(1), .D(2)) u_pd2_x_0_t_27 (.clk(clk), .d(pd20_x_0_t_25[0]), .q(pd2_x_0_t_27));  // landing pad trunk: shared stages of pad 27 (tail split)\n"
             "    ot_dp_dly_keep #(.W(1), .D(3)) u_pd3_x_0_pvg0_p1_27 (.clk(clk), .d(pd2_x_0_t_27[0]), .q(pd3_x_0_pvg0_p1_27));\n    core u_pvg0_p1 (") \
    .replace("assign z_o = ^d17_w ^ other_q;", "assign z_o = ^d17_w ^ other_q ^ pd3_x_0_pvg0_p1_27;")


def test_unchain_trunk_piece():
    assert "u_pd2_x_0_t_27" in RTL_CH and RTL_CH.count("landing pad trunk") == 2
    txt, lat, st = dl.apply(RTL_CH, cores=["u_pvg0_p1"], tail_groups=2)
    # the 2-stage piece behind the pad-25 trunk end becomes a 22-stage trunk from the source x_i[0]: 3 segments, no input latch
    segs = re.findall(r"ot_dp_dly_keep #\(\.W\(1\), \.D\((\d+)\)\) u_pd2_x_0_t_27_sg(\d+) \(\.clk\(clk\), \.d\((\S+?)\),", txt)
    assert [int(s[0]) for s in segs] == [8, 7, 7] and segs[0][2] == "x_i[0]"
    assert st["unchained"] == 1 and st["unchained_stages"] == 20
    assert "u_fl_pd2_x_0_t_27_i" not in {l["inst"] for l in lat} and "u_fl_pd3_x_0_pvg0_p1_27_i" in {l["inst"] for l in lat}
    # the shallower trunk is untouched by it (still 20 stages), and --no-unchain keeps the chain with an input latch
    assert sum(int(x) for x in re.findall(r"\.D\((\d+)\)\) u_pd20_x_0_t_25_sg\d+ ", txt)) == 20
    txt2, lat2, st2 = dl.apply(RTL_CH, cores=["u_pvg0_p1"], tail_groups=2, unchain=False)
    assert st2["unchained"] == 0 and "u_fl_pd2_x_0_t_27_i" in {l["inst"] for l in lat2}


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
@pytest.mark.parametrize("unchain", [True, False])
def test_unchain_same_outputs_iverilog(tmp_path, unchain):
    txt, lat, st = dl.apply(RTL_CH, cores=["u_pvg0_p1"], unchain=unchain)
    tb = """`timescale 1ps/1ps
module tb;
    reg clk = 0; reg [1:0] x = 0; wire [2:0] ya, yb; wire za, zb; integer n, bad = 0;
    top_a a (.clk(clk), .x_i(x), .y_o(ya), .z_o(za));
    top_b b (.clk(clk), .x_i(x), .y_o(yb), .z_o(zb));
    always #416 clk = ~clk;
    initial begin
        for (n = 0; n < 400; n = n + 1) begin
            @(negedge clk); x = $random;
            @(posedge clk); #1;
            if (n > 60 && (ya !== yb || za !== zb)) bad = bad + 1;
        end
        if (bad == 0) $display("DLK_EQ PASS"); else $display("DLK_EQ FAIL %0d", bad);
        $finish;
    end
endmodule
"""
    (tmp_path / "a.v").write_text(CELLS + RTL_CH.replace("module top", "module top_a") + txt.replace("module top", "module top_b") + tb)
    subprocess.run(["iverilog", "-g2005", "-o", str(tmp_path / "a.out"), str(tmp_path / "a.v")], check=True)
    out = subprocess.run(["vvp", str(tmp_path / "a.out")], check=True, capture_output=True, text=True).stdout
    assert "DLK_EQ PASS" in out, out


def test_pad_min_stations_cuts_sparse_pad_lines_only():
    """FABLE-FIX-KV-PV-R2 11-20: a sparse pad line gets a segment (= a placement station) per transport hop; dense pad lines, tail
    copies and non-pad lines keep the SEG form; 0 / absent is the form as first built."""
    base, lat0, st0 = run()
    assert dl.apply(RTL, cores=["u_pvg0_p1"], tail_groups=2, pad_min_stations=0)[0] == base
    txt, lat, st = run(pad_min_stations=16)
    # D 20 pad trunk: 20 // 16 = 1 stage per segment, 20 stations (was 7 + 7 + 6)
    segs = [int(d) for d in re.findall(r"ot_dp_dly #\(\.W\(1\), \.D\((\d+)\)\) u_pd20_x_0_t_25_sg\d+ ", txt)]
    assert segs == [1] * 20 and sum(1 for l in lat if l["inst"].startswith("u_fl_pd20_x_0_t_25_sg")) == 19
    # D 4 pad trunk piece: 4 segments of 1 (it was one instance)
    assert [int(d) for d in re.findall(r"\.D\((\d+)\)\) u_pd4_x_0_t_29_sg\d+ ", txt)] == [1] * 4
    # the non-pad line u_d17_w keeps <= 8, the marked tail copy keeps its 2 groups, the unselected line its text
    assert sorted(int(d) for d in re.findall(r"\.D\((\d+)\)\) u_d17_w_sg\d+ ", txt)) == [5, 6, 6]
    assert "ot_dp_dly_keep #(.W(1), .D(3)) u_pd5_x_0_pvg0_p1_25_sg0 " in txt and "u_other (.clk(clk), .d(x_i[0]), .q(other_q));" in txt
    # dense pad line: D 136 with N 16 -> segment size min(8, 136 // 16) = 8, unchanged
    dense = RTL.replace("ot_dp_dly #(.W(1), .D(20)) u_pd20_x_1_t_25", "ot_dp_dly #(.W(1), .D(136)) u_pd20_x_1_t_25")
    a = dl.apply(dense, cores=["u_pvg0_p1"], tail_groups=2)[0]
    b = dl.apply(dense, cores=["u_pvg0_p1"], tail_groups=2, pad_min_stations=16)[0]
    pick = lambda t: re.findall(r"\.D\((\d+)\)\) u_pd20_x_1_t_25_sg\d+ ", t)
    assert pick(a) == pick(b) and len(pick(a)) == 17
    # D 40: 40 // 16 = 2 stages per segment, 20 stations
    mid = RTL.replace("ot_dp_dly #(.W(1), .D(20)) u_pd20_x_1_t_25", "ot_dp_dly #(.W(1), .D(40)) u_pd20_x_1_t_25")
    assert pick(dl.apply(mid, cores=["u_pvg0_p1"], tail_groups=2, pad_min_stations=16)[0]) == ["2"] * 20
    # same stage total on every line
    for nm, d in (("u_pd20_x_0_t_25", 20), ("u_pd20_x_1_t_25", 20), ("u_pd4_x_0_t_29", 4)):
        assert sum(int(x) for x in re.findall(r"\.D\((\d+)\)\) %s_sg\d+ " % nm, txt)) == d


def test_pad_min_stations_plan_key():
    import gen_phys
    import schema
    c = gen_phys.dly_lockup_cfg
    assert c({"r_dly_lockup": {"kv3_pv": {"pad_min_stations": 16}}}, "kv3_pv_v8") == dict(seg=8, tail_groups=0, pad_min_stations=16)
    assert c({"r_dly_lockup": {"kv3_pv": {"pad_min_stations": 0}}}, "kv3_pv_v8") == dict(seg=8, tail_groups=0)
    props = schema.SCHEMA["properties"]["budgets"]["properties"]["r_dly_lockup"]["additionalProperties"]["properties"]
    assert props["pad_min_stations"] == {"type": "integer", "minimum": 0}


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_pad_min_stations_same_outputs_iverilog(tmp_path):
    txt, lat, st = dl.apply(RTL, cores=["u_pvg0_p1"], pad_min_stations=16)
    tb = """`timescale 1ps/1ps
module tb;
    reg clk = 0; reg [1:0] x = 0; wire [2:0] ya, yb; wire za, zb; integer k, bad = 0;
    top_a a (.clk(clk), .x_i(x), .y_o(ya), .z_o(za));
    top_b b (.clk(clk), .x_i(x), .y_o(yb), .z_o(zb));
    always #50 clk = ~clk;
    initial begin
        for (k = 0; k < 400; k = k + 1) begin
            @(posedge clk); #7 x = $random;
            if (k > 80 && (ya !== yb || za !== zb)) bad = bad + 1;
        end
        if (bad == 0) $display("SAME"); else $display("DIFF %0d", bad);
        $finish;
    end
endmodule
"""
    (tmp_path / "a.v").write_text(CELLS + RTL.replace("module top (", "module top_a ("))
    (tmp_path / "b.v").write_text(txt.replace("module top (", "module top_b ("))
    (tmp_path / "tb.v").write_text(tb)
    subprocess.run(["iverilog", "-g2012", "-o", str(tmp_path / "s"), str(tmp_path / "a.v"), str(tmp_path / "b.v"), str(tmp_path / "tb.v")], check=True)
    assert "SAME" in subprocess.run(["vvp", str(tmp_path / "s")], capture_output=True, text=True, check=True).stdout
