`timescale 1ns/1ps
// One quarter's direct 16-score selector ingress at NK=4. Four slices each
// score four keys in parallel. Atomic beat handshakes preserve the quarter's
// ascending global-index order through independent finite output FIFOs.
module ot_hdc_v41x_idx_score_quarter #(
    parameter integer NK=4, NB=4, IH=32, IW=30, MD=64
) (
    input wire clk,rst_n,
    input wire ql_v,
    output wire ql_ready,
    input wire [7:0] ql_head,
    input wire [NB*128-1:0] ql_codes,
    input wire [NB*8-1:0] ql_sc,
    input wire [15:0] ql_w,
    input wire i_valid,
    output wire i_ready,
    input wire i_last,
    input wire [IW-1:0] i_first_index,
    input wire [4*NK-1:0] i_kv,i_ref,i_keep,
    input wire [4*NK*NB*136-1:0] i_key,
    output wire o_valid,
    input wire o_ready,
    output wire o_last,
    output wire [4*NK-1:0] o_kv,o_fault,
    output wire [4*NK*16-1:0] o_score,
    output wire [4*NK*IW-1:0] o_index,
    output wire protocol_fault
);
    wire [3:0] sr,sv,sl,qr;
    wire take=i_valid && i_ready;
    wire consume=o_valid && o_ready;
    assign i_ready=&sr;
    assign ql_ready=&qr;
    assign o_valid=&sv;
    assign o_last=sl[0];
    assign protocol_fault=(|sv && !(&sv)) || ((&sv) && sl!={4{sl[0]}});
    genvar s;
    generate for(s=0;s<4;s=s+1) begin:g_slice
        localparam [IW-1:0] OFFSET=IW'(s*NK);
        ot_hdc_v41x_idx_score_slice #(.NK(NK),.NB(NB),.IH(IH),.IW(IW),.MD(MD)) u (
            .clk(clk),.rst_n(rst_n),.ql_v(ql_v),.ql_ready(qr[s]),.ql_head(ql_head),
            .ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
            .i_valid(take),.i_ready(sr[s]),.i_last(i_last),
            .i_first_index(i_first_index+OFFSET),
            .i_kv(i_kv[s*NK +: NK]),.i_ref(i_ref[s*NK +: NK]),
            .i_keep(i_keep[s*NK +: NK]),
            .i_key(i_key[s*NK*NB*136 +: NK*NB*136]),
            .o_valid(sv[s]),.o_ready(consume),.o_last(sl[s]),
            .o_kv(o_kv[s*NK +: NK]),.o_fault(o_fault[s*NK +: NK]),
            .o_score(o_score[s*NK*16 +: NK*16]),
            .o_index(o_index[s*NK*IW +: NK*IW]));
    end endgenerate
endmodule
