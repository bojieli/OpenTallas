`timescale 1ns/1ps
// Address one key in the pooled indexer's quarter-order 64-key beat.
//
// The four HBM stacks hold disjoint 16-key stripes. Within each stack, keys
// retain their order and use the compact 68-B/key superblock layout of the
// existing kstream: 1024 scales in block 0, then 16 code blocks of 64 keys.
// One key occupies two 32-B code sectors and a four-byte scale slot. The
// caller fetches a scale sector once for each eight present local keys.
//
// This is only the address stage. The HBM request scheduler and collector must
// use these descriptors and preserve quarter order; no read-path timing claim
// follows from this combinational module alone.
module ot_hdc_v41x_idx_shard_addr #(
    parameter integer HAW=28
) (
    input  wire [29:0] i_nkeys,
    input  wire [29:0] i_beat,
    input  wire [1:0]  i_quarter,
    input  wire [3:0]  i_lane,
    input  wire [HAW-1:0] i_base_sec,
    output wire        o_present,
    output wire [29:0] o_global,
    output wire [1:0]  o_stack,
    output wire [29:0] o_local,
    output wire [HAW-1:0] o_scale_sec,
    output wire [2:0] o_scale_slot,
    output wire [HAW-1:0] o_code_sec
);
    // Qs = 8 floor(N/32); Q0..Q2 have Qs keys, Q3 has the remainder.
    wire [29:0] qs = {2'b00,i_nkeys[29:5],3'b000};
    wire [29:0] qlen = (i_quarter==2'd3) ? i_nkeys - qs - qs - qs : qs;
    wire [29:0] off = {i_beat[25:0],4'b0000} + {26'd0,i_lane};
    assign o_present = off < qlen;
    assign o_global = (i_quarter==2'd0 ? 30'd0 :
                       i_quarter==2'd1 ? qs :
                       i_quarter==2'd2 ? qs+qs : qs+qs+qs) + off;
    assign o_stack = o_global[5:4];
    assign o_local = {2'b00,o_global[29:6],o_global[3:0]};
    // 17 * 128 sectors per 1024 local keys. An addition/shift form avoids a
    // general multiplier in the hardware address path.
    wire [HAW-1:0] sb = HAW'(o_local[29:10]);
    wire [HAW-1:0] sb_sec = (sb << 11) + (sb << 7); // 2176 sectors
    assign o_scale_sec = i_base_sec + sb_sec + HAW'(o_local[9:3]);
    assign o_scale_slot = o_local[2:0];
    assign o_code_sec = i_base_sec + sb_sec + HAW'(128) + HAW'({o_local[9:0],1'b0});
endmodule
