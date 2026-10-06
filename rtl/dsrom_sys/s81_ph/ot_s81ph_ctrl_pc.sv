`timescale 1ns/1ps
// CLAUDE S81-PH: one pseudo-channel of the S81 HBM controller boundary dsfd_ctrl (contract:
// results/rtl/s81_ph_20261006/ctrl/contract.json).  Stream domain (cks): the svc's request word rq (341 b, credit
// flow: the svc holds DQ credits per PC, one returned on rk per request the PHY has taken), the response word
// {kr_v, beat, tag, data} on rd (valid-only: the stream side drains every cycle), write-done pulses wd.
// HBM domain (ckh): the PHY K/KR port of this PC (ot_hbm3e_phy_v41x_aw30_e8p5: k_v/k_rdy/k_addr/k_len/k_tag/k_we/
// k_wdata/k_wstrb/k_wr_done, kr_v/kr_rdy/kr_tag/kr_beat/kr_data).
// Every die input is captured in a flop at the pin, every die output is a flop, except the PHY k_rdy, which enters
// the request hand-off (fire = k_v_q & k_rdy: one gate before the hold register's load enable) -- the PHY's own
// valid/ready contract, on the abutted PHY face.
// Latency (measured, tb_dsfd_ctrl): request rq pin -> k_v at the PHY = 1 cks + FIFO crossing (2 ckh sync) + 1 ckh;
// response kr at the PHY -> rd = 1 ckh pin reg + 1 ckh write + 2 cks sync + 1 cks out reg.
module ot_s81ph_ctrl_pc #(
    parameter integer DQ = 8,       // request FIFO entries = svc credits
    parameter integer DR = 8,       // response landing entries
    parameter integer AW = 30,
    parameter integer TW = 17
) (
    input  wire          cks,
    input  wire          ckh,
    input  wire          rst,         // die reset (active low, asynchronous): synchronised locally into cks and ckh
    input  wire [1:0]    ci,          // status chain in {fault, live} (registered in the neighbouring column)
    output reg  [1:0]    co,          // status chain out
    // stream side (die)
    input  wire [340:0]  rq,          // {wdata 256, wstrb 32, tag 17, len 4, addr 30, we, v}
    output wire          rk,          // request credit pulse
    output reg           rv,          // response valid
    output reg  [255:0]  r_data,
    output reg  [TW-1:0] r_tag,
    output reg  [3:0]    r_beat,
    output wire          wd,          // write-done pulse
    output wire          s_ovf,       // sticky: request beyond credits (dropped)
    // HBM side (PHY)
    output reg           k_v,
    input  wire          k_rdy,
    output reg  [AW-1:0] k_addr,
    output reg  [3:0]    k_len,
    output reg  [TW-1:0] k_tag,
    output reg           k_we,
    output reg  [255:0]  k_wdata,
    output reg  [31:0]   k_wstrb,
    input  wire          k_wr_done,
    input  wire          kr_v,
    output wire          kr_rdy,
    input  wire [TW-1:0] kr_tag,
    input  wire [3:0]    kr_beat,
    input  wire [255:0]  kr_data
);
    localparam integer QW = 340, RW = 256 + TW + 4;
    // ---- local reset synchronisers (one per column and domain: no die-wide synchronous reset tree)
    wire srst_n, hrst_n;
    ot_s81ph_sync u_srs (.clk(cks), .rst_n(rst), .d(1'b1), .q(srst_n));
    ot_s81ph_sync u_hrs (.clk(ckh), .rst_n(rst), .d(1'b1), .q(hrst_n));
    wire h_live;
    ot_s81ph_sync u_hl (.clk(cks), .rst_n(srst_n), .d(hrst_n), .q(h_live));
    always @(posedge cks or negedge srst_n)
        if (!srst_n) co <= 2'b00; else co <= {ci[1] | s_ovf, ci[0] & h_live};
    // ---- stream side: request pin register -> request FIFO
    reg [340:0] rq_q;
    always @(posedge cks or negedge srst_n)
        if (!srst_n) rq_q <= 341'd0; else rq_q <= rq;
    wire          q_v;
    wire [QW-1:0] q_d;
    reg           h_pop;
    wire          q_rdy_unused;
    ot_s81ph_afifo #(.W(QW), .DEPTH(DQ), .AF(1)) u_q (
        .wclk(cks), .wrst_n(srst_n), .w_v(rq_q[0]), .w_d(rq_q[340:1]), .w_rdy(q_rdy_unused), .w_credit(rk), .w_ovf(s_ovf),
        .rclk(ckh), .rrst_n(hrst_n), .r_v(q_v), .r_pop(h_pop), .r_d(q_d));
    // ---- HBM side: request hold register (the PHY's valid/ready)
    wire fire = k_v && k_rdy;
    always @(*) h_pop = q_v && (!k_v || fire);
    always @(posedge ckh or negedge hrst_n)
        if (!hrst_n) begin
            k_v <= 1'b0; k_we <= 1'b0; k_addr <= {AW{1'b0}}; k_len <= 4'd0; k_tag <= {TW{1'b0}};
            k_wdata <= 256'd0; k_wstrb <= 32'd0;
        end else if (!k_v || fire) begin
            k_v <= q_v;
`ifdef S81PH_MUT_PACK
            if (q_v) {k_wdata, k_wstrb, k_tag, k_len, k_addr, k_we} <= q_d ^ {{(QW-36){1'b0}}, 1'b1, 35'd0};   // mutant: tag bit 0 flipped
`else
            if (q_v) {k_wdata, k_wstrb, k_tag, k_len, k_addr, k_we} <= q_d;
`endif
        end
    // ---- HBM side: response pin register -> landing FIFO (kr_rdy reserves the word in the pin register)
    reg           kr_q;
    reg [RW-1:0]  krd_q;
    wire          l_rdy;
    assign kr_rdy = l_rdy;
    always @(posedge ckh or negedge hrst_n)
        if (!hrst_n) begin kr_q <= 1'b0; krd_q <= {RW{1'b0}}; end
        else begin
            kr_q <= kr_v && l_rdy;
            if (kr_v && l_rdy) krd_q <= {kr_data, kr_tag, kr_beat};
        end
    wire          l_v;
    wire [RW-1:0] l_d;
    wire          l_ovf, l_cr;
    ot_s81ph_afifo #(.W(RW), .DEPTH(DR), .AF(2)) u_r (
        .wclk(ckh), .wrst_n(hrst_n), .w_v(kr_q), .w_d(krd_q), .w_rdy(l_rdy), .w_credit(l_cr), .w_ovf(l_ovf),
        .rclk(cks), .rrst_n(srst_n), .r_v(l_v), .r_pop(1'b1), .r_d(l_d));
    always @(posedge cks or negedge srst_n)
        if (!srst_n) begin rv <= 1'b0; r_data <= 256'd0; r_tag <= {TW{1'b0}}; r_beat <= 4'd0; end
        else begin
            rv <= l_v;
`ifdef S81PH_MUT_BEAT
            if (l_v) {r_data, r_tag, r_beat} <= {l_d[RW-1:4], l_d[2:0], l_d[3]};                        // mutant: beat bits rotated
`else
            if (l_v) {r_data, r_tag, r_beat} <= l_d;
`endif
        end
    // ---- write done: HBM pin register -> pulse crossing
    reg wd_q;
    always @(posedge ckh or negedge hrst_n) if (!hrst_n) wd_q <= 1'b0; else wd_q <= k_wr_done;
    ot_s81ph_pulse_x #(.CW(4)) u_wd (.sclk(ckh), .srst_n(hrst_n), .s_p(wd_q), .dclk(cks), .drst_n(srst_n), .d_p(wd));
endmodule
