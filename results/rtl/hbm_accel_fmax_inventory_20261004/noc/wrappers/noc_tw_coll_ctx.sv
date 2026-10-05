`timescale 1ns/1ps
// In-context timing wrappers of one die's baseline collective path (ot_gpu_coll_mux NSM 2 + endpoint NL 128, R 2,
// RANK 0), registered on every port exactly as rtl/hbm_accel/collective/ot_hbm_accel_coll_port_ctx.sv (HA3 = 0)
// registers them (SM-side coll_* registers, link pipe first stage), so --false-path-io leaves every internal path
// timed register to register.  clk_link is tied to clk_sm (conservative for the Gray pointers).
//   noc_tw_coll_ctx_base: ot_gpu_coll_endpoint (as built)     noc_tw_coll_ctx_f12: ot_gpu_coll_mux_f12 + ot_gpu_coll_endpoint_f12
//   noc_tw_coll_ctx_f12x: ot_gpu_coll_endpoint_f12 XREG = 1
module noc_tw_coll_ctx_base (
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
    always @(posedge clk) begin
        o_req_rdy <= req_rdy; o_rsp_v <= rsp_v; o_rsp_data <= rsp_data; o_fault <= fault;
        o_tx_v <= tx_v; o_tx_rec <= tx_rec;
    end
endmodule
module noc_tw_coll_ctx_f12 (
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
    ot_gpu_coll_mux_f12 #(.ENABLE(1), .NSM(NSM), .NL(NL)) u_mux (
        .clk(clk), .rst_n(rst_n), .s_req_v(req_v), .s_req_rdy(req_rdy), .s_mode(mode), .s_count(count),
        .s_data(data), .s_rsp_v(rsp_v), .s_rsp_rdy(rsp_rdy), .s_rsp_data(rsp_data), .m_req_v(m_req_v),
        .m_req_rdy(m_req_rdy), .m_mode(m_mode), .m_count(m_count), .m_data(m_data), .m_rsp_v(m_rsp_v),
        .m_rsp_rdy(m_rsp_rdy), .m_rsp_data(m_rsp_data));
    ot_gpu_coll_endpoint_f12 #(.ENABLE(1), .NL(NL), .R(2), .RANK(0)) u_ep (
        .clk_sm(clk), .rst_sm_n(rst_n), .coll_req_v(m_req_v), .coll_req_rdy(m_req_rdy), .coll_mode(m_mode),
        .coll_count(m_count), .coll_data(m_data), .coll_rsp_v(m_rsp_v), .coll_rsp_rdy(m_rsp_rdy),
        .coll_rsp_data(m_rsp_data), .coll_fault(fault), .clk_link(clk), .rst_link_n(rst_n),
        .lk_tx_v(tx_v), .lk_tx_rec(tx_rec), .lk_rx_v(rx_v), .lk_rx_rec(rx_rec));
    always @(posedge clk) begin
        o_req_rdy <= req_rdy; o_rsp_v <= rsp_v; o_rsp_data <= rsp_data; o_fault <= fault;
        o_tx_v <= tx_v; o_tx_rec <= tx_rec;
    end
endmodule
module noc_tw_coll_ctx_f12x (
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
    ot_gpu_coll_mux_f12 #(.ENABLE(1), .NSM(NSM), .NL(NL)) u_mux (
        .clk(clk), .rst_n(rst_n), .s_req_v(req_v), .s_req_rdy(req_rdy), .s_mode(mode), .s_count(count),
        .s_data(data), .s_rsp_v(rsp_v), .s_rsp_rdy(rsp_rdy), .s_rsp_data(rsp_data), .m_req_v(m_req_v),
        .m_req_rdy(m_req_rdy), .m_mode(m_mode), .m_count(m_count), .m_data(m_data), .m_rsp_v(m_rsp_v),
        .m_rsp_rdy(m_rsp_rdy), .m_rsp_data(m_rsp_data));
    ot_gpu_coll_endpoint_f12 #(.ENABLE(1), .XREG(1), .NL(NL), .R(2), .RANK(0)) u_ep (
        .clk_sm(clk), .rst_sm_n(rst_n), .coll_req_v(m_req_v), .coll_req_rdy(m_req_rdy), .coll_mode(m_mode),
        .coll_count(m_count), .coll_data(m_data), .coll_rsp_v(m_rsp_v), .coll_rsp_rdy(m_rsp_rdy),
        .coll_rsp_data(m_rsp_data), .coll_fault(fault), .clk_link(clk), .rst_link_n(rst_n),
        .lk_tx_v(tx_v), .lk_tx_rec(tx_rec), .lk_rx_v(rx_v), .lk_rx_rec(rx_rec));
    always @(posedge clk) begin
        o_req_rdy <= req_rdy; o_rsp_v <= rsp_v; o_rsp_data <= rsp_data; o_fault <= fault;
        o_tx_v <= tx_v; o_tx_rec <= tx_rec;
    end
endmodule
