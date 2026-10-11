`timescale 1ns/1ps
// Physical view of the HBM accelerator's N64 / D5120 / KIND0 RMSNorm engine (ot_dsrom_su_norm with the owner-pinned
// library selection of the Gibbs bench engine_recipe: LM5 LA6 RXS1 SXC1 FREG1 RW9 BW9, HC1 RD0 QUANT1).
// The engine is a fixed-schedule stream (valid + data, no ready), so the boundary is latency-insensitive by
// construction: every input pin is captured by a flop, every output pin is launched by a flop, reset is released
// synchronously.  Cost: +1 edge in and +1 edge out; the integrated stream already budgets BCAST=7 / RET=8 wire stages
// around the engine, so two of those stages become the pin registers (net cycle cost 0).
//
// Feasibility fixes (fe-push-hgi-1010, opt-in; RLY=0 XST=0 is the pinned view, byte-for-byte in behaviour):
//   RLY=1: the rst_n port drives only ot_rst_relay flops (the engine's own relay: 4 lane regions + the control/tail
//          region, ot_dsrom_su_norm RLY=1; and a 1-region relay for the 5 output valid / fault flops), instead of one
//          local 2-flop sync whose output fanned out to every reset flop of the engine.  Release: 3 edges (was 2).
//   XST=1: a second register stage on every input (valid and data alike, so they stay aligned): at a 1,400 um outline
//          the pin capture flop -> engine lane wire is otherwise one stage over the 504 um reach.  +1 cycle in, taken
//          from the BCAST wire budget (BCAST=7 already counts the capture stage).
module ot_hbm_norm_engine_view #(
    parameter integer RLY = 0,
    parameter integer XST = 0
) (
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
    wire rstn, rst_e;                   // rstn: the output valid flops; rst_e: the engine's rst_n
    generate if (RLY) begin : g_rly
        wire [0:0] ro_rst;
        ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rly_o (.clk(clk), .rst_n_in(rst_n), .rst_n(ro_rst));
        assign rstn = ro_rst[0];
        assign rst_e = rst_n;           // the engine relays the port itself (ot_dsrom_su_norm RLY=1)
    end else begin : g_sync
        reg [1:0] rs;
        always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
        assign rstn = rs[1];
        assign rst_e = rs[1];
    end endgenerate
    // input capture, no logic ahead of the flops
    reg go_c, in_v_c, wl_v_c; reg [7:0] wl_i_c;
    reg [4*64*32-1:0] x_c; reg [127:0] pre_c; reg [31:0] nf_c, eps_c, cos_c, sin_c; reg [64*32-1:0] wl_d_c;
    always @(posedge clk) begin
        go_c <= go; in_v_c <= in_v; wl_v_c <= wl_v; wl_i_c <= wl_i;
        x_c <= in_x; pre_c <= pre; nf_c <= n_f; eps_c <= eps; cos_c <= cos_t; sin_c <= sin_t; wl_d_c <= wl_d;
    end
    // XST: the second stage (placed between the pin bank and the lanes)
    wire go_e, in_v_e, wl_v_e; wire [7:0] wl_i_e;
    wire [4*64*32-1:0] x_e; wire [127:0] pre_e; wire [31:0] nf_e, eps_e, cos_e, sin_e; wire [64*32-1:0] wl_d_e;
    generate if (XST) begin : g_xst
        reg go_s, in_v_s, wl_v_s; reg [7:0] wl_i_s;
        reg [4*64*32-1:0] x_s; reg [127:0] pre_s; reg [31:0] nf_s, eps_s, cos_s, sin_s; reg [64*32-1:0] wl_d_s;
        always @(posedge clk) begin
            go_s <= go_c; in_v_s <= in_v_c; wl_v_s <= wl_v_c; wl_i_s <= wl_i_c;
            x_s <= x_c; pre_s <= pre_c; nf_s <= nf_c; eps_s <= eps_c; cos_s <= cos_c; sin_s <= sin_c; wl_d_s <= wl_d_c;
        end
        assign go_e = go_s; assign in_v_e = in_v_s; assign wl_v_e = wl_v_s; assign wl_i_e = wl_i_s;
        assign x_e = x_s; assign pre_e = pre_s; assign nf_e = nf_s; assign eps_e = eps_s; assign cos_e = cos_s;
        assign sin_e = sin_s;
`ifdef OT_NEV_MUT_SKEW
        assign wl_d_e = wl_d_c;         // NEGATIVE CONTROL: gain data skips the second stage (one cycle ahead of wl_v / wl_i)
`else
        assign wl_d_e = wl_d_s;
`endif
    end else begin : g_nxst
        assign go_e = go_c; assign in_v_e = in_v_c; assign wl_v_e = wl_v_c; assign wl_i_e = wl_i_c;
        assign x_e = x_c; assign pre_e = pre_c; assign nf_e = nf_c; assign eps_e = eps_c; assign cos_e = cos_c;
        assign sin_e = sin_c; assign wl_d_e = wl_d_c;
    end endgenerate
    wire e_y_v, e_r_v, e_q_v, e_ro_v, e_fault;
    wire [7:0] e_y_i, e_q_i; wire [64*32-1:0] e_y, e_ro; wire [31:0] e_r;
    wire [2*256-1:0] e_qc; wire [2*10-1:0] e_qe; wire [2*512-1:0] e_qy;
    ot_dsrom_su_norm #(.N(64), .D(5120), .HC(1), .RD(0), .QUANT(1), .RW(9), .BW(9), .LM(5), .LA(6),
                       .RXS(1), .SXC(1), .FREG(1), .MEMSPLIT(0), .MEM(1), .RLY(RLY), .RGN(4)) u_engine (
        .clk(clk), .rst_n(rst_e), .go(go_e), .in_v(in_v_e), .in_x(x_e), .pre(pre_e), .n_f(nf_e), .eps(eps_e),
        .wl_v(wl_v_e), .wl_i(wl_i_e), .wl_d(wl_d_e), .cos_t(cos_e), .sin_t(sin_e),
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
