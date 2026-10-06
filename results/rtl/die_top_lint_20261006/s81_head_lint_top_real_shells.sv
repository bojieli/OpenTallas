// die_top_lint: REAL-INTERFACE shells (port lists parsed from the RTL named in each header; interiors are
// the element owners' lint scope).

// rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv
module ot_v41_rom_elem_q_qp_w10 #(parameter NB = 2, parameter MTP = 1, parameter EARLY = 1, parameter FAST = 1, parameter PP = 1, parameter QTIMING_FIX = 1, parameter QPIPE = 1, parameter QP_XS = 1, parameter QP_CAP = 0, parameter QP_P1 = 1, parameter QP_CSAM = 10) (
    input wire [0:0] clk,
    input wire [0:0] rst_n,
    input wire [0:0] cfg_v,
    input wire [4:0] cfg_a,
    input wire [47:0] cfg_d,
    input wire [0:0] go,
    input wire [0:0] xs_v,
    input wire [7:0] xs_p,
    input wire [2:0] xs_b,
    input wire [1:0] xs_sv,
    input wire [255:0] xs_q0,
    input wire [9:0] xs_e0,
    input wire [255:0] xs_q1,
    input wire [9:0] xs_e1,
    input wire [2:0] xs_pos,
    output wire [1:0] pv,
    output wire [63:0] pval,
    output wire [31:0] prow,
    output wire [9:0] pseg,
    output wire [9:0] pnseg,
    output wire [1:0] perr,
    output wire [5:0] ppos,
    output wire [0:0] busy,
    output wire [0:0] fault);
    wire lint_in = ^{^clk, ^rst_n, ^cfg_v, ^cfg_a, ^cfg_d, ^go, ^xs_v, ^xs_p, ^xs_b, ^xs_sv, ^xs_q0, ^xs_e0, ^xs_q1, ^xs_e1, ^xs_pos};
    reg [1:0] r_pv; always @(posedge clk) r_pv <= {2{lint_in}}; assign pv = r_pv;
    reg [63:0] r_pval; always @(posedge clk) r_pval <= {64{lint_in}}; assign pval = r_pval;
    reg [31:0] r_prow; always @(posedge clk) r_prow <= {32{lint_in}}; assign prow = r_prow;
    reg [9:0] r_pseg; always @(posedge clk) r_pseg <= {10{lint_in}}; assign pseg = r_pseg;
    reg [9:0] r_pnseg; always @(posedge clk) r_pnseg <= {10{lint_in}}; assign pnseg = r_pnseg;
    reg [1:0] r_perr; always @(posedge clk) r_perr <= {2{lint_in}}; assign perr = r_perr;
    reg [5:0] r_ppos; always @(posedge clk) r_ppos <= {6{lint_in}}; assign ppos = r_ppos;
    reg [0:0] r_busy; always @(posedge clk) r_busy <= {1{lint_in}}; assign busy = r_busy;
    reg [0:0] r_fault; always @(posedge clk) r_fault <= {1{lint_in}}; assign fault = r_fault;
endmodule

// rtl/v41die/ot_v41_retn_w17w10.sv
module ot_v41_retn_w17w10 (
    input wire [0:0] clk,
    input wire [0:0] rst_n,
    input wire [0:0] a_v,
    input wire [31:0] a_t,
    input wire [31:0] a_d,
    input wire [0:0] a_e,
    input wire [0:0] b_v,
    input wire [31:0] b_t,
    input wire [31:0] b_d,
    input wire [0:0] b_e,
    output wire [0:0] o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire [0:0] o_e,
    output wire [0:0] fault,
    output wire [0:0] quiet);
    wire lint_in = ^{^clk, ^rst_n, ^a_v, ^a_t, ^a_d, ^a_e, ^b_v, ^b_t, ^b_d, ^b_e};
    reg [0:0] r_o_v; always @(posedge clk) r_o_v <= {1{lint_in}}; assign o_v = r_o_v;
    reg [31:0] r_o_t; always @(posedge clk) r_o_t <= {32{lint_in}}; assign o_t = r_o_t;
    reg [31:0] r_o_d; always @(posedge clk) r_o_d <= {32{lint_in}}; assign o_d = r_o_d;
    reg [0:0] r_o_e; always @(posedge clk) r_o_e <= {1{lint_in}}; assign o_e = r_o_e;
    reg [0:0] r_fault; always @(posedge clk) r_fault <= {1{lint_in}}; assign fault = r_fault;
    reg [0:0] r_quiet; always @(posedge clk) r_quiet <= {1{lint_in}}; assign quiet = r_quiet;
endmodule
