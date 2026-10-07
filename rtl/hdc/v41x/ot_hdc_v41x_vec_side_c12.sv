`timescale 1ns/1ps
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv for the
// c12 build.  Defaults (DDIV 19, SIDEX 0, FSQ 0) are the original cycle for cycle.  The c12 build:
//   * SIDEX = 3: lane 0 registers side_v / side_x (rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv), this block registers
//     its inputs (fn delayed one cycle to meet them) and its output; the output register selects the function
//     whose unit completes (its vo), so it needs no early fn_out (the controller orders the side's elements at
//     the S output, one a cycle: at most one vo is high), and the fault OR is registered.  The routed side at
//     0.833 ns missed by 169 ps at its input (sqrt's normalise from the port), 429 ps at its output mux and
//     743 ps on its fault OR.  Every function is SIDEX deeper.
//   * DDIV = 21: the gate's divider is the DS ROM kit's ot_dsrom_fdiv_f12 (rtl/hdc/v41x/ot_dsrom_su_f12.sv).
//   * FSQ = 1: the square roots are ot_hdc_fsqrt_c12 (rtl/hdc/v41/ot_hdc_fsqrt_c12.sv, keep-prefix digit
//     recurrence and precomputed finish; same DEPTH 31, bit-identical).
// The softplus is rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv's (DDIV / FSQ passed through).
// ---------------------------------------------------------------------------
// Scalar side pipe of the V4.1 vector stream unit: the SFU functions that act
// on at most a few elements per op, so they live beside lane 0 only.  Its input
// is lane 0's R, at the S stage; lane 0 takes `y` at its S output, each
// function at its own depth:
//
//   rsqrt            ot_hdc_v41x_rsqrt                              37   (MLAT 4: 46)
//   sqrt             ot_hdc_fsqrt                                   31
//   sqrt(softplus)   ot_hdc_v41x_softplus                          162  (MLAT 4: 180)
//   Engram gate      m = max(|R|, 1e-6); sqrt; sign of R restored;
//                    sigmoid (exp, +1, divide)              1+31+1+71 = 104  (MLAT 4: 1+31+1+78 = 111)
//
// This is tools/hdc_program_v41.Machine.su's egate, bit for bit: sigmoid(x < 0 ?
// -sqrt(max(|x|, 1e-6)) : +sqrt(...)).  Each function has its own units.  The
// controller orders ELEMENTS at the S output (the checkpoint rule), not at the
// units' inputs, and a unit shared across depths would need the latter.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vec_side #(
    parameter integer MLAT = 3,     // multiplier latency of the units (ot_hdc_qmul_lat): 3, 4, or 5 (W11 serial domain)
    parameter integer ALAT = 3,     // add latency (ot_hdc_qadd_lat): 3, or 4
    parameter integer DDIV = 19,    // the gate's divider: 19 ot_hdc_v41x_fdiv, 21 ot_dsrom_fdiv_f12
    parameter integer SIDEX = 0,    // 0, 3 or 4: input and output registers here (+ lane 0's port registers)
    parameter integer FSQ = 0       // 1: ot_hdc_fsqrt_c12
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [2:0]  fn,          // the S code at the S input
    input  wire [31:0] x,
    input  wire [2:0]  fn_out,      // the S code at the S output
    output wire [31:0] y,
    output wire        fault
);
    localparam [2:0] SFU_RSQRT = 2, SFU_SQRT = 3, SFU_SPSQRT = 6, SFU_EGATE = 7;
    generate if ((SIDEX != 0 && SIDEX != 3 && SIDEX != 4) || (DDIV != 19 && DDIV != 21 && DDIV != 31) || (FSQ != 0 && FSQ != 1)) begin : g_bad
        ot_hdc_v41x_vec_side_c12_SIDEX_0_3_DDIV_19_21_FSQ_0_1 u_trap ();
    end endgenerate
    // c12 SIDEX = 3: v and x arrive from lane 0's register one cycle after fn (the controller's S-in code):
    // fn is delayed to meet them, and all three are registered here
    wire        vi;
    wire [2:0]  fi;
    wire [31:0] xi;
    generate if (SIDEX != 0) begin : g_in
        reg [2:0]  fn_d, fn_q;
        reg        v_q;
        reg [31:0] x_q;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) v_q <= 1'b0; else v_q <= v;
        end
        always @(posedge clk) begin fn_d <= fn; fn_q <= fn_d; x_q <= x; end
        assign {vi, fi, xi} = {v_q, fn_q, x_q};
    end else begin : g_inw
        assign {vi, fi, xi} = {v, fn, x};
    end endgenerate
    localparam integer D_EXP = 7 * MLAT + 8 * ALAT + 4;    // ot_hdc_v41x_exp DEPTH: 49 at 3 / 3
    localparam integer KS = (MLAT != 3 || ALAT != 3) ? 1 : 0;
    wire [31:0] y_rsq, y_sq, y_sp, y_eg;
    wire f_rsq, f_sq, f_sp, f_eg1, f_eg2, f_eg3, f_eg4;
    wire vo_rsq, vo_sq, vo_sp, vo_eg;
    ot_hdc_v41x_rsqrt #(.LM(MLAT), .LA(ALAT)) u_rsq (.clk(clk), .rst_n(rst_n), .v(vi && fi == SFU_RSQRT), .x(xi), .y(y_rsq),
                             .vo(vo_rsq), .fault(f_rsq));
    generate if (FSQ != 0) begin : g_sq12
        ot_hdc_fsqrt_c12 u_sq (.clk(clk), .rst_n(rst_n), .v(vi && fi == SFU_SQRT), .a(xi), .y(y_sq), .vo(vo_sq), .fault(f_sq));
    end else begin : g_sq
        ot_hdc_fsqrt u_sq (.clk(clk), .rst_n(rst_n), .v(vi && fi == SFU_SQRT), .a(xi), .y(y_sq), .vo(vo_sq), .fault(f_sq));
    end endgenerate
    ot_hdc_v41x_softplus #(.LM(MLAT), .LA(ALAT), .DDIV(DDIV), .FSQ(FSQ)) u_sp (.clk(clk), .rst_n(rst_n), .v(vi && fi == SFU_SPSQRT),
                               .x(xi), .sp(), .r(y_sp), .vo(vo_sp), .fault(f_sp));
    // Engram gate
    reg  [31:0] eg_m;
    reg         eg_v;
    reg  [31:0] eg_sgn;                 // the sign, along the square root (31)
    wire [31:0] absr = {1'b0, xi[30:0]};
    wire        eg_le;                                  // absr <= 1e-6 (0x358637BD)
    ot_hdc_kge #(.W(32), .K(KS)) u_egc (.a(32'h358637BD), .b(absr), .ge(eg_le));
    wire        eg_gt = !eg_le;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) eg_v <= 1'b0; else eg_v <= vi && fi == SFU_EGATE;
    end
    always @(posedge clk) begin
        eg_m <= eg_gt ? absr : 32'h358637BD;                           // max(|x|, 1e-6)
        eg_sgn <= {eg_sgn[30:0], xi[31] && (xi[30:0] != 31'd0)};
    end
    wire [31:0] eg_r;
    wire        eg_rv;
    generate if (FSQ != 0) begin : g_egs12
        ot_hdc_fsqrt_c12 u_egs (.clk(clk), .rst_n(rst_n), .v(eg_v), .a(eg_m), .y(eg_r), .vo(eg_rv), .fault(f_eg1));
    end else begin : g_egs
        ot_hdc_fsqrt u_egs (.clk(clk), .rst_n(rst_n), .v(eg_v), .a(eg_m), .y(eg_r), .vo(eg_rv), .fault(f_eg1));
    end endgenerate
    reg  [31:0] eg_s;
    reg         eg_sv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) eg_sv <= 1'b0; else eg_sv <= eg_rv;
    end
    always @(posedge clk) eg_s <= {eg_r[31] ^ eg_sgn[31], eg_r[30:0]};
    // sigmoid(eg_s) = 1 / (exp(-eg_s) + 1)
    wire [31:0] e_y, den;
    wire [D_EXP:0] ve;
    ot_hdc_vline #(.D(D_EXP)) u_ve (.clk(clk), .rst_n(rst_n), .v(eg_sv), .vd(ve));
    ot_hdc_v41x_exp #(.LM(MLAT), .LA(ALAT)) u_exp (.clk(clk), .rst_n(rst_n), .v(eg_sv), .x({~eg_s[31], eg_s[30:0]}), .y(e_y), .vo(),
                           .fault(f_eg2));
    ot_hdc_qadd_lat #(.KEEP(KS), .LAT(ALAT)) u_den (clk, rst_n, ve[D_EXP], e_y, 32'h3F800000, den, f_eg3);
    wire [ALAT:0] vd;
    ot_hdc_vline #(.D(ALAT)) u_vd (.clk(clk), .rst_n(rst_n), .v(ve[D_EXP]), .vd(vd));
    generate if (DDIV == 31) begin : g_d31
        ot_hdc_fdiv    u_div (.clk(clk), .rst_n(rst_n), .v(vd[ALAT]), .a(32'h3F800000), .b(den), .y(y_eg), .vo(vo_eg),
                                 .fault(f_eg4));
    end else if (DDIV == 21) begin : g_d21
        ot_dsrom_fdiv_f12 u_div (.clk(clk), .rst_n(rst_n), .v(vd[ALAT]), .a(32'h3F800000), .b(den), .y(y_eg), .vo(vo_eg),
                                 .fault(f_eg4));
    end else begin : g_d19
        ot_hdc_v41x_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(vd[ALAT]), .a(32'h3F800000), .b(den), .y(y_eg), .vo(vo_eg),
                                .fault(f_eg4));
    end endgenerate
    wire fault_c = f_rsq | f_sq | f_sp | f_eg1 | f_eg2 | f_eg3 | f_eg4;
    generate if (SIDEX != 0) begin : g_out
        // the completing function's result (one vo at most), registered; the fault OR registered
        reg [31:0] y_q;
        reg        f_q;
        always @(posedge clk)
            y_q <= ({32{vo_rsq}} & y_rsq) | ({32{vo_sq}} & y_sq) | ({32{vo_sp}} & y_sp) | ({32{vo_eg}} & y_eg);
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) f_q <= 1'b0; else f_q <= fault_c;
        end
        assign y = y_q;
        assign fault = f_q;
    end else begin : g_outw
        assign y = (fn_out == SFU_RSQRT) ? y_rsq : (fn_out == SFU_SQRT) ? y_sq : (fn_out == SFU_SPSQRT) ? y_sp : y_eg;
        assign fault = fault_c;
    end endgenerate
endmodule
