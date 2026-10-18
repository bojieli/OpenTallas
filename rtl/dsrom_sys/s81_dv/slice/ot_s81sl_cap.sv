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
    output reg           fault
);
    wire [559:0] rt = {rt_e, rt_w};
    reg  [9:0]   cw_v; reg [119:0] cw_a; reg [319:0] cw_d;
    assign cw_s_v = cw_v[5:0];   assign cw_s_a = cw_a[71:0];   assign cw_s_d = cw_d[191:0];
    assign cw_n_v = cw_v[9:6];   assign cw_n_a = cw_a[119:72]; assign cw_n_d = cw_d[319:192];
    integer i, j;
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_t = rsv[0], rs_f = rsv[1], rs_o = rsv[2], rs_c = rsv[3];

    // ------------------------------------------------------------ ot_v41_ret_pkg (copied: no package import in ORFS)
    function automatic [31:0] norm(input [31:0] t);
        reg [18:0] row; reg [4:0] lo, n, c; reg [2:0] k, kf; integer q;
        begin
            {row, lo, k, n} = t;
            for (q = 0; q < 5; q = q + 1)
                c[q] = !(lo == 5'd0 && (6'd1 << q) >= {1'b0, n}) && lo[q] == 1'b0 && ({1'b0, lo} + (6'd1 << q)) >= {1'b0, n};
            kf = k;
            if (k < 3'd5) begin
                kf = 3'd5;
                for (q = 4; q >= 0; q = q - 1) if (q >= k && !c[q]) kf = q[2:0];
            end
            norm = {row, lo, kf, n};
        end
    endfunction
    function automatic complete(input [31:0] t);
        complete = t[12:8] == 5'd0 && (6'd1 << t[7:5]) >= {1'b0, t[4:0]};
    endfunction

    // ------------------------------------------------------------ lane pin flops + decode
    // pin flops: only the lane valid / reset bits and cfg_v are reset flops (no reset on the data bits)
    reg [559:0] rt_q; reg [7:0] rv_q; reg cfgv_q; reg [159:0] cfgd_q;
    always @(posedge clk or negedge rs_t) if (!rs_t) begin rv_q <= 8'd0; cfgv_q <= 1'b0; end
        else begin for (i = 0; i < 8; i = i + 1) rv_q[i] <= rt[70 * i + 1] && rt[70 * i]; cfgv_q <= cfg_v; end
    always @(posedge clk) begin rt_q <= rt; cfgd_q <= cfg_d; end
    wire [7:0] l_v, l_e, l_f; wire [31:0] l_t [0:7], l_d [0:7];
    reg [2:0] l5_cnt;                                      // MUT 4 only
    always @(posedge clk or negedge rs_t) if (!rs_t) l5_cnt <= 3'd0;
                                         else if (rv_q[5] && l5_cnt != 3'd7) l5_cnt <= l5_cnt + 3'd1;
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_lane
        wire [69:0] w = rt_q[70 * gl +: 70];
        wire drop = (MUT == 4) && gl == 5 && l5_cnt == 3'd2;
        assign l_v[gl] = rv_q[gl] && !drop;
        if (MUT == 2) begin : g_swap
            assign l_t[gl] = w[66:35]; assign l_d[gl] = w[34:3];
        end else begin : g_ok
            assign l_t[gl] = w[34:3];  assign l_d[gl] = w[66:35];
        end
        assign l_e[gl] = w[67];
        assign l_f[gl] = w[69];
    end endgenerate

    // ------------------------------------------------------------ TREE: 7 static nodes
    wire [6:0] n_v, n_e, n_f; wire [31:0] n_t [0:6], n_d [0:6];
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_l1
        ot_s81_retn_static #(.WIN(WIN), .RST(1)) u_n (.clk(clk), .rst_n(rs_t),
            .a_v(l_v[2*gl]), .a_t(l_t[2*gl]), .a_d(l_d[2*gl]), .a_e(l_e[2*gl]),
            .b_v(l_v[2*gl+1]), .b_t(l_t[2*gl+1]), .b_d(l_d[2*gl+1]), .b_e(l_e[2*gl+1]),
            .o_v(n_v[gl]), .o_t(n_t[gl]), .o_d(n_d[gl]), .o_e(n_e[gl]), .fault(n_f[gl]));
    end
    for (gl = 0; gl < 2; gl = gl + 1) begin : g_l2
        ot_s81_retn_static #(.WIN(WIN), .RST(1)) u_n (.clk(clk), .rst_n(rs_t),
            .a_v(n_v[2*gl]), .a_t(n_t[2*gl]), .a_d(n_d[2*gl]), .a_e(n_e[2*gl]),
            .b_v(n_v[2*gl+1]), .b_t(n_t[2*gl+1]), .b_d(n_d[2*gl+1]), .b_e(n_e[2*gl+1]),
            .o_v(n_v[4+gl]), .o_t(n_t[4+gl]), .o_d(n_d[4+gl]), .o_e(n_e[4+gl]), .fault(n_f[4+gl]));
    end endgenerate
    ot_s81_retn_static #(.WIN(WIN), .RST(1)) u_n6 (.clk(clk), .rst_n(rs_t),
        .a_v(n_v[4]), .a_t(n_t[4]), .a_d(n_d[4]), .a_e(n_e[4]),
        .b_v(n_v[5]), .b_t(n_t[5]), .b_d(n_d[5]), .b_e(n_e[5]),
        .o_v(n_v[6]), .o_t(n_t[6]), .o_d(n_d[6]), .o_e(n_e[6]), .fault(n_f[6]));

    // ------------------------------------------------------------ FIN: F1 registers (A = tree root, B = re-entry)
    reg        re_v; reg [31:0] re_t, re_d; reg re_e;     // re-entry register (adder sum + parent tag)
    reg        fa_v, fb_v; reg [31:0] fa_t, fa_d, fb_t, fb_d; reg fa_e, fb_e;
    always @(posedge clk or negedge rs_f) if (!rs_f) begin fa_v <= 1'b0; fb_v <= 1'b0; end
                                         else begin fa_v <= n_v[6]; fb_v <= re_v; end
    always @(posedge clk) begin
        fa_t <= n_t[6]; fa_d <= n_d[6]; fa_e <= n_e[6];
        fb_t <= re_t;   fb_d <= re_d;   fb_e <= re_e;
    end
    wire ca = complete(fa_t), cb = complete(fb_t);
    wire sa = fa_v && !ca, sb = fb_v && !cb;              // store candidates
    wire f5 = sa && sb;
    // the store word of this edge (B first if both: F5 is a fault anyway)
    wire        s_v = sa || sb;
    wire [31:0] s_t = sb ? fb_t : fa_t;
    wire [31:0] s_d = sb ? fb_d : fa_d;
    wire [2:0]  s_k = s_t[7:5];
    wire [4:0]  s_lo = s_t[12:8];
    wire [23:0] s_key = {s_t[31:13], s_t[4:0]};          // {pos, row, nseg}
    wire [5:0]  s_slot = s_t[18:13] + {s_t[31:29], 3'd0}; // (row + 8 pos) mod 64
    reg  [4:0]  s_h;
    always @* begin
        s_h = 5'd0;
        case (s_k)
            3'd0: s_h = {1'b1, s_lo[4:1]};
            3'd1: s_h = {2'b01, s_lo[4:2]};
            3'd2: s_h = {3'b001, s_lo[4:3]};
            3'd3: s_h = {4'b0001, s_lo[4]};
            3'd4: s_h = 5'b00001;
            default: s_h = 5'd0;
        endcase
        if (MUT == 1 && s_k < 3'd3) s_h = {1'b0, s_h[4:1]};   // mutant: pairs at the grandparent (wrong sibling)
    end
    wire s_side = s_lo[s_k];
    // malformed: not a tree node (k > 4, or lo not a multiple of 2^k)
    wire s_bad = s_k > 3'd4 || ((s_lo & ((5'd1 << s_k) - 5'd1)) != 5'd0);

    // pairing store state.  cnt[slot] = waiting entries + parents in flight, so a slot is never re-keyed while a
    // partial of its row is anywhere in the finish (the parent has the same key and comes back to the same slot):
    //   A insert +1 | A merge 0 (entry -> parent in flight) | B insert 0 | B merge -1 | B complete -1.
    reg [23:0] key [0:63];
    reg [5:0]  cnt [0:63];
    reg [31:0] ev [0:63];                                 // entry valid, bit h
    reg [31:0] es [0:63];                                 // entry side (lo[k] of the waiting child)
    reg        any_open;                                  // registered OR of cnt != 0 (F11)
    wire        slot_busy = cnt[s_slot] != 6'd0;
    wire        key_hit = key[s_slot] == s_key;
    wire        f6 = s_v && slot_busy && !key_hit;
    wire        e_wait = slot_busy && key_hit && ev[s_slot][s_h];
    wire        f7 = s_v && (s_bad || (e_wait && es[s_slot][s_h] == s_side));
    wire        do_ins = s_v && !f6 && !f7 && !e_wait;
    wire        do_mrg = s_v && !f6 && !f7 && e_wait;
    wire        do_rel = fb_v && cb;                      // a complete re-entry leaves its slot
    wire [5:0]  r_slot = fb_t[18:13] + {fb_t[31:29], 3'd0};
    // pre-parent (norm applied at the re-entry register)
    wire [31:0] s_pp = {s_t[31:13], s_lo & ~(5'd1 << s_k), s_k + 3'd1, s_t[4:0]};
    reg  [5:0]  cnt_s, cnt_r;
    always @* begin
        cnt_s = cnt[s_slot] + ((do_ins && !sb) ? 6'd1 : 6'd0) - ((do_mrg && sb) ? 6'd1 : 6'd0)
                            - ((do_rel && r_slot == s_slot) ? 6'd1 : 6'd0);
        cnt_r = cnt[r_slot] - 6'd1;
    end
    always @(posedge clk or negedge rs_f)
        if (!rs_f) begin
            for (i = 0; i < 64; i = i + 1) begin cnt[i] <= 6'd0; ev[i] <= 32'd0; end
            any_open <= 1'b0;
        end else begin
            if (do_ins) ev[s_slot][s_h] <= 1'b1;
            if (do_mrg) ev[s_slot][s_h] <= 1'b0;
            if (do_rel && !((do_ins || do_mrg) && r_slot == s_slot)) cnt[r_slot] <= cnt_r;
            if (do_ins || do_mrg) cnt[s_slot] <= cnt_s;      // (B complete on the same slot folded in)
            any_open <= 1'b0;
            for (i = 0; i < 64; i = i + 1) if (cnt[i] != 6'd0) any_open <= 1'b1;
        end
    always @(posedge clk) begin
        if (do_ins) begin es[s_slot][s_h] <= s_side; if (!slot_busy) key[s_slot] <= s_key; end
    end
    // SRAM: pins driven by flops; insert writes at the next edge, a merge reads at the next edge (read-old; an entry
    // inserted at decision c is read at the earliest by decision c + 1, i.e. after its write: no bypass)
    reg        m_wce, m_rce; reg [8:0] m_wa, m_ra; reg [127:0] m_wd, m_wm;
    reg [1:0]  m1_w; reg m1_v; reg [31:0] m1_d, m1_t;
    always @(posedge clk or negedge rs_f)
        if (!rs_f) begin m_wce <= 1'b0; m_rce <= 1'b0; m1_v <= 1'b0; end
        else begin m_wce <= do_ins; m_rce <= do_mrg; m1_v <= do_mrg; end
    always @(posedge clk) begin
        m_wa <= {s_slot, s_h[4:2]}; m_wd <= {4{s_d}}; m_wm <= 128'd0; m_wm[32 * s_h[1:0] +: 32] <= 32'hFFFF_FFFF;
        m_ra <= {s_slot, s_h[4:2]}; m1_w <= s_h[1:0]; m1_d <= s_d; m1_t <= s_pp;
    end
    wire [127:0] m_q;
    ot_sram_1r1w_512x128_m4_r2c2 u_st (.clk(clk), .r_ce_in(m_rce), .r_addr_in(m_ra), .rd_out(m_q),
        .w_ce_in(m_wce), .w_addr_in(m_wa), .wd_in(m_wd), .w_mask_in(m_wm),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
    // M2: macro read edge; M3: macro output register (word select) -> adder operand register
    reg m2_v, m3_v; reg [1:0] m2_w; reg [31:0] m2_d, m2_t, m3_d, m3_t, m3_q;
    always @(posedge clk or negedge rs_f) if (!rs_f) begin m2_v <= 1'b0; m3_v <= 1'b0; end
                                         else begin m2_v <= m1_v; m3_v <= m2_v; end
    always @(posedge clk) begin
        m2_w <= m1_w; m2_d <= m1_d; m2_t <= m1_t;
        m3_q <= m_q[32 * m2_w +: 32]; m3_d <= m2_d; m3_t <= m2_t;
    end
    wire [31:0] sum; wire [1:0] serr; wire sv;
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rs_f), .valid_in(m3_v), .a(m3_q), .b(m3_d),
                                .y(sum), .err(serr), .valid_out(sv));
    wire [31:0] st_q;
    ot_hdc_delay #(.W(32), .D(5)) u_std (.clk(clk), .rst_n(rs_f), .d(m3_t), .q(st_q));
    always @(posedge clk or negedge rs_f) if (!rs_f) re_v <= 1'b0; else re_v <= sv;
    always @(posedge clk) begin re_t <= norm(st_q); re_d <= sum; re_e <= serr != 2'd0; end

    // ------------------------------------------------------------ DEC: config + two complete-word pipes
    reg [11:0] c_obase, c_ops; reg [2:0] c_np; reg [1:0] c_fmt; reg [15:0] c_rbase, c_rsplit; reg [10:0] c_rcnt;
    reg c_lo32, c_hi32;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin c_obase <= 12'd0; c_ops <= 12'd0; c_np <= 3'd0; c_fmt <= 2'd1; c_rbase <= 16'd0; c_rcnt <= 11'd0;
                         c_rsplit <= 16'd0; c_lo32 <= 1'b0; c_hi32 <= 1'b0; end
        else if (cfgv_q) begin
            c_obase <= cfgd_q[11:0]; c_ops <= cfgd_q[23:12]; c_np <= cfgd_q[26:24]; c_fmt <= cfgd_q[28:27];
            c_rbase <= cfgd_q[44:29]; c_rcnt <= cfgd_q[55:45]; c_rsplit <= cfgd_q[71:56];
            c_lo32 <= cfgd_q[72]; c_hi32 <= cfgd_q[73];
        end
    // D1: the complete words leave F1 (port pipe p = 0: A, 1: B)
    reg [1:0] d1_v; reg [31:0] d1_t [0:1], d1_d [0:1]; reg [1:0] d1_e;
    always @(posedge clk or negedge rs_o) if (!rs_o) d1_v <= 2'b00; else d1_v <= {fb_v && cb, fa_v && ca};
    always @(posedge clk) begin
        d1_t[0] <= fa_t; d1_d[0] <= fa_d; d1_e[0] <= fa_e;
        d1_t[1] <= fb_t; d1_d[1] <= fb_d; d1_e[1] <= fb_e;
    end
    // D2: e = row - rbase, range, chunk; data rounding
    reg [1:0] d2_v, d2_r; reg [9:0] d2_e [0:1]; reg [2:0] d2_p [0:1]; reg [31:0] d2_d [0:1]; reg [3:0] d2_c [0:1];
    // D3: k, wrap, word address
    reg [1:0] d3_v; reg [2:0] d3_k [0:1]; reg [11:0] d3_a [0:1]; reg [31:0] d3_d [0:1];
    reg [1:0] f9;
    function automatic [31:0] fmt_d(input [31:0] x, input [15:0] row, input [1:0] fmt, input [15:0] rs, input lo32, input hi32);
        reg [32:0] rb;
        begin
            rb = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            fmt_d = (fmt == 2'd1 || (fmt == 2'd0 && (row < rs ? lo32 : hi32))) ? x : {rb[31:16], 16'd0};
        end
    endfunction
    function automatic [2:0] mod5(input [3:0] c);
        mod5 = (c >= 4'd15) ? 3'd0 : (c >= 4'd10) ? c - 4'd10 : (c >= 4'd5) ? c - 4'd5 : c[2:0];
    endfunction
    function automatic [1:0] div5(input [3:0] c);
        div5 = (c >= 4'd15) ? 2'd3 : (c >= 4'd10) ? 2'd2 : (c >= 4'd5) ? 2'd1 : 2'd0;
    endfunction
    always @(posedge clk or negedge rs_o) if (!rs_o) begin d2_v <= 2'b00; d3_v <= 2'b00; f9 <= 2'b00; end
        else begin
            for (j = 0; j < 2; j = j + 1) begin
                d2_v[j] <= d1_v[j];
                d3_v[j] <= d2_v[j] && !d2_r[j];
                f9[j] <= d2_v[j] && d2_r[j];
            end
        end
    reg [15:0] e16 [0:1];
    always @* for (j = 0; j < 2; j = j + 1) e16[j] = d1_t[j][28:13] - c_rbase;
    always @(posedge clk) begin
        for (j = 0; j < 2; j = j + 1) begin
            d2_r[j] <= (e16[j] >= {5'd0, c_rcnt}) || d1_t[j][31:29] > c_np || c_fmt == 2'd3 || d1_e[j];
            d2_e[j] <= e16[j][9:0] + ((MUT == 3) ? 10'd64 : 10'd0);
            d2_c[j] <= e16[j][9:6] + ((MUT == 3) ? 4'd1 : 4'd0);
            d2_p[j] <= d1_t[j][31:29];
            d2_d[j] <= fmt_d(d1_d[j], d1_t[j][28:13], c_fmt, c_rsplit, c_lo32, c_hi32);
            d3_k[j] <= mod5(d2_c[j]);
            d3_a[j] <= c_obase + d2_p[j] * c_ops + {4'd0, div5(d2_c[j]), 6'd0} + {6'd0, d2_e[j][5:0]};
            d3_d[j] <= d2_d[j];
        end
    end
    // D4: output flops, fixed port rule port = address bit 2
    reg f8;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin cw_v <= 10'd0; f8 <= 1'b0; end
        else begin
            cw_v <= 10'd0; f8 <= 1'b0;
            for (j = 0; j < 2; j = j + 1)
                if (d3_v[j] && d3_k[j] < 3'd5) cw_v[2 * d3_k[j] + d3_a[j][2]] <= 1'b1;
            f8 <= d3_v[0] && d3_v[1] && d3_k[0] == d3_k[1] && d3_a[0][2] == d3_a[1][2];
        end
    always @(posedge clk)
        for (j = 0; j < 2; j = j + 1)
            if (d3_v[j])
                for (i = 0; i < 5; i = i + 1)
                    if (d3_k[j] == i) begin
                        cw_a[24 * i + 12 * d3_a[j][2] +: 12] <= d3_a[j];
                        cw_d[64 * i + 32 * d3_a[j][2] +: 32] <= d3_d[j];
                    end

    // ------------------------------------------------------------ sticky fault
    wire f10 = (|(l_v & l_e)) || (|l_f) || (re_v && re_e) || (fa_v && fa_e);
    wire f11 = cfgv_q && any_open;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) fault <= 1'b0;
        else if ((|n_f) || f5 || f6 || f7 || f8 || (|f9) || f10 || f11) fault <= 1'b1;
`ifndef SYNTHESIS
    // bench visibility: which obligation fired first
    reg [15:0] fcause;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) fcause <= 16'd0;
        else fcause <= fcause | {5'd0, f11, f10, |f9, f8, f7, f6, f5, 1'b0, |n_f[6:4], |n_f[3:0], 1'b0};
`endif
endmodule
`default_nettype wire
