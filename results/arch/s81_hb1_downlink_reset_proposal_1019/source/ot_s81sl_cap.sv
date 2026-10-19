`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): cap = the CAPTURE ROOT sub-leaf of one DV vector slice (x1, centre leaf, own clock
// root).  Contract: results/rtl/s81_slice_1017/SLICE_CONTRACT.md section 4 `ot_s81sl_cap`.
//
// The slice's matvec rows return on the 8 frame lanes rt[l] = the frame cfifo `rd` (dsfd_cfifo_crs, after the die
// re-time).  Bit order, derived from the RTL that packs it (NOT assumed):
//   rd = {rr[67:0], rr[0], rsync_s}                      dsfd_cfifo_crs:  rr = {st[1] | flt, st[0], ri_q[65:0]}
//   ri = the column return-tree root word through dsfd_rstg stages (pass-through, valid bit = column-reset flop)
//      = {e[65], d[64:33], t[32:1], v[0]}                dsfd_node_<ab> (tools/dsrom_s81_fulldie.py): o = {oe, od, ot_, ov}
//   so  rt[0] rst_n, rt[1] valid, rt[2] = ri.v, rt[34:3] tag, rt[66:35] FP32 data, rt[67] err, rt[68] busy, rt[69] fault
//   (tag = ot_v41_ret_pkg {pos3, row16, lo5, k3, nseg5}; the column word is a PARTIAL, finished here).
//
// A row's K segments stay inside the slice's 8 frames but not inside one frame (S81-DV ruling), so the slice finishes
// the partials with golden sibling adds (ot_v41_ret_pkg tag arithmetic, bit-identical ot_fp32_add_rne_pipe):
//   TREE  7 x ot_s81_retn_static (WIN 2, RST 1; the fixed-slot node of the field, compiler model
//         tools/s81/static_return_calendar.py) over the 8 lanes: n0..n3 = lanes (0,1) (2,3) (4,5) (6,7), n4 = (n0,n1),
//         n5 = (n2,n3), n6 = (n4,n5).  Siblings that meet within WIN merge in flight; the others are forwarded.
//   FIN   static root finish for siblings the tree cannot meet (they come from frames whose return slots are far
//         apart).  A DIRECT-MAPPED pairing store, no CAM, no queue, no arbitration:
//           slot  = (row + 8 pos) mod 64 holds the key {pos, row, nseg} of ONE open row (6-b count of waiting entries);
//           entry = {slot, h}, h = 2^(4-k) | lo >> (k+1) = the PARENT tree node of the partial (1..31): both siblings
//                   map to the same entry.  Data in one ot_sram_1r1w_512x128_m4 (2,048 x FP32 = {slot, h}); valid +
//                   side (lo[k]) in flops.
//           a non-complete partial at F1: entry empty -> INSERT (write d); entry waiting with the other side -> MERGE:
//           read the sibling, fp32 add (operands {stored, new}: the adder is commutative bit for bit), parent tag =
//           norm(pre-parent), and the sum RE-ENTERS F1 a fixed RE edges after the merge decision.
//         F1 takes the tree root word (A) and a re-entry (B) in the same edge; a complete word needs no store, so up
//         to two complete words leave F1 per edge (the two capture ports per leaf).
//   DEC   each complete row -> leaf k and leaf word address, per-phase config (cfg_d, below), FP32 or BF16 RNE (the
//         ot_s81ph_capture / ot_v41_ret_root rounding: ({1'b0, fp32} + 0x7FFF + fp32[16]) >> 16, low half zero).
//           e = row - rbase (fault unless e < rcnt);  chunk = e >> 6;  k = chunk mod 5;  wrap = chunk / 5
//           word address = obase + pos * ops + 64 wrap + e[5:0]        (rcnt <= 320: k = (row - rbase) / 64, wrap 0)
//         FIXED PORT RULE: port = word address bit 2 (= the vp leaf-store bank, row bit 0 of {row 10, word 2}).
//
// COMPILER OBLIGATIONS (sticky fault, never re-timed; tools/s81_slice/cap_model.py reproduces every edge):
//   T   the 7 nodes' F1..F4 (ot_s81_retn_static);  F5 two non-complete words at F1 in one edge (A and re-entry);
//   F6  a partial whose slot holds another open row;  F7 a duplicate (same entry, same side) or malformed partial;
//   F8  two writes to one leaf port in one edge;  F9 a row outside [rbase, rbase + rcnt), pos > np, fmt 3;
//   F10 an err word (lane err bit, adder err) or a lane status fault (rt[69]);
//   F11 cfg_v (phase start) while a pairing-store slot is open: a partial was dropped or a row never finished.
//
// cfg_d[159:0] (cfg_v: phase start, applied to the words decoded after it):
//   [11:0] obase  [23:12] ops (pos stride)  [26:24] np  [28:27] fmt (0 split by rsplit, 1 FP32, 2 BF16, 3 fault)
//   [44:29] rbase  [55:45] rcnt  [71:56] rsplit  [72] fp32 for rows < rsplit (fmt 0)  [73] fp32 for rows >= rsplit
// Outputs per leaf k = 0..4 (contract cw_v[k] / cw_a[k] / cw_d[k]): bits [2k +: 2], [24k +: 24] ({port1 a12, port0 a12}),
// [64k +: 64] of {cw_n_*, cw_s_*}; the ports are split by face (S: leaves 0..2, N: leaves 3, 4) and rt by frame column
// (rt_w lanes 0..3, rt_e lanes 4..7), lane l = bits [70 (l mod 4) +: 70].
// Every input lands in a flop; every output leaves a flop.
// PHYSICAL FORM (S81U-CAP2, 2026-10-17): this module is a WIRES-ONLY parent of three hardened leaves, each with its own
// clock root (the flat form failed the clock rule: 22,261 sinks on one root, TT insertion 368.5 ps > 300):
//   u_tw  ot_s81sl_cap_tr  W tree: lane pin flops 0..3 + n0, n1, n4      (rt_w on its W face)
//   u_te  ot_s81sl_cap_tr  E tree: lane pin flops 4..7 + n2, n3, n5      (same master, placed MY: rt_e on the E face)
//   u_rt  ot_s81sl_cap_rt  n6 + FIN + DEC + cfg + sticky fault            (cw_n_* / cfg on N, cw_s_* / fault on S)
// Seams: n4 / n5's RST output flop -> abutted wire -> n6's P1 port flop: registered both sides, NO added edge, so the
// edge-exact behaviour above (and tools/s81_slice/cap_model.py) is unchanged.  Fault visibility moves +2 edges for lane
// err/status and n0..n5 faults (leaf sticky flop + root pin flop); fault is sticky and checked at phase end, not timed.
// MUT (bench mutants only): 1 wrong sibling association (h = parent of the parent), 2 ri bit order t <-> d,
//   3 leaf mapping off by one (chunk + 1), 4 a dropped partial (lane 5's 3rd word).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap #(
    parameter integer WIN = 2,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [279:0]  rt_w,         // lanes 0..3 (W frame column), 4 x 70
    input  wire [279:0]  rt_e,         // lanes 4..7 (E frame column)
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,       // leaves 0..2 (S face: leaves 0, 1 and the centre leaf's own vp)
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,       // leaves 3, 4 (N face)
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);
    localparam integer MUT_W = (MUT == 2) ? 2 : 0;
    localparam integer MUT_E = (MUT == 2 || MUT == 4) ? MUT : 0;
    localparam integer MUT_R = (MUT == 1 || MUT == 3) ? MUT : 0;
    wire w_v, w_e, w_f, e_v, e_e, e_f; wire [31:0] w_t, w_d, e_t, e_d;
    // the hardened leaves are instantiated WITHOUT parameter overrides (one master each; WIN = 2 is their default);
    // the bench mutants (MUT != 0) re-elaborate the RTL with the mutant parameter on the leaf that holds it
    generate if (MUT == 0) begin : g_hard
        ot_s81sl_cap_tr u_tw (.clk(clk), .rst_n(rst_n), .rt(rt_w), .o_v(w_v), .o_t(w_t), .o_d(w_d), .o_e(w_e), .fault(w_f));
        ot_s81sl_cap_tr u_te (.clk(clk), .rst_n(rst_n), .rt(rt_e), .o_v(e_v), .o_t(e_t), .o_d(e_d), .o_e(e_e), .fault(e_f));
        ot_s81sl_cap_rt u_rt (.clk(clk), .rst_n(rst_n),
            .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f), .e_v(e_v), .e_t(e_t), .e_d(e_d), .e_e(e_e), .e_f(e_f),
            .cfg_v(cfg_v), .cfg_d(cfg_d),
            .cw_s_v(cw_s_v), .cw_s_a(cw_s_a), .cw_s_d(cw_s_d), .cw_n_v(cw_n_v), .cw_n_a(cw_n_a), .cw_n_d(cw_n_d),
            .fault(fault));
    end else begin : g_mut
        ot_s81sl_cap_tr #(.MUT(MUT_W)) u_tw (.clk(clk), .rst_n(rst_n), .rt(rt_w),
            .o_v(w_v), .o_t(w_t), .o_d(w_d), .o_e(w_e), .fault(w_f));
        ot_s81sl_cap_tr #(.MUT(MUT_E)) u_te (.clk(clk), .rst_n(rst_n), .rt(rt_e),
            .o_v(e_v), .o_t(e_t), .o_d(e_d), .o_e(e_e), .fault(e_f));
        ot_s81sl_cap_rt #(.MUT(MUT_R)) u_rt (.clk(clk), .rst_n(rst_n),
            .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f), .e_v(e_v), .e_t(e_t), .e_d(e_d), .e_e(e_e), .e_f(e_f),
            .cfg_v(cfg_v), .cfg_d(cfg_d),
            .cw_s_v(cw_s_v), .cw_s_a(cw_s_a), .cw_s_d(cw_s_d), .cw_n_v(cw_n_v), .cw_n_a(cw_n_a), .cw_n_d(cw_n_d),
            .fault(fault));
    end endgenerate
`ifndef SYNTHESIS
    initial if (WIN != 2) $fatal(1, "ot_s81sl_cap: the hardened leaves are built at WIN = 2");
`endif
endmodule
`default_nettype wire
