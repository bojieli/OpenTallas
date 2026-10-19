`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81U-CAP2 (2026-10-17): ot_s81sl_cap_rt = the ROOT leaf of the capture root ot_s81sl_cap (hardened leaf, own clock
// root, x1 per slice).  The flat cap (22,261 sinks on one root, TT insertion 368.5 ps > 300) is split into
// 2 x ot_s81sl_cap_tr (the W / E column trees) + this leaf; ot_s81sl_cap is instances + abutted wiring only.
//
// Content = the old flat cap's tree root n6 + FIN + DEC + sticky fault, edge for edge (full description of FIN / DEC,
// the cfg_d format and the compiler obligations F5..F11: rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv header):
//   w_* / e_*  = the tree leaves' nc output words (their RST output flops) -> n6's P1 port flops directly: no added edge;
//   w_f / e_f  = the tree leaves' sticky faults -> one pin flop each -> this leaf's sticky fault.
// Structural changes against the flat form (no edge moves; cap_model.py unchanged):
//   * F1 decode (slot, parent node h, side, malformed, complete, pre-parent tag) is computed one register EARLIER, from
//     the n6 output flop and the re-entry register, into F1 side registers (fa_* / fb_*): the flat form's 21-level
//     fb_t -> slot add -> ev[slot][h] stage (~874 ps) loses the slot adder, the h decode and complete()/norm.
//   * the pairing-store state (cnt / ev, 2,432 reset flops) is 8 slot groups, each reset by its own relay copy
//     (ot_rst_relay REGIONS 20: two copies per group, <= ~180 loads a copy; the flat form had 2 copies x 2.8k loads).
//   * S81U-CAP3 (10-17): the pairing-store LOOKUP of each F1 word (cnt / key hit / ev bit / es bit of its slot) is read
//     one register EARLIER, at the edge that loads the F1 word, from the store's next state (the array read, with the
//     update the decision of that same edge makes forwarded: slot / h compare + mux).  The decision then starts from
//     registered lookups (fa_cn / fa_kh / fa_ev / fa_es and fb_*), so the gate's 18-level fb_t -> s_key -> key[s_slot]
//     compare -> do_ins -> cnt_s -> cnt stage (~795 ps) loses the 64:1 / 2048:1 muxes and the 24-bit compare.
//     Exact same state at every decision: no edge moves (cap_model.py unchanged, cap_bench cycle-exact).
//   * S81U-CAP5 (10-17, CAP3 gate @1d808d023 WARN: n6_t[13] / re_t[13] 3,604 loads each, TT ins 328.1 / spread 104.6,
//     resets 401 / 384, u_add s2_small -> s3_val ~647 ps): the look-ahead slot / h selects are REPLICATED, registered
//     copies per slot group (la_* / lb_*: slot[2:0] + h for ev + h for es, (* keep *), <= ~128 loads a copy) loaded at
//     the same edge as the word they decode -- n6's output register stage moves here (u_n6 RST 0 + n6_* flops = RST 1)
//     so the A copies load from n6's calendar read like n6_t; the B copies load from norm(st_q) like re_t.  The store
//     (cnt / ev / key / es) lives in the 8 slot groups (ot_s81sl_cap_grp, keep_hierarchy); a lookup is a group-local 8:1 (x 32:1 for ev / es) on the
//     group's copies and an 8:1 across groups.  Both adders (u_add, u_n6) are ot_s81_fadd_pipe (bit-identical,
//     valid-only reset, one add in stage 3).  Same values at the same edges: cap_model.py unchanged.
// MUT (bench mutants only): 1 wrong sibling association (h = parent of the parent), 3 leaf mapping off by one.
// OWNERS-S81/CAP2 (10-18, CAP5 --cts gate @59b690283 + cts_native_probe launch FAIL fault 236.7 / cw_n_a[12] 227.3 /
// [13] 224.9 > 220): every held output now launches from a dedicated TOP-module pin copy flop whose only load is its pin
// (cw_a_p / cw_d_p: same next state, same edge; fault_p: copy of the sticky, +1 edge on fault visibility only).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_rt #(
    parameter integer WIN = 2,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          w_v,          // W tree leaf output word (lanes 0..3 finished as far as the column tree goes)
    input  wire [31:0]   w_t,
    input  wire [31:0]   w_d,
    input  wire          w_e,
    input  wire          w_f,
    input  wire          e_v,          // E tree leaf (lanes 4..7)
    input  wire [31:0]   e_t,
    input  wire [31:0]   e_d,
    input  wire          e_e,
    input  wire          e_f,
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,       // leaves 0..2 (S face)
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,       // leaves 3, 4 (N face)
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);
    reg  [9:0]   cw_v; (* keep = "true" *) reg [119:0] cw_a; (* keep = "true" *) reg [319:0] cw_d;   // kept: never folded into the pin copies
    // OWNERS-S81/CAP2 (10-18): the held capture words cw_a / cw_d keep their value between writes, so their flops load
    // their own hold muxes and io_flop_at_pins cannot anchor them (cts_native_probe launch cw_n_a[12] 227.3 ps: flop
    // ~25 um from its N pin on a late leaf).  The pins are driven by dedicated TOP-module copy flops (* keep *) loaded
    // with the SAME next state at the SAME edge (0 edges moved); the hold feedback taps the internal copies only.
    (* keep = "true" *) reg [119:0] cw_a_p; (* keep = "true" *) reg [319:0] cw_d_p;
    (* keep = "true" *) reg fault_p;
    assign cw_s_v = cw_v[5:0];   assign cw_s_a = cw_a_p[71:0];   assign cw_s_d = cw_d_p[191:0];
    assign cw_n_v = cw_v[9:6];   assign cw_n_a = cw_a_p[119:72]; assign cw_n_d = cw_d_p[319:192];
    assign fault = fault_p;
    integer i, j;
    wire [19:0] rsv;
    ot_rst_relay #(.REGIONS(20), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_n = rsv[0], rs_f = rsv[1], rs_o = rsv[2], rs_c = rsv[3];
    wire [15:0] rs_s = rsv[19:4];                     // 2 per slot group

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

    function automatic [4:0] hof(input [31:0] t);      // parent tree node of a partial (1..31); MUT 1: grandparent
        reg [2:0] k; reg [4:0] lo;
        begin
            k = t[7:5]; lo = t[12:8];
            case (k)
                3'd0: hof = {1'b1, lo[4:1]};
                3'd1: hof = {2'b01, lo[4:2]};
                3'd2: hof = {3'b001, lo[4:3]};
                3'd3: hof = {4'b0001, lo[4]};
                3'd4: hof = 5'b00001;
                default: hof = 5'd0;
            endcase
            if (MUT == 1 && k < 3'd3) hof = {1'b0, hof[4:1]};
        end
    endfunction
    function automatic [5:0] slotof(input [31:0] t);   // (row + 8 pos) mod 64
        slotof = t[18:13] + {t[31:29], 3'd0};
    endfunction
    function automatic badof(input [31:0] t);          // not a tree node: k > 4, or lo not a multiple of 2^k
        badof = t[7:5] > 3'd4 || ((t[12:8] & ((5'd1 << t[7:5]) - 5'd1)) != 5'd0);
    endfunction
    function automatic [31:0] ppof(input [31:0] t);    // pre-parent (norm applied at the re-entry register)
        ppof = {t[31:13], t[12:8] & ~(5'd1 << t[7:5]), t[7:5] + 3'd1, t[4:0]};
    endfunction

    // ------------------------------------------------------------ TREE ROOT n6 (inputs = the tree leaves' output flops)
    wire n6_v, n6_e, n6_f; wire [31:0] n6_t, n6_d;
    wire n6r_v, n6r_e; wire [31:0] n6r_t, n6r_d;          // n6 calendar read (its r_* registers)
    ot_s81sl_cap_rt_retn #(.WIN(WIN), .RST(0)) u_n6 (.clk(clk), .rst_n(rs_n),
        .a_v(w_v), .a_t(w_t), .a_d(w_d), .a_e(w_e),
        .b_v(e_v), .b_t(e_t), .b_d(e_d), .b_e(e_e),
        .o_v(n6r_v), .o_t(n6r_t), .o_d(n6r_d), .o_e(n6r_e), .fault(n6_f));
    // n6's RST = 1 output register stage, here (as ot_s81_retn_static u_rd / g_rv: data without reset, valid with reset)
    reg n6v_q, n6e_q; reg [31:0] n6t_q, n6d_q;
    always @(posedge clk or negedge rs_n) if (!rs_n) n6v_q <= 1'b0; else n6v_q <= n6r_v;
    always @(posedge clk) begin n6t_q <= n6r_t; n6d_q <= n6r_d; n6e_q <= n6r_e; end
    assign n6_v = n6v_q, n6_t = n6t_q, n6_d = n6d_q, n6_e = n6e_q;
    reg lf_q;                                             // tree-leaf fault pin flops (OR after the flops)
    reg [1:0] lf_p;
    always @(posedge clk or negedge rs_c) if (!rs_c) lf_p <= 2'b00; else lf_p <= {e_f, w_f};
    always @* lf_q = |lf_p;

    // ------------------------------------------------------------ FIN: F1 registers (A = tree root, B = re-entry)
    reg        re_v; reg [31:0] re_t, re_d; reg re_e;     // re-entry register (adder sum + parent tag)
    reg        fa_v, fb_v; reg [31:0] fa_t, fa_d, fb_t, fb_d; reg fa_e, fb_e;
    // F1 side registers: the decode of the F1 word, computed from the n6 output flop / the re-entry register
    reg [5:0]  fa_sl, fb_sl; reg [4:0] fa_h, fb_h; reg fa_c, fb_c, fa_bad, fb_bad; reg [31:0] fa_pp, fb_pp;
    always @(posedge clk or negedge rs_f) if (!rs_f) begin fa_v <= 1'b0; fb_v <= 1'b0; end
                                         else begin fa_v <= n6_v; fb_v <= re_v; end
    always @(posedge clk) begin
        fa_t <= n6_t; fa_d <= n6_d; fa_e <= n6_e;
        fb_t <= re_t; fb_d <= re_d; fb_e <= re_e;
        fa_sl <= na_sl; fa_h <= na_h; fa_c <= complete(n6_t); fa_bad <= badof(n6_t); fa_pp <= ppof(n6_t);
        fb_sl <= nb_sl; fb_h <= nb_h; fb_c <= complete(re_t); fb_bad <= badof(re_t); fb_pp <= ppof(re_t);
    end
    wire ca = fa_c, cb = fb_c;
    wire sa = fa_v && !ca, sb = fb_v && !cb;              // store candidates
    wire f5 = sa && sb;
    // the store word of this edge (B first if both: F5 is a fault anyway)
    wire        s_v = sa || sb;
    wire [31:0] s_t = sb ? fb_t : fa_t;
    wire [31:0] s_d = sb ? fb_d : fa_d;
    wire [2:0]  s_k = s_t[7:5];
    wire [4:0]  s_lo = s_t[12:8];
    wire [23:0] s_key = {s_t[31:13], s_t[4:0]};          // {pos, row, nseg}
    wire [5:0]  s_slot = sb ? fb_sl : fa_sl;
    wire [4:0]  s_h = sb ? fb_h : fa_h;
    wire        s_side = s_lo[s_k];
    wire        s_bad = sb ? fb_bad : fa_bad;
    wire [31:0] s_pp = sb ? fb_pp : fa_pp;

    // pairing store state.  cnt[slot] = waiting entries + parents in flight, so a slot is never re-keyed while a
    // partial of its row is anywhere in the finish (the parent has the same key and comes back to the same slot):
    //   A insert +1 | A merge 0 (entry -> parent in flight) | B insert 0 | B merge -1 | B complete -1.
    // key [slot] {pos, row, nseg}, es [slot] entry side (lo[k] of the waiting child), cnt [slot], ev [slot] entry valid
    // bit h: all in the slot groups g_st[slot / 8]
    wire [7:0]  any_g;                                    // registered OR of cnt != 0 per slot group (F11)
    wire        any_open = |any_g;
    // registered look-ahead lookups of the F1 words' slots (loaded with fa_* / fb_*, see below)
    reg  [5:0]  fa_cn, fb_cn; reg fa_kh, fb_kh, fa_ev, fb_ev, fa_es, fb_es;
    wire [5:0]  s_cn = sb ? fb_cn : fa_cn;                // = cnt[s_slot]
    wire        slot_busy = s_cn != 6'd0;
    wire        key_hit = sb ? fb_kh : fa_kh;             // = key[s_slot] == s_key
    wire        f6 = s_v && slot_busy && !key_hit;
    wire        e_wait = slot_busy && key_hit && (sb ? fb_ev : fa_ev);   // ev[s_slot][s_h]
    wire        f7 = s_v && (s_bad || (e_wait && (sb ? fb_es : fa_es) == s_side));
    wire        do_ins = s_v && !f6 && !f7 && !e_wait;
    wire        do_mrg = s_v && !f6 && !f7 && e_wait;
    wire        do_rel = fb_v && cb;                      // a complete re-entry leaves its slot
    wire [5:0]  r_slot = fb_sl;
    reg  [5:0]  cnt_s, cnt_r;
    always @* begin
        cnt_s = s_cn + ((do_ins && !sb) ? 6'd1 : 6'd0) - ((do_mrg && sb) ? 6'd1 : 6'd0)
                     - ((do_rel && r_slot == s_slot) ? 6'd1 : 6'd0);
        cnt_r = fb_cn - 6'd1;                             // cnt[r_slot], r_slot = fb_sl
    end
    // ---- look-ahead lookups (S81U-CAP3): the slot state the NEXT decision sees = this edge's update forwarded over
    //      the array read, for the word now entering F1 on each side (A from the n6 output flop, B from the re-entry)
    // top copies of the incoming words' slot / h (= slotof / hof of n6_t / re_t, registered with them)
    (* keep = "true" *) reg [5:0] na_sl, nb_sl;
    (* keep = "true" *) reg [4:0] na_h, nb_h;
    (* keep = "true" *) reg [2:0] la_gs, lb_gs;          // group select copies for the across-group 8:1
    wire [31:0] re_tn = norm(st_q);                       // = re_t at the next edge
    wire [5:0]  na_sln = slotof(n6r_t), nb_sln = slotof(re_tn);
    always @(posedge clk) begin
        na_sl <= na_sln; na_h <= hof(n6r_t); la_gs <= na_sln[5:3];
        nb_sl <= nb_sln; nb_h <= hof(re_tn); lb_gs <= nb_sln[5:3];
    end
    // group-local lookups (g_st), selected across groups
    wire [5:0]  ga_cn [0:7], gb_cn [0:7];
    wire [23:0] ga_key [0:7], gb_key [0:7];
    wire [7:0]  ga_ev, gb_ev, ga_es, gb_es;
    wire [23:0] na_key = {n6_t[31:13], n6_t[4:0]}, nb_key = {re_t[31:13], re_t[4:0]};
    wire        upd = do_ins || do_mrg;
    wire        kwr = do_ins && !slot_busy;               // key[s_slot] <= s_key at this edge
    wire        a_ss = s_slot == na_sl, b_ss = s_slot == nb_sl;
    always @(posedge clk) begin
        fa_cn <= (upd && a_ss) ? cnt_s : (do_rel && r_slot == na_sl) ? cnt_r : ga_cn[la_gs];
        fb_cn <= (upd && b_ss) ? cnt_s : (do_rel && r_slot == nb_sl) ? cnt_r : gb_cn[lb_gs];
        fa_kh <= (kwr && a_ss) ? (s_key == na_key) : (ga_key[la_gs] == na_key);
        fb_kh <= (kwr && b_ss) ? (s_key == nb_key) : (gb_key[lb_gs] == nb_key);
        fa_ev <= (upd && a_ss && s_h == na_h) ? do_ins : ga_ev[la_gs];
        fb_ev <= (upd && b_ss && s_h == nb_h) ? do_ins : gb_ev[lb_gs];
        fa_es <= (do_ins && a_ss && s_h == na_h) ? s_side : ga_es[la_gs];
        fb_es <= (do_ins && b_ss && s_h == nb_h) ? s_side : gb_es[lb_gs];
    end
    wire [4:0]  na_hn = hof(n6r_t), nb_hn = hof(re_tn);
    wire        rs_same = r_slot == s_slot;
    genvar gs;
    generate for (gs = 0; gs < 8; gs = gs + 1) begin : g_st
        ot_s81sl_cap_grp u_g (.clk(clk), .rs_e(rs_s[2 * gs + 1]), .rs_c(rs_s[2 * gs]),
            .la_d(na_sln[2:0]), .ha_d(na_hn), .lb_d(nb_sln[2:0]), .hb_d(nb_hn),
            .s_in(s_slot[5:3] == gs), .r_in(r_slot[5:3] == gs), .do_ins(do_ins), .do_mrg(do_mrg), .do_rel(do_rel),
            .rs_same(rs_same), .s_sl(s_slot[2:0]), .r_sl(r_slot[2:0]), .s_h(s_h), .s_side(s_side), .s_key(s_key),
            .slot_busy(slot_busy), .cnt_s(cnt_s), .cnt_r(cnt_r),
            .a_cn(ga_cn[gs]), .a_key(ga_key[gs]), .a_ev(ga_ev[gs]), .a_es(ga_es[gs]),
            .b_cn(gb_cn[gs]), .b_key(gb_key[gs]), .b_ev(gb_ev[gs]), .b_es(gb_es[gs]), .any_o(any_g[gs]));
    end endgenerate
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
    ot_s81_fadd_pipe u_add (.clk(clk), .rst_n(rs_f), .valid_in(m3_v), .a(m3_q), .b(m3_d),
                                .y(sum), .err(serr), .valid_out(sv));
    wire [31:0] st_q;
    ot_hdc_delay #(.W(32), .D(5)) u_std (.clk(clk), .rst_n(rs_f), .d(m3_t), .q(st_q));
    always @(posedge clk or negedge rs_f) if (!rs_f) re_v <= 1'b0; else re_v <= sv;
    always @(posedge clk) begin re_t <= re_tn; re_d <= sum; re_e <= serr != 2'd0; end

    // cfg pin flops
    reg cfgv_q; reg [159:0] cfgd_q;
    always @(posedge clk or negedge rs_c) if (!rs_c) cfgv_q <= 1'b0; else cfgv_q <= cfg_v;
    always @(posedge clk) cfgd_q <= cfg_d;
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
    reg [119:0] cw_a_n; reg [319:0] cw_d_n;                // next state of the held capture words (internal + pin copy)
    always @* begin
        cw_a_n = cw_a; cw_d_n = cw_d;
        for (j = 0; j < 2; j = j + 1)
            if (d3_v[j])
                for (i = 0; i < 5; i = i + 1)
                    if (d3_k[j] == i) begin
                        cw_a_n[24 * i + 12 * d3_a[j][2] +: 12] = d3_a[j];
                        cw_d_n[64 * i + 32 * d3_a[j][2] +: 32] = d3_d[j];
                    end
    end
    always @(posedge clk) begin cw_a <= cw_a_n; cw_d <= cw_d_n; cw_a_p <= cw_a_n; cw_d_p <= cw_d_n; end

    // ------------------------------------------------------------ sticky fault
    wire f10 = (re_v && re_e) || (fa_v && fa_e);         // lane err / status faults: in the tree leaves (lf_q)
    wire f11 = cfgv_q && any_open;
    reg fault_q;                                          // internal sticky fault (D = the decision logic's OR)
    always @(posedge clk or negedge rs_c)
        if (!rs_c) fault_q <= 1'b0;
        else if (n6_f || lf_q || f5 || f6 || f7 || f8 || (|f9) || f10 || f11) fault_q <= 1'b1;
    // OWNERS-S81/CAP2 (10-18): the fault pin is a dedicated copy flop of the sticky (+1 edge on fault visibility only;
    // fault is checked at phase end, not timed: SLICE_CONTRACT).  Its only load is the S pin, so io_flop_at_pins anchors
    // it there (gate @59b690283: the sticky flop sat at (120, 77.8) beside its OR cone, ~170 um from the S pin, launch
    // 236.7 ps > 220).  f5..f7 are decision logic, not registered bits: a same-edge copy would carry the cone to the pin.
    always @(posedge clk or negedge rs_c) if (!rs_c) fault_p <= 1'b0; else fault_p <= fault_q;
`ifndef SYNTHESIS
    // bench visibility: which obligation fired first ([1] tree leaves, [3] n6, [4..10] F5..F11)
    reg [15:0] fcause;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) fcause <= 16'd0;
        else fcause <= fcause | {5'd0, f11, f10, |f9, f8, f7, f6, f5, n6_f, 1'b0, lf_q, 1'b0};
`endif
endmodule
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81sl_cap_grp (S81U-CAP5): one slot group (8 slots) of the cap_rt pairing store -- cnt / ev (reset) + key / es --
// with its OWN registered copies of the incoming words' slot[2:0] / h (A from n6, B from the re-entry) and its local
// lookups.  keep_hierarchy: the CAP5 first gate showed yosys (share / opt) re-pointing all 8 groups' read muxes onto
// ONE group's copy (g_st[7].la_sl[0] 3,803 loads) when the groups were a flat generate; a hard module boundary keeps
// each group's selects local (<= ~130 loads a copy).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_s81sl_cap_grp (
    input  wire        clk,
    input  wire        rs_e,
    input  wire        rs_c,
    input  wire [2:0]  la_d,
    input  wire [4:0]  ha_d,
    input  wire [2:0]  lb_d,
    input  wire [4:0]  hb_d,
    input  wire        s_in,
    input  wire        r_in,
    input  wire        do_ins,
    input  wire        do_mrg,
    input  wire        do_rel,
    input  wire        rs_same,
    input  wire [2:0]  s_sl,
    input  wire [2:0]  r_sl,
    input  wire [4:0]  s_h,
    input  wire        s_side,
    input  wire [23:0] s_key,
    input  wire        slot_busy,
    input  wire [5:0]  cnt_s,
    input  wire [5:0]  cnt_r,
    output wire [5:0]  a_cn,
    output wire [23:0] a_key,
    output wire        a_ev,
    output wire        a_es,
    output wire [5:0]  b_cn,
    output wire [23:0] b_key,
    output wire        b_ev,
    output wire        b_es,
    output wire        any_o
);
    reg [5:0]  cnt_g [0:7];
    reg [31:0] ev_g [0:7];
    reg [23:0] key_g [0:7];
    reg [31:0] es_g [0:7];
    reg        any_q;
    integer q;
    (* keep = "true" *) reg [2:0] la_sl, lb_sl;
    (* keep = "true" *) reg [4:0] la_hv, la_hs, lb_hv, lb_hs;
    always @(posedge clk) begin
        la_sl <= la_d; la_hv <= ha_d; la_hs <= ha_d;
        lb_sl <= lb_d; lb_hv <= hb_d; lb_hs <= hb_d;
    end
    assign a_cn = cnt_g[la_sl]; assign a_key = key_g[la_sl];
    assign a_ev = ev_g[la_sl][la_hv]; assign a_es = es_g[la_sl][la_hs];
    assign b_cn = cnt_g[lb_sl]; assign b_key = key_g[lb_sl];
    assign b_ev = ev_g[lb_sl][lb_hv]; assign b_es = es_g[lb_sl][lb_hs];
    always @(posedge clk)
        if (do_ins && s_in) begin
            es_g[s_sl][s_h] <= s_side;
            if (!slot_busy) key_g[s_sl] <= s_key;
        end
    always @(posedge clk or negedge rs_e)
        if (!rs_e) begin
            for (q = 0; q < 8; q = q + 1) ev_g[q] <= 32'd0;
        end else begin
            if (do_ins && s_in) ev_g[s_sl][s_h] <= 1'b1;
            if (do_mrg && s_in) ev_g[s_sl][s_h] <= 1'b0;
        end
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin
            for (q = 0; q < 8; q = q + 1) cnt_g[q] <= 6'd0;
            any_q <= 1'b0;
        end else begin
            if (do_rel && r_in && !((do_ins || do_mrg) && rs_same)) cnt_g[r_sl] <= cnt_r;
            if ((do_ins || do_mrg) && s_in) cnt_g[s_sl] <= cnt_s;   // (B complete on the same slot folded in)
            any_q <= 1'b0;
            for (q = 0; q < 8; q = q + 1) if (cnt_g[q] != 6'd0) any_q <= 1'b1;
        end
    assign any_o = any_q;
endmodule


// s81sl_cap_rt-ONLY node + adder (HOURLY-S81/CAPRT 2026-10-19, COORD 10-19 ~02:40).
//
// The CAP5 structural fix first put ot_s81_fadd_pipe and an ADDN parameter (default 0) into the SHARED
// rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv.  Even default-off, that edit changes the file the CLOSED s81sl_cap_tr
// and s81net_node_* views are source-bound to.  So the shared file stays byte-identical to main and cap_rt binds these
// (kept in this file so the kit and cap_bench.sh source lists are unchanged):
//   * ot_s81sl_cap_rt_retn = ot_s81_retn_static (main, verbatim: same ports, parameters, slot rule, faults, mutants),
//     except that the node adder u_add is ot_s81_fadd_pipe instead of ot_fp32_add_rne_pipe (same 5 edges, bit-identical);
//   * ot_s81_fadd_pipe (the CAP5 adder, unchanged).
// Keep ot_s81sl_cap_rt_retn in step with ot_s81_retn_static: any fix there is copied here (cap_bench checks both paths).

module ot_s81sl_cap_rt_retn #(
    parameter integer WIN = 2,           // sibling window, edges (>= 1)
    parameter integer RST = 1,           // output register stages (wire reach), as ot_v41_retn_w17w10
    parameter integer MUT = 0,           // bench mutants only: 1 window off by one, 2 forward slot +1, 3 fault blind
    // DLR (S81U-CAP4 2026-10-17, default 0 = the shift form, netlist unchanged for every existing node tile): the two
    // AL-deep side-band lanes (q_asb + u_asb, q_fsb + u_fsb: (34+SW) + (66+SW) bits x 6 registers) as cycle-exact
    // register-file delay lines ot_hdc_delay_rf D = AL + 1 (input register = the old q_*sb, N = AL - 1 rows written once
    // and read through the N:1 mux, output register), so no zero-logic flop -> flop hop is left in them.  Same flop count,
    // same edges.  Why: s81sl_cap_tr route 9df7f8153 (3 nodes, 6,200 sinks) NEEDS_RTL FF hold -6.37 ps; all 188 violators
    // are flop -> INV -> flop pass hops (93 of them in u_fsb / u_asb), capture clock 14 ps after launch, ECO 7,489 cells.
    parameter integer DLR = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        a_v,
    input  wire [31:0] a_t,
    input  wire [31:0] a_d,
    input  wire        a_e,
    input  wire        b_v,
    input  wire [31:0] b_t,
    input  wire [31:0] b_d,
    input  wire        b_e,
    output wire        o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e,
    output reg         fault
);
    // ot_v41_ret_pkg norm / complete / sibling / parent, copied verbatim (the ORFS yosys front end has no package import)
    localparam integer TW = 3 + 16 + 5 + 3 + 5;   // {position, row, lo, k, nseg}
    // norm(): the ot_v41_ret_pkg loop "k++ while C(k)" (5 iterations, k < 5 only) in closed form (n5b: the serial loop
    // synthesised to 35 levels / ~1,275 ps).  C(j) for j = 0..4 are independent; k_final = the first j >= k with !C(j),
    // else 5; k >= 5 is never incremented.  Bit-identical to the loop (exhaustive check tools/s81/static_return_calendar.py
    // norm_closed_check).
    function automatic [TW-1:0] norm(input [TW-1:0] t);
        reg [18:0] row;
        reg [4:0] lo, n, c;
        reg [2:0] k, kf;
        integer j;
        begin
            {row, lo, k, n} = t;
            for (j = 0; j < 5; j = j + 1)
                c[j] = !(lo == 5'd0 && (6'd1 << j) >= {1'b0, n}) && lo[j] == 1'b0 && ({1'b0, lo} + (6'd1 << j)) >= {1'b0, n};
            kf = k;
            if (k < 3'd5) begin
                kf = 3'd5;
                for (j = 4; j >= 0; j = j - 1)
                    if (j >= k && !c[j]) kf = j;
            end
            norm = {row, lo, kf, n};
        end
    endfunction
    function automatic complete(input [TW-1:0] t);
        complete = t[12:8] == 5'd0 && (6'd1 << t[7:5]) >= {1'b0, t[4:0]};
    endfunction
    function automatic sibling(input [TW-1:0] a, input [TW-1:0] b);
        sibling = a[31:13] == b[31:13] && a[7:5] == b[7:5] && a[4:0] == b[4:0] &&
                  (a[12:8] ^ b[12:8]) == (5'd1 << a[7:5]);
    endfunction
    function automatic [TW-1:0] preparent(input [TW-1:0] a, input [TW-1:0] b);   // parent() before its norm()
        preparent = {a[31:13], (a[12:8] < b[12:8]) ? a[12:8] : b[12:8], a[7:5] + 3'd1, a[4:0]};
    endfunction
    function automatic [TW-1:0] parent(input [TW-1:0] a, input [TW-1:0] b);
        reg [4:0] lo;
        begin
            lo = (a[12:8] < b[12:8]) ? a[12:8] : b[12:8];
            parent = norm({a[31:13], lo, a[7:5] + 3'd1, a[4:0]});
        end
    endfunction
    localparam integer WE = (MUT == 1) ? WIN + 1 : WIN;      // mutant 1: window one edge too long
    localparam integer SL = (WIN + 2 <= 4) ? 4 : (WIN + 2 <= 8) ? 8 : 16;   // exit calendar slots (power of two)
    localparam integer SW = $clog2(SL);
    localparam integer AL = 5;                                 // ot_fp32_add_rne_pipe latency (edges)

    // ---------------- sibling windows: entry k holds the word that arrived k+1 edges ago --------------------------
    reg          wa_v [0:WE-1], wb_v [0:WE-1];
    reg [31:0]   wa_t [0:WE-1], wb_t [0:WE-1], wa_d [0:WE-1], wb_d [0:WE-1];
    reg          wa_e [0:WE-1], wb_e [0:WE-1];

    // ---------------- P1 port registers, P2 normalised tag registers ------------------------------------------------
    reg         p1a_v, p1b_v, p2a_v, p2b_v;
    reg  [31:0] p1a_t, p1a_d, p1b_t, p1b_d, na, nb, pa_d, pb_d;
    reg         p1a_e, p1b_e, pa_e, pb_e;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin p1a_v <= 1'b0; p1b_v <= 1'b0; p2a_v <= 1'b0; p2b_v <= 1'b0; end
        else begin p1a_v <= a_v; p1b_v <= b_v; p2a_v <= p1a_v; p2b_v <= p1b_v; end
    end
    always @(posedge clk) begin
        p1a_t <= a_t; p1a_d <= a_d; p1a_e <= a_e; p1b_t <= b_t; p1b_d <= b_d; p1b_e <= b_e;
        na <= norm(p1a_t); pa_d <= p1a_d; pa_e <= p1a_e; nb <= norm(p1b_t); pb_d <= p1b_d; pb_e <= p1b_e;
    end
    wire xa_v = p2a_v, xb_v = p2b_v;
    wire m_ab = xa_v && xb_v && sibling(na, nb);               // same-edge siblings
    reg  [WE-1:0] ma, mb;                                      // a vs window b, b vs window a
    integer k;
    always @* begin
        for (k = 0; k < WE; k = k + 1) begin
            ma[k] = xa_v && wb_v[k] && sibling(na, wb_t[k]);
            mb[k] = xb_v && wa_v[k] && sibling(nb, wa_t[k]);
        end
    end
    // one-hot picks (F3: more than one match is a fault; the lowest index is used, deterministically)
    function automatic integer first1(input [WE-1:0] v);
        integer i; begin first1 = -1; for (i = WE - 1; i >= 0; i = i - 1) if (v[i]) first1 = i; end
    endfunction
    function automatic integer cnt1(input [WE-1:0] v);
        integer i; begin cnt1 = 0; for (i = 0; i < WE; i = i + 1) cnt1 = cnt1 + v[i]; end
    endfunction
    integer ka, kb;
    always @* begin ka = first1(ma); kb = first1(mb); end
    wire a_win = !m_ab && ka >= 0;                             // a merges with an older b
    wire b_win = !m_ab && kb >= 0;                             // b merges with an older a
    wire add2 = a_win && b_win;                                // F2 violation
    wire multi = (cnt1(ma) + (m_ab ? 1 : 0) > 1) || (cnt1(mb) + (m_ab ? 1 : 0) > 1);   // F3 violation

    // merge issue this edge: operands, tag, error, and the earlier sibling's age (edges since its arrival)
    reg         is_add;
    reg  [31:0] add_x, add_y, add_t;
    reg         add_e;
    reg  [SW:0] add_age;
    always @* begin
        is_add = 1'b0; add_x = 32'd0; add_y = 32'd0; add_t = 32'd0; add_e = 1'b0; add_age = '0;
        if (m_ab) begin
            is_add = 1'b1; add_x = pa_d; add_y = pb_d; add_t = preparent(na, nb); add_e = pa_e | pb_e; add_age = '0;
        end else if (a_win) begin
            is_add = 1'b1; add_x = pa_d; add_y = wb_d[ka]; add_t = preparent(na, wb_t[ka]); add_e = pa_e | wb_e[ka];
            add_age = ka + 1;
        end else if (b_win) begin
            is_add = 1'b1; add_x = wa_d[kb]; add_y = pb_d; add_t = preparent(wa_t[kb], nb); add_e = wa_e[kb] | pb_e;
            add_age = kb + 1;
        end
    end
    // consumption of window entries this edge
    wire [WE-1:0] ca, cb;
    genvar g;
    generate for (g = 0; g < WE; g = g + 1) begin : g_c
        assign cb[g] = !m_ab && a_win && ka == g;
        assign ca[g] = !m_ab && b_win && !a_win && kb == g;
    end endgenerate
    // arrivals that stay in the window (not merged on arrival)
    wire a_in = xa_v && !m_ab && !a_win;
    wire b_in = xb_v && !m_ab && !(b_win && !a_win);
    // window exits (unmerged, age WE): forwarded
    wire fa = wa_v[WE-1] && !ca[WE-1];
    wire fb = wb_v[WE-1] && !cb[WE-1];
    wire fwd2 = fa && fb;                                      // F1 violation (two exit-slot owners)
    wire        is_fwd = fa | fb;
    wire [31:0] fw_t = fa ? wa_t[WE-1] : wb_t[WE-1];
    wire [31:0] fw_d = fa ? wa_d[WE-1] : wb_d[WE-1];
    wire        fw_e = fa ? wa_e[WE-1] : wb_e[WE-1];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < WE; k = k + 1) begin wa_v[k] <= 1'b0; wb_v[k] <= 1'b0; end
        end else begin
            wa_v[0] <= a_in; wb_v[0] <= b_in;
            for (k = 1; k < WE; k = k + 1) begin
                wa_v[k] <= wa_v[k-1] && !ca[k-1];
                wb_v[k] <= wb_v[k-1] && !cb[k-1];
            end
        end
    end
    always @(posedge clk) begin
        wa_t[0] <= na; wa_d[0] <= pa_d; wa_e[0] <= pa_e;
        wb_t[0] <= nb; wb_d[0] <= pb_d; wb_e[0] <= pb_e;
        for (k = 1; k < WE; k = k + 1) begin
            wa_t[k] <= wa_t[k-1]; wa_d[k] <= wa_d[k-1]; wa_e[k] <= wa_e[k-1];
            wb_t[k] <= wb_t[k-1]; wb_d[k] <= wb_d[k-1]; wb_e[k] <= wb_e[k-1];
        end
    end

    // ---------------- 5-stage lanes: adder + matched forward delay ---------------------------------------------------
    wire [31:0] sum; wire [1:0] err; wire sv;
    // P3 issue register: the adder, its side band and the forward lane start from flops (uniform +1 edge)
    reg         q_add, q_fwd;
    reg  [31:0] q_x, q_y;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin q_add <= 1'b0; q_fwd <= 1'b0; end
                                           else begin q_add <= is_add; q_fwd <= is_fwd; end
    always @(posedge clk) begin q_x <= add_x; q_y <= add_y; end
    ot_s81_fadd_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(q_add), .a(q_x), .b(q_y),
                            .y(sum), .err(err), .valid_out(sv));
    // side band of the add: tag, error, wait-to-exit; forward lane: word + wait
    // exit edge = early + WIN + EXIT_C.  A sum issued at edge n whose earlier sibling arrived age edges before waits
    // WIN - age more edges than a forward (which issues at age WIN).
    localparam integer FWD_WAIT = (MUT == 2) ? 2 : 1;        // a forward issues at age WIN: one edge in the calendar
    localparam [SW:0] WIN1 = WIN + 1;
    wire [SW:0] add_wait = WIN1 - add_age;                     // sum: early + WIN + 6 = issue + 5 + (WIN + 1 - age)
    wire [32+1+SW:0] add_sb, add_sbq, asb_rf;
    reg  [32+1+SW:0] q_asb;
    always @(posedge clk) q_asb <= {add_t, add_e, add_wait};
    assign add_sb = (DLR != 0) ? asb_rf : q_asb;
    ot_hdc_delay #(.W(34 + SW), .D((DLR != 0) ? 0 : AL)) u_asb (.clk(clk), .rst_n(rst_n), .d(add_sb), .q(add_sbq));
    wire [65+SW:0] fw_sb, fw_sbq, fsb_rf;
    localparam [SW:0] FWW = FWD_WAIT;
    reg  [65+SW:0] q_fsb;
    always @(posedge clk) q_fsb <= {fw_t, fw_d, fw_e, FWW};
    assign fw_sb = (DLR != 0) ? fsb_rf : q_fsb;
    ot_hdc_delay #(.W(66 + SW), .D((DLR != 0) ? 0 : AL)) u_fsb (.clk(clk), .rst_n(rst_n), .d(fw_sb), .q(fw_sbq));
    generate if (DLR != 0) begin : g_dlr   // q_*sb + D = AL shift == rf D = AL + 1 (q_*sb unused, removed by synthesis)
        ot_hdc_delay_rf #(.W(34 + SW), .D(AL + 1)) u_asb_rf (.clk(clk), .rst_n(rst_n), .d({add_t, add_e, add_wait}),
                                                            .q(asb_rf));
        ot_hdc_delay_rf #(.W(66 + SW), .D(AL + 1)) u_fsb_rf (.clk(clk), .rst_n(rst_n), .d({fw_t, fw_d, fw_e, FWW}),
                                                            .q(fsb_rf));
    end else begin : g_shl
        assign asb_rf = '0;
        assign fsb_rf = '0;
    end endgenerate
    reg [AL-1:0] fv;
    always @(posedge clk or negedge rst_n) if (!rst_n) fv <= '0; else fv <= {fv[AL-2:0], q_fwd};
    wire fwd_v5 = fv[AL-1];

    // ---------------- exit calendar ---------------------------------------------------------------------------------
    reg [SW-1:0] now;                                          // free-running edge counter (mod SL)
    reg          cal_v [0:SL-1];
    reg [31:0]   cal_t [0:SL-1], cal_d [0:SL-1];
    reg          cal_e [0:SL-1];
    wire [SW-1:0] slot_a = now + add_sbq[SW-1:0];
    wire [SW-1:0] slot_f = now + fw_sbq[SW-1:0];
    wire coll = (sv && cal_v[slot_a]) || (fwd_v5 && cal_v[slot_f]) || (sv && fwd_v5 && slot_a == slot_f);   // F4
    reg         r_v, r_e;
    reg  [31:0] r_t, r_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            now <= '0; r_v <= 1'b0; fault <= 1'b0;
            for (k = 0; k < SL; k = k + 1) cal_v[k] <= 1'b0;
        end else begin
            now <= now + 1'b1;
            r_v <= cal_v[now];
            cal_v[now] <= 1'b0;
            if (sv && !cal_v[slot_a]) cal_v[slot_a] <= 1'b1;
            if (fwd_v5 && !(sv && slot_a == slot_f) && !cal_v[slot_f]) cal_v[slot_f] <= 1'b1;
            if (MUT != 3 && (fwd2 || add2 || multi || coll)) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        r_t <= cal_t[now]; r_d <= cal_d[now]; r_e <= cal_e[now];
        if (sv && !cal_v[slot_a]) begin
            cal_t[slot_a] <= norm(add_sbq[33+SW:2+SW]); cal_d[slot_a] <= sum;   // parent = norm(pre-parent)
            cal_e[slot_a] <= add_sbq[1+SW] | (err != 2'd0);
        end
        if (fwd_v5 && !(sv && slot_a == slot_f) && !cal_v[slot_f]) begin
            cal_t[slot_f] <= fw_sbq[65+SW:34+SW]; cal_d[slot_f] <= fw_sbq[33+SW:2+SW]; cal_e[slot_f] <= fw_sbq[1+SW];
        end
    end

    // ---------------- RST output register stages (as ot_v41_retn_w17w10) --------------------------------------------
    wire [65:0] rq;
    ot_hdc_delay #(.W(66), .D(RST)) u_rd (.clk(clk), .rst_n(rst_n), .d({r_t, r_d, r_e, 1'b0}), .q(rq));
    wire [RST:0] rv;
    assign rv[0] = r_v;
    genvar r;
    generate for (r = 0; r < RST; r = r + 1) begin : g_rv
        reg q;
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= rv[r];
        assign rv[r+1] = q;
    end endgenerate
    assign o_v = rv[RST];
    assign o_t = rq[65:34];
    assign o_d = rq[33:2];
    assign o_e = rq[1];
`ifndef SYNTHESIS
    initial if (WIN < 1 || WIN > 14) $fatal(1, "ot_s81sl_cap_rt_retn: 1 <= WIN <= 14");
`endif
endmodule


// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_fadd_pipe (S81U-CAP5 2026-10-17): ot_fp32_add_rne_pipe, bit-identical (y, err, valid_out at the same 5 edges;
// equivalence bench rtl/dsrom_sys/s81_dv/slice/test/tb_s81_fadd_eq.sv), restructured for the s81sl_cap_rt gate:
//   * reset only on the valid chain: the datapath registers carry no reset (the original resets all ~350 of them, which
//     made every node / finish reset net 384-401 loads);
//   * stage 2 registers the small operand already inverted for a subtraction and the exact-cancellation flag
//     (|a| == |b| <=> dist == 0 && big == small: for dist > 0 the big operand is normal, >= 2^26 in the 28-bit frame,
//     and the shifted small one is < 2^26), so stage 3 is ONE 28-bit add (big + small' + sub) with no sum/dif mux and
//     no 28-bit zero detect behind it (gate: u_add.s2_small -> s3_val 18 levels ~647 ps);
//   * the carry renormalize (shift right one, exponent + 1) moves into stage 4, where a carry excludes the cancellation
//     normalize (carry => add => no left shift), so stage 4 gains one final 2:1 mux and nothing else.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_fadd_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;
    integer k;
    // -- stage 1: decode, order by magnitude, resolve the zero operands (as ot_fp32_add_rne_pipe)
    wire        a_sign = a[31], b_sign = b[31];
    wire [7:0]  a_field = a[30:23], b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire s1_nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_is_zero = (a_man == 24'd0);
    wire b_is_zero = (b_man == 24'd0);
    wire s1_bypass = s1_nonfinite || a_is_zero || b_is_zero;
    wire [31:0] s1_bypass_code = s1_nonfinite ? 32'd0 : (a_is_zero ? (b_is_zero ? 32'd0 : b) : a);
    wire swap = (b_exp > a_exp) || ((b_exp == a_exp) && (b_man > a_man));
    reg        s1_v, s2_v, s3_v, s4_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v <= 1'b0; s2_v <= 1'b0; s3_v <= 1'b0; s4_v <= 1'b0; valid_out <= 1'b0; end
        else begin s1_v <= valid_in; s2_v <= s1_v; s3_v <= s2_v; s4_v <= s3_v; valid_out <= s4_v; end
    reg        s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp, s1_dist;
    reg [23:0] s1_big, s1_small;
    always @(posedge clk) begin
        s1_byp <= s1_bypass;
        s1_err <= s1_nonfinite ? E_NONFINITE : E_NONE;
        s1_code <= s1_bypass_code;
        s1_sub <= (a_sign != b_sign);
        s1_sign <= swap ? b_sign : a_sign;
        s1_exp <= swap ? b_exp : a_exp;
        s1_dist <= (swap ? b_exp : a_exp) - (swap ? a_exp : b_exp);
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? a_man : b_man;
    end
    // -- stage 2: align (jamming), invert for a subtraction, exact-cancellation flag
    function automatic [27:0] shift_right_jam_28(input [27:0] value, input [7:0] distance);
        reg discarded; reg [27:0] shifted; integer bit_index;
        begin
            discarded = 1'b0; shifted = 28'd0;
            if (distance == 8'd0) shifted = value;
            else if (distance >= 8'd28) shifted[0] = |value;
            else begin
                shifted = value >> distance;
                for (bit_index = 0; bit_index < 28; bit_index = bit_index + 1)
                    if ({24'd0, bit_index[7:0]} < distance) discarded = discarded | value[bit_index];
                shifted[0] = shifted[0] | discarded;
            end
            shift_right_jam_28 = shifted;
        end
    endfunction
    wire [27:0] s2_sh = shift_right_jam_28({1'b0, s1_small, 3'b000}, s1_dist);
    reg        s2_byp, s2_sub, s2_sign, s2_eq;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [27:0] s2_big, s2_smallx;
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_sub <= s1_sub; s2_sign <= s1_sign; s2_err <= s1_err; s2_code <= s1_code; s2_exp <= s1_exp;
        s2_big <= {1'b0, s1_big, 3'b000};
        s2_smallx <= s1_sub ? ~s2_sh : s2_sh;
        s2_eq <= (s1_dist == 8'd0) && (s1_big == s1_small);
    end
    // -- stage 3: ONE add (big + small + 0, or big + ~small + 1 = big - small: big >= small, no borrow)
    wire [27:0] s3_arith = s2_big + s2_smallx + {27'd0, s2_sub};
    reg        s3_byp, s3_sub, s3_sign, s3_zero, s3_carry;
    reg [1:0]  s3_err;
    reg [31:0] s3_code;
    reg [7:0]  s3_exp;
    reg [27:0] s3_raw;
    always @(posedge clk) begin
        s3_byp <= s2_byp; s3_sub <= s2_sub; s3_sign <= s2_sign; s3_err <= s2_err; s3_code <= s2_code;
        s3_zero <= s2_sub && s2_eq;
        s3_exp <= s2_exp;
        s3_raw <= s3_arith;
        s3_carry <= !s2_sub && s3_arith[27];
    end
    // -- stage 4: carry renormalize OR cancellation normalize (exclusive: a carry is an add)
    wire [26:0] s4_in = s3_raw[26:0];
    wire [26:0] s4_rsh = {s3_raw[27:2], s3_raw[1] | s3_raw[0]};
    reg [4:0] s4_lz;
    always @* begin
        s4_lz = 5'd27;
        for (k = 0; k <= 26; k = k + 1)
            if (s4_in[k]) s4_lz = 5'd26 - k[4:0];
    end
    wire [7:0] s4_room = s3_exp - 8'd1;
    wire [7:0] s4_shift = ({3'd0, s4_lz} > s4_room) ? s4_room : {3'd0, s4_lz};
    wire       s4_apply = s3_sub && !s3_zero && !s3_byp;
    reg        s4_byp, s4_sign, s4_zero;
    reg [1:0]  s4_err;
    reg [31:0] s4_code;
    reg [7:0]  s4_exp;
    reg [26:0] s4_val;
    always @(posedge clk) begin
        s4_byp <= s3_byp; s4_sign <= s3_sign; s4_zero <= s3_zero; s4_err <= s3_err; s4_code <= s3_code;
        s4_exp <= s3_carry ? (s3_exp + 8'd1) : s4_apply ? (s3_exp - s4_shift) : s3_exp;
        s4_val <= s3_carry ? s4_rsh : s4_apply ? (s4_in << s4_shift) : s4_in;
    end
    // -- stage 5: round to nearest even, encode, fail closed on overflow (as ot_fp32_add_rne_pipe)
    wire [24:0] s5_trunc = {1'b0, s4_val[26:3]};
    wire        s5_inc = s4_val[2] && ((|s4_val[1:0]) || s4_val[3]);
    wire [24:0] s5_round = s5_trunc + {24'd0, s5_inc};
    wire        s5_carry = s5_round[24];
    wire [23:0] s5_man = s5_carry ? s5_round[24:1] : s5_round[23:0];
    wire [7:0]  s5_exp = s5_carry ? (s4_exp + 8'd1) : s4_exp;
    wire        s5_subnormal = (s5_exp == 8'd1) && !s5_man[23];
    wire [31:0] s5_code = {s4_sign, s5_subnormal ? 8'd0 : s5_exp, s5_man[22:0]};
    wire        s5_over = (s4_exp >= 8'hff) || (s5_exp >= 8'hff);
    always @(posedge clk) begin
        if (s4_byp) begin y <= s4_code; err <= s4_err; end
        else if (s4_zero) begin y <= 32'd0; err <= E_NONE; end
        else if (s5_over) begin y <= 32'd0; err <= E_OVERFLOW; end
        else begin y <= (s5_code[30:0] == 31'd0) ? 32'd0 : s5_code; err <= E_NONE; end
    end
endmodule
`default_nettype wire
