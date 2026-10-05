`timescale 1ns/1ps
// V4.1 collective GW4 -> VM static-bank neighborhood (W2 rung-4 cluster).
// The pipelined full-shape transpose (OUT_PIPE=1) drives each output lane k
// straight into VM bank k's write port of the registered four-bank macro VM
// (ot_v41_vm_bank4_macro_pipe); no rotation or shared enable crosses banks.
// The VM read port (ME side) is exposed unchanged. DEPTH_GROUPS selects how
// many 4-macro depth groups each bank holds (16 = the full 2 MiB VM; the
// representative physical cut uses 1, i.e. 16 macros). No latency is added:
// the transpose and VM keep their own registered edges.
module ot_v41_coll_vm_gw4_neighborhood #(
    parameter integer DEPTH_GROUPS = 1,
    parameter integer WA = 15
) (
    input  wire clk,
    input  wire rst_n,
    // collective gather side (index-major four-rank beats)
    input  wire start,
    input  wire [WA-1:0] dst,
    input  wire [WA-1:0] n,
    output wire in_ready,
    input  wire in_valid,
    input  wire [2047:0] in_data,
    input  wire in_last,
    output wire coll_done,
    output wire coll_fault,
    // VM read service (ME side)
    input  wire rd_v,
    input  wire [WA-1:0] rd_base_word,
    output wire rd_out_v,
    output wire [1:0] rd_out_rot,
    output wire [2047:0] rd_out_bank_words,
    output wire rd_fault,
    output wire wr_fault,
    output wire rw_collision_fault
);
    wire out_valid, out_last;
    wire [3:0] out_we;
    wire [4*WA-1:0] out_addr;
    wire [2047:0] out_data;
    ot_chip_v41x_coll_transpose #(.WA(WA), .FW(512), .OUT_PIPE(1)) u_tr (
        .clk(clk), .rst_n(rst_n), .start(start), .dst(dst), .n(n),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data), .in_last(in_last),
        .out_ready(1'b1), .out_valid(out_valid), .out_we(out_we), .out_addr(out_addr),
        .out_data(out_data), .out_last(out_last), .done(coll_done), .fault(coll_fault));
    ot_v41_vm_bank4_macro_pipe #(.DEPTH_GROUPS(DEPTH_GROUPS), .AW(WA)) u_vm (
        .clk(clk), .rst_n(rst_n), .rd_v(rd_v), .rd_base_word(rd_base_word),
        .rd_out_v(rd_out_v), .rd_out_rot(rd_out_rot), .rd_out_bank_words(rd_out_bank_words),
        .rd_fault(rd_fault), .wr_v(out_we), .wr_word_addr(out_addr), .wr_word_data(out_data),
        .wr_fault(wr_fault), .rw_collision_fault(rw_collision_fault));
endmodule
