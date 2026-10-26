`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81/PORTFIX-DEAD D-CAPEND (2026-10-25): ot_s81sl_cap_rt_w = the capture ROOT leaf of a slice whose frames are all in
// the W column (3-frame row-end slices: no E frame column, the as-built tied rt_e = 0).  = ot_s81sl_cap_rt (verbatim:
// FIN / DEC / pairing store / faults F5..F11, the pin copy flops) with NO e_* ports: the tree root n6 has one side, so it
// is ot_s81_retn_fwd #(RST 0) (cycle-exact with cap_rt_retn #(RST 0) at b idle) and the tree-leaf fault pin flop is W only.
// Every edge and bit equal to ot_s81sl_cap_rt with e_* = 0 (tools/s81_slice/cap_end/cap_end_eq.sh).  The CLOSED
// ot_s81sl_cap_rt.sv is not edited; ot_s81sl_cap_grp / ot_s81_fadd_pipe come from it (read it with this file).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_rt_w #(
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
    wire n6_v, n6_e; wire [31:0] n6_t, n6_d;
    wire n6r_v, n6r_e; wire [31:0] n6r_t, n6r_d;          // n6 calendar read (its r_* registers)
    // PORTFIX-DEAD D-CAPEND: no E tree -> n6 is one-sided: ot_s81_retn_fwd (= cap_rt_retn #(RST 0) with b idle, every
    // edge: tools/s81_slice/cap_end/fwd_eq.sh); it has no fault source (F1..F4 need two sides)
    ot_s81_retn_fwd #(.WIN(WIN), .RST(0)) u_n6 (.clk(clk), .rst_n(rs_n),
        .a_v(w_v), .a_t(w_t), .a_d(w_d), .a_e(w_e),
        .o_v(n6r_v), .o_t(n6r_t), .o_d(n6r_d), .o_e(n6r_e));
    // n6's RST = 1 output register stage, here (as ot_s81_retn_static u_rd / g_rv: data without reset, valid with reset)
    reg n6v_q, n6e_q; reg [31:0] n6t_q, n6d_q;
    always @(posedge clk or negedge rs_n) if (!rs_n) n6v_q <= 1'b0; else n6v_q <= n6r_v;
    always @(posedge clk) begin n6t_q <= n6r_t; n6d_q <= n6r_d; n6e_q <= n6r_e; end
    assign n6_v = n6v_q, n6_t = n6t_q, n6_d = n6d_q, n6_e = n6e_q;
    reg lf_q;                                             // tree-leaf fault pin flops (OR after the flops)
    reg lf_p;                                             // W tree leaf only
    always @(posedge clk or negedge rs_c) if (!rs_c) lf_p <= 1'b0; else lf_p <= w_f;
    always @* lf_q = lf_p;

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
        else if (lf_q || f5 || f6 || f7 || f8 || (|f9) || f10 || f11) fault_q <= 1'b1;
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
        else fcause <= fcause | {5'd0, f11, f10, |f9, f8, f7, f6, f5, 1'b0, 1'b0, lf_q, 1'b0};
`endif
endmodule
`default_nettype wire
