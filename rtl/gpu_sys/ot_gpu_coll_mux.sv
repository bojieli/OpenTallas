`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_coll_mux: the SMs of one die share the die's collective endpoint
// (as a GPU's SMs share its NVLink/NVLS ports).  The lowest-numbered
// requesting SM is granted when the endpoint is free; the grant is held until
// that SM accepted its response, so one collective is in flight per die and
// the dies issue collectives in program order (the kernels issue them from
// one SM per die, in the same order on every die).
// ENABLE = 0: inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_coll_mux #(
    parameter integer ENABLE = 0,
    parameter integer NSM    = 2,
    parameter integer NL     = 128
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
    output wire                  m_req_v,
    input  wire                  m_req_rdy,
    output wire                  m_mode,
    output wire [7:0]            m_count,
    output wire [NL*32-1:0]      m_data,
    input  wire                  m_rsp_v,
    output wire                  m_rsp_rdy,
    input  wire [NL*32-1:0]      m_rsp_data
);
generate if (ENABLE == 0) begin : g_off
    assign s_req_rdy = {NSM{1'b0}}; assign s_rsp_v = {NSM{1'b0}}; assign s_rsp_data = {NL*32{1'b0}};
    assign m_req_v = 1'b0; assign m_mode = 1'b0; assign m_count = 8'd0; assign m_data = {NL*32{1'b0}};
    assign m_rsp_rdy = 1'b0;
end else begin : g_on
    localparam integer SB = (NSM > 1) ? $clog2(NSM) : 1;
    reg          busy, sent;
    reg [SB-1:0] own;
    reg [SB-1:0] pick;
    reg          any;
    integer i;
    always @* begin
        any = 1'b0; pick = {SB{1'b0}};
        for (i = NSM - 1; i >= 0; i = i - 1) if (s_req_v[i]) begin any = 1'b1; pick = i[SB-1:0]; end
    end
    wire [SB-1:0] sel = busy ? own : pick;
    assign m_req_v = busy && !sent && s_req_v[own];
    assign m_mode = s_mode[own];
    assign m_count = s_count[own*8 +: 8];
    assign m_data = s_data[own*NL*32 +: NL*32];
    genvar s;
    for (s = 0; s < NSM; s = s + 1) begin : g_s
        assign s_req_rdy[s] = busy && !sent && (own == s) && m_req_rdy;
        assign s_rsp_v[s] = busy && sent && (own == s) && m_rsp_v;
    end
    assign s_rsp_data = m_rsp_data;
    assign m_rsp_rdy = busy && sent && s_rsp_rdy[own];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy <= 1'b0; sent <= 1'b0; own <= {SB{1'b0}}; end
        else begin
            if (!busy && any) begin busy <= 1'b1; sent <= 1'b0; own <= sel; end
            else if (busy && !sent && m_req_v && m_req_rdy) sent <= 1'b1;
            else if (busy && sent && m_rsp_v && m_rsp_rdy) begin busy <= 1'b0; sent <= 1'b0; end
        end
    end
end endgenerate
endmodule
