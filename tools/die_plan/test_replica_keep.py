"""MERGE-CENSUS 11-15 (FABLE-GENBUG G5): replica_keep derives the port-staging registers of multiply instantiated modules
(the registers yosys opt_merge folds between intended copies) and gen_phys exports them scoped by module.
    python3 -m pytest -q tools/die_plan/test_replica_keep.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import replica_keep as RK  # noqa: E402
import schema  # noqa: E402

TINY = HERE / "examples" / "tiny_plan.json"

FAN = """
module qkd_seq_fan_s #(parameter integer MUT = 0) (
    input wire ck, input wire rst_n, input wire [27:0] aqm, input wire [511:0] q, input wire [32:0] kc_i,
    output wire [32:0] kc, input wire af, output reg af_o);
    wire rr;
    reg [27:0] am, am2; reg [511:0] qd, qd2; reg [32:0] kq, kq2; reg a1; reg [7:0] cnt;
    always @(posedge ck) begin
        am[26:7] <= aqm[26:7]; am2[26:7] <= am[26:7];
        qd <= q; qd2 <= qd; kq[31:0] <= kc_i[31:0]; kq2[31:0] <= (MUT == 9) ? kc_i[31:0] : kq[31:0];
    end
    always @(posedge ck or negedge rr)
        if (!rr) begin am[27] <= 1'b0; kq[32] <= 1'b0; a1 <= 1'b0; af_o <= 1'b0; end
        else begin am[27] <= aqm[27]; kq[32] <= kc_i[32]; a1 <= af; af_o <= a1; end
    always @(posedge ck) if (af) cnt <= cnt + 1'b1;     // enabled counter: not a staging register
    assign kc = kq2;
endmodule
module wreg (input wire clk, input wire [7:0] wd, output wire [7:0] o);
    reg [7:0] wdata; always @(posedge clk) wdata <= wd; assign o = wdata;
endmodule
module tstage (input wire ck, input wire [3:0] ti_a, output reg [3:0] ti_b);
    always @(posedge ck) begin ti_b <= ti_a; end
endmodule
module single (input wire ck, input wire [3:0] d, output reg [3:0] q);
    always @(posedge ck) q <= d;
endmodule
module top (input wire ck, rst_n, input wire [511:0] q, input wire [3:0] t, output wire [7:0] o0, o1, output wire [3:0] u0, u1, s);
    qkd_seq_fan_s #(.MUT(0)) f0 (.ck(ck), .rst_n(rst_n), .q(q));
    qkd_seq_fan_s #(.MUT(0)) f1 (.ck(ck), .rst_n(rst_n), .q(q));
    genvar i;
    generate for (i = 0; i < 4; i = i + 1) begin : g
        wreg w (.clk(ck), .wd(8'd0), .o());
    end endgenerate
    tstage a (.ck(ck), .ti_a(t), .ti_b(u0));
    tstage b (.ck(ck), .ti_a(t), .ti_b(u1));
    single x (.ck(ck), .d(t), .q(s));
endmodule
"""


def _rtl(d, text=FAN):
    (Path(d) / "x.sv").write_text(text)
    return d


def test_replica_pattern_derives_staging_registers():
    with tempfile.TemporaryDirectory() as d:
        got = set(RK.derive(_rtl(d)))
    assert {"qkd_seq_fan_s:qd", "qkd_seq_fan_s:qd2", "qkd_seq_fan_s:kq", "qkd_seq_fan_s:kq2", "qkd_seq_fan_s:am",
            "qkd_seq_fan_s:am2", "wreg:wdata", "tstage:ti_b"} <= got
    assert "qkd_seq_fan_s:cnt" not in got          # enable-gated: not a pure stage
    assert not any(x.startswith("single:") for x in got)   # one instance: nothing to fold
    assert not any(x.startswith("top:") for x in got)


def test_gen_phys_exports_scoped_keep_and_merges_env(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        _rtl(d)
        monkeypatch.delenv("OT_REPLICA_KEEP", raising=False)
        w = gen_phys.replica_keep_wires(d, "ti_b,extra_x")
        assert "wreg:wdata" in w and "ti_b" in w and "extra_x" in w and len(w) == len(set(w))
        monkeypatch.setenv("OT_REPLICA_KEEP", "0")
        assert gen_phys.replica_keep_wires(d, "ti_b") == ["ti_b"]


def test_kit_config_carries_replica_keep(monkeypatch):
    monkeypatch.delenv("OT_REPLICA_KEEP", raising=False)
    P = schema.Plan(json.loads(TINY.read_text()))
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(P, "mid", d, [])
        assert "OT_KEEP_WIRES" not in (kd / "config.mk").read_text()      # tiny kit has no replicated module
        (kd / "rtl").mkdir(exist_ok=True)
    assert gen_phys.replica_keep_wires(HERE / "nonexistent_rtl_dir") == []


def test_hook_accepts_module_scoped_names():
    tcl = (HERE.parents[1] / "physical" / "common_flow" / "ot_keep_regs.tcl").read_text()
    assert "ot_kwn_m" in tcl and "$paramod*?${ot_kwn_m}?*" in tcl and '"\\$paramod*?${ot_kwn_m}"' in tcl   # paramod name without a parameter suffix
    assert "not a wire base name" in tcl            # bare names keep their check
    assert 'w:*.$ot_kwn_w' in tcl                   # Module:wire reaches generate-scoped regs (g_r.r)


HDC = """
`ifndef OT_ARST
  `define OT_ARST(x) or negedge x
`endif
module w11_cut #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk `OT_ARST(rst_n)) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv; reg [W-1:0] rd;
        always @(posedge clk `OT_ARST(rst_n)) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        assign q = rd;
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule
module addv (input wire clk, rst_n, valid_in, output wire v);
    reg s1_v, s2_v, cnt_v;
    always @(posedge clk `OT_ARST(rst_n)) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk `OT_ARST(rst_n)) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk `OT_ARST(rst_n)) begin
        if (!rst_n) cnt_v <= 1'b0;
        else if (valid_in) cnt_v <= ~cnt_v;       // enable + logic: not a staging register
    end
    assign v = s2_v;
endmodule
module lanes (input wire clk, rst_n, input wire [7:0] d, output wire [7:0] q0, q1, output wire v0, v1);
    w11_cut #(.W(8), .CUT(1)) a (.clk(clk), .rst_n(rst_n), .d(d), .q(q0));
    w11_cut #(.W(8), .CUT(1)) b (.clk(clk), .rst_n(rst_n), .d(d), .q(q1));
    addv x (.clk(clk), .rst_n(rst_n), .valid_in(d[0]), .v(v0));
    addv y (.clk(clk), .rst_n(rst_n), .valid_in(d[0]), .v(v1));
endmodule
"""


def test_replicated_constant_reset_and_ot_arst_block():
    with tempfile.TemporaryDirectory() as d:
        got = set(RK.derive(_rtl(d, HDC)))
    assert {"w11_cut:r", "w11_cut:rv", "w11_cut:rd", "addv:s1_v", "addv:s2_v"} <= got
    assert "addv:cnt_v" not in got                    # enable-gated toggle is not a staging register


def test_replicated_constant_is_a_constant_not_a_data_term():
    with tempfile.TemporaryDirectory() as d:
        bad = HDC.replace("else r <= d;", "else r <= d ^ r;")
        got = set(RK.derive(_rtl(d, bad)))
    assert "w11_cut:r" not in got                     # r now depends on itself through logic


BOUND = """
module leaf_bound (input wire clk, input wire [7:0] a, output wire [15:0] o);
    reg [7:0] g_u_lf0_u_vp_g_ln_0_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q;
    always @(posedge clk) g_u_lf0_u_vp_g_ln_0_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q <= a;
    reg [7:0] g_u_lf0_u_vp_g_ln_1_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q;
    always @(posedge clk) g_u_lf0_u_vp_g_ln_1_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q <= a;
    reg [7:0] g_u_lf0_u_vp_driver_x_q;
    always @(posedge clk) g_u_lf0_u_vp_driver_x_q <= a;
    assign o = {g_u_lf0_u_vp_g_ln_0_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q,
                g_u_lf0_u_vp_g_ln_1_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q} ^ {2{g_u_lf0_u_vp_driver_x_q}};
endmodule
"""
IST = """proc is_place {pat x y tag} {}
is_place {*u_vp_g_ln_0_u_cst_hi_gd_s_0_u_*} 168.48 533.817 cst:hi
is_place {*u_vp_g_ln_1_u_cst_hi_gd_s_0_u_*} 289.44 145.017 cst:hi
is_place {*u_ist_leafup_o0_0[./]q\\[4[0-9]\\]*} 1.0 2.0 ist:leafup_o0:bit
"""


def test_bound_plan_stations_are_kept(monkeypatch):
    """FABLE-FIX-S81-LEAF: per-lane stations of ONE bound module (plain regs, equal D) get a module-scoped keep."""
    monkeypatch.delenv("OT_REPLICA_KEEP", raising=False)
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "leaf_bound.sv").write_text(BOUND)
        ist = Path(d) / "istations.tcl"
        ist.write_text(IST)
        assert RK.derive(d) == []                                   # one module instance: the module rule sees nothing
        got = RK.station_regs(d, [Path(d) / "missing.tcl", ist])
        assert got == ["leaf_bound:g_u_lf0_u_vp_g_ln_0_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q",
                       "leaf_bound:g_u_lf0_u_vp_g_ln_1_u_cst_hi_gd_s_0_u_src_bdbec6ef94848d02f109_q"]
        assert RK.station_regs(d, []) == [] and RK.station_regs(d, None) == []
        w = gen_phys.replica_keep_wires(d, "extra_x", stations=[ist])
        assert got[0] in w and got[1] in w and "extra_x" in w and not any("driver_x" in x for x in w)
        assert gen_phys.replica_keep_wires(d, "extra_x") == ["extra_x"]          # no sidecar: unchanged
        monkeypatch.setenv("OT_REPLICA_KEEP", "0")
        assert gen_phys.replica_keep_wires(d, None, stations=[ist]) == []
