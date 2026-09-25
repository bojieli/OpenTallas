`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Record format of the ROM array's communication operators.
//
// Every message on an ot_rom_pkg_link or through rtl/rom/ot_rom_fabric_router
// is a run of RECORDS.  A record is one HEADER flit followed by the fixed
// number of payload flits its type implies; `last` marks the end of a packet
// (one or more records for one destination).  The low 32 header bits are the
// fabric's own (docs/ROM_ARRAY_FABRIC_RTL.md section 1), so the router routes
// these records exactly as it routes ot_rom_pkg_ctrl's HIDDEN / RESULT
// messages (DEST_LSB = 0), and the types do not collide with 1 and 2:
//
//   [7:0]    dest        fabric id: a package, or a multicast group id that
//                        the router's table expands (GROUP_BASE + set, below)
//   [15:8]   src         sending package
//   [19:16]  type        3 DISPATCH, 4 RETURN, 5 KV (multicast row), 6 ARGMAX
//   [31:24]  len         payload flits of this record
//   [39:32]  tag         token slot of the home package (the fabric's `user`)
//   [40]     eob         DISPATCH: last token of the micro-batch
//   [43:41]  rank        RETURN: the result's position in the fixed sum order
//   [63:48]  dst_mask    destination set, one bit per package (multicast)
//   [70:64]  item_valid  DISPATCH: which of the 7 items are present (owned)
//   [79:72]  aux         KV: source layer
//
// DISPATCH items (7, from bit 80, 48 bits each): item i at [80 + 48 i +: 48]
//   [31:0]  routing weight, binary32 (the golden's wgt; zero for the shared expert)
//   [40:32] expert id (routed 0 .. N_EXP-1; the shared expert is id N_EXP, item 6)
//   [43:41] rank: position of the expert in ascending-id order (shared = 6)
//   [47:44] owning package
//
// ARGMAX header: [127:96] best logit (binary32), [159:128] its vocabulary
// id, [160] carried-best valid.  KV header: [111:80] position.
//
// A multicast record's dest is GROUP_BASE + (its destination set): with a
// package's ids below GROUP_BASE, the router's routing table holds, at entry
// GROUP_BASE + m, the output ports that reach the packages of set m.
//
// Payloads.  DISPATCH carries the FP8 activation exactly as the golden's
// quant_fp8 produces it: the E4M3 codes, 32 per block, flit after flit, then
// the per-block UE8M0 exponents (8-bit two's complement) packed right after
// the last code.  RETURN carries one vector in element order: an expert
// output in BF16, or (combine IN_W = 32) a binary32 partial sum.  KV carries
// the row bytes verbatim.
// ---------------------------------------------------------------------------
package ot_rom_coll_pkg;
    localparam [3:0] K_DISPATCH = 4'd3;
    localparam [3:0] K_RETURN   = 4'd4;
    localparam [3:0] K_KV       = 4'd5;
    localparam [3:0] K_ARGMAX   = 4'd6;

    localparam integer H_DST   = 0;    // 8 bits
    localparam integer H_SRC   = 8;    // 8 bits
    localparam integer H_KIND  = 16;   // 4 bits
    localparam integer H_LEN   = 24;   // 8 bits
    localparam integer H_TAG   = 32;   // 8 bits
    localparam integer H_EOB   = 40;   // 1 bit
    localparam integer H_RANK  = 41;   // 3 bits
    localparam integer H_MASK  = 48;   // 16 bits
    localparam integer H_IVAL  = 64;   // 7 bits
    localparam integer H_AUX   = 72;   // 8 bits
    localparam integer H_ITEM  = 80;   // 7 x 48 bits
    localparam integer ITEM_W  = 48;
    localparam integer N_ITEMS = 7;
    localparam integer I_WGT   = 0;    // 32 bits
    localparam integer I_ID    = 32;   // 9 bits
    localparam integer I_RANK  = 41;   // 3 bits
    localparam integer I_DEST  = 44;   // 4 bits
    localparam integer H_ARG_VAL = 96;
    localparam integer H_ARG_ID  = 128;
    localparam integer H_ARG_OK  = 160;
    localparam integer H_KV_POS  = 80;
    localparam integer HDR_BITS  = H_ITEM + N_ITEMS * ITEM_W;   // 416
    localparam integer GROUP_BASE = 32;                         // first multicast group id
endpackage
