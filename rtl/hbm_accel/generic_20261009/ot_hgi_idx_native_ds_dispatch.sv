`timescale 1ns/1ps
// HGI unit9 op3 binds unchanged full native candidate ports.
// Parent holds command and original tuple throughout drain; no added cycle.
module ot_hgi_idx_native_ds_dispatch #(

    parameter bit ENABLE = 1'b1,
    parameter integer Q   = 4,
    parameter integer SL  = 16,       // score lanes per quarter (multiple of 8)
    parameter integer IWP = 20,       // position width
    parameter integer K   = 2048,     // largest runtime k (blocks)
    parameter integer AW  = 10,       // line-memory address width per quarter
    parameter integer DG  = 8,
    parameter integer READLAT = 1,   // external line memory latency (1 baseline, 2 captured)
    parameter integer OD  = 4,
    parameter bit MUTANT_ID = 0,
    parameter integer KW  = $clog2(K + 1)
) (
    input  wire                         clk,
    input  wire                         rst_n,
    // These are the actual issuer's held tuple, stable through all accepted
    // quarter-last outputs and memory/replay drain. This wrapper grants no owner.
    input wire [3:0] cmd_unit,
    input wire [5:0] cmd_op,
    output wire decode_error,
    input  wire                         held_valid,
    input  wire [31:0]                  held_job,
    input  wire [3:0]                   held_gen,
    input  wire [19:0]                  held_pos,
    input  wire [6:0]                   held_rank,
    output wire [31:0]                  out_job,
    output wire [3:0]                   out_gen,
    output wire [19:0]                  out_pos,
    output wire [6:0]                   out_rank,
    input  wire [Q-1:0]                 in_valid,
    output wire [Q-1:0]                 in_ready,
    input  wire [Q-1:0]                 in_last,
    input  wire [Q*SL-1:0]              in_lv,
    input  wire [Q*SL*16-1:0]           in_val,
    input  wire [Q*SL*IWP-1:0]          in_idx,
    input  wire [KW-1:0]                in_k,
    output wire [Q-1:0]                 out_valid,
    input  wire [Q-1:0]                 out_ready,
    output wire [Q-1:0]                 out_last,
    output wire [Q*(SL/8)-1:0]          out_lv,
    output wire [Q*(SL/8)*16-1:0]       out_val,
    output wire [Q*(SL/8)*(IWP-3)-1:0]  out_blk,
    output wire [Q-1:0]                 mem_we,
    output wire [Q*AW-1:0]              mem_waddr,
    output wire [Q*(SL/8)*(14+IWP)-1:0] mem_wdata,
    output wire [Q-1:0]                 mem_re,
    output wire [Q*AW-1:0]              mem_raddr,
    input  wire [Q*(SL/8)*(14+IWP)-1:0] mem_rdata,
    output wire                         rep_req,
    output wire                         ovf,
    output wire                         busy,
    output wire [Q*3*(AW+1)-1:0]        stats
);
 wire selected = cmd_unit == 4'd9 && cmd_op == 6'd3;
 assign decode_error = held_valid && !selected;
 wire [Q*(SL/8)*(IWP-3)-1:0] native_blk;
 assign out_blk = native_blk ^ {{(Q*(SL/8)*(IWP-3)-1){1'b0}},MUTANT_ID};
 ot_hbm_accel_index_candidate #(.ENABLE(ENABLE),.Q(Q),.SL(SL),.IWP(IWP),.K(K),.AW(AW),.DG(DG),.READLAT(READLAT),.OD(OD),.KW(KW)) native(
 .clk(clk),
 .rst_n(rst_n),
 .held_valid(held_valid && selected),
 .held_job(held_job),
 .held_gen(held_gen),
 .held_pos(held_pos),
 .held_rank(held_rank),
 .out_job(out_job),
 .out_gen(out_gen),
 .out_pos(out_pos),
 .out_rank(out_rank),
 .in_valid(in_valid),
 .in_ready(in_ready),
 .in_last(in_last),
 .in_lv(in_lv),
 .in_val(in_val),
 .in_idx(in_idx),
 .in_k(in_k),
 .out_valid(out_valid),
 .out_ready(out_ready),
 .out_last(out_last),
 .out_lv(out_lv),
 .out_val(out_val),
 .out_blk(native_blk),
 .mem_we(mem_we),
 .mem_waddr(mem_waddr),
 .mem_wdata(mem_wdata),
 .mem_re(mem_re),
 .mem_raddr(mem_raddr),
 .mem_rdata(mem_rdata),
 .rep_req(rep_req),
 .ovf(ovf),
 .busy(busy),
 .stats(stats)
);
endmodule
