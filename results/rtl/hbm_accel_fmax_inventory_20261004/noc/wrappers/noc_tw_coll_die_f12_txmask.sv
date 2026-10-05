`timescale 1ns/1ps
// Timing wrapper (fmax closure, noc family), successor endpoint ot_gpu_coll_endpoint_f12: one die's on-die collective path of the GPU-organised HBM
// baseline -- ot_gpu_coll_mux (NSM SMs share the endpoint) + ot_gpu_coll_endpoint (segmentation, tag check,
// reassembly, TX/RX ot_gpu_cdc_fifo).  clk_sm and clk_link are the SAME clock here (both 1.2 GHz domains):
// the Gray-pointer synchroniser paths and the afifo storage->read paths are timed as single-cycle paths,
// which is pessimistic against the real asynchronous constraint (set_max_delay on the Gray buses).
module noc_tw_coll_die_f12_txmask #(
    parameter integer TX_MASK_LA = 0,
    parameter integer NSM = 2,
    parameter integer NL  = 128,
    parameter integer R   = 2,
    parameter integer RANK = 0,
    parameter integer PW  = 32 * 16 + 2 + 32
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [NSM-1:0]        s_req_v,
    output wire [NSM-1:0]        s_req_rdy,
    input  wire [NSM-1:0]        s_mode,
    input  wire [NSM*8-1:0]      s_count,
    input  wire [NSM*NL*32-1:0]  s_data,
    output wire [NSM-1:0]        s_rsp_v,
    input  wire [NSM-1:0]        s_rsp_rdy,
    output wire [NL*32-1:0]      s_rsp_data,
    output wire                  fault,
    output wire                  lk_tx_v,
    output wire [PW-1:0]         lk_tx_rec,
    input  wire                  lk_rx_v,
    input  wire [PW-1:0]         lk_rx_rec
);
    wire m_req_v, m_req_rdy, m_mode, m_rsp_v, m_rsp_rdy;
    wire [7:0] m_count;
    wire [NL*32-1:0] m_data, m_rsp_data;
    ot_gpu_coll_mux_f12 #(.ENABLE(1), .NSM(NSM), .NL(NL)) u_cmux (
        .clk(clk), .rst_n(rst_n), .s_req_v(s_req_v), .s_req_rdy(s_req_rdy), .s_mode(s_mode),
        .s_count(s_count), .s_data(s_data), .s_rsp_v(s_rsp_v), .s_rsp_rdy(s_rsp_rdy), .s_rsp_data(s_rsp_data),
        .m_req_v(m_req_v), .m_req_rdy(m_req_rdy), .m_mode(m_mode), .m_count(m_count), .m_data(m_data),
        .m_rsp_v(m_rsp_v), .m_rsp_rdy(m_rsp_rdy), .m_rsp_data(m_rsp_data));
    ot_gpu_coll_endpoint_f12_txmask #(.TX_MASK_LA(TX_MASK_LA), .XREG(1), .ENABLE(1), .NL(NL), .R(R), .RANK(RANK)) u_ep (
        .clk_sm(clk), .rst_sm_n(rst_n), .coll_req_v(m_req_v), .coll_req_rdy(m_req_rdy), .coll_mode(m_mode),
        .coll_count(m_count), .coll_data(m_data), .coll_rsp_v(m_rsp_v), .coll_rsp_rdy(m_rsp_rdy),
        .coll_rsp_data(m_rsp_data), .coll_fault(fault), .clk_link(clk), .rst_link_n(rst_n),
        .lk_tx_v(lk_tx_v), .lk_tx_rec(lk_tx_rec), .lk_rx_v(lk_rx_v), .lk_rx_rec(lk_rx_rec));
endmodule
