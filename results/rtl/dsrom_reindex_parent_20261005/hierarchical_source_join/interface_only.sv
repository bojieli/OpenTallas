module ot_dsrom_reindex_native_quarter #(parameter integer ENABLE=0) (
    input wire clk, rst_n,
    input wire ql_v,
    output wire ql_ready,
    input wire [7:0] ql_head,
    input wire [511:0] ql_codes,
    input wire [31:0] ql_sc,
    input wire [15:0] ql_w,
    input wire ks_valid,
    output wire ks_ready,
    input wire ks_last,
    input wire [15:0] ks_lv, ks_ref,
    input wire [8703:0] ks_key,
    input wire [319:0] ks_idx,
    output wire sc_valid,
    input wire sc_ready,
    output wire sc_last,
    output wire [3:0] sc_last_slices,
    output wire [15:0] sc_lv, sc_fault,
    output wire [255:0] sc_val,
    output wire [319:0] sc_idx,
    output wire protocol_fault
);
endmodule
module ot_dsrom_reindex_chain #(
    parameter integer OPT_REINDEX_PARENT = 0,
    parameter integer Q    = 4,        // stacks = select quarters
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer AW   = 28,       // HBM sector address
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer DF   = 8,
    parameter integer LSW  = 3,        // list slots 2^LSW (>= WIN); 0 = as-built single list
    parameter integer IW   = 20,       // position bits
    parameter integer K    = 512,
    parameter integer SAW  = 8,        // select line-memory words per quarter (log2)
    parameter integer MDROP = 1,
    localparam integer SLW = (LSW > 0) ? LSW : 1,
    localparam integer KW = $clog2(K + 1),
    localparam integer EW = 17 + IW
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // candidate lists (written ahead by the candidate source)
    input  wire [Q-1:0]          lw_v,
    input  wire [SLW-1:0]        lw_slot,
    input  wire [LMW-1:0]        lw_addr,
    input  wire [Q*LBW-1:0]      lw_blk,
    // job
    input  wire                  start,
    input  wire [SLW-1:0]        start_slot,
    input  wire [IW-1:0]         start_pos,
    input  wire [KW-1:0]         start_k,
    input  wire [Q*HW-1:0]       start_base,
    input  wire [Q*10-1:0]       start_skip,
    input  wire [Q*(LMW+1)-1:0]  start_n,
    input  wire [Q*IW-1:0]       start_qbase,
    output reg                   done,
    output wire                  busy,
    output reg                   fault,
    // HBM (per stack NPC pseudo-channels)
    output wire [Q*NPC-1:0]      req_v,
    input  wire [Q*NPC-1:0]      req_rdy,
    output wire [Q*NPC*AW-1:0]   req_addr,
    output wire [Q*NPC*LENW-1:0] req_len,
    output wire [Q*NPC*TAGW-1:0] req_tag,
    input  wire [Q*NPC-1:0]      rsp_v,
    output wire [Q*NPC-1:0]      rsp_rdy,
    input  wire [Q*NPC*TAGW-1:0] rsp_tag,
    input  wire [Q*NPC*BEATW-1:0] rsp_beat,
    input  wire [Q*NPC*DW-1:0]   rsp_data,
    // scorer: key beats out (16 keys = 2 blocks a beat) ...
    output wire [Q-1:0]          ks_valid,
    input  wire [Q-1:0]          ks_ready,
    output wire [Q*16-1:0]       ks_lv,
    output wire [Q*16*544-1:0]   ks_key,
    output wire [Q*16*IW-1:0]    ks_idx,
    output wire [Q-1:0]          ks_last,
    // ... scored beats in (same beats, same order, BF16 scores)
    input  wire [Q-1:0]          sc_valid,
    output wire [Q-1:0]          sc_ready,
    input  wire [Q*16-1:0]       sc_lv,
    input  wire [Q*16*16-1:0]    sc_val,
    input  wire [Q*16*IW-1:0]    sc_idx,
    input  wire [Q-1:0]          sc_last,
    // selection (per quarter, packed, ascending positions)
    output wire [Q-1:0]          out_valid,
    input  wire [Q-1:0]          out_ready,
    output wire [Q-1:0]          out_last,
    output wire [Q*16-1:0]       out_lv,
    output wire [Q*16*16-1:0]    out_val,
    output wire [Q*16*IW-1:0]    out_idx,
    output wire [Q*16-1:0]       out_ninf,
    output wire                  ovf,
    output wire                  short,
    output reg  [3:0]            passes,     // gather passes of the current job (1 + replays)
    output wire [Q*48-1:0]       cnt_keys,
    output wire [Q*48-1:0]       cnt_beats
);
endmodule
