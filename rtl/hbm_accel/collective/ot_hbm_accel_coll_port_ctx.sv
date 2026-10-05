`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_coll_port_ctx: physical in-context wrapper of the HA3 collective
// port (ot_hbm_accel_coll_port, NSM = 2, NL = 128) and, for the A/B area
// ledger, of the baseline it replaces (ot_gpu_coll_mux + ot_gpu_coll_endpoint):
// every port faces a register (the SM side as the SMs' coll_* registers drive
// and sample it, the link side as the link pipe's first stage), so every
// internal path is timed register to register.  One clock: clk_link is tied to
// clk_sm, which times the clock-crossing FIFOs' paths at a full period
// (conservative for the gray-code pointers; their asynchronous behaviour is the
// unchanged ot_link_afifo's).
//   HA3 = 1: ot_hbm_accel_coll_port (FLAT = the FP pipe depth, 7 = SS pipes)
//   HA3 = 0: ot_gpu_coll_mux -> ot_gpu_coll_endpoint (the ablation's endpoint)
// ---------------------------------------------------------------------------
module ot_hbm_accel_coll_port_ctx #(
    parameter integer HA3  = 1,
    parameter integer FLAT = 7,
    parameter integer EPI  = 1         // 0: the cut-through port alone (no fused epilogue)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    i_req_v,
    input  wire [1:0]    i_mode,
    input  wire [15:0]   i_count,
    input  wire [8191:0] i_data,
    input  wire [1:0]    i_x,
    input  wire [15:0]   i_off,
    input  wire [15:0]   i_nown,
    input  wire [1:0]    i_fuse,
    input  wire [8191:0] i_resid,
    input  wire [1:0]    i_rsp_rdy,
    output reg  [1:0]    o_req_rdy,
    output reg  [1:0]    o_rsp_v,
    output reg  [4095:0] o_rsp_data,
    output reg  [31:0]   o_rsp_ss,
    output reg           o_rsp_err,
    output reg           o_fault,
    output reg           o_tx_v,
    output reg  [545:0]  o_tx_rec,
    input  wire          i_rx_v,
    input  wire [545:0]  i_rx_rec
);
    localparam integer NSM = 2, NL = 128, PW = 546;
    reg [1:0] req_v, mode, x, fuse, rsp_rdy;
    reg [15:0] count, off, nown;
    reg [8191:0] data, resid;
    reg rx_v;
    reg [PW-1:0] rx_rec;
    always @(posedge clk) begin
        req_v <= i_req_v; mode <= i_mode; count <= i_count; data <= i_data; x <= i_x; off <= i_off;
        nown <= i_nown; fuse <= i_fuse; resid <= i_resid; rsp_rdy <= i_rsp_rdy; rx_v <= i_rx_v; rx_rec <= i_rx_rec;
    end
    wire [1:0] req_rdy, rsp_v;
    wire [NL*32-1:0] rsp_data;
    wire [31:0] rsp_ss, st_coll;
    wire rsp_err, fault, tx_v;
    wire [PW-1:0] tx_rec;
    if (HA3 != 0) begin : g_ha3
        ot_hbm_accel_coll_port #(.ENABLE(1), .NSM(NSM), .NL(NL), .R(2), .RANK(0), .FLAT(FLAT), .EPI(EPI)) u_port (
            .clk_sm(clk), .rst_sm_n(rst_n), .s_req_v(req_v), .s_req_rdy(req_rdy), .s_mode(mode), .s_count(count),
            .s_data(data), .s_x(x), .s_off(off), .s_nown(nown), .s_fuse(fuse), .s_resid(resid), .s_rsp_v(rsp_v),
            .s_rsp_rdy(rsp_rdy), .s_rsp_data(rsp_data), .s_rsp_ss(rsp_ss), .s_rsp_err(rsp_err), .fault(fault),
            .st_coll(st_coll), .clk_link(clk), .rst_link_n(rst_n), .lk_tx_v(tx_v), .lk_tx_rec(tx_rec),
            .lk_rx_v(rx_v), .lk_rx_rec(rx_rec));
    end else begin : g_base
        wire m_req_v, m_req_rdy, m_mode, m_rsp_v, m_rsp_rdy;
        wire [7:0] m_count;
        wire [NL*32-1:0] m_data, m_rsp_data;
        ot_gpu_coll_mux #(.ENABLE(1), .NSM(NSM), .NL(NL)) u_mux (
            .clk(clk), .rst_n(rst_n), .s_req_v(req_v), .s_req_rdy(req_rdy), .s_mode(mode), .s_count(count),
            .s_data(data), .s_rsp_v(rsp_v), .s_rsp_rdy(rsp_rdy), .s_rsp_data(rsp_data), .m_req_v(m_req_v),
            .m_req_rdy(m_req_rdy), .m_mode(m_mode), .m_count(m_count), .m_data(m_data), .m_rsp_v(m_rsp_v),
            .m_rsp_rdy(m_rsp_rdy), .m_rsp_data(m_rsp_data));
        ot_gpu_coll_endpoint #(.ENABLE(1), .NL(NL), .R(2), .RANK(0)) u_ep (
            .clk_sm(clk), .rst_sm_n(rst_n), .coll_req_v(m_req_v), .coll_req_rdy(m_req_rdy), .coll_mode(m_mode),
            .coll_count(m_count), .coll_data(m_data), .coll_rsp_v(m_rsp_v), .coll_rsp_rdy(m_rsp_rdy),
            .coll_rsp_data(m_rsp_data), .coll_fault(fault), .clk_link(clk), .rst_link_n(rst_n),
            .lk_tx_v(tx_v), .lk_tx_rec(tx_rec), .lk_rx_v(rx_v), .lk_rx_rec(rx_rec));
        assign rsp_ss = 32'd0; assign rsp_err = 1'b0; assign st_coll = 32'd0;
        /* verilator lint_off UNUSED */
        wire unused_b = &{1'b0, x, off, nown, fuse, resid};
        /* verilator lint_on UNUSED */
    end
    always @(posedge clk) begin
        o_req_rdy <= req_rdy; o_rsp_v <= rsp_v; o_rsp_data <= rsp_data; o_rsp_ss <= rsp_ss; o_rsp_err <= rsp_err;
        o_fault <= fault; o_tx_v <= tx_v; o_tx_rec <= tx_rec;
    end
endmodule
