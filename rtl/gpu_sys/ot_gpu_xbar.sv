`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_xbar: clk_mem crossbar of the GPU-organised HBM comparator die:
// NC MREQ clients (SM load/store units, bulk copy, collective endpoint) to NS
// address-interleaved L2 slices.
//
//  * slice select: byte-address bits [7 +: log2(NS)] (128-byte interleave);
//    the full address is forwarded (the slice and partition strip the bits);
//  * per slice, round-robin request arbitration among the clients that target
//    it (combinational grant, pointer advances past the winner on handshake);
//  * the slice-side tag is {client id, client tag} (TW + log2(NC) bits) and
//    responses are routed back by its upper bits;
//  * per client, round-robin response arbitration among the slices;
//  * full valid/ready backpressure, no storage (zero-latency, pure routing).
// ENABLE = 0 (default): inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_xbar #(
    parameter integer ENABLE = 0,
    parameter integer NC     = 4,
    parameter integer NS     = 2,
    parameter integer TW     = 16,
    parameter integer LNC    = (NC > 1) ? $clog2(NC) : 1,
    parameter integer LNS    = (NS > 1) ? $clog2(NS) : 0,
    parameter integer STW    = TW + LNC
) (
    input  wire              clk,
    input  wire              rst_n,
    // client side (packed, client c at [c*W +: W])
    input  wire [NC-1:0]     c_req_v,
    output reg  [NC-1:0]     c_req_rdy,
    input  wire [NC-1:0]     c_req_we,
    input  wire [NC*32-1:0]  c_req_addr,
    input  wire [NC*256-1:0] c_req_wdata,
    input  wire [NC*32-1:0]  c_req_wstrb,
    input  wire [NC*TW-1:0]  c_req_tag,
    output reg  [NC-1:0]     c_rsp_v,
    input  wire [NC-1:0]     c_rsp_rdy,
    output reg  [NC*TW-1:0]  c_rsp_tag,
    output reg  [NC-1:0]     c_rsp_we,
    output reg  [NC*256-1:0] c_rsp_data,
    // slice side
    output reg  [NS-1:0]     s_req_v,
    input  wire [NS-1:0]     s_req_rdy,
    output reg  [NS-1:0]     s_req_we,
    output reg  [NS*32-1:0]  s_req_addr,
    output reg  [NS*256-1:0] s_req_wdata,
    output reg  [NS*32-1:0]  s_req_wstrb,
    output reg  [NS*STW-1:0] s_req_tag,
    input  wire [NS-1:0]     s_rsp_v,
    output reg  [NS-1:0]     s_rsp_rdy,
    input  wire [NS*STW-1:0] s_rsp_tag,
    input  wire [NS-1:0]     s_rsp_we,
    input  wire [NS*256-1:0] s_rsp_data
);
    generate if (ENABLE != 0) begin : g_on
        reg [LNC-1:0] rq_ptr [0:NS-1];      // per-slice request round-robin pointer
        reg [LNC-1:0] rq_gnt [0:NS-1];
        reg [NS-1:0]  rq_any;
        localparam integer LS1 = (LNS > 0) ? LNS : 1;
        reg [LS1-1:0] rs_ptr [0:NC-1];      // per-client response round-robin pointer (slice index)
        reg [LS1-1:0] rs_gnt [0:NC-1];
        reg [NC-1:0]  rs_any;

        function automatic integer slice_of(input [31:0] a);
            slice_of = (NS > 1) ? integer'((a >> 7) & (NS - 1)) : 0;
        endfunction
        function automatic integer client_of(input [LNC-1:0] t);
            client_of = (NC > 1) ? integer'(t) : 0;
        endfunction

        always @(*) begin : p_rq
            integer s, k, ci;
            // request arbitration per slice
            for (s = 0; s < NS; s = s + 1) begin
                rq_any[s] = 1'b0; rq_gnt[s] = '0;
                for (k = NC - 1; k >= 0; k = k - 1) begin
                    ci = (integer'(rq_ptr[s]) + k) % NC;
                    if (c_req_v[ci] && slice_of(c_req_addr[ci*32 +: 32]) == s) begin
                        rq_any[s] = 1'b1; rq_gnt[s] = LNC'(ci);
                    end
                end
            end
            for (s = 0; s < NS; s = s + 1) begin
                ci = integer'(rq_gnt[s]);
                s_req_v[s] = rq_any[s];
                s_req_we[s] = rq_any[s] & c_req_we[ci];
                s_req_addr[s*32 +: 32] = rq_any[s] ? c_req_addr[ci*32 +: 32] : 32'd0;
                s_req_wdata[s*256 +: 256] = rq_any[s] ? c_req_wdata[ci*256 +: 256] : 256'd0;
                s_req_wstrb[s*32 +: 32] = rq_any[s] ? c_req_wstrb[ci*32 +: 32] : 32'd0;
                s_req_tag[s*STW +: STW] = rq_any[s] ? ((STW'(ci) << TW) | STW'(c_req_tag[ci*TW +: TW])) : '0;
            end
        end
        always @(*) begin : p_crdy
            integer s;
            c_req_rdy = '0;
            for (s = 0; s < NS; s = s + 1)
                if (rq_any[s] && s_req_rdy[s]) c_req_rdy[integer'(rq_gnt[s])] = 1'b1;
        end
        always @(*) begin : p_rs
            integer c, k, si;
            // response arbitration per client
            for (c = 0; c < NC; c = c + 1) begin
                rs_any[c] = 1'b0; rs_gnt[c] = '0;
                for (k = NS - 1; k >= 0; k = k - 1) begin
                    si = (integer'(rs_ptr[c]) + k) % NS;
                    if (s_rsp_v[si] && client_of(s_rsp_tag[si*STW + TW +: LNC]) == c) begin
                        rs_any[c] = 1'b1; rs_gnt[c] = LS1'(si);
                    end
                end
            end
            for (c = 0; c < NC; c = c + 1) begin
                si = integer'(rs_gnt[c]);
                c_rsp_v[c] = rs_any[c];
                c_rsp_tag[c*TW +: TW] = rs_any[c] ? s_rsp_tag[si*STW +: TW] : '0;
                c_rsp_we[c] = rs_any[c] & s_rsp_we[si];
                c_rsp_data[c*256 +: 256] = rs_any[c] ? s_rsp_data[si*256 +: 256] : 256'd0;
            end
        end
        always @(*) begin : p_srdy
            integer c;
            s_rsp_rdy = '0;
            for (c = 0; c < NC; c = c + 1)
                if (rs_any[c] && c_rsp_rdy[c]) s_rsp_rdy[integer'(rs_gnt[c])] = 1'b1;
        end

        always @(posedge clk) begin : p_ptr
            integer s, c;
            if (!rst_n) begin
                for (s = 0; s < NS; s = s + 1) rq_ptr[s] <= '0;
                for (c = 0; c < NC; c = c + 1) rs_ptr[c] <= '0;
            end else begin
                for (s = 0; s < NS; s = s + 1)
                    if (rq_any[s] && s_req_rdy[s])
                        rq_ptr[s] <= (integer'(rq_gnt[s]) == NC - 1) ? '0 : rq_gnt[s] + 1'b1;
                for (c = 0; c < NC; c = c + 1)
                    if (rs_any[c] && c_rsp_rdy[c])
                        rs_ptr[c] <= (integer'(rs_gnt[c]) == NS - 1) ? '0 : rs_gnt[c] + 1'b1;
            end
        end
    end else begin : g_off
        assign c_req_rdy = '0;
        assign c_rsp_v = '0;
        assign c_rsp_tag = '0;
        assign c_rsp_we = '0;
        assign c_rsp_data = '0;
        assign s_req_v = '0;
        assign s_req_we = '0;
        assign s_req_addr = '0;
        assign s_req_wdata = '0;
        assign s_req_wstrb = '0;
        assign s_req_tag = '0;
        assign s_rsp_rdy = '0;
    end endgenerate
endmodule
