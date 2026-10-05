`timescale 1ns/1ps
// Same full128 two-SM registered parent boundary as r6X; no new IO exceptions.
module noc_tw_coll_ctx_owner64 #(parameter integer TX_MASK_LA=0, parameter integer OWNER64=0, parameter integer RXOH=0, parameter integer RDUP=8) (
    input  wire clk, input wire rst_n,
    input  wire [1:0] i_req_v, input wire [1:0] i_mode, input wire [15:0] i_count, input wire [8191:0] i_data,
    input  wire [1:0] i_rsp_rdy,
    output reg  [1:0] o_req_rdy, output reg [1:0] o_rsp_v, output reg [4095:0] o_rsp_data, output reg o_fault,
    output reg  o_tx_v, output reg [545:0] o_tx_rec, input wire i_rx_v, input wire [545:0] i_rx_rec
);
    localparam integer NSM = 2, NL = 128, PW = 546;
    reg [1:0] req_v, mode, rsp_rdy;
    reg [15:0] count;
    reg [8191:0] data;
    reg rx_v;
    reg [PW-1:0] rx_rec;
    always @(posedge clk) begin
        req_v <= i_req_v; mode <= i_mode; count <= i_count; data <= i_data; rsp_rdy <= i_rsp_rdy;
        rx_v <= i_rx_v; rx_rec <= i_rx_rec;
    end
    wire [1:0] req_rdy, rsp_v;
    wire [NL*32-1:0] rsp_data;
    wire fault, tx_v;
    wire [PW-1:0] tx_rec;
    wire m_req_v, m_req_rdy, m_mode, m_rsp_v, m_rsp_rdy;
    wire [7:0] m_count;
    wire [NL*32-1:0] m_data, m_rsp_data;
    ot_gpu_coll_mux_owner64 #(.OWNER64(OWNER64), .ENABLE(1), .NSM(NSM), .NL(NL)) u_mux (
        .clk(clk), .rst_n(rst_n), .s_req_v(req_v), .s_req_rdy(req_rdy), .s_mode(mode), .s_count(count),
        .s_data(data), .s_rsp_v(rsp_v), .s_rsp_rdy(rsp_rdy), .s_rsp_data(rsp_data), .m_req_v(m_req_v),
        .m_req_rdy(m_req_rdy), .m_mode(m_mode), .m_count(m_count), .m_data(m_data), .m_rsp_v(m_rsp_v),
        .m_rsp_rdy(m_rsp_rdy), .m_rsp_data(m_rsp_data));
    ot_gpu_coll_endpoint_f12_cuts #(.RXOH(RXOH), .RDUP(RDUP), .TX_MASK_LA(TX_MASK_LA), .ENABLE(1), .XREG(1), .NL(NL), .R(2), .RANK(0)) u_ep (
        .clk_sm(clk), .rst_sm_n(rst_n), .coll_req_v(m_req_v), .coll_req_rdy(m_req_rdy), .coll_mode(m_mode),
        .coll_count(m_count), .coll_data(m_data), .coll_rsp_v(m_rsp_v), .coll_rsp_rdy(m_rsp_rdy),
        .coll_rsp_data(m_rsp_data), .coll_fault(fault), .clk_link(clk), .rst_link_n(rst_n),
        .lk_tx_v(tx_v), .lk_tx_rec(tx_rec), .lk_rx_v(rx_v), .lk_rx_rec(rx_rec));
    always @(posedge clk) begin
        o_req_rdy <= req_rdy; o_rsp_v <= rsp_v; o_rsp_data <= rsp_data; o_fault <= fault;
        o_tx_v <= tx_v; o_tx_rec <= tx_rec;
    end
endmodule
