`timescale 1ns/1ps
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
    parameter integer MLAT = 3      // multiplier latency of the units (ot_hdc_qmul_lat): 3, or 4 (W11 serial domain)
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
    localparam integer D_EXP = 7 * MLAT + 28;          // ot_hdc_v41x_exp DEPTH: 49 (MLAT 3), 56 (MLAT 4)
    wire [31:0] y_rsq, y_sq, y_sp, y_eg;
    wire f_rsq, f_sq, f_sp, f_eg1, f_eg2, f_eg3, f_eg4;
    ot_hdc_v41x_rsqrt #(.LM(MLAT)) u_rsq (.clk(clk), .rst_n(rst_n), .v(v && fn == SFU_RSQRT), .x(x), .y(y_rsq), .vo(),
                             .fault(f_rsq));
    ot_hdc_fsqrt u_sq (.clk(clk), .rst_n(rst_n), .v(v && fn == SFU_SQRT), .a(x), .y(y_sq), .vo(), .fault(f_sq));
    ot_hdc_v41x_softplus #(.LM(MLAT)) u_sp (.clk(clk), .rst_n(rst_n), .v(v && fn == SFU_SPSQRT), .x(x), .sp(), .r(y_sp),
                               .vo(), .fault(f_sp));
    // Engram gate
    reg  [31:0] eg_m;
    reg         eg_v;
    reg  [31:0] eg_sgn;                 // the sign, along the square root (31)
    wire [31:0] absr = {1'b0, x[30:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) eg_v <= 1'b0; else eg_v <= v && fn == SFU_EGATE;
    end
    always @(posedge clk) begin
        eg_m <= (absr > 32'h358637BD) ? absr : 32'h358637BD;          // 1e-6
        eg_sgn <= {eg_sgn[30:0], x[31] && (x[30:0] != 31'd0)};
    end
    wire [31:0] eg_r;
    wire        eg_rv;
    ot_hdc_fsqrt u_egs (.clk(clk), .rst_n(rst_n), .v(eg_v), .a(eg_m), .y(eg_r), .vo(eg_rv), .fault(f_eg1));
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
    ot_hdc_v41x_exp #(.LM(MLAT)) u_exp (.clk(clk), .rst_n(rst_n), .v(eg_sv), .x({~eg_s[31], eg_s[30:0]}), .y(e_y), .vo(),
                           .fault(f_eg2));
    ot_hdc_qadd u_den (clk, rst_n, ve[D_EXP], e_y, 32'h3F800000, den, f_eg3);
    wire [3:0] vd;
    ot_hdc_vline #(.D(3)) u_vd (.clk(clk), .rst_n(rst_n), .v(ve[D_EXP]), .vd(vd));
    ot_hdc_v41x_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(vd[3]), .a(32'h3F800000), .b(den), .y(y_eg), .vo(),
                            .fault(f_eg4));
    assign y = (fn_out == SFU_RSQRT) ? y_rsq : (fn_out == SFU_SQRT) ? y_sq : (fn_out == SFU_SPSQRT) ? y_sp : y_eg;
    assign fault = f_rsq | f_sq | f_sp | f_eg1 | f_eg2 | f_eg3 | f_eg4;
endmodule
