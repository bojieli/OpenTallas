// Actual source header only: ABI compile, no behavioral or physical proof.
module ot_hdc_v41x_idx_array_l #(
    parameter integer NS = 16,         // slice replicas
    parameter integer NK = 4,          // keys per slice per cycle
    parameter integer NB = 4,          // 32-blocks per head (index_head_dim/32)
    parameter integer IH = 32,         // index heads
    parameter integer IW = 30,         // global key index width
    parameter integer MD = 64,         // per-slice score/metadata FIFO depth (deepened to cover the latency)
    parameter integer FPL = 3,         // binary32 add latency (7: 1.2 GHz streaming domain)
    parameter integer FML = 3,         // head-weight product latency
    parameter integer QL = 3           // block-dot latency
) (
    input  wire                     clk,
    input  wire                     rst_n,
    // q load, broadcast: one head per cycle
    input  wire                     ql_v,
    output wire                     ql_ready,
    input  wire [7:0]               ql_head,
    input  wire [NB*128-1:0]        ql_codes,
    input  wire [NB*8-1:0]          ql_sc,
    input  wire [15:0]              ql_w,
    // key beat: NS*NK slots
    input  wire                     i_valid,
    output wire                     i_ready,
    input  wire [NS-1:0]            i_last,
    input  wire [NS*NK-1:0]         i_kv,
    input  wire [NS*NK-1:0]         i_ref,
    input  wire [NS*NK-1:0]         i_keep,
    input  wire [NS*NK*IW-1:0]      i_index,
    input  wire [NS*NK*NB*136-1:0]  i_key,
    // score beat to the selector port: NS*NK slots in beat order
    output wire                     o_valid,
    input  wire                     o_ready,
    output wire [NS-1:0]            o_last,
    output wire [NS*NK-1:0]         o_kv,
    output wire [NS*NK-1:0]         o_fault,
    output wire [NS*NK*16-1:0]      o_score,
    output wire [NS*NK*IW-1:0]      o_index,
    output wire                     protocol_fault
);

endmodule
