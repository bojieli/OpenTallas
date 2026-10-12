`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11: blackbox of the hardened IDX.TOPK heap tile (MAX_K 2,048) for the hierarchical w8 top.
// Read BEFORE ot_hgi_idx_topk_heap.sv: the define drops the RTL heap/tile and makes the engine instantiate this macro.
`define OT_TOPK_TILE_HARD
(* blackbox *)
module ot_hgi_topk_heap_tile (
 input wire clk, rst_n,
 input wire [11:0] k,
 input wire op_v, input wire op_ext, input wire [53:0] op_x,
 output wire op_cr,
 output wire ext_v, output wire [53:0] ext_d,
 output wire [52:0] root_key,
 input wire clr_go, output wire idle
);
endmodule
