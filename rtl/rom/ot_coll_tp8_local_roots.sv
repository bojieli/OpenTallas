`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-coll-io 2026-10-14 (OWNER 0ah, binding): STATIC-CYCLE-SCHEDULED TP8 collective of one Qwen ROM compute die.
// Successor of ot_coll_tp8_die (credit-managed queues: local ICR 32, P 64, R 32, engine 32/destination, LQ/TQ
// reservations).  Here there is NO credit, ready, occupancy-driven issue, arbitration or queue: the compiler issues
// one command per collective message {mode, words, tag} at cycle c; every later event of every word happens at a
// fixed cycle derived from c and the implemented latencies, on all 8 dies (common compiled epoch):
//   word slot w at the in_* pins       : c + 1 + w            (reduce)      c + 1 + GC*w      (gather, GC = 8)
//   UCIe P (all words)                 : sent at A + 1 = c + 3 + w*cad; peer pin + LU
//   pairing B, package fold (owner)     : B = c + LU + 4 + w*cad; slices fed at B1 = B + 1
//   SerDes send / S-ring write W       : reduce W = B1 + SL + 1 (owned words only); gather W = B1 + k, k = 0..7,
//                                        the die sends package-message word d = k / 4 at k mod 4 == its package rank
//   SerDes receive / cross fold D      : D = W + LS + 2
//   UCIe R (reduce, owned words)       : E = D + SL + 1 sent at E + 1; F = E + LU + 2
//   out_valid                          : reduce F + 1 = c + 2LU + 2SL + LS + 12 + w;  gather D + 1 = c + LU + LS + 8 + 8i + k
// Arithmetic is the existing hardened ot_coll_fold_slice master (N 4, ADD_LAT 7, SEAM 1), unchanged:
//   package sum  p = ((lo + hi) + 0) + 0 = lo + hi  (lo = the package's die 0), owner die = word parity;
//   cross package ((p0 + p1) + p2) + p3 in package-rank order: bit-identical to ot_coll_tp8_die / tools/hdc_golden.
// All-gather (argmax words): output word 8i + 4d + r = TP8 rank 4d + r (package r, die d) word i, out_rank {d, r}.
// Buffers are statically sized delay rings written UNCONDITIONALLY every cycle at the free-running slot index and read
// at a fixed offset (never by a pointer that a missing word could desynchronise):
//   P ring  ot_coll_local_ring: 32 * B x 546 (B = 1, 2 or 4 banks of ot_sram_1r1w_32x546_m1, B from LU), local
//           record, delay LU + 2 (LU <= 126: the die value includes both CDC channels of the static UCIe path)
//   S ring  5 x ot_sram_1r1w_512x128_m4_r2c2  {token, tag, local package word}, offset LS + 1 (LS <= 509); the ring
//           also carries the word's schedule token across the board latency, so no long control delay line exists
//   R ring  ot_coll_local_ring (as P)          local cross-fold result, offset LU + 1
// Availability is CHECKED, never waited for: a missing / extra / late producer word or link record, a metadata
// mismatch or a double-booked stage sets a sticky fault and the timeline is unchanged (fault-only checks).
//   fault_code[0] arithmetic (pre-fold or cross-fold adder error, or an error-flagged peer result)
//   fault_code[1] record metadata mismatch (peer P tag/mode/last, SerDes tag/mode/last, R last)
//   fault_code[2] producer slot fault (in_valid != compiled slot, or in_tag/in_mode/in_last != command)
//   fault_code[3] link schedule fault (dp / sr / dr valid != the compiled expectation)
//   fault_code[4] calendar conflict (command while the slot sequencer is busy, words 0, S-ring/SerDes slot or output
//                 slot claimed by a reduce and a gather in the same cycle, gather hold overwritten)
// The rank is strapped (pkg_s / die_ps, one pin flop each): ONE master for all 8 compute dies.
// Negative controls (bench only): OT_TP8S_MUT_OWNER (owner ignores the die strap; a uniform parity swap is an
// equivalent mutant, results stay exact), OT_TP8S_MUT_GATHER (die sends
// hi before lo), OT_TP8S_MUT_RANK (cross fold ranks 1 and 2 swapped), OT_TP8S_MUT_RLAT (R ring read one cycle early).
// ---------------------------------------------------------------------------
module ot_coll_tp8_local_roots #(
    parameter integer LANES   = 16,
    parameter integer TAGW    = 32,
    parameter integer ADD_LAT = 7,
    parameter integer LU      = 19,     // UCIe: up/ur output-register cycle -> peer dp/dr pin cycle (implemented)
    parameter integer LS      = 344,    // SerDes: sx output-register cycle -> peer sr pin cycle (implemented)
    parameter integer GC      = 8,      // gather input cadence: 8 output words per input word on a 1-word output
    parameter integer CCLK    = 0,      // 1: each hardened fold slice on its own clock entry (clk_pfold / clk_xfold)
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW,
    parameter integer RW      = FW + 2
) (
    input  wire              clk,
    input wire [33:0] clk_region, // same compiled edge; independent physical roots
    input  wire [3:0]        clk_pfold,     // CCLK 1: package-fold slice clock entries (same edge as clk)
    input  wire [3:0]        clk_xfold,     // CCLK 1: cross-fold slice clock entries
    input wire [8:0] clk_mem, // CCLK1: P0/P1,S0..S4,R0/R1 direct macro entries
    input  wire              rst_n,
    input  wire [1:0]        pkg_s,
    input  wire              die_ps,
    // compiler command (one per message, at its compiled cycle)
    input  wire              cmd_v,
    input  wire              cmd_mode,      // 0 all-reduce, 1 all-gather
    input  wire [15:0]       cmd_words,
    input  wire [TAGW-1:0]   cmd_tag,
    // local producer: word w at its compiled slot (checked, never waited for)
    input  wire              in_valid,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,
    input  wire [TAGW-1:0]   in_tag,
    // UCIe partial channel {tag, mode, last, data}
    output wire              up_valid,
    output wire [PW-1:0]     up_rec,
    input  wire              dp_valid,
    input  wire [PW-1:0]     dp_rec,
    // UCIe result channel {err, last, data}
    output wire              ur_valid,
    output wire [RW-1:0]     ur_rec,
    input  wire              dr_valid,
    input  wire [RW-1:0]     dr_rec,
    // SerDes port j <-> package (rank + 1 + j) mod 4, die-in-package equal
    output wire [2:0]        sx_valid,
    output wire [3*PW-1:0]   sx_rec,
    input  wire [2:0]        sr_valid,
    input  wire [3*PW-1:0]   sr_rec,
    // result
    output wire              out_valid,
    output wire [FW-1:0]     out_data,
    output wire              out_last,
    output wire [2:0]        out_rank,
    output wire              out_err,
    output wire              fault,
    output wire [4:0]        fault_code,
    // compiled link calendar (schedule tokens only, never observed valids), each aligned with the cycle its record
    // register is presented: the IO calendar (ot_coll_static_linkcal) derives every CDC / codec slot from these
    output wire              up_slot,       // P record slot (up_valid = up_slot && the producer word was observed)
    output wire              ur_peer_slot,  // the package peer's R send slot (= my dr arrival LU later)
    output wire [2:0]        sx_peer_slot,  // SerDes port j: package (rank + 1 + j)'s send slot (= my sr arrival LS later)
    output wire              cmd_free,      // current internal command cycle (fault check only)
    output wire              cmd_free_next  // next edge, for registered external command face
);
    localparam integer NS = FW / 128;
    localparam integer SL = 3 * ADD_LAT + 2;     // ot_coll_fold_slice red_in -> v_out (N 4, SEAM 1)
    localparam integer SEW = 640;                // S ring width (5 x 128)
    initial if (FW != 512 || TAGW != 32 || LU < 1 || LU > 126 || LS < 1 || LS > 509 || GC != 8)
        $error("ot_coll_tp8_static: FW 512, TAGW 32, 1 <= LU <= 126, 1 <= LS <= 509, GC 8");

    // ---------------- straps and reset leaves ----------------
    reg [1:0] pkg_q; reg die_q;
    always @(posedge clk) begin pkg_q <= pkg_s; die_q <= die_ps; end
    wire [1:0] PK = pkg_q;
    wire       DI = die_q;
    wire rs_q, rs_p, rs_s, rs_r;
    (* keep_hierarchy *) ot_coll_rst_leaf u_rsq (.clk(clk), .arst_n(rst_n), .q(rs_q));
    (* keep_hierarchy *) ot_coll_rst_leaf u_rsp (.clk(clk), .arst_n(rst_n), .q(rs_p));
    (* keep_hierarchy *) ot_coll_rst_leaf u_rss (.clk(clk), .arst_n(rst_n), .q(rs_s));
    (* keep_hierarchy *) ot_coll_rst_leaf u_rsr (.clk(clk), .arst_n(rst_n), .q(rs_r));
    reg f_ar, f_md, f_pr, f_ln, f_cf;

    // free-running slot index (ring addresses); only offsets matter, so the dies need not agree on its value
    reg [8:0] cc;
    always @(posedge clk or negedge rs_s) if (!rs_s) cc <= 9'd0; else cc <= cc + 9'd1;

    // ---------------- Q: compiled slot sequencer ----------------
    reg [15:0] rem, sidx; reg [2:0] cnt; reg s_mode; reg [TAGW-1:0] s_tag;
    wire slot    = (rem != 0) && (cnt == 0);
    wire can_cmd = (rem == 0) || (rem == 16'd1 && cnt == 0);
    wire cmd_bad = cmd_v && (!can_cmd || cmd_words == 0);
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin rem <= 0; sidx <= 0; cnt <= 0; s_mode <= 1'b0; s_tag <= 0; end
        else if (cmd_v && !cmd_bad) begin rem <= cmd_words; sidx <= 0; cnt <= 0; s_mode <= cmd_mode; s_tag <= cmd_tag; end
        else if (slot) begin rem <= rem - 16'd1; sidx <= sidx + 16'd1; cnt <= s_mode ? 3'(GC - 1) : 3'd0; end
        else if (cnt != 0) cnt <= cnt - 3'd1;

    // ---------------- A: producer pins, check, P send, P ring write ----------------
    wire iv_q; wire [PW-1:0] ir_q;
    ot_coll_local_record #(.W(PW),.ID(0)) u_region_0 (.clk(clk_region[0]),.rst_n(rs_p),.dv(in_valid),.d({in_tag, in_mode, in_last, in_data}),.qv(iv_q),.q(ir_q));
    reg ta_v, ta_m, ta_l, ta_p; reg [TAGW-1:0] ta_t;

    always @(posedge clk or negedge rs_p)
        if (!rs_p) begin ta_v <= 1'b0; ta_m <= 1'b0; ta_l <= 1'b0; ta_p <= 1'b0; ta_t <= 0; end
        else begin
            ta_v <= slot; ta_m <= s_mode; ta_l <= (rem == 16'd1); ta_p <= sidx[0]; ta_t <= s_tag;
        end
    wire a_bad = (iv_q != ta_v) || (ta_v && iv_q && (ir_q[FW +: TAGW + 2] != {ta_t, ta_m, ta_l}));
    wire upv_q; wire [PW-1:0] uprec_q;
    ot_coll_local_record #(.W(PW),.ID(1)) u_region_1 (.clk(clk_region[1]),.rst_n(rs_p),.dv(ta_v && iv_q),.d(ir_q),.qv(upv_q),.q(uprec_q));


    reg upc_q;
    always @(posedge clk or negedge rs_p) if (!rs_p) upc_q <= 1'b0; else upc_q <= ta_v;
    assign up_slot  = upc_q;
    assign cmd_free = can_cmd;
    // External command pins are captured one edge ahead of the core. Predict
    // the same deterministic state transition; this signal never gates issue.
    assign cmd_free_next = (cmd_v && !cmd_bad) ? (cmd_words <= 1) :
        can_cmd || (rem == 2 && cnt == 0 && !s_mode) || (rem == 1 && cnt == 1);
    assign up_valid = upv_q;
    assign up_rec   = uprec_q;
    wire [PW-1:0] pr_rd;
    ot_coll_local_ring #(.OFF(LU + 2)) u_pring (.clk(clk_region[32]), .mem_ck(CCLK ? {clk_mem[1:0],clk_mem[1:0]} : {4{clk}}), .rs_n(rs_p), .wd(ir_q), .rd(pr_rd));
    // schedule token A -> B (LU + 2 edges): {v, mode, last, parity}
    localparam integer DAB = LU + 2;
    wire [4*DAB-1:0] tab;
    ot_coll_local_delay #(.W(4*DAB),.ID(25)) u_region_25 (.clk(clk_region[25]),.rst_n(rs_p),.d({tab[4*(DAB-1)-1:0], ta_v, ta_m, ta_l, ta_p}),.q(tab));
    wire tb_v = tab[4*DAB-1], tb_m = tab[4*DAB-2], tb_l = tab[4*DAB-3], tb_p = tab[4*DAB-4];

    // ---------------- B: peer partial pins, pairing check, owner, package fold ----------------
    wire dpv_q; wire [PW-1:0] dpr_q;
    ot_coll_local_record #(.W(PW),.ID(2)) u_region_2 (.clk(clk_region[2]),.rst_n(rs_p),.dv(dp_valid),.d(dp_rec),.qv(dpv_q),.q(dpr_q));


    wire b_lnk = (dpv_q != tb_v);
    wire b_md  = tb_v && dpv_q && (dpr_q[FW +: TAGW + 2] != pr_rd[FW +: TAGW + 2]);
    // s4 fanout structure (s1/s3 gates: strap PK/DI and token-valid broadcasts drove 2,000-4,600 loads each over the
    // 860-um cluster and crashed the resizer): every wide-word select comes from its own registered copy per 128-bit
    // slice (keep_hierarchy, distinct IDs: no merge), loaded from the same D as the original -> identical cycle.
    wire [NS-1:0] di_r, tbv_r;
    genvar gr;
    generate for (gr = 0; gr < NS; gr = gr + 1) begin : g_rb
        ot_coll_local_rep_reg #(.W(1), .ID(16 + gr), .RST(0)) u_di (.clk(clk_region[13+gr]), .rst_n(1'b1), .d(die_ps), .q(di_r[gr]));
        ot_coll_local_rep_reg #(.W(1), .ID(20 + gr), .RST(1)) u_tbv (.clk(clk_region[13+gr]), .rst_n(rs_p), .d(tab[4*(DAB-1)-1]), .q(tbv_r[gr]));
    end endgenerate
    wire [FW-1:0] lo, hi;
    generate for (gr = 0; gr < NS; gr = gr + 1) begin : g_lohi
        assign lo[gr*128 +: 128] = !di_r[gr] ? pr_rd[gr*128 +: 128] : dpr_q[gr*128 +: 128];
        assign hi[gr*128 +: 128] = !di_r[gr] ? dpr_q[gr*128 +: 128] : pr_rd[gr*128 +: 128];
    end endgenerate
`ifdef OT_TP8S_MUT_OWNER
    wire own_b = tb_v && !tb_m && (tb_p == 1'b0);    // owner ignores the die strap: both dies claim even words
`else
    wire own_b = tb_v && !tb_m && (tb_p == DI);
`endif
    // B1 registers: the fold-slice feed and the gather hold (loaded only on a scheduled word)
    wire [FW-1:0] lo_q, hi_q; reg red_q;
    generate for (gr = 0; gr < NS; gr = gr + 1) begin : g_lohiq
        ot_coll_local_capture #(.W(256),.ID(13+gr)) u_region (.clk(clk_region[13+gr]),.en(tbv_r[gr]),.d({hi[gr*128 +: 128],lo[gr*128 +: 128]}),.q({hi_q[gr*128 +: 128],lo_q[gr*128 +: 128]}));
    end endgenerate
    always @(posedge clk or negedge rs_p) if (!rs_p) red_q <= 1'b0; else red_q <= own_b;
    wire [NS-1:0] ps_v, ps_e; wire [FW-1:0] ps_sum;
    genvar gs;
    generate for (gs = 0; gs < NS; gs = gs + 1) begin : g_pf
        (* keep_hierarchy *) ot_coll_fold_slice u_fs (.clk(CCLK ? clk_pfold[gs] : clk), .rst_n(rst_n), .red_in(red_q),
            .src({256'd0, hi_q[gs*128 +: 128], lo_q[gs*128 +: 128]}),
            .sum(ps_sum[gs*128 +: 128]), .v_out(ps_v[gs]), .e_out(ps_e[gs]));
    end endgenerate
    // reduce token B -> C (SL + 2 edges): {v, own, last, tag}
    localparam integer DBC = SL + 2, TBW = TAGW + 3;
    wire [TBW*DBC-1:0] tbc;
    wire [TBW*DBC-1:0] tbc_d = {tbc[TBW*(DBC-1)-1:0], tb_v && !tb_m, own_b, tb_l, pr_rd[FW+2 +: TAGW]};
    genvar gc;
    generate for(gc=0;gc<4;gc=gc+1) begin:g_calendar
        localparam integer LO=(TBW*DBC*gc)/4, HI=(TBW*DBC*(gc+1))/4;
        ot_coll_local_delay #(.W(HI-LO),.ID(21+gc)) u_region (.clk(clk_region[21+gc]),.rst_n(rs_p),.d(tbc_d[LO +: HI-LO]),.q(tbc[LO +: HI-LO]));
    end endgenerate
    wire tc_v = tbc[TBW*DBC-1], tc_o = tbc[TBW*DBC-2], tc_l = tbc[TBW*DBC-3];
    wire [TAGW-1:0] tc_t = tbc[TBW*DBC-4 -: TAGW];
    // gather hold run: k = 0..7 at B1 .. B1 + 7
    reg g_run; reg [2:0] g_k; reg g_l; reg [TAGW-1:0] g_t;
    wire g_bad = tb_v && g_run && (g_k != 3'd7);
    wire [2:0] gk_next = (tb_v && tb_m) ? 3'd0 : g_run ? g_k + 3'd1 : g_k;
    always @(posedge clk or negedge rs_p)
        if (!rs_p) begin g_run <= 1'b0; g_k <= 0; g_l <= 1'b0; g_t <= 0; end
        else if (tb_v && tb_m) begin g_run <= 1'b1; g_k <= 0; g_l <= tb_l; g_t <= pr_rd[FW+2 +: TAGW]; end
        else if (g_run) begin g_run <= (g_k != 3'd7); g_k <= g_k + 3'd1; end
`ifdef OT_TP8S_MUT_GATHER
    wire g_d = !g_k[2];
`else
    wire g_d = g_k[2];
`endif
    wire [1:0] g_r = g_k[1:0];

    // ---------------- C / W: package word, S ring write, SerDes send ----------------
    wire [FW-1:0] pf_q; reg pe_q;
    generate for (gs = 0; gs < NS; gs = gs + 1) begin : g_pfe
        ot_coll_local_capture #(.W(128),.ID(17+gs)) u_region (.clk(clk_region[17+gs]),.en(1'b1),.d(ps_e[gs] ? {4{32'h7fc00000}} : ps_sum[gs*128 +: 128]),.q(pf_q[gs*128 +: 128]));
    end endgenerate
    always @(posedge clk or negedge rs_s) if (!rs_s) pe_q <= 1'b0; else pe_q <= |(ps_e & ps_v);
    wire w_conf = tc_v && g_run;
    wire w_red  = tc_v;
    wire w_v    = tc_v || g_run;
    wire w_mode = !tc_v;                                   // reduce wins a conflict (and faults)
    wire w_od   = w_red ? tc_o : g_d;                      // own (reduce) / package-message word d (gather)
    wire [1:0] w_r = w_red ? 2'd0 : g_r;
    wire w_l    = w_red ? tc_l : g_l;
    wire [TAGW-1:0] w_t = w_red ? tc_t : g_t;
    wire [NS-1:0] tcv_r, gd_r;
    wire [FW-1:0] w_d;
    generate for (gr = 0; gr < NS; gr = gr + 1) begin : g_wd
        ot_coll_local_rep_reg #(.W(1), .ID(24 + gr), .RST(1)) u_tcv (.clk(clk_region[17+gr]), .rst_n(rs_p), .d(tbc[TBW*(DBC-1)-1]), .q(tcv_r[gr]));
        // g_d = g_k[2]: the copy follows g_k's next-state (same reset/enable as g_k)
        ot_coll_local_rep_reg #(.W(1), .ID(28 + gr), .RST(1)) u_gd (.clk(clk_region[17+gr]), .rst_n(rs_p), .d(gk_next[2]), .q(gd_r[gr]));
`ifdef OT_TP8S_MUT_GATHER
        assign w_d[gr*128 +: 128] = tcv_r[gr] ? pf_q[gr*128 +: 128] : (!gd_r[gr] ? hi_q[gr*128 +: 128] : lo_q[gr*128 +: 128]);
`else
        assign w_d[gr*128 +: 128] = tcv_r[gr] ? pf_q[gr*128 +: 128] : (gd_r[gr] ? hi_q[gr*128 +: 128] : lo_q[gr*128 +: 128]);
`endif
    end endgenerate
    wire w_send = w_red ? (tc_v && tc_o) : (g_run && g_r == PK);
    wire [SEW-1:0] s_wd = {{(SEW-550){1'b0}}, w_v, w_r, w_od, w_mode, w_l, w_t, w_d};
    // These are physically distinct face registers. Keep each soft hierarchy
    // through synthesis so identical data/valid cones cannot be merged across
    // opposite die faces (the failed s1 gate merged all three copies).
    genvar gj;
    generate for (gj = 0; gj < 3; gj = gj + 1) begin : g_sxo
        (* keep_hierarchy = 1 *) ot_coll_local_sx_reg #(.W(PW),.FACE(gj)) u_face (
            .clk(clk_region[3+gj]),.rst_n(rs_s),.dv(w_send),.data({w_t,w_mode,w_l,w_d}),
            .qv(sx_valid[gj]),.qdata(sx_rec[gj*PW +: PW]));
    end endgenerate
    // peer send slots per SerDes port: reduce = the same owned words (equal die-in-package parity); gather = the
    // hold cycle k whose rank field equals the peer package (PK + 1 + j)
    reg [2:0] sxp_q;
    always @(posedge clk or negedge rs_s) if (!rs_s) sxp_q <= 3'b0;
        else sxp_q <= {w_red ? (tc_v && tc_o) : (g_run && g_r == PK + 2'd3),
                       w_red ? (tc_v && tc_o) : (g_run && g_r == PK + 2'd2),
                       w_red ? (tc_v && tc_o) : (g_run && g_r == PK + 2'd1)};
    assign sx_peer_slot = sxp_q;
    wire [SEW-1:0] s_rd;
    genvar gm;
    generate for (gm = 0; gm < SEW / 128; gm = gm + 1) begin : g_sring
        ot_sram_1r1w_512x128_m4_r2c2 u_m (.clk(CCLK ? clk_mem[2+gm] : clk), .r_ce_in(1'b1), .r_addr_in(cc - 9'(LS + 1)),
            .rd_out(s_rd[gm*128 +: 128]), .w_ce_in(1'b1), .w_addr_in(cc), .wd_in(s_wd[gm*128 +: 128]),
            .w_mask_in({128{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(14'b0));
    end endgenerate

    // ---------------- D: SerDes receive (pins), check, cross fold / gather output ----------------
    wire [2:0] srv_q; wire [PW-1:0] srr_q [0:2];
    generate for (gj = 0; gj < 3; gj = gj + 1) begin : g_sri
        ot_coll_local_record #(.W(PW),.ID(6+gj)) u_region (.clk(clk_region[6+gj]),.rst_n(rs_s),.dv(sr_valid[gj]),.d(sr_rec[gj*PW +: PW]),.qv(srv_q[gj]),.q(srr_q[gj]));
    end endgenerate

    // a token is meaningful only once the ring has been written LS + 1 cycles after reset (ring power-up content)
    reg [9:0] warm;
    always @(posedge clk or negedge rs_s) if (!rs_s) warm <= 0; else if (warm != 10'(LS + 3)) warm <= warm + 10'd1;
    wire       td_v  = s_rd[549] && (warm == 10'(LS + 3));
    wire [1:0] td_r  = s_rd[548:547];
    wire       td_od = s_rd[546], td_m = s_rd[545], td_l = s_rd[544];
    wire [TAGW-1:0] td_t = s_rd[512 +: TAGW];
    wire [FW-1:0]   td_d = s_rd[FW-1:0];
    // source of package rank gq: own ring word (gq == PK) or SerDes port (gq - PK + 3) mod 4
    wire [1:0] jr = td_r - PK + 2'd3;                       // gather: port of the scheduled rank
    wire [2:0] exp_sr = !td_v ? 3'b000 : !td_m ? (td_od ? 3'b111 : 3'b000)
                      : (td_r == PK) ? 3'b000 : (3'b001 << jr);
    wire d_lnk = (srv_q != exp_sr);
    reg  d_md;
    integer jj;
    always @(*) begin
        d_md = 1'b0;
        for (jj = 0; jj < 3; jj = jj + 1)
            if (exp_sr[jj] && srv_q[jj] && (srr_q[jj][FW +: TAGW + 2] != {td_t, td_m, td_l})) d_md = 1'b1;
    end
    wire red2 = td_v && !td_m && td_od;
    wire [4*FW-1:0] xsrc;
    genvar gq;
    // static rank select, decoded from the strap into a registered one-hot {own, port2, port1, port0} per (rank, slice)
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_xs
        for (gr = 0; gr < NS; gr = gr + 1) begin : g_s
            wire [1:0] jqs = 2'(gq) - pkg_s + 2'd3;
            wire [3:0] sel;
            ot_coll_local_rep_reg #(.W(4), .ID(32 + gq*NS + gr), .RST(0)) u_sel (.clk(clk_region[28+gr]), .rst_n(1'b1),
                .d({2'(gq) == pkg_s, (2'(gq) != pkg_s) && jqs == 2'd2, (2'(gq) != pkg_s) && jqs == 2'd1,
                    (2'(gq) != pkg_s) && jqs == 2'd0}), .q(sel));
            assign xsrc[gq*FW + gr*128 +: 128] = (td_d[gr*128 +: 128] & {128{sel[3]}}) | (srr_q[2][gr*128 +: 128] & {128{sel[2]}})
                                             | (srr_q[1][gr*128 +: 128] & {128{sel[1]}}) | (srr_q[0][gr*128 +: 128] & {128{sel[0]}});
        end
    end endgenerate
`ifdef OT_TP8S_MUT_RANK
    wire [4*FW-1:0] xs = {xsrc[3*FW +: FW], xsrc[1*FW +: FW], xsrc[2*FW +: FW], xsrc[0 +: FW]};
`else
    wire [4*FW-1:0] xs = xsrc;
`endif
    wire [NS-1:0] xs_v, xs_e; wire [FW-1:0] xs_sum;
    generate for (gs = 0; gs < NS; gs = gs + 1) begin : g_xf
        (* keep_hierarchy *) ot_coll_fold_slice u_fs (.clk(CCLK ? clk_xfold[gs] : clk), .rst_n(rst_n), .red_in(red2),
            .src({xs[3*FW + gs*128 +: 128], xs[2*FW + gs*128 +: 128], xs[FW + gs*128 +: 128], xs[gs*128 +: 128]}),
            .sum(xs_sum[gs*128 +: 128]), .v_out(xs_v[gs]), .e_out(xs_e[gs]));
    end endgenerate
    // gather output (D + 1)
    wire [FW-1:0] g_out = (td_r == PK) ? td_d : (jr == 2'd0) ? srr_q[0][FW-1:0] : (jr == 2'd1) ? srr_q[1][FW-1:0]
                                                                                              : srr_q[2][FW-1:0];
    wire gd_v = td_v && td_m;
    // reduce token D -> E (SL + 1 edges): {v, own, last}
    localparam integer DDE = SL + 1;
    wire [3*DDE-1:0] tde;
    ot_coll_local_delay #(.W(3*DDE),.ID(26)) u_region_26 (.clk(clk_region[26]),.rst_n(rs_r),.d({tde[3*(DDE-1)-1:0], td_v && !td_m, td_od, td_l}),.q(tde));
    wire te_v = tde[3*DDE-1], te_o = tde[3*DDE-2], te_l = tde[3*DDE-3];

    // ---------------- E: cross-fold result, R ring write, UCIe R send ----------------
    wire [FW-1:0] xr_q; reg xe_q;
    ot_coll_local_capture #(.W(FW),.ID(9)) u_region_9 (.clk(clk_region[9]),.en(1'b1),.d(xs_sum),.q(xr_q));
    always @(posedge clk or negedge rs_r) if (!rs_r) xe_q <= 1'b0; else xe_q <= |(xs_e & xs_v);
    wire e_own = te_v && te_o;
    wire urv_q; wire [RW-1:0] urr_q;
    ot_coll_local_record #(.W(RW),.ID(10)) u_region_10 (.clk(clk_region[10]),.rst_n(rs_r),.dv(e_own),.d({xe_q, te_l, xr_q}),.qv(urv_q),.q(urr_q));


    reg urp_q;
    always @(posedge clk or negedge rs_r) if (!rs_r) urp_q <= 1'b0; else urp_q <= te_v && !te_o;
    assign ur_valid = urv_q;
    assign ur_peer_slot = urp_q;
    assign ur_rec   = urr_q;
    wire [PW-1:0] rr_rd;
`ifdef OT_TP8S_MUT_RLAT
    localparam integer ROFF = LU + 1;
`else
    localparam integer ROFF = LU + 2;
`endif
    ot_coll_local_ring #(.OFF(ROFF)) u_rring (.clk(clk_region[33]), .mem_ck(CCLK ? {clk_mem[8:7],clk_mem[8:7]} : {4{clk}}), .rs_n(rs_r), .wd({{(PW-RW){1'b0}}, xe_q, te_l, xr_q}), .rd(rr_rd));
    // token E -> F (LU + 2 edges): {v, own, last}
    localparam integer DEF = LU + 2;
    wire [3*DEF-1:0] tef;
    ot_coll_local_delay #(.W(3*DEF),.ID(27)) u_region_27 (.clk(clk_region[27]),.rst_n(rs_r),.d({tef[3*(DEF-1)-1:0], te_v, te_o, te_l}),.q(tef));
    wire tf_v = tef[3*DEF-1], tf_o = tef[3*DEF-2], tf_l = tef[3*DEF-3];

    // ---------------- F: peer result pins, merge, output ----------------
    wire drv_q; wire [RW-1:0] drr_q;
    ot_coll_local_record #(.W(RW),.ID(11)) u_region_11 (.clk(clk_region[11]),.rst_n(rs_r),.dv(dr_valid),.d(dr_rec),.qv(drv_q),.q(drr_q));


    wire f_lnk = (drv_q != (tf_v && !tf_o));
    wire f_mdx = tf_v && !tf_o && drv_q && (drr_q[FW] != tf_l);
    wire [NS-1:0] tfv_r, tfo_r;
    wire [FW-1:0] rf_d;
    generate for (gr = 0; gr < NS; gr = gr + 1) begin : g_rf
        ot_coll_local_rep_reg #(.W(1), .ID(48 + gr), .RST(1)) u_tfv (.clk(clk_region[12]), .rst_n(rs_r), .d(tef[3*(DEF-1)-1]), .q(tfv_r[gr]));
        ot_coll_local_rep_reg #(.W(1), .ID(52 + gr), .RST(1)) u_tfo (.clk(clk_region[12]), .rst_n(rs_r), .d(tef[3*(DEF-1)-2]), .q(tfo_r[gr]));
        assign rf_d[gr*128 +: 128] = tfo_r[gr] ? rr_rd[gr*128 +: 128] : drr_q[gr*128 +: 128];
    end endgenerate
    wire          rf_e = tf_o ? rr_rd[FW+1] : drr_q[FW+1];
    wire o_conf = tf_v && gd_v;
    reg ov_q, ol_q, oe_q; reg [2:0] or_q; reg [FW-1:0] od_q; integer kq;
    always @(posedge clk_region[12]) begin
        for (kq = 0; kq < NS; kq = kq + 1) od_q[kq*128 +: 128] <= tfv_r[kq] ? rf_d[kq*128 +: 128] : g_out[kq*128 +: 128];
        ol_q <= tf_v ? tf_l : (td_l && td_od && td_r == 2'd3);
        or_q <= tf_v ? 3'd0 : {td_od, td_r};
        oe_q <= tf_v ? rf_e : 1'b0;
    end
    always @(posedge clk_region[12] or negedge rs_r) if (!rs_r) ov_q <= 1'b0; else ov_q <= tf_v || gd_v;
    assign out_valid = ov_q; assign out_data = od_q; assign out_last = ol_q; assign out_rank = or_q; assign out_err = oe_q;

    // ---------------- sticky faults (checks never reschedule) ----------------
    always @(posedge clk or negedge rs_q)
        if (!rs_q) begin f_ar <= 1'b0; f_md <= 1'b0; f_pr <= 1'b0; f_ln <= 1'b0; f_cf <= 1'b0; end
        else begin
            if (pe_q || (xe_q && e_own) || (tf_v && rf_e)) f_ar <= 1'b1;
            if (b_md || d_md || f_mdx) f_md <= 1'b1;
            if (a_bad) f_pr <= 1'b1;
            if (b_lnk || d_lnk || f_lnk) f_ln <= 1'b1;
            if (cmd_bad || w_conf || o_conf || g_bad) f_cf <= 1'b1;
        end
    assign fault_code = {f_cf, f_ln, f_pr, f_md, f_ar};
    assign fault = |fault_code;
endmodule

// Fixed-offset delay ring: written unconditionally every cycle at the free-running index, read OFF cycles later
// (rd valid OFF cycles after wd).  Depth = 32 * B >= OFF, B banks of the 32 x 546 1R1W macro; the read bank
// select is registered with the macro's registered read.
module ot_coll_local_ring #(parameter integer OFF = 20) (
    input  wire         clk,
    input wire [3:0] mem_ck,
    input  wire         rs_n,
    input  wire [545:0] wd,
    output wire [545:0] rd
);
    localparam integer B  = (OFF <= 32) ? 1 : (OFF <= 64) ? 2 : 4;
    localparam integer AW = 5 + $clog2(B);
    initial if (OFF < 2 || OFF > 128) $error("ot_coll_local_ring: 2 <= OFF <= 128");
    reg [AW-1:0] wa;
    always @(posedge clk or negedge rs_n) if (!rs_n) wa <= 0; else wa <= wa + 1'b1;
    wire [AW-1:0] ra = wa - AW'(OFF - 1);      // read issued OFF - 1 cycles after the write, data one edge later
    wire [546*B-1:0] rdb;
    genvar b;
    generate for (b = 0; b < B; b = b + 1) begin : g_b
        ot_sram_1r1w_32x546_m1 u_m (.clk(mem_ck[b]), .r_ce_in(1'b1), .r_addr_in(ra[4:0]), .rd_out(rdb[b*546 +: 546]),
            .w_ce_in((B == 1) ? 1'b1 : (wa[AW-1:5] == b)), .w_addr_in(wa[4:0]), .wd_in(wd), .w_mask_in({546{1'b1}}));
    end endgenerate
    generate if (B == 1) begin : g_one
        assign rd = rdb;
    end else begin : g_sel
        // decoded bank select (one-hot AND-OR, constant-index slices: no wide runtime part-select); the registered
        // one-hot is replicated per <= 110-bit group (s4: one rbs drove 1,604 loads)
        localparam integer NG = 5, GW = 110;
        reg [545:0] rsel;
        wire [B*NG-1:0] boh;
        genvar gg;
        for (gg = 0; gg < NG; gg = gg + 1) begin : g_g
            wire [B-1:0] oh_d;
            for (genvar kd = 0; kd < B; kd = kd + 1) begin : g_d
                assign oh_d[kd] = (ra[AW-1:5] == kd);
            end
            ot_coll_local_rep_reg #(.W(B), .ID(64 + OFF*8 + gg), .RST(0)) u_oh (.clk(clk), .rst_n(1'b1), .d(oh_d), .q(boh[gg*B +: B]));
        end
        integer kb, kbit;
        always @(*) begin
            rsel = 546'd0;
            for (kbit = 0; kbit < 546; kbit = kbit + 1)
                for (kb = 0; kb < B; kb = kb + 1)
                    rsel[kbit] = rsel[kbit] | (rdb[kb*546 + kbit] & boh[(kbit / GW)*B + kb]);
        end
        assign rd = rsel;
    end endgenerate
endmodule

// One existing stage, independently instantiated per physical SerDes face.
// FACE creates separate parameterized modules; keep_hierarchy prevents global
// duplicate-register merging. No additional transport cycle is introduced.
(* keep_hierarchy = 1 *) module ot_coll_local_sx_reg #(
 parameter integer W=546, FACE=0
)(input wire clk,rst_n,dv,input wire[W-1:0]data,
 output reg qv,output reg[W-1:0]qdata);
 (* keep *)wire[W-1:0]face_data=data;
 always @(posedge clk)qdata<=face_data;
 always @(posedge clk or negedge rst_n)if(!rst_n)qv<=0;else qv<=dv;
endmodule

// Registered copy of a broadcast select (s4 fanout structure).  Each instance is a separate hardened-in-place
// soft hierarchy so synthesis cannot merge the copies back into one high-fanout driver; no cycle is added (the copy
// is loaded from the same D as the register it replaces).
(* keep_hierarchy = 1 *) module ot_coll_local_rep_reg #(parameter integer W = 1, ID = 0, RST = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output reg [W-1:0] q);
    generate if (RST) begin : g_r
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= {W{1'b0}}; else q <= d;
    end else begin : g_n
        always @(posedge clk) q <= d;
    end endgenerate
endmodule

// These leaves keep the original edge/reset/enable semantics. Data are never
// reset where the original datapath did not reset them.
(* keep_hierarchy = 1 *) module ot_coll_local_record #(parameter integer W=546,ID=0)(
 input wire clk,rst_n,dv,input wire[W-1:0]d,output reg qv,output reg[W-1:0]q);
 always @(posedge clk) q<=d;
 always @(posedge clk or negedge rst_n) if(!rst_n)qv<=0;else qv<=dv;
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_capture #(parameter integer W=128,ID=0)(
 input wire clk,en,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge clk) if(en)q<=d;
endmodule
(* keep_hierarchy = 1 *) module ot_coll_local_delay #(parameter integer W=128,ID=0)(
 input wire clk,rst_n,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge clk or negedge rst_n) if(!rst_n)q<=0;else q<=d;
endmodule
