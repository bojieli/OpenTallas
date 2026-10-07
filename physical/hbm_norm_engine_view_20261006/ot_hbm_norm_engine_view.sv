`timescale 1ns/1ps
// Physical view of the HBM accelerator's N64 / D5120 / KIND0 RMSNorm engine (ot_dsrom_su_norm with the owner-pinned
// library selection of the Gibbs bench engine_recipe: LM5 LA6 RXS1 SXC1 FREG1 RW9 BW9, HC1 RD0 QUANT1).
// The engine is a fixed-schedule stream (valid + data, no ready), so the boundary is latency-insensitive by
// construction: every input pin is captured by a flop, every output pin is launched by a flop, reset is released
// synchronously.  Cost: +1 edge in and +1 edge out; the integrated stream already budgets BCAST=7 / RET=8 wire stages
// around the engine, so two of those stages become the pin registers (net cycle cost 0).
module ot_hbm_norm_engine_view (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 go,
    input  wire                 in_v,
    input  wire [4*64*32-1:0]   in_x,
    input  wire [127:0]         pre,
    input  wire [31:0]          n_f,
    input  wire [31:0]          eps,
    input  wire                 wl_v,
    input  wire [7:0]           wl_i,
    input  wire [64*32-1:0]     wl_d,
    input  wire [31:0]          cos_t,
    input  wire [31:0]          sin_t,
    output wire                 y_v,
    output wire [7:0]           y_i,
    output wire [64*32-1:0]     y,
    output wire                 r_v,
    output wire [31:0]          r,
    output wire                 q_v,
    output wire [7:0]           q_i,
    output wire [2*256-1:0]     q_codes,
    output wire [2*10-1:0]      q_e,
    output wire [2*512-1:0]     q_y,
    output wire                 ro_v,
    output wire [64*32-1:0]     ro,
    output wire                 fault
);
    // reset: asynchronous assert, synchronous release (two flops)
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rstn = rs[1];
    // input capture, no logic ahead of the flops
    reg go_c, in_v_c, wl_v_c; reg [7:0] wl_i_c;
    reg [4*64*32-1:0] x_c; reg [127:0] pre_c; reg [31:0] nf_c, eps_c, cos_c, sin_c; reg [64*32-1:0] wl_d_c;
    always @(posedge clk) begin
        go_c <= go; in_v_c <= in_v; wl_v_c <= wl_v; wl_i_c <= wl_i;
        x_c <= in_x; pre_c <= pre; nf_c <= n_f; eps_c <= eps; cos_c <= cos_t; sin_c <= sin_t; wl_d_c <= wl_d;
    end
    wire e_y_v, e_r_v, e_q_v, e_ro_v, e_fault;
    wire [7:0] e_y_i, e_q_i; wire [64*32-1:0] e_y, e_ro; wire [31:0] e_r;
    wire [2*256-1:0] e_qc; wire [2*10-1:0] e_qe; wire [2*512-1:0] e_qy;
    ot_dsrom_su_norm #(.N(64), .D(5120), .HC(1), .RD(0), .QUANT(1), .RW(9), .BW(9), .LM(5), .LA(6),
                       .RXS(1), .SXC(1), .FREG(1), .MEMSPLIT(1)) u_engine (
        .clk(clk), .rst_n(rstn), .go(go_c), .in_v(in_v_c), .in_x(x_c), .pre(pre_c), .n_f(nf_c), .eps(eps_c),
        .wl_v(wl_v_c), .wl_i(wl_i_c), .wl_d(wl_d_c), .cos_t(cos_c), .sin_t(sin_c),
        .y_v(e_y_v), .y_i(e_y_i), .y(e_y), .r_v(e_r_v), .r(e_r),
        .q_v(e_q_v), .q_i(e_q_i), .q_codes(e_qc), .q_e(e_qe), .q_y(e_qy),
        .ro_v(e_ro_v), .ro(e_ro), .fault(e_fault));
    // output launch flops
    reg y_v_o, r_v_o, q_v_o, ro_v_o, fault_o; reg [7:0] y_i_o, q_i_o;
    reg [64*32-1:0] y_o, ro_o; reg [31:0] r_o; reg [2*256-1:0] qc_o; reg [2*10-1:0] qe_o; reg [2*512-1:0] qy_o;
    always @(posedge clk or negedge rstn) if (!rstn) begin
        y_v_o <= 0; r_v_o <= 0; q_v_o <= 0; ro_v_o <= 0; fault_o <= 0;
    end else begin
        y_v_o <= e_y_v; r_v_o <= e_r_v; q_v_o <= e_q_v; ro_v_o <= e_ro_v; fault_o <= e_fault;
    end
    always @(posedge clk) begin
        y_i_o <= e_y_i; q_i_o <= e_q_i; y_o <= e_y; ro_o <= e_ro; r_o <= e_r; qc_o <= e_qc; qe_o <= e_qe; qy_o <= e_qy;
    end
    assign y_v = y_v_o; assign r_v = r_v_o; assign q_v = q_v_o; assign ro_v = ro_v_o; assign fault = fault_o;
    assign y_i = y_i_o; assign q_i = q_i_o; assign y = y_o; assign ro = ro_o; assign r = r_o;
    assign q_codes = qc_o; assign q_e = qe_o; assign q_y = qy_o;
endmodule
