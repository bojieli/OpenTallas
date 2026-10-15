`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-tp8 (2026-10-12, results/arch/qwen_tp8_1012/SPEC.md section 3): the TP8 collective cluster of one Qwen ROM die.
// 8 dies = 4 packages x 2 dies (die DIE of package PKG; TP8 rank = 4 * DIE + PKG).  The existing TP4 engine
// ot_rom_oneshot_die_m (N 4, rank-ordered one-shot fold, its hardened ot_coll_fold_slice children) is instantiated
// UNCHANGED as the cross-package level, so TP4 behaviour is bit-identical by construction; this wrapper adds:
//   (1) in-package exchange over UCIe (partial channel P): every local word goes to the peer die; words are paired in
//       order (local, peer) and the package sum p = lo + hi (lo = the package's die 0, fixed order on both dies) is
//       computed by 4 more hardened ot_coll_fold_slice tiles fed {0, 0, hi, lo}: ((lo + hi) + 0) + 0 = lo + hi bit for
//       bit (every zero result is canonical +0, x + 0 = x otherwise; tools/hdc_golden.add);
//   (2) owner half: all-reduce word w is owned by die (w mod 2); a die feeds only its owned package sums to the engine,
//       which folds them with die DIE of the 3 other packages over 3 SerDes ports, ((p0 + p1) + p2) + p3;
//       (pairs are taken two at a time so the owned word's `last` is known: reduce messages have an even word count,
//       an odd count is a protocol fault);
//   (3) in-package all-gather over UCIe (result channel R): each die sends its engine results to the peer, and the
//       merger emits word w from the local engine (w mod 2 == DIE) or from the peer, in order;
//   (4) all-gather (argmax (max, index) words): the package message is the pair interleave lo_w, hi_w; both dies run
//       the full 4-package gather, so output word k is TP8 rank k mod 8 (= 4 * die + package), index k / 8, on all 8.
// All boundaries are registered (pin flops in, flops out); every queue is credit-managed (no same-cycle cross-block
// handshake); big queues are ot_sram_1r1w_32x546_m1 macros (QMEM 1).  Faults: fault_code[2:0] = the engine's;
// [3] = arithmetic error (pre-fold slice error or an error-flagged peer result); [4] = protocol (peer pairing tag /
// mode / last disagreement, odd reduce length, queue overflow, slice/meta misalignment).
// Negative controls (bench only): OT_TP8_MUT_OWNER (each die feeds the other half), OT_TP8_MUT_GATHER (package
// gather message hi before lo); the engine's OT_ONESHOT_M_MUTANT swaps package ranks 1 and 2.
// ---------------------------------------------------------------------------
module ot_coll_tp8_die #(
    parameter integer CCLK = 0, // independent hardened-child clocks; legacy default unchanged
    parameter integer PKG     = 0,
    parameter integer DIE     = 0,
    parameter integer LANES   = 16,
    parameter integer TAGW    = 32,
    parameter integer DEPTH   = 32,      // engine source FIFO depth (MEMM 1 needs 32)
    parameter integer ADD_LAT = 7,
    parameter integer PR      = 2,
    parameter integer TXK     = 1,
    parameter integer FPIPE   = 2,
    parameter integer HDLO    = 0,
    parameter integer MEMM    = 1,
    parameter integer FSL     = 1,
    parameter integer IBH     = 1,
    parameter integer WT      = 0,       // opt-in wrapper column leaves: 1 = ot_coll_tp8_col_tile (unchanged edge timing),
                                         // 2 = ot_coll_tp8_col_tile_r (registered returns, qwen-coll-io 10-14: EQ/LQ/TQ
                                         //     writes +1 edge, no data word leaves a leaf to come back)
                                         // 3 = pin-registered data leaves ot_coll_tp8_col_tile_r3 (x4, every input
                                         //     in a pin flop: each leaf = the WT 2 column one edge late, s_lo / s_hi
                                         //     two) + the metadata column flat beside the controller (MEM 2 core);
                                         //     every parent signal paired with a leaf output is delayed to match
    parameter integer CT      = 1,
    // STRAP = 1 (qwen-coll-io r3 2026-10-14, WT 3 only): ONE hardened cluster for all 8 compute dies of the one die type:
    // the package rank and the die-in-package come from the static straps pkg_s / die_ps (die bumps, one pin flop each)
    // instead of PKG / DIE: engine own-source (RSTRAP), SerDes port <-> engine source rotation, owner half (leaf die_s),
    // package tag and merger order become strap-selected.  STRAP = 0: the straps are unused, PKG / DIE as before.
    parameter integer STRAP   = 0,       // qwen-tp8/coll4: engine column datapath in hardened ot_coll_col_tile leaves
    parameter integer ICR     = 32,      // credits held by the die's sequencer (<= LBD, <= PQD)
    parameter integer LBD     = 64,      // local partial buffer (words), 32 * k with QMEM 1
    parameter integer PQD     = 64,      // peer partial receive queue (= P-channel credits)
    parameter integer EQD     = 32,      // engine feed queue
    parameter integer LQD     = 64,      // local result queue (reservation per engine word: 1 reduce / 4 gather)
    parameter integer TQD     = 32,      // result-to-peer queue
    parameter integer RQD     = 32,      // peer result receive queue (= R-channel credits)
    parameter integer MFD     = 32,      // engine message mode queue
    parameter integer QMEM    = 1,
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW,
    parameter integer RW      = FW + 2
) (
    input  wire              clk,
    input wire [FW/128-1:0] clk_colr, clk_pfold, clk_efold,
    input wire [(PW+127)/128-1:0] clk_ecol,
    input  wire              rst_n,
    // local port (credit-based, ICR credits)
    input  wire              in_valid,
    output wire              in_cr,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,
    input  wire [TAGW-1:0]   in_tag,
    // UCIe partial channel {tag, mode, last, data}
    output wire              up_valid,
    output wire [PW-1:0]     up_rec,
    input  wire              up_ready,
    input  wire              up_cr_in,
    input  wire              dp_valid,
    input  wire [PW-1:0]     dp_rec,
    output wire              dp_cr_out,
    // UCIe result channel {err, last, data}
    output wire              ur_valid,
    output wire [RW-1:0]     ur_rec,
    input  wire              ur_ready,
    input  wire              ur_cr_in,
    input  wire              dr_valid,
    input  wire [RW-1:0]     dr_rec,
    output wire              dr_cr_out,
    // 3 SerDes ports: port j <-> package (PKG + 1 + j) mod 4 (the engine's record format and credits)
    output wire [2:0]        sx_valid,
    output wire [3*PW-1:0]   sx_rec,
    input  wire [2:0]        sx_ready,
    input  wire [2:0]        sx_cr_in,
    input  wire [2:0]        sr_valid,
    input  wire [3*PW-1:0]   sr_rec,
    output wire [2:0]        sr_cr_out,
    // result
    output wire              out_valid,
    output wire [FW-1:0]     out_data,
    output wire              out_last,
    output wire [2:0]        out_rank,
    output wire              out_err,
    output wire              fault,
    output wire [4:0]        fault_code,
    // STRAP = 1: static rank straps (TP8 rank = 4 * die_ps + pkg_s)
    input  wire [1:0]        pkg_s,
    input  wire              die_ps
);
    localparam integer N  = 4;
    localparam integer SL = 3 * 7 + 2;      // hardened slice latency (N 4, ADD_LAT 7, SEAM 1): red_in -> v_out
    localparam integer SLX = SL + ((WT == 3) ? 2 : 0);   // WT 3: s_lo / s_hi reach the slices two edges late
    localparam integer LW = FW + 5;         // LQ entry {mode, rank[1:0], err, last, data}
    localparam integer NS = FW / 128;
    initial if (FW % 128 != 0 || DIE > 1 || PKG > 3 || ICR > LBD || ICR > PQD) $error("ot_coll_tp8_die: FW multiple of 128, DIE 0..1, PKG 0..3, ICR <= LBD, PQD");
    // control reset: one leaf per region (input / pairing + engine feed / results + merger); every queue has its own
    initial if (STRAP != 0 && WT != 3) $error("ot_coll_tp8_die: STRAP needs WT 3");
    // rank straps: one pin flop each (static; captured every edge, settled long before the reset release)
    reg [1:0] pkg_q; reg die_q;
    always @(posedge clk) begin pkg_q <= pkg_s; die_q <= die_ps; end
    wire [1:0] PK = (STRAP != 0) ? pkg_q : PKG[1:0];
    wire       DI = (STRAP != 0) ? die_q : DIE[0];
    wire [3:0] self_oh = 4'b0001 << PK;
    wire rs_a, rs, rs_m;
    (* keep_hierarchy *) ot_coll_rst_leaf u_rsa (.clk(clk), .arst_n(rst_n), .q(rs_a));
    (* keep_hierarchy *) ot_coll_rst_leaf u_rs  (.clk(clk), .arst_n(rst_n), .q(rs));
    (* keep_hierarchy *) ot_coll_rst_leaf u_rsm (.clk(clk), .arst_n(rst_n), .q(rs_m));
    reg prot, arith;

    // ---------------- A/B: local input pins -> relay -> local buffer + UCIe P ----------------
    // The sequencer holds ICR credits (ICR <= LBD, ICR <= PQD): a credit returns (in_cr) only when both the local
    // buffer entry of a word is freed (its pair is taken here) and the peer has freed its copy (a P credit came
    // back), so neither buffer can overflow and every accepted word is sent at once (no input queue, no stall).
    // The word crosses from the S face (in) to the W face (up) through one relay register (<= 500 um per stage).
    reg iv_q, rl_v; reg [PW-1:0] ir_q, rl_d;
    always @(posedge clk or negedge rs_a) if (!rs_a) begin iv_q <= 1'b0; rl_v <= 1'b0; end
        else begin iv_q <= in_valid; rl_v <= iv_q; end
    generate if (WT == 0) begin : g_wide_in
    always @(posedge clk) begin ir_q <= {in_tag, in_mode, in_last, in_data}; rl_d <= ir_q; end
    end endgenerate
    reg upr_q, upc_q, upv_q, icr_q; reg [PW-1:0] uprec_q;
    reg [6:0] cr_a, cr_b;          // freed local entries / returned P credits not yet given back to the sequencer
    wire pair_pop;
    wire cr_go = (cr_a != 0) && (cr_b != 0);
    generate if (WT == 0) begin
    always @(posedge clk) uprec_q <= rl_d;
    end endgenerate
    always @(posedge clk or negedge rs_a)
        if (!rs_a) begin upr_q <= 1'b0; upc_q <= 1'b0; upv_q <= 1'b0; icr_q <= 1'b0; cr_a <= 0; cr_b <= 0; end
        else begin
            upr_q <= up_ready; upc_q <= up_cr_in; upv_q <= rl_v; icr_q <= cr_go;
            cr_a <= cr_a + (pair_pop ? 7'd1 : 7'd0) - (cr_go ? 7'd1 : 7'd0);
            cr_b <= cr_b + (upc_q ? 7'd1 : 7'd0) - (cr_go ? 7'd1 : 7'd0);
        end
    assign in_cr = icr_q;
    reg upv_q2;
    always @(posedge clk or negedge rs_a) if (!rs_a) upv_q2 <= 1'b0; else upv_q2 <= upv_q;
    assign up_valid = (WT == 3) ? upv_q2 : upv_q;
    assign up_rec = uprec_q;
    wire up_bad = rl_v && !upr_q;   // a send against the link layer's registered may-send
    wire lb_hv, lb_ovf; wire [PW-1:0] lb_hd;
    generate if (WT == 0) begin : g_u_lb
    ot_coll_tp8_q #(.W(PW), .D(LBD), .MEM(QMEM)) u_lb (.clk(clk), .rst_n(rst_n), .push(rl_v), .wd(rl_d), .pop(pair_pop),
        .hv(lb_hv), .hd(lb_hd), .ovf(lb_ovf));
    end endgenerate

    // ---------------- C: peer partial receive ----------------
    reg dpv_q, dpc_q; reg [PW-1:0] dpr_q;
    generate if (WT == 0) begin
    always @(posedge clk) dpr_q <= dp_rec;
    end endgenerate
    always @(posedge clk or negedge rs) if (!rs) begin dpv_q <= 1'b0; dpc_q <= 1'b0; end
        else begin dpv_q <= dp_valid; dpc_q <= pair_pop; end
    assign dp_cr_out = dpc_q;
    wire pq_hv, pq_ovf; wire [PW-1:0] pq_hd;
    generate if (WT == 0) begin : g_u_pq
    ot_coll_tp8_q #(.W(PW), .D(PQD), .MEM(QMEM)) u_pq (.clk(clk), .rst_n(rst_n), .push(dpv_q), .wd(dpr_q), .pop(pair_pop),
        .hv(pq_hv), .hd(pq_hd), .ovf(pq_ovf));
    end endgenerate

    // ---------------- D: pairing, owner half, pre-fold slices ----------------
    wire [FW-1:0]   lw = lb_hd[FW-1:0], pw = pq_hd[FW-1:0];
    wire [FW-1:0]   lo = !DI ? lw : pw;
    wire [FW-1:0]   hi = !DI ? pw : lw;
    wire            p_last = lb_hd[FW], p_mode = lb_hd[FW+1];
    wire [TAGW-1:0] p_tag = !DI ? lb_hd[FW+2 +: TAGW] : pq_hd[FW+2 +: TAGW];   // the package message tag
    wire            p_bad = (lb_hd[FW+2 +: TAGW] != pq_hd[FW+2 +: TAGW]) || (lb_hd[FW +: 2] != pq_hd[FW +: 2]);
    reg  [7:0] eq_res, infl;
    reg        wpar, gh_v;
    reg [PW-1:0] gh_w;
    reg [FW-1:0] hl_lo, hl_hi;
    reg [SLX-1:0] ml_v, ml_last;
    reg [TAGW-1:0] ml_tag [0:SLX-1];
    wire [NS-1:0] sl_v, sl_e;
    wire [FW-1:0] sl_sum;
    wire sl_tail = ml_v[SLX-1];
    wire pr_ok  = lb_hv && pq_hv && !gh_v && (eq_res + 8'd2 <= EQD);
    wire pr_red = pr_ok && !p_mode;
    wire pr_gat = pr_ok && p_mode && (infl == 0) && !sl_tail;
    assign pair_pop = pr_red || pr_gat;
    wire issue = pr_red && wpar;                  // second pair of a (w even, w + 1) couple: the owned word goes in
`ifdef OT_TP8_MUT_OWNER
    localparam integer HELD = (DIE != 0);
`else
    localparam integer HELD = (DIE == 0);          // die 0 owns the even word (held), die 1 the odd word (current)
`endif
    wire [FW-1:0] s_lo, s_hi;
    // WT 3: the slices take red_in two edges late, with the leaves' s_lo / s_hi
    reg iss_d1, iss_d2;
    always @(posedge clk or negedge rs) if (!rs) begin iss_d1 <= 1'b0; iss_d2 <= 1'b0; end
        else begin iss_d1 <= issue; iss_d2 <= iss_d1; end
    wire red_x = (WT == 3) ? iss_d2 : issue;
    generate if (WT < 2) begin : g_slo
        assign s_lo = HELD ? hl_lo : lo;
        assign s_hi = HELD ? hl_hi : hi;
    end endgenerate
    genvar gs;
    generate for (gs = 0; gs < NS; gs = gs + 1) begin : g_pf
        (* keep_hierarchy *) ot_coll_fold_slice u_fs (   // the hardened N 4 / ADD_LAT 7 / SEAM 1 master, no override
            .clk(CCLK ? clk_pfold[gs] : clk), .rst_n(rst_n), .red_in(red_x),
            .src({256'd0, s_hi[gs*128 +: 128], s_lo[gs*128 +: 128]}),
            .sum(sl_sum[gs*128 +: 128]), .v_out(sl_v[gs]), .e_out(sl_e[gs]));
    end endgenerate
    integer k;
    always @(posedge clk) begin
        if (WT == 0 && pr_red && !wpar) begin hl_lo <= lo; hl_hi <= hi; end
        ml_tag[0] <= p_tag;
        for (k = 1; k < SLX; k = k + 1) ml_tag[k] <= ml_tag[k-1];
`ifdef OT_TP8_MUT_GATHER
        if (WT == 0) gh_w <= {p_tag, 1'b1, p_last, lo};
`else
        if (WT == 0) gh_w <= {p_tag, 1'b1, p_last, hi};
`endif
    end
    always @(posedge clk or negedge rs)
        if (!rs) begin ml_v <= 0; ml_last <= 0; wpar <= 1'b0; gh_v <= 1'b0; end
        else begin
            ml_v <= {ml_v[SLX-2:0], issue};
            ml_last <= {ml_last[SLX-2:0], p_last};
            if (pr_red) wpar <= p_last ? 1'b0 : !wpar;
            gh_v <= pr_gat;
        end
    // engine feed queue write: slice tail (reduce) | gather lo | gather hi
`ifdef OT_TP8_MUT_GATHER
    wire [FW-1:0] g_first = hi;
`else
    wire [FW-1:0] g_first = lo;
`endif
    // a pre-fold arithmetic error (NaN / Inf operand or overflow; the slice adders report it, their value is not
    // meaningful) forces the slice's 4 lanes to the canonical NaN, so the engine's fold faults on all 4 dies of the
    // half and flags the word, and the peer half sees the flagged result (arith fault) -> all 8 dies fault.
    wire [FW-1:0] sl_sum_f;
    generate for (gs = 0; gs < NS; gs = gs + 1) begin : g_pfe
        assign sl_sum_f[gs*128 +: 128] = sl_e[gs] ? {4{32'h7fc00000}} : sl_sum[gs*128 +: 128];
    end endgenerate
    wire          eq_push = sl_tail || pr_gat || gh_v;
    wire [PW-1:0] eq_wd = sl_tail ? {ml_tag[SLX-1], 1'b0, ml_last[SLX-1], sl_sum_f}
                        : pr_gat  ? {p_tag, 1'b1, 1'b0, g_first} : gh_w;

    // ---------------- E: engine feed ----------------
    wire eq_hv, eq_ovf; wire [PW-1:0] eq_hd;
    wire eq_mode = eq_hd[FW+1], eq_last = eq_hd[FW];
    reg [2:0] ecred;
    reg [8:0] lq_res, tq_res;
    wire e_icr, mf_hv, mf_ovf, mf_hd;
    wire lq_pop, tq_pop;
    reg [7:0] mf_n;
    reg eq_first;                 // the next engine-fed word starts a message (its mode enters the mode queue then:
                                  // the engine may emit results of a long message before its last word is fed)
    wire eq_pop = eq_hv && (ecred != 0) && (lq_res + (eq_mode ? 9'd4 : 9'd1) <= LQD) && (eq_mode || tq_res < TQD)
                  && (mf_n < MFD);
    generate if (WT == 0) begin : g_u_eq
    ot_coll_tp8_q #(.W(PW), .D(EQD), .MEM(QMEM)) u_eq (.clk(clk), .rst_n(rst_n), .push(eq_push), .wd(eq_wd), .pop(eq_pop),
        .hv(eq_hv), .hd(eq_hd), .ovf(eq_ovf));
    end endgenerate
    wire e_ov, e_ol, e_oe, e_f;
    wire [FW-1:0] e_od;
    wire [1:0] e_or;
    wire [2:0] e_fc;
    always @(posedge clk or negedge rs)
        if (!rs) begin eq_first <= 1'b1; eq_res <= 0; infl <= 0; ecred <= 3'd4; lq_res <= 0; tq_res <= 0; mf_n <= 0; end
        else begin
            eq_res <= eq_res + (issue ? 8'd1 : 8'd0) + (pr_gat ? 8'd2 : 8'd0) - (eq_pop ? 8'd1 : 8'd0);
            infl   <= infl + (issue ? 8'd1 : 8'd0) - (sl_tail ? 8'd1 : 8'd0);
            if (eq_pop) eq_first <= eq_last;
            ecred  <= ecred - (eq_pop ? 3'd1 : 3'd0) + (e_icr ? 3'd1 : 3'd0);
            lq_res <= lq_res + (eq_pop ? (eq_mode ? 9'd4 : 9'd1) : 9'd0) - (lq_pop ? 9'd1 : 9'd0);
            tq_res <= tq_res + ((eq_pop && !eq_mode) ? 9'd1 : 9'd0) - (tq_pop ? 9'd1 : 9'd0);
            mf_n   <= mf_n + ((eq_pop && eq_first) ? 8'd1 : 8'd0) - ((e_ov && e_ol) ? 8'd1 : 8'd0);
        end
    ot_coll_tp8_q #(.W(1), .D(MFD), .MEM(0)) u_mf (.clk(clk), .rst_n(rst_n), .push(eq_pop && eq_first), .wd(eq_mode),
        .pop(e_ov && e_ol), .hv(mf_hv), .hd(mf_hd), .ovf(mf_ovf));

    // ---------------- the cross-package level: the unchanged TP4 engine, die DIE of every package ----------------
    reg  [2:0]    sxr_q, sxc_q, srv_q, src_q;
    reg  [3*PW-1:0] srr_q, sxrec_q;
    reg  [2:0]    sxv_q;
    reg  [2:0]    sxr_q2, sxc_q2, srv_q2, sxv_q2;   // WT 3: one more edge (paired with the leaves' sr / sx)
    always @(posedge clk or negedge rs)
        if (!rs) begin sxr_q2 <= 0; sxc_q2 <= 0; srv_q2 <= 0; sxv_q2 <= 0; end
        else begin sxr_q2 <= sxr_q; sxc_q2 <= sxc_q; srv_q2 <= srv_q; sxv_q2 <= sxv_q; end
    // WT 3 engine feed: eq_pop and the EQ head metadata one edge late, with the leaves' EQ head data
    reg           eqp_q; reg [TAGW+1:0] eqm_q;
    always @(posedge clk or negedge rs) if (!rs) eqp_q <= 1'b0; else eqp_q <= eq_pop;
    always @(posedge clk) eqm_q <= eq_hd[FW +: TAGW + 2];
    wire          e_iv  = (WT == 3) ? eqp_q : eq_pop;
    wire          e_il  = (WT == 3) ? eqm_q[0] : eq_last;
    wire          e_im  = (WT == 3) ? eqm_q[1] : eq_mode;
    wire [TAGW-1:0] e_itg = (WT == 3) ? eqm_q[2 +: TAGW] : eq_hd[FW+2 +: TAGW];
    wire          e_txv;
    wire [PW-1:0] e_txr;
    wire [N-1:0]  e_txrdy, e_crin, e_rxv, e_crout;
    wire [N*PW-1:0] e_rxr;
    genvar gj, gq;
    generate for (gq = 0; gq < N; gq = gq + 1) begin : g_port
        if (STRAP != 0) begin : g_st
            // engine source gq <-> SerDes port jq = (gq - PK + 3) mod 4 (jq = 3: the die's own source)
            localparam [1:0] G3 = (gq + 3) % 4;
            wire [1:0] jq = G3 - PK;              // 2-bit wrap = mod 4
            wire       me = self_oh[gq];
            wire [2:0] rdy = sxr_q2, crn = sxc_q2, rxv = srv_q2;
            assign e_txrdy[gq] = me ? 1'b1 : rdy[jq];
            assign e_crin[gq]  = me ? 1'b0 : crn[jq];
            assign e_rxv[gq]   = me ? 1'b0 : rxv[jq];
            // decoded constant-index AND-OR (no runtime-indexed 546-bit part-select)
            wire [2:0] js = {jq == 2'd2, jq == 2'd1, jq == 2'd0};
            assign e_rxr[gq*PW +: PW] = ({PW{js[0]}} & srr_q[0 +: PW]) | ({PW{js[1]}} & srr_q[PW +: PW])
                                      | ({PW{js[2]}} & srr_q[2*PW +: PW]);
        end else if (gq == PKG) begin : g_self
            assign e_txrdy[gq] = 1'b1; assign e_crin[gq] = 1'b0; assign e_rxv[gq] = 1'b0;
            assign e_rxr[gq*PW +: PW] = {PW{1'b0}};
        end else begin : g_sx
            localparam integer J = (gq - PKG + 3) % 4;   // gq = (PKG + 1 + J) mod 4
            assign e_txrdy[gq] = (WT == 3) ? sxr_q2[J] : sxr_q[J];
            assign e_crin[gq]  = (WT == 3) ? sxc_q2[J] : sxc_q[J];
            assign e_rxv[gq]   = (WT == 3) ? srv_q2[J] : srv_q[J];
            assign e_rxr[gq*PW +: PW] = srr_q[J*PW +: PW];
            always @(posedge clk or negedge rs) if (!rs) src_q[J] <= 1'b0; else src_q[J] <= e_crout[gq];
        end
    end endgenerate
    generate if (STRAP != 0) begin : g_st_cr
        for (gj = 0; gj < 3; gj = gj + 1) begin : g_j
            localparam [1:0] J1 = gj + 1;
            wire [1:0] sq = PK + J1;              // 2-bit wrap = mod 4
            always @(posedge clk or negedge rs) if (!rs) src_q[gj] <= 1'b0; else src_q[gj] <= e_crout[sq];
        end
    end endgenerate
    // tx: one registered copy per SerDes port (each placed at its own face)
    generate if (WT == 0) begin
    always @(posedge clk) begin sxrec_q <= {3{e_txr}}; srr_q <= sr_rec; end
    end endgenerate
    always @(posedge clk or negedge rs)
        if (!rs) begin sxv_q <= 0; sxr_q <= 0; sxc_q <= 0; srv_q <= 0; end
        else begin sxv_q <= {3{e_txv}}; sxr_q <= sx_ready; sxc_q <= sx_cr_in; srv_q <= sr_valid; end
    assign sx_valid = (WT == 3) ? sxv_q2 : sxv_q; assign sx_rec = sxrec_q; assign sr_cr_out = src_q;
    ot_rom_oneshot_die_m #(.N(N), .RANK(PKG), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH), .ADD_LAT(ADD_LAT), .IB(4),
        .PR(PR), .OPQ(0), .TXK(TXK), .FPIPE(FPIPE), .HDLO(HDLO), .MEMM(MEMM), .FSL(FSL), .IBH(IBH), .CT(CT),
        .RSTRAP(STRAP), .CCLK(CCLK)) u_eng (
        .clk(clk), .clk_cols(clk_ecol), .clk_folds(clk_efold), .rst_n(rst_n), .self_s(self_oh),
        .in_valid(e_iv), .in_cr(e_icr), .in_data(eq_hd[FW-1:0]), .in_last(e_il), .in_mode(e_im),
        .in_tag(e_itg),
        .tx_valid(e_txv), .tx_rec(e_txr), .tx_ready(e_txrdy), .cr_in(e_crin),
        .rx_valid(e_rxv), .rx_rec(e_rxr), .cr_out(e_crout),
        .out_valid(e_ov), .out_data(e_od), .out_last(e_ol), .out_rank(e_or), .out_err(e_oe),
        .fault(e_f), .fault_code(e_fc));

    // ---------------- F: engine results -> local result queue (+ to-peer queue for reduce words) ----------------
    wire lq_hv, lq_ovf, tq_hv, tq_ovf;
    wire [LW-1:0] lq_hd;
    wire [RW-1:0] tq_hd;
    generate if (WT == 0) begin : g_u_lq
    ot_coll_tp8_q #(.W(LW), .D(LQD), .MEM(QMEM)) u_lq (.clk(clk), .rst_n(rst_n), .push(e_ov),
        .wd({mf_hd, e_or, e_oe, e_ol, e_od}), .pop(lq_pop), .hv(lq_hv), .hd(lq_hd), .ovf(lq_ovf));
    end endgenerate
    generate if (WT == 0) begin : g_u_tq
    ot_coll_tp8_q #(.W(RW), .D(TQD), .MEM(QMEM)) u_tq (.clk(clk), .rst_n(rst_n), .push(e_ov && !mf_hd),
        .wd({e_oe, e_ol, e_od}), .pop(tq_pop), .hv(tq_hv), .hd(tq_hd), .ovf(tq_ovf));
    end endgenerate

    // ---------------- G: to-peer results -> UCIe R ----------------
    reg urr_q, urc_q, urv_q; reg [RW-1:0] urrec_q; reg [8:0] rcred;
    assign tq_pop = tq_hv && (rcred != 0) && urr_q;
    generate if (WT == 0) begin
    always @(posedge clk) urrec_q <= tq_hd;
    end endgenerate
    always @(posedge clk or negedge rs_m)
        if (!rs_m) begin urr_q <= 1'b0; urc_q <= 1'b0; urv_q <= 1'b0; rcred <= RQD; end
        else begin
            urr_q <= ur_ready; urc_q <= ur_cr_in; urv_q <= tq_pop;
            rcred <= rcred - (tq_pop ? 9'd1 : 9'd0) + (urc_q ? 9'd1 : 9'd0);
        end
    reg urv_q2;
    always @(posedge clk or negedge rs_m) if (!rs_m) urv_q2 <= 1'b0; else urv_q2 <= urv_q;
    assign ur_valid = (WT == 3) ? urv_q2 : urv_q; assign ur_rec = urrec_q;

    // ---------------- H: peer results receive ----------------
    reg drv_q, drc_q; reg [RW-1:0] drr_q;
    wire rq_hv, rq_ovf, rq_pop; wire [RW-1:0] rq_hd;
    generate if (WT == 0) begin
    always @(posedge clk) drr_q <= dr_rec;
    end endgenerate
    always @(posedge clk or negedge rs_m) if (!rs_m) begin drv_q <= 1'b0; drc_q <= 1'b0; end
        else begin drv_q <= dr_valid; drc_q <= rq_pop; end
    assign dr_cr_out = drc_q;
    generate if (WT == 0) begin : g_u_rq
    ot_coll_tp8_q #(.W(RW), .D(RQD), .MEM(QMEM)) u_rq (.clk(clk), .rst_n(rst_n), .push(drv_q), .wd(drr_q), .pop(rq_pop),
        .hv(rq_hv), .hd(rq_hd), .ovf(rq_ovf));
    end endgenerate

    // ---------------- I: merger (in-package all-gather) ----------------
    reg [15:0] mc; reg cur_mode;
    wire m_mode = (mc == 0) ? lq_hd[FW+4] : cur_mode;
    wire take_l = m_mode || (mc[0] == DI);
    // a message's mode is read from the LQ head at its first word (LQ always holds a word of the message by then)
    wire m_go   = (take_l ? lq_hv : rq_hv) && (mc != 0 || lq_hv);
    assign lq_pop = m_go && take_l;
    assign rq_pop = m_go && !take_l;
    wire [FW-1:0] m_d    = take_l ? lq_hd[FW-1:0] : rq_hd[FW-1:0];
    wire          m_e    = take_l ? lq_hd[FW+1] : rq_hd[FW+1];
    wire          m_lst  = m_mode ? lq_hd[FW] : ((take_l ? lq_hd[FW] : rq_hd[FW]) && mc[0]);
    wire [2:0]    m_rank = m_mode ? {mc[2], lq_hd[FW+2 +: 2]} : 3'd0;
    reg ov_q, ol_q, oe_q; reg [FW-1:0] od_q; reg [2:0] or_q;
    always @(posedge clk) begin if (WT == 0) od_q <= m_d; ol_q <= m_lst; oe_q <= m_e; or_q <= m_rank; end
    always @(posedge clk or negedge rs_m)
        if (!rs_m) begin ov_q <= 1'b0; mc <= 0; cur_mode <= 1'b0; end
        else begin
            ov_q <= m_go;
            if (m_go) begin
                if (mc == 0) cur_mode <= m_mode;
                mc <= m_lst ? 16'd0 : mc + 16'd1;
            end
        end
    reg ov_q2, ol_q2, oe_q2; reg [2:0] or_q2;
    always @(posedge clk) begin ol_q2 <= ol_q; oe_q2 <= oe_q; or_q2 <= or_q; end
    always @(posedge clk or negedge rs_m) if (!rs_m) ov_q2 <= 1'b0; else ov_q2 <= ov_q;
    assign out_valid = (WT == 3) ? ov_q2 : ov_q; assign out_data = od_q;
    assign out_last = (WT == 3) ? ol_q2 : ol_q; assign out_rank = (WT == 3) ? or_q2 : or_q; assign out_err = (WT == 3) ? oe_q2 : oe_q;

    // WT factors the existing register/queue datapath into five 128-bit leaves.
    // Metadata occupies the fifth column; every leaf advances on the identical
    // original push/pop decisions, so word identity and timing are unchanged.
    generate if (WT == 1) begin : g_wrapper_cols
        initial if (FW != 512 || TAGW != 32 || LBD != 64 || PQD != 64 || EQD != 32 || LQD != 64 || TQD != 32 || RQD != 32 || QMEM != 1)
            $error("WT requires the production 512b, 64/64/32/64/32/32 queue shape");
        wire [639:0] ind = {{(640-PW){1'b0}}, in_tag, in_mode, in_last, in_data};
        wire [639:0] dpd = {{(640-PW){1'b0}}, dp_rec};
        wire [639:0] drd = {{(640-RW){1'b0}}, dr_rec};
        wire [639:0] gh = {{(640-PW){1'b0}}, p_tag, 1'b1, p_last,
`ifdef OT_TP8_MUT_GATHER
            lo
`else
            hi
`endif
        };
        wire [639:0] ew = {{(640-PW){1'b0}}, eq_wd};
        wire [639:0] lwc = {{(640-LW){1'b0}}, mf_hd, e_or, e_oe, e_ol, e_od};
        wire [639:0] tw = {{(640-RW){1'b0}}, e_oe, e_ol, e_od};
        wire [639:0] low = {128'd0, lo}, high = {128'd0, hi}, md = {128'd0, m_d};
        wire [639:0] et = {{(640-PW){1'b0}}, e_txr};
        wire [1919:0] srp;
        for (genvar j=0;j<3;j=j+1) begin : g_pad_sr
            assign srp[j*640 +: 640] = {{(640-PW){1'b0}}, sr_rec[j*PW +: PW]};
        end
        wire [639:0] irc, rlc, upc, dpc, hlc, hhc, ghc, urc, drc, odc;
        wire [639:0] lbh, pqh, eqh, lqh, tqh, rqh;
        wire [1919:0] srr, sxr;
        wire [29:0] hv, ovf;
        for (genvar c=0;c<5;c=c+1) begin : g_col
            wire [383:0] sri = {srp[1280+c*128 +: 128],srp[640+c*128 +: 128],srp[c*128 +: 128]};
            wire [383:0] sro,sxo;
            ot_coll_tp8_col_tile u_wc (.clk(clk),.rst_n(rst_n),
                .in_d(ind[c*128 +: 128]),.dp_d(dpd[c*128 +: 128]),.dr_d(drd[c*128 +: 128]),.sr_d(sri),
                .lo(low[c*128 +: 128]),.hi(high[c*128 +: 128]),.gh_d(gh[c*128 +: 128]),
                .eq_wd(ew[c*128 +: 128]),.lq_wd(lwc[c*128 +: 128]),.tq_wd(tw[c*128 +: 128]),
                .e_tx(et[c*128 +: 128]),.m_d(md[c*128 +: 128]),
                .c_push({drv_q,e_ov&&!mf_hd,e_ov,eq_push,dpv_q,rl_v}),
                .c_pop({rq_pop,tq_pop,lq_pop,eq_pop,pair_pop,pair_pop}),.c_hold(pr_red&&!wpar),
                .ir(irc[c*128 +: 128]),.rl(rlc[c*128 +: 128]),.up(upc[c*128 +: 128]),.dp(dpc[c*128 +: 128]),
                .hl(hlc[c*128 +: 128]),.hh(hhc[c*128 +: 128]),.gh(ghc[c*128 +: 128]),
                .sr(sro),.sx(sxo),.ur(urc[c*128 +: 128]),.dr(drc[c*128 +: 128]),.od(odc[c*128 +: 128]),
                .lb_hd(lbh[c*128 +: 128]),.pq_hd(pqh[c*128 +: 128]),.eq_hd(eqh[c*128 +: 128]),
                .lq_hd(lqh[c*128 +: 128]),.tq_hd(tqh[c*128 +: 128]),.rq_hd(rqh[c*128 +: 128]),
                .hv(hv[c*6 +: 6]),.ovf(ovf[c*6 +: 6]));
            for (genvar j=0;j<3;j=j+1) begin : g_unpad_sr
                assign srr[j*640+c*128 +: 128] = sro[j*128 +: 128];
                assign sxr[j*640+c*128 +: 128] = sxo[j*128 +: 128];
            end
        end
        assign ir_q=irc[PW-1:0]; assign rl_d=rlc[PW-1:0]; assign uprec_q=upc[PW-1:0]; assign dpr_q=dpc[PW-1:0];
        assign hl_lo=hlc[FW-1:0]; assign hl_hi=hhc[FW-1:0]; assign gh_w=ghc[PW-1:0];
        assign urrec_q=urc[RW-1:0]; assign drr_q=drc[RW-1:0]; assign od_q=odc[FW-1:0];
        for (genvar j=0;j<3;j=j+1) begin : g_sx
            assign srr_q[j*PW +: PW]=srr[j*640 +: PW];
            assign sxrec_q[j*PW +: PW]=sxr[j*640 +: PW];
        end
        assign lb_hd=lbh[PW-1:0]; assign pq_hd=pqh[PW-1:0]; assign eq_hd=eqh[PW-1:0];
        assign lq_hd=lqh[LW-1:0]; assign tq_hd=tqh[RW-1:0]; assign rq_hd=rqh[RW-1:0];
        assign {rq_hv,tq_hv,lq_hv,eq_hv,pq_hv,lb_hv}=hv[5:0];
        assign {rq_ovf,tq_ovf,lq_ovf,eq_ovf,pq_ovf,lb_ovf}=ovf[5:0];
    end endgenerate

    // WT 2 (qwen-coll-io 2026-10-14): registered-return leaves.  The leaves compute the pairing / gather / merger words
    // from their own queue heads (die strap), register every write word that comes from outside (fold-slice sum, meta,
    // engine results) at their pins and write it one edge later; the parent sends only 1-bit decisions.
    generate if (WT == 2) begin : g_wrapper_cols_r
        initial if (FW != 512 || TAGW != 32 || LBD != 64 || PQD != 64 || EQD != 32 || LQD != 128 || TQD != 128 || RQD != 32 || QMEM != 1)
            $error("WT 2 requires the production 512b, LB/PQ/EQ/LQ/TQ/RQ 64/64/32/128/128/32 queue shape");
        wire [639:0] ind = {{(640-PW){1'b0}}, in_tag, in_mode, in_last, in_data};
        wire [639:0] dpd = {{(640-PW){1'b0}}, dp_rec};
        wire [639:0] drd = {{(640-RW){1'b0}}, dr_rec};
        wire [639:0] smd = {94'd0, ml_tag[SLX-1], 1'b0, ml_last[SLX-1], sl_sum_f};
        wire [639:0] lwc = {{(640-LW){1'b0}}, mf_hd, e_or, e_oe, e_ol, e_od};
        wire [639:0] tw = {{(640-RW){1'b0}}, e_oe, e_ol, e_od};
        wire [639:0] et = {{(640-PW){1'b0}}, e_txr};
        wire [1919:0] srp;
        for (genvar j=0;j<3;j=j+1) begin : g_pad_sr
            assign srp[j*640 +: 640] = {{(640-PW){1'b0}}, sr_rec[j*PW +: PW]};
        end
        wire [639:0] upc, urc, odc, slo, shi;
        wire [639:0] lbh, pqh, eqh, lqh, tqh, rqh;
        wire [1919:0] srr, sxr;
        wire [29:0] hv, ovf;
        for (genvar c=0;c<5;c=c+1) begin : g_col
            wire [383:0] sri = {srp[1280+c*128 +: 128],srp[640+c*128 +: 128],srp[c*128 +: 128]};
            wire [383:0] sro,sxo;
            ot_coll_tp8_col_tile_r u_wc (.clk(clk),.rst_n(rst_n),.die_s(DIE[0]),.meta_s(c == 4),
                .in_d(ind[c*128 +: 128]),.dp_d(dpd[c*128 +: 128]),.dr_d(drd[c*128 +: 128]),.sr_d(sri),
                .sum_d(smd[c*128 +: 128]),.lq_wd(lwc[c*128 +: 128]),.tq_wd(tw[c*128 +: 128]),
                .e_tx(et[c*128 +: 128]),
                .c_push({drv_q,e_ov&&!mf_hd,e_ov,eq_push,dpv_q,rl_v}),
                .c_pop({rq_pop,tq_pop,lq_pop,eq_pop,pair_pop,pair_pop}),.c_hold(pr_red&&!wpar),
                .c_sel({sl_tail,pr_gat}),.c_takel(take_l),
                .up(upc[c*128 +: 128]),.ur(urc[c*128 +: 128]),.od(odc[c*128 +: 128]),
                .sr(sro),.sx(sxo),.s_lo(slo[c*128 +: 128]),.s_hi(shi[c*128 +: 128]),
                .lb_hd(lbh[c*128 +: 128]),.pq_hd(pqh[c*128 +: 128]),.eq_hd(eqh[c*128 +: 128]),
                .lq_hd(lqh[c*128 +: 128]),.tq_hd(tqh[c*128 +: 128]),.rq_hd(rqh[c*128 +: 128]),
                .hv(hv[c*6 +: 6]),.ovf(ovf[c*6 +: 6]));
            for (genvar j=0;j<3;j=j+1) begin : g_unpad_sr
                assign srr[j*640+c*128 +: 128] = sro[j*128 +: 128];
                assign sxr[j*640+c*128 +: 128] = sxo[j*128 +: 128];
            end
        end
        assign uprec_q=upc[PW-1:0]; assign urrec_q=urc[RW-1:0]; assign od_q=odc[FW-1:0];
        assign s_lo=slo[FW-1:0]; assign s_hi=shi[FW-1:0];
        for (genvar j=0;j<3;j=j+1) begin : g_sx
            assign srr_q[j*PW +: PW]=srr[j*640 +: PW];
            assign sxrec_q[j*PW +: PW]=sxr[j*640 +: PW];
        end
        assign lb_hd=lbh[PW-1:0]; assign pq_hd=pqh[PW-1:0]; assign eq_hd=eqh[PW-1:0];
        assign lq_hd=lqh[LW-1:0]; assign tq_hd=tqh[RW-1:0]; assign rq_hd=rqh[RW-1:0];
        // queue status from the META leaf (column 4: the controller reads its heads' tag / mode / last anyway, so the
        // control sits beside one leaf); overflow is the OR over all five replicas
        assign {rq_hv,tq_hv,lq_hv,eq_hv,pq_hv,lb_hv}=hv[29:24];
        assign {rq_ovf,tq_ovf,lq_ovf,eq_ovf,pq_ovf,lb_ovf}=ovf[29:24]|ovf[23:18]|ovf[17:12]|ovf[11:6]|ovf[5:0];
    end endgenerate

    // WT 3 (qwen-coll-io r2 2026-10-14): four pin-registered data leaves (ot_coll_tp8_col_tile_r3, each the WT 2 column
    // one edge late) + the metadata column flat beside the controller (ot_coll_tp8_col_core, MEM 2 flop storage with
    // the macro's read timing).  The controller reads only the metadata column; leaf outputs pair with parent
    // valids / metadata delayed by the same edge (up / ur / out / sx valid, engine port inputs and feed above; the
    // metadata halves of up / ur / od / sr / sx here).
    generate if (WT == 3) begin : g_wrapper_cols_r3
        initial if (FW != 512 || TAGW != 32 || LBD != 64 || PQD != 64 || EQD != 32 || LQD != 128 || TQD != 128 || RQD != 32 || QMEM != 1)
            $error("WT 3 requires the production 512b, LB/PQ/EQ/LQ/TQ/RQ 64/64/32/128/128/32 queue shape");
        localparam integer MW = PW - FW;          // 34: {tag, mode, last}
        wire [MW-1:0] m_ind = {in_tag, in_mode, in_last};
        wire [MW-1:0] m_smd = {ml_tag[SLX-1], 1'b0, ml_last[SLX-1]};
        wire [MW-1:0] m_lwc = {{(MW-5){1'b0}}, mf_hd, e_or, e_oe, e_ol};
        wire [MW-1:0] m_tw  = {{(MW-2){1'b0}}, e_oe, e_ol};
        wire [MW-1:0] m_dr  = {{(MW-2){1'b0}}, dr_rec[FW +: 2]};
        wire [MW-1:0] m_up, m_ur, m_od, m_lb, m_pq, m_eq, m_lq, m_tq, m_rq, m_slo, m_shi;
        wire [3*MW-1:0] m_sr, m_sx;
        wire [5:0] m_hv, m_ovf;
        ot_coll_tp8_col_core #(.W(MW), .WLQ(5), .WTQ(2), .WRQ(2), .MEM(2)) u_meta (.clk(clk), .rst_n(rst_n),
            .die_s(DI), .meta_s(1'b1),
            .in_d(m_ind), .dp_d(dp_rec[FW +: MW]), .dr_d(m_dr),
            .sr_d({sr_rec[2*PW+FW +: MW], sr_rec[PW+FW +: MW], sr_rec[FW +: MW]}),
            .sum_d(m_smd), .lq_wd(m_lwc), .tq_wd(m_tw), .e_tx(e_txr[FW +: MW]),
            .c_push({drv_q,e_ov&&!mf_hd,e_ov,eq_push,dpv_q,rl_v}),
            .c_pop({rq_pop,tq_pop,lq_pop,eq_pop,pair_pop,pair_pop}),.c_hold(pr_red&&!wpar),
            .c_sel({sl_tail,pr_gat}),.c_takel(take_l),
            .up(m_up), .ur(m_ur), .od(m_od), .sr(m_sr), .sx(m_sx), .s_lo(m_slo), .s_hi(m_shi),
            .lb_hd(m_lb), .pq_hd(m_pq), .eq_hd(m_eq), .lq_hd(m_lq), .tq_hd(m_tq), .rq_hd(m_rq), .hv(m_hv), .ovf(m_ovf));
        // metadata halves of the leaf-paired outputs, one edge late
        reg [MW-1:0] m_up_q, m_ur_q, m_od_q; reg [3*MW-1:0] m_sr_q, m_sx_q;
        always @(posedge clk) begin m_up_q <= m_up; m_ur_q <= m_ur; m_od_q <= m_od; m_sr_q <= m_sr; m_sx_q <= m_sx; end
        wire [511:0] d_up, d_ur, d_od, d_eq, d_slo, d_shi;
        wire [1535:0] d_sr, d_sx;
        wire [23:0] d_ovf;
        for (genvar c=0;c<4;c=c+1) begin : g_col
            wire [383:0] sri = {sr_rec[2*PW+c*128 +: 128], sr_rec[PW+c*128 +: 128], sr_rec[c*128 +: 128]};
            wire [383:0] sro, sxo;
            ot_coll_tp8_col_tile_r3 u_wc (.clk(CCLK ? clk_colr[c] : clk),.rst_n(rst_n),.die_s(DI),
                .in_d(in_data[c*128 +: 128]),.dp_d(dp_rec[c*128 +: 128]),.dr_d(dr_rec[c*128 +: 128]),.sr_d(sri),
                .sum_d(sl_sum_f[c*128 +: 128]),.lq_wd(e_od[c*128 +: 128]),.tq_wd(e_od[c*128 +: 128]),
                .e_tx(e_txr[c*128 +: 128]),
                .c_push({drv_q,e_ov&&!mf_hd,e_ov,eq_push,dpv_q,rl_v}),
                .c_pop({rq_pop,tq_pop,lq_pop,eq_pop,pair_pop,pair_pop}),.c_hold(pr_red&&!wpar),
                .c_sel({sl_tail,pr_gat}),.c_takel(take_l),
                .up(d_up[c*128 +: 128]),.ur(d_ur[c*128 +: 128]),.od(d_od[c*128 +: 128]),
                .sr(sro),.sx(sxo),.s_lo(d_slo[c*128 +: 128]),.s_hi(d_shi[c*128 +: 128]),
                .eq_hd(d_eq[c*128 +: 128]),.ovf(d_ovf[c*6 +: 6]));
            for (genvar j=0;j<3;j=j+1) begin : g_unpad_sr
                assign d_sr[j*512+c*128 +: 128] = sro[j*128 +: 128];
                assign d_sx[j*512+c*128 +: 128] = sxo[j*128 +: 128];
            end
        end
        assign uprec_q = {m_up_q, d_up}; assign urrec_q = {m_ur_q[1:0], d_ur}; assign od_q = d_od;
        assign s_lo = d_slo; assign s_hi = d_shi;
        for (genvar j=0;j<3;j=j+1) begin : g_sx
            assign srr_q[j*PW +: PW]   = {m_sr_q[j*MW +: MW], d_sr[j*512 +: 512]};
            assign sxrec_q[j*PW +: PW] = {m_sx_q[j*MW +: MW], d_sx[j*512 +: 512]};
        end
        // controller view: metadata column heads (data bits of the heads are not used by the controller in WT >= 2;
        // the engine's in_data takes the leaves' EQ head, one edge late, with eqp_q / eqm_q)
        assign lb_hd = {m_lb, {FW{1'b0}}}; assign pq_hd = {m_pq, {FW{1'b0}}}; assign eq_hd = {m_eq, d_eq};
        assign lq_hd = {m_lq[4:0], {FW{1'b0}}}; assign tq_hd = {m_tq[1:0], {FW{1'b0}}}; assign rq_hd = {m_rq[1:0], {FW{1'b0}}};
        assign {rq_hv,tq_hv,lq_hv,eq_hv,pq_hv,lb_hv} = m_hv;
        assign {rq_ovf,tq_ovf,lq_ovf,eq_ovf,pq_ovf,lb_ovf} = m_ovf|d_ovf[23:18]|d_ovf[17:12]|d_ovf[11:6]|d_ovf[5:0];
    end endgenerate

    // ---------------- faults ----------------
    wire prot_n = (pair_pop && p_bad) || (pr_red && p_last && !wpar) || (sl_v[0] != sl_tail)
                  || (e_ov && !mf_hv) || (m_go && take_l && !m_mode && lq_hd[FW+4])
                  || up_bad || lb_ovf || pq_ovf || eq_ovf || mf_ovf || lq_ovf || tq_ovf || rq_ovf;
    wire arith_n = (sl_v[0] && (|sl_e)) || (rq_pop && rq_hd[FW+1]);
    always @(posedge clk or negedge rs_m)
        if (!rs_m) begin prot <= 1'b0; arith <= 1'b0; end
        else begin if (prot_n) prot <= 1'b1; if (arith_n) arith <= 1'b1; end
    assign fault_code = {prot, arith, e_fc};
    assign fault = e_f || prot || arith;
endmodule

// First-word-fall-through queue.  MEM 0: flop array (head = a registered pointer's mux).  MEM 1: D / 32
// ot_sram_1r1w_32x546_m1 macros (registered read) behind a 2-entry output buffer (one pop per cycle sustained).
// rst_n is the raw asynchronous reset (released through the queue's own leaf).
// ovf flags a push into a full body or a pop of an empty queue (the callers' credits must prevent both).
module ot_coll_tp8_q #(parameter integer W = 8, parameter integer D = 4, parameter integer MEM = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] wd,
    input  wire         pop,
    output wire         hv,
    output wire [W-1:0] hd,
    output reg          ovf
);
    localparam integer AB = (D > 1) ? $clog2(D) : 1;
    wire qr;                                   // the queue's own reset leaf (2-edge release)
    (* keep_hierarchy *) ot_coll_rst_leaf u_qr (.clk(clk), .arst_n(rst_n), .q(qr));
    generate if (MEM == 0) begin : g_f
        reg [W-1:0] m [0:D-1];
        reg [AB-1:0] wp, rp;
        reg [AB:0] n;
        always @(posedge clk) if (push) m[wp] <= wd;
        always @(posedge clk or negedge qr)
            if (!qr) begin wp <= 0; rp <= 0; n <= 0; ovf <= 1'b0; end
            else begin
                if (push) wp <= (wp == D - 1) ? {AB{1'b0}} : wp + 1'b1;
                if (pop && n != 0) rp <= (rp == D - 1) ? {AB{1'b0}} : rp + 1'b1;
                n <= n + (push ? 1'b1 : 1'b0) - ((pop && n != 0) ? 1'b1 : 1'b0);
                if ((push && n == D && !pop) || (pop && n == 0)) ovf <= 1'b1;
            end
        assign hv = (n != 0);
        assign hd = m[rp];
    end else begin : g_m
        localparam integer K = D / 32;
        localparam integer MW = 546;
        initial if (D % 32 != 0 || W > MW || (K & (K - 1)) != 0) $error("ot_coll_tp8_q MEM: D = 32 * 2^k, W <= 546");
        reg [AB-1:0] wp, rp;
        reg [AB:0] mcnt;
        reg rf;
        reg [1:0] obn;
        reg [W-1:0] ob0, ob1;
        reg [(K > 1 ? $clog2(K) : 1)-1:0] rsel;
        wire popv = pop && (obn != 0);
        wire [2:0] after = {1'b0, obn} + {2'b0, rf} - {2'b0, popv};
        wire rd = (mcnt != 0) && (after <= 3'd1);
        wire [MW-1:0] rdo [0:K-1];
        genvar gk;
        for (gk = 0; gk < K; gk = gk + 1) begin : g_k
            wire sel_r = (K == 1) ? 1'b1 : (rp >> 5) == gk;
            wire sel_w = (K == 1) ? 1'b1 : (wp >> 5) == gk;
            ot_sram_1r1w_32x546_m1 u_m (.clk(clk), .r_ce_in(rd && sel_r), .r_addr_in(rp[4:0]), .rd_out(rdo[gk]),
                .w_ce_in(push && sel_w), .w_addr_in(wp[4:0]), .wd_in({{(MW-W){1'b0}}, wd}), .w_mask_in({MW{1'b1}}));
        end
        wire [W-1:0] rdat = rdo[rsel][W-1:0];
        wire [1:0] n0 = obn - (popv ? 2'd1 : 2'd0);
        always @(posedge clk) begin
            if (popv) ob0 <= ob1;
            if (rf) begin if (n0 == 0) ob0 <= rdat; else ob1 <= rdat; end
            if (rd) rsel <= (K == 1) ? 0 : (rp >> 5);
        end
        always @(posedge clk or negedge qr)
            if (!qr) begin wp <= 0; rp <= 0; mcnt <= 0; rf <= 1'b0; obn <= 0; ovf <= 1'b0; end
            else begin
                if (push) wp <= wp + 1'b1;
                if (rd) rp <= rp + 1'b1;
                mcnt <= mcnt + (push ? 1'b1 : 1'b0) - (rd ? 1'b1 : 1'b0);
                rf <= rd;
                obn <= n0 + (rf ? 2'd1 : 2'd0);
                if ((push && mcnt == D && !rd) || (pop && obn == 0)) ovf <= 1'b1;
            end
        assign hv = (obn != 0);
        assign hd = ob0;
    end endgenerate
endmodule
