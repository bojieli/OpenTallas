`timescale 1ns/1ps
// HBM-P5-RTLB 10-23: over-cap SPLIT twin of ot_hbm_su_static_side (pinned file untouched).  The side pipe is cut into
// two cores (physical/die_plan/hbm/over_cap_split/ot_hbm_su_static_pgslice_lg__pv0.split.json):
//   side_softplus = ot_hbm_su_static_side_softplus_s (the pinned softplus + its fsqrt, unchanged, plus ONE fault pin
//                   register);  side_rest = everything else here (rsqrt, sqrt, Engram gate, result mux, fault OR).
// Cut pins softplus -> rest, all launched by a flop:  r (= y_sp, the fsqrt output register `y`), vo (vline flop),
//   sp (ot_hdc_delay flop, unread), fault (NEW register f_q: the pinned softplus ORs nine unit fault pulses
//   combinationally into the side fault OR = the only COMB crossing of the cut).
// Cost: 0 edges on every side DATA result (y unchanged, every function, every edge); the side fault PULSE of the
//   sqrt(softplus) function reaches the slice's sticky fault 1 edge later (status only, not on any schedule).
// Rest -> softplus inputs (v gated by fn == SPSQRT, x) are the FULL lane's side pins (REG->LOGIC->REG, as before).
// SMUT (bench mutants, 0 = design): 1 = an extra register on y_sp (a +1-edge side result WITHOUT the fn_out
//   re-alignment: must FAIL the lock-step), 2 = fault pin register removed (pinned comb crossing: must FAIL the
//   +1-edge fault relation check).
module ot_hbm_su_static_side_s #(parameter integer MUT=0, parameter integer SMUT=0, parameter integer MLAT=3, ALAT=3) (
    input wire [5:0] clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [2:0]  fn,
    input  wire [31:0] x,
    input  wire [2:0]  fn_out,
    output wire [31:0] y,
    output wire        fault
);
    wire [2:0] output_fn=fn_out ^ (MUT==1 ? 3'd1:3'd0);
    localparam [2:0] SFU_RSQRT = 2, SFU_SQRT = 3, SFU_SPSQRT = 6, SFU_EGATE = 7;
    localparam integer D_EXP = 7 * MLAT + 8 * ALAT + 4;
    localparam integer KS = (MLAT != 3 || ALAT != 3) ? 1 : 0;
    wire [31:0] y_rsq, y_sq, y_sp_c, y_sp, y_eg;
    wire f_rsq, f_sq, f_sp, f_eg1, f_eg2, f_eg3, f_eg4;
    ot_hdc_v41x_rsqrt #(.LM(MLAT), .LA(ALAT)) u_rsq (.clk(clk[0]), .rst_n(rst_n), .v(v && fn == SFU_RSQRT), .x(x), .y(y_rsq), .vo(),
                             .fault(f_rsq));
    ot_hdc_fsqrt u_sq (.clk(clk[1]), .rst_n(rst_n), .v(v && fn == SFU_SQRT), .a(x), .y(y_sq), .vo(), .fault(f_sq));
    ot_hbm_su_static_side_softplus_s #(.LM(MLAT), .LA(ALAT), .FREG(SMUT == 2 ? 0 : 1)) u_sp (.clk(clk[4:2]), .rst_n(rst_n),
                               .v(v && fn == SFU_SPSQRT), .x(x), .sp(), .r(y_sp_c), .vo(), .fault(f_sp));
    if (SMUT == 1) begin : g_smut1
        reg [31:0] y_sp_q; always @(posedge clk[4]) y_sp_q <= y_sp_c; assign y_sp = y_sp_q;
    end else begin : g_ysp
        assign y_sp = y_sp_c;
    end
    // Engram gate (unchanged)
    reg  [31:0] eg_m;
    reg         eg_v;
    reg  [31:0] eg_sgn;
    wire [31:0] absr = {1'b0, x[30:0]};
    wire        eg_le;
    ot_hdc_kge #(.W(32), .K(KS)) u_egc (.a(32'h358637BD), .b(absr), .ge(eg_le));
    wire        eg_gt = !eg_le;
    always @(posedge clk[5] or negedge rst_n) begin
        if (!rst_n) eg_v <= 1'b0; else eg_v <= v && fn == SFU_EGATE;
    end
    always @(posedge clk[5]) begin
        eg_m <= eg_gt ? absr : 32'h358637BD;
        eg_sgn <= {eg_sgn[30:0], x[31] && (x[30:0] != 31'd0)};
    end
    wire [31:0] eg_r;
    wire        eg_rv;
    ot_hdc_fsqrt u_egs (.clk(clk[5]), .rst_n(rst_n), .v(eg_v), .a(eg_m), .y(eg_r), .vo(eg_rv), .fault(f_eg1));
    reg  [31:0] eg_s;
    reg         eg_sv;
    always @(posedge clk[5] or negedge rst_n) begin
        if (!rst_n) eg_sv <= 1'b0; else eg_sv <= eg_rv;
    end
    always @(posedge clk[5]) eg_s <= {eg_r[31] ^ eg_sgn[31] ^ (MUT==2), eg_r[30:0]};
    wire [31:0] e_y, den;
    wire [D_EXP:0] ve;
    ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk[5]), .rst_n(rst_n), .v(eg_sv), .vd(ve));
    ot_hdc_v41x_exp #(.LM(MLAT), .LA(ALAT)) u_exp (.clk(clk[5]), .rst_n(rst_n), .v(eg_sv), .x({~eg_s[31], eg_s[30:0]}), .y(e_y), .vo(),
                           .fault(f_eg2));
    ot_hdc_qadd_lat #(.KEEP(KS), .LAT(ALAT)) u_den (clk[5], rst_n, ve[D_EXP], e_y, 32'h3F800000, den, f_eg3);
    wire [ALAT:0] vd;
    ot_hdc_vline #(.D(ALAT)) u_vd (.clk(clk[5]), .rst_n(rst_n), .v(ve[D_EXP]), .vd(vd));
    ot_hdc_v41x_fdiv u_div (.clk(clk[5]), .rst_n(rst_n), .v(vd[ALAT]), .a(32'h3F800000), .b(den), .y(y_eg), .vo(),
                            .fault(f_eg4));
    assign y = (output_fn == SFU_RSQRT) ? y_rsq : (output_fn == SFU_SQRT) ? y_sq : (output_fn == SFU_SPSQRT) ? y_sp : y_eg;
    assign fault = f_rsq | f_sq | f_sp | f_eg1 | f_eg2 | f_eg3 | f_eg4;
endmodule

// The side_softplus core: the pinned ot_hbm_su_static_side_softplus unchanged + a fault pin register (FREG 1) on
// clk[2] (its finishing root).  Every output pin is launched by a flop.
module ot_hbm_su_static_side_softplus_s #(
    parameter integer LM = 3,
    parameter integer LA = 3,
    parameter integer FREG = 1
) (
    input wire [2:0] clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] sp,
    output wire [31:0] r,
    output wire        vo,
    output wire        fault
);
    wire f_c;
    ot_hbm_su_static_side_softplus #(.LM(LM), .LA(LA)) u_core (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .sp(sp), .r(r),
                                     .vo(vo), .fault(f_c));
    if (FREG != 0) begin : g_freg
        reg f_q;
        always @(posedge clk[2] or negedge rst_n) if (!rst_n) f_q <= 1'b0; else f_q <= f_c;
        assign fault = f_q;
    end else begin : g_fcomb
        assign fault = f_c;
    end
endmodule
