`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_ret_root_s -- S81 region root with SRAM storage and a CAM-free pairing store (s81-gather 2026-10-13).
//
// Same ports, same arithmetic, same pairing rule and, on every well-formed stream inside both capacities, the SAME
// OUTPUT CYCLES as ot_s81ph_ret_root_p (22,552 flops: 128 x 65 queue flops, a 128-entry 32-b key CAM, 128 x 33 data
// flops, nine 128-b one-hot vectors, a 128-entry free list).  What changed is where the state lives:
//   Q   input queue payload {e, d32, t32}: one 1R1W 128 x 66 SRAM (registered write port, registered read).  The
//       pointer / credit / prefetch control is ot_s81ph_ret_root_p's, unchanged; the macro's registered read output
//       takes the place of the first read level (r1_g), the second level (r2_w) is the flop behind the macro, so
//       a word still lands in the prefetch FIFO 2 cycles after its read issue.  A read can be issued the cycle
//       after the word's write (mc_nz is registered): the word is then still in the write register and is
//       forwarded from it (the array is never read and written at one address in one cycle).
//   B   pairing store.  A partial {pos3, row16, lo5, k3, n5} waits for exactly one other partial: its sibling
//       (same row / pos / n / k, lo ^ 2^k), i.e. the other child of its PARENT tree node.  A row of n <= 31 segments
//       has at most 31 parent nodes (heap index h = 2^(4-k) | lo >> (k+1), 1 .. 31), so the store is
//       S open-row slots x 32 entries {side, e, d32} in one 1R1W S*32 x 34 SRAM addressed {slot, h}; a slot is
//       named by the 24-b key {pos, row, n} (S key registers, S equalities: the only associative part), one valid
//       flop per entry (S x 32) and a 6-b entry count per slot.  No free list, no one-hot 128-b vectors.
//       decision of a non-complete candidate (ONE per cycle, from registers, as before):
//         slot  = the previous decision's slot if it had the same key (its key register is written this edge), else
//                 the slot whose key matched one cycle ahead, else the lowest free slot
//         entry valid (the sibling is waiting) -> ADD: clear the entry, count - 1 (0: the slot is free again);
//         else INSERT: set it, count + 1, write {side, e, d32}; the entry valid of the previous decision's own
//         entry is forwarded (S81PH_MUT_NOFWD removes that).
//       The SRAM is written the cycle after an insert decision and read the cycle after an add decision; a decision
//       is one or the other, so the array never sees a read and a write in one cycle (asserted), and a partial
//       inserted by decision c is readable by the add of decision c + 1 with no bypass.
//   ADD the operand read is address register + SRAM registered read = the two registered OR levels of
//       ot_s81ph_ret_root_p (a3 -> o1 -> b_sel): the adder starts in the same cycle as before.  SRAM read +1 cycle is
//       therefore absorbed, not added: latency difference to ot_s81ph_ret_root_p = 0 cycles.
// CAPACITY (contract change, results/rtl/s81_ph_20261006/gather/contract.json "capacity"): the root holds partials
// of at most S distinct (pos, row, n) at one time (ot_s81ph_ret_root_p: 128 partials of any rows).  A partial of an
// (S+1)-th row raises the sticky fault (fail closed, never silent).  Queue: QD words, a word into a full queue
// faults (unchanged).  Malformed streams fail closed too: a non-complete tag with k > 4 or lo not a multiple of 2^k
// (not a tree node), or a second partial with the tag of a waiting one (found at the operand read), raise fault.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_ret_root_s #(
    parameter integer S    = 8,              // open (pos, row, n) slots: 8 (256 x 34 macro) or 16 (512 x 34 macro)
    parameter integer QD   = 128,
    parameter integer SRAM = 0,              // 1: the two hard macros; 0: flop arrays of the same cycle behaviour
`ifdef S81PH_GTH_LOCAL_BANKS
    parameter integer LOCAL_BANKS = 1
`else
    parameter integer LOCAL_BANKS = 0        // opt-in zero-cycle SS repair: predecode heap and local EV banks
`endif
`ifdef S81PH_GTH_SSA2
    , parameter integer LOCAL_DECISIONS = 1
`else
    , parameter integer LOCAL_DECISIONS = 0
`endif
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    output reg         r_v,
    output reg  [15:0] r_row,
    output reg  [2:0]  r_pos,
    output reg  [31:0] r_fp32,
    output reg  [15:0] r_bf16,
    output reg         r_e,
    output reg         fault
);
    function automatic complete(input [31:0] t);
        complete = t[12:8] == 5'd0 && (6'd1 << t[7:5]) >= {1'b0, t[4:0]};
    endfunction
    function automatic [31:0] norm_step(input [31:0] t);
        reg [18:0] row; reg [4:0] lo, n; reg [2:0] kk;
        begin
            {row, lo, kk, n} = t;
            if (!(lo == 5'd0 && (6'd1 << kk) >= {1'b0, n}) && lo[kk] == 1'b0 && ({1'b0, lo} + (6'd1 << kk)) >= {1'b0, n})
                kk = kk + 3'd1;
            norm_step = {row, lo, kk, n};
        end
    endfunction
    localparam integer QW = $clog2(QD);
    localparam integer SW = (S > 1) ? $clog2(S) : 1;
    localparam integer LAT = 8;              // ot_fp32_add_rne_deep SPLIT 3'b111
    localparam integer NP = 5;               // input norm stages
    integer c, k;

    // ------------------------------------------------------------ P: normalised input (one norm iteration a stage)
    reg [NP-1:0] p_v; reg [31:0] p_t [0:NP-1]; reg [31:0] p_d [0:NP-1]; reg [NP-1:0] p_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) p_v <= {NP{1'b0}}; else p_v <= {p_v[NP-2:0], i_v};
    always @(posedge clk) begin
        p_t[0] <= norm_step(i_t); p_d[0] <= i_d; p_e[0] <= i_e;
        for (c = 1; c < NP; c = c + 1) begin p_t[c] <= norm_step(p_t[c-1]); p_d[c] <= p_d[c-1]; p_e[c] <= p_e[c-1]; end
    end
    wire n_v = p_v[NP-1]; wire [31:0] n_t = p_t[NP-1], n_d = p_d[NP-1]; wire n_e = p_e[NP-1];

    // ------------------------------------------------------------ adder return (tag / valid delay line)
    reg [LAT-2:0] dv;
    reg [33*(LAT-1)-1:0] dtg;
    reg st_e;
    reg sv;
    wire [31:0] sum; wire [1:0] err; wire sv_add;
    reg add; reg [31:0] add_a, add_b; reg [32:0] tag_in;
    wire [31:0] dtg_last = dtg[33*(LAT-2) + 1 +: 32];

    // ------------------------------------------------------------ Q: SRAM queue + prefetch (control of root_p)
    localparam integer PFD = 4;              // prefetch entries (covers the 3-cycle issue -> pop loop)
    reg [QW-1:0] qw, qr;
    reg [QW:0] mc; reg mc_nz;
    reg hv; reg [31:0] h_d; reg h_e; reg [31:0] h_t;
    reg pv; reg [31:0] pq_t, pq_d; reg pq_e;
    reg [2:0] cr;                            // prefetch entries + reads in flight (0 .. PFD)
    reg r1_v, r2_v;
    reg [64:0] r2_w;
    reg [64:0] pf [0:PFD-1];
    reg [1:0] pf_wp, pf_rp; reg [2:0] pf_n; reg pf_nz;
    wire take = !hv || !sv;                  // H is free or popped
    wire p_free = !pv || take;
    wire pf_pop = p_free && pf_nz;
    wire rd_go = mc_nz && (cr < PFD);        // registers only
    wire q_full = mc == QD;
    wire wr_mem = n_v;                       // a word into a full queue overwrites and faults (fail closed)
    wire [QW:0] mc_n = mc + (wr_mem ? 1'b1 : 1'b0) - (rd_go ? 1'b1 : 1'b0);
    wire [2:0] pf_n_n = pf_n + (r2_v ? 3'd1 : 3'd0) - (pf_pop ? 3'd1 : 3'd0);
`ifdef S81PH_MUT_CREDIT
    wire cr_ret = 1'b0;                      // MUTANT: a popped prefetch entry does not return its read credit
`else
    wire cr_ret = pf_pop;
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            qw <= 0; qr <= 0; mc <= 0; mc_nz <= 1'b0; hv <= 1'b0; pv <= 1'b0;
            cr <= 3'd0; r1_v <= 1'b0; r2_v <= 1'b0; pf_wp <= 2'd0; pf_rp <= 2'd0; pf_n <= 3'd0; pf_nz <= 1'b0;
        end else begin
            if (wr_mem) qw <= qw + 1'b1;
            if (rd_go) qr <= qr + 1'b1;
            mc <= mc_n; mc_nz <= mc_n != 0;
            cr <= cr + (rd_go ? 3'd1 : 3'd0) - (cr_ret ? 3'd1 : 3'd0);
            r1_v <= rd_go; r2_v <= r1_v;
            if (r2_v) pf_wp <= pf_wp + 2'd1;
            if (pf_pop) pf_rp <= pf_rp + 2'd1;
            pf_n <= pf_n_n; pf_nz <= pf_n_n != 0;
            if (take) hv <= pv;
            if (p_free) pv <= pf_nz;
        end
    // write port register (every array write pin is driven by a flop that drives nothing else but the forward)
    reg qwv_q; reg [QW-1:0] qwa_q; reg [64:0] qwd_q;
    reg qf_sel; reg [64:0] qf_d;
`ifdef S81PH_MUT_QFWD
    wire q_hit = 1'b0;                       // MUTANT: no forward of the word still in the write register
`else
    wire q_hit = qwv_q && (qr == qwa_q);
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin qwv_q <= 1'b0; qf_sel <= 1'b0; end
        else begin qwv_q <= wr_mem; if (rd_go) qf_sel <= q_hit; end
    always @(posedge clk) begin
        qwa_q <= qw; qwd_q <= {n_e, n_d, n_t};
        if (rd_go && q_hit) qf_d <= qwd_q;
    end
    wire [65:0] q_q;
    wire q_re = rd_go && !q_hit;             // the forwarded read does not touch the array
    ot_s81ph_root_ram #(.W(66), .DEPTH(QD), .KIND(SRAM ? 1 : 0)) u_qm (.clk(clk), .we(qwv_q), .wa(qwa_q),
        .wd({1'b0, qwd_q}), .re(q_re), .ra(qr), .q(q_q));
    wire [64:0] r1_w = qf_sel ? qf_d : q_q[64:0];
    always @(posedge clk) begin
        r2_w <= r1_w;
        if (r2_v) pf[pf_wp] <= r2_w;
        if (take) begin h_t <= pq_t; h_d <= pq_d; h_e <= pq_e; end
        if (pf_pop) begin pq_t <= pf[pf_rp][31:0]; pq_d <= pf[pf_rp][63:32]; pq_e <= pf[pf_rp][64]; end
    end

    // ------------------------------------------------------------ S1: candidate register, slot / entry look-ahead
    reg [31:0] cand;
    // Real candidate-only SV state samples the SAME D at the original SV edge.
    // Both copies are used: core SV retains scheduling, local SV drives decoding.
    wire cand_pick_sv;
    wire [31:0] pick_dtg_oh, pick_pq_oh, pick_h_oh;
    generate if (LOCAL_DECISIONS) begin : g_candidate_local
`ifdef S81PH_MUT_SELECT_PHASE
        wire sv_D = sv; // mutant: candidate selector lags the original state edge
`else
        wire sv_D = dv[LAT-2];
`endif
        (* keep_hierarchy = 1, dont_touch = 1 *)
        ot_s81ph_candidate_valid u_sv (.clk(clk), .rst_n(rst_n), .d(sv_D), .q(cand_pick_sv));
        (* keep_hierarchy = 1, dont_touch = 1 *)
        ot_s81ph_heap_decode u_dtg (.t(dtg_last), .hot(pick_dtg_oh));
        (* keep_hierarchy = 1, dont_touch = 1 *)
        ot_s81ph_heap_decode u_pq (.t(pq_t), .hot(pick_pq_oh));
        (* keep_hierarchy = 1, dont_touch = 1 *)
        ot_s81ph_heap_decode u_h (.t(h_t), .hot(pick_h_oh));
    end else begin : g_candidate_original
        assign cand_pick_sv = sv;
        assign pick_dtg_oh = 0; assign pick_pq_oh = 0; assign pick_h_oh = 0;
    end endgenerate
    wire [31:0] cand_next = dv[LAT-2] ? dtg_last : ((!hv || !cand_pick_sv) ? pq_t : h_t);
    always @(posedge clk) cand <= cand_next;
    // Decode in the existing candidate epoch. No additional decision/read edge.
    function automatic [4:0] heap_h(input [31:0] t);
        case (t[7:5])
            3'd0: heap_h = {1'b1, t[12:9]};
            3'd1: heap_h = {2'b01, t[12:10]};
            3'd2: heap_h = {3'b001, t[12:11]};
            3'd3: heap_h = {4'b0001, t[12]};
            3'd4: heap_h = 5'd1;
            3'd7: heap_h = t[12:8]; // original 3-bit (k+1) wraps at k=7; malformed still faults
            default: heap_h = 5'd0;
        endcase
    endfunction
    (* keep = 1 *) reg [4:0] cand_h;
    (* keep = 1 *) reg [31:0] cand_h_oh;
    generate if (LOCAL_BANKS) begin : g_heap_local
        always @(posedge clk) begin
            cand_h <= heap_h(cand_next);
`ifdef S81PH_MUT_HEAP_PHASE
            cand_h_oh <= 32'd1 << heap_h(cand); // mutant: decode lags the candidate epoch
`else
            // Decode each real source before the late choice. Kept branch
            // hierarchy prevents refactoring control back through the decoder.
            cand_h_oh <= LOCAL_DECISIONS ?
                (dv[LAT-2] ? pick_dtg_oh : ((!hv || !cand_pick_sv) ? pick_pq_oh : pick_h_oh)) :
                (32'd1 << heap_h(cand_next));
`endif
        end
    end endgenerate
    wire        x_v = cand_pick_sv || hv;
    wire [31:0] x_d = cand_pick_sv ? sum : h_d;
    wire        x_e = cand_pick_sv ? (st_e | err != 2'd0) : h_e;
    wire [23:0] x_key = {cand[31:13], cand[4:0]};
    wire [2:0]  x_kk = cand[7:5];
    wire [4:0]  x_lo = cand[12:8];
    // parent heap index: level k + 1 has 32 >> (k + 1) nodes, node lo >> (k + 1)
    wire [4:0]  x_h = LOCAL_BANKS ? cand_h : ((5'd16 >> x_kk) | (x_lo >> (x_kk + 3'd1)));
    wire        x_bad = (x_kk > 3'd4) || ((x_lo & ~(5'h1F << x_kk)) != 5'd0);   // not a tree node below the top
    reg [S-1:0]  sv_s;                       // slot holds at least one entry
    reg [23:0]   skey [0:S-1];
    reg [5:0]    scnt [0:S-1];
    reg [31:0]   ev [0:S-1];                 // entry valid, per slot
    reg [S-1:0] m1, vh1;
    always @* for (k = 0; k < S; k = k + 1) begin
        m1[k] = sv_s[k] && (skey[k] == x_key);
        vh1[k] = LOCAL_BANKS ? (|(ev[k] & cand_h_oh)) : ev[k][x_h];
    end
    reg s2_v, s2_cmp, s2_sp, s2_sh, s2_e, s2_side, s2_bad; reg [31:0] s2_d, s2_t; reg [23:0] s2_key; reg [4:0] s2_h;
    reg [S-1:0] s2_m, s2_vh;
    (* keep = 1 *) reg [31:0] s2_h_oh;
    generate if (LOCAL_BANKS) begin : g_node_local
        always @(posedge clk) s2_h_oh <= cand_h_oh;
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= x_v;
    always @(posedge clk) begin
        s2_t <= cand; s2_key <= x_key; s2_h <= x_h; s2_d <= x_d; s2_e <= x_e; s2_side <= x_lo[x_kk]; s2_bad <= x_bad;
        s2_cmp <= complete(cand);
        s2_sp <= s2_v && (s2_key == x_key);  // the candidate has the key of the one now deciding
        s2_sh <= s2_h == x_h;                // ... and its parent node
        s2_m <= m1; s2_vh <= vh1;
    end

    // ------------------------------------------------------------ S2: decision (registers in)
    reg p_use, p_ins; reg [S-1:0] p_slot;    // previous decision: used a slot (add or insert), inserted, which slot
    function automatic [S-1:0] lowest(input [S-1:0] x);
        lowest = x & (~x + 1'b1);
    endfunction
    function automatic [SW-1:0] enc(input [S-1:0] x);
        integer j;
        begin enc = {SW{1'b0}}; for (j = 0; j < S; j = j + 1) if (x[j]) enc = enc | j[SW-1:0]; end
    endfunction
    (* keep = 1 *) reg s2_hit;
    generate if (LOCAL_DECISIONS) begin : g_decision_local
`ifdef S81PH_MUT_DECISION_PHASE
        always @(posedge clk) s2_hit <= |s2_m; // deliberately stale epoch
`else
        always @(posedge clk) s2_hit <= |m1;   // same existing S2 edge as s2_m
`endif
    end endgenerate
    wire live = s2_v && !s2_cmp;
    wire use_fwd = s2_sp && p_use;
    wire hit_m = LOCAL_DECISIONS ? s2_hit : (|s2_m);
    wire [S-1:0] free_oh = lowest(~sv_s);
    wire free_any = !(&sv_s);
    wire is_new = !use_fwd && !hit_m;
    wire [S-1:0] slot_oh = use_fwd ? p_slot : (hit_m ? s2_m : free_oh);
`ifdef S81PH_MUT_NOFWD
    wire v_fwd = 1'b0;                                             // MUTANT: no forwarding of the previous decision's entry
`else
    wire v_fwd = use_fwd && s2_sh;
`endif
    wire v_cur = v_fwd ? p_ins : (!is_new && (|(slot_oh & s2_vh)));
    wire ok = live && !s2_bad;
`ifdef S81PH_MUT_OVF
    wire no_slot = 1'b0;                                           // MUTANT: slot overflow is not detected (slot 0 is reused)
    wire [S-1:0] slot_w = (is_new && !free_any) ? {{(S-1){1'b0}}, 1'b1} : slot_oh;
`else
    wire no_slot = is_new && !free_any;
    wire [S-1:0] slot_w = slot_oh;
`endif
    wire dec_add = ok && v_cur;
    wire dec_ins = ok && !v_cur && !no_slot;
    wire [5:0] cnt_sel;                      // entry count of the chosen slot
    reg [5:0] cnt_mx;
    always @* begin cnt_mx = 6'd0; for (k = 0; k < S; k = k + 1) cnt_mx = cnt_mx | ({6{slot_w[k]}} & scnt[k]); end
    assign cnt_sel = cnt_mx;
    wire [2:0] s2_kk = s2_t[7:5];
    wire [4:0] s2_lo = s2_t[12:8];
    wire [31:0] s2_par = {s2_t[31:13], s2_lo & ~(5'd1 << s2_kk), s2_kk + 3'd1, s2_t[4:0]};   // normalised in the delay line
    reg a3_v, a3_right, a3_e; reg [31:0] a3_d, a3_t;
    reg a4_v, a4_right, a4_e; reg [31:0] a4_d, a4_t;
    reg e_two, e_dup;
    wire [33:0] b_q;                         // {side, e, d32} of the waiting sibling, valid with a4_v
    // pairing store ports: registered at the macro pins
    reg bwe_q, bre_q; reg [SW+4:0] bwa_q, bra_q; reg [33:0] bwd_q;
`ifdef S81PH_MUT_WADDR
    wire [SW+4:0] b_wa = {enc(slot_w), s2_h} + 1'b1;               // MUTANT: pairing store write address off by one
`else
    wire [SW+4:0] b_wa = {enc(slot_w), s2_h};
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            if (!LOCAL_DECISIONS) sv_s <= {S{1'b0}}; p_use <= 1'b0; p_ins <= 1'b0; p_slot <= {S{1'b0}};
            if (!LOCAL_DECISIONS) for (k = 0; k < S; k = k + 1) scnt[k] <= 6'd0;
            a3_v <= 1'b0; a4_v <= 1'b0; add <= 1'b0; r_v <= 1'b0; fault <= 1'b0; e_two <= 1'b0; e_dup <= 1'b0;
            bwe_q <= 1'b0; bre_q <= 1'b0;
        end else begin
            p_use <= dec_add || dec_ins; p_ins <= dec_ins; p_slot <= slot_w;
            if (!LOCAL_DECISIONS) for (k = 0; k < S; k = k + 1) if (slot_w[k]) begin
                if (dec_ins) begin scnt[k] <= (LOCAL_DECISIONS ? scnt[k] : cnt_sel) + 6'd1; sv_s[k] <= 1'b1; end
                if (dec_add) begin scnt[k] <= (LOCAL_DECISIONS ? scnt[k] : cnt_sel) - 6'd1; sv_s[k] <= (LOCAL_DECISIONS ? scnt[k] : cnt_sel) != 6'd1; end
            end
            bwe_q <= dec_ins; bre_q <= dec_add;
            a3_v <= dec_add; a4_v <= a3_v; add <= a4_v;
            r_v <= s2_v && s2_cmp;
            // off the loop: two slots with one key (cannot happen: checked), a second partial with a waiting tag
            e_two <= live && ((s2_m & (s2_m - 1'b1)) != {S{1'b0}});
            e_dup <= a4_v && (b_q[33] == a4_right);
            if (n_v && q_full) fault <= 1'b1;
            if (live && s2_bad) fault <= 1'b1;
            if (ok && !v_cur && no_slot) fault <= 1'b1;               // a partial of an (S+1)-th open row
            if (e_two || e_dup) fault <= 1'b1;
        end
    // Per-slot enable and predecoded node select replace the nested dynamic
    // vector update. The state still changes at the original decision edge.
    genvar bank, node;
    generate for (bank = 0; bank < S; bank = bank + 1) begin : g_ev_bank
        // The selected slot alone consumes its local valid/count decision.
        // These are the original state and edge, with no shared selected-vh
        // reduction or counter operand selection in the per-slot update cone.
        if (LOCAL_DECISIONS) begin : g_count_local
            wire count_use = slot_w[bank] && ok;
            wire count_cur = v_fwd ? p_ins : (!is_new && s2_vh[bank]);
            wire [5:0] count_inc = scnt[bank] + 6'd1;
            wire [5:0] count_dec = scnt[bank] - 6'd1;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin scnt[bank] <= 6'd0; sv_s[bank] <= 1'b0; end
                else if (count_use) begin
                    if (count_cur) begin
                        scnt[bank] <= count_dec;
                        sv_s[bank] <= scnt[bank] != 6'd1;
                    end else if (!no_slot) begin
                        scnt[bank] <= count_inc;
                        sv_s[bank] <= 1'b1;
                    end
                end
        end
        if (LOCAL_BANKS) begin : g_local
            (* keep = 1 *) wire bank_use = slot_w[bank] && (LOCAL_DECISIONS ? ok : (dec_add || dec_ins));
            wire bank_cur = LOCAL_DECISIONS ? (v_fwd ? p_ins : (!is_new && s2_vh[bank])) : v_cur;
            for (node = 0; node < 32; node = node + 1) begin : g_node
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) ev[bank][node] <= 1'b0;
                    else if (bank_use && s2_h_oh[node]) ev[bank][node] <= !bank_cur;
            end
        end else begin : g_legacy
            always @(posedge clk or negedge rst_n)
                if (!rst_n) ev[bank] <= 32'd0;
                else if (slot_w[bank]) begin
                    if (dec_ins) ev[bank][s2_h] <= 1'b1;
                    if (dec_add) ev[bank][s2_h] <= 1'b0;
                end
        end
    end endgenerate
    always @(posedge clk) begin
        for (k = 0; k < S; k = k + 1) if (slot_w[k] && dec_ins) skey[k] <= s2_key;
        bwa_q <= b_wa; bwd_q <= {s2_side, s2_e, s2_d};
        bra_q <= {enc(slot_w), s2_h};
        a3_d <= s2_d; a3_e <= s2_e; a3_t <= s2_par; a3_right <= s2_side;
        a4_d <= a3_d; a4_t <= a3_t; a4_right <= a3_right; a4_e <= a3_e;
        r_row <= s2_t[28:13]; r_pos <= s2_t[31:29]; r_fp32 <= s2_d; r_e <= s2_e;
        r_bf16 <= ({1'b0, s2_d} + 33'h7FFF + {32'd0, s2_d[16]}) >> 16;
    end
    ot_s81ph_root_ram #(.W(34), .DEPTH(S * 32), .KIND(SRAM ? (S > 8 ? 2 : 3) : 0)) u_bm (.clk(clk), .we(bwe_q), .wa(bwa_q), .wd(bwd_q),
        .re(bre_q), .ra(bra_q), .q(b_q));

    // ------------------------------------------------------------ operands (waiting sibling = left if the candidate is right)
    always @(posedge clk) begin
        if (a4_v) begin
            if (a4_right) begin add_a <= b_q[31:0]; add_b <= a4_d; end
            else begin add_a <= a4_d; add_b <= b_q[31:0]; end
        end
        tag_in <= {a4_t, b_q[32] | a4_e};
    end
    ot_fp32_add_rne_deep #(.SPLIT(3'b111), .KS(1)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(add_a), .b(add_b),
        .y(sum), .err(err), .valid_out(sv_add));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin dv <= 0; sv <= 1'b0; end
        else begin dv <= {dv[LAT-3:0], add}; sv <= dv[LAT-2]; end
    always @(posedge clk) begin
        // delay line stage j < 5 applies norm iteration j to the parent tag (5 iterations = norm)
        for (c = 0; c < LAT - 1; c = c + 1)
            if (c < 5) dtg[33*c +: 33] <= {norm_step(c == 0 ? tag_in[32:1] : dtg[33*(c-1) + 1 +: 32]),
                                           (c == 0) ? tag_in[0] : dtg[33*(c-1)]};
            else dtg[33*c +: 33] <= dtg[33*(c-1) +: 33];
        st_e <= dtg[33*(LAT-2)];
    end
`ifndef SYNTHESIS
    // coverage / occupancy observation for the lockstep bench (simulation only)
    integer ob_open, ob_open_pk = 0, ob_q_pk = 0;
    reg cv_fwd_add = 0, cv_fwd_ins = 0, cv_fwd_oth = 0, cv_reuse = 0, cv_reval = 0, cv_qfwd = 0, cv_ovf = 0, cv_qfull = 0,
        cv_lvl4 = 0, cv_bad = 0, cv_dup = 0;
    reg [S-1:0] ob_was;                      // slots that have been freed at least once
    initial ob_was = {S{1'b0}};
    always @(posedge clk) if (rst_n) begin
        ob_open = $countones(sv_s);
        if (ob_open > ob_open_pk) ob_open_pk = ob_open;
        if (mc > ob_q_pk) ob_q_pk = mc;
        if (dec_add && v_fwd) cv_fwd_add = 1;                  // add with the partial the previous decision inserted
        if (dec_ins && v_fwd) cv_fwd_ins = 1;                  // insert into the entry the previous decision emptied
        if ((dec_add || dec_ins) && use_fwd && !s2_sh) cv_fwd_oth = 1;
        if (dec_ins && is_new && (|(slot_w & ob_was))) cv_reuse = 1;
        if (dec_ins && !is_new && !(|(slot_w & sv_s))) cv_reval = 1;   // insert into a slot freed after the look-ahead
        if (dec_add && cnt_sel == 6'd1) ob_was = ob_was | slot_w;
        if (rd_go && q_hit) cv_qfwd = 1;                       // queue read the cycle after the write of that word
        if (ok && !v_cur && is_new && !free_any) cv_ovf = 1;
        if (n_v && q_full) cv_qfull = 1;
        if (dec_add && s2_kk == 3'd3) cv_lvl4 = 1;
        if (live && s2_bad) cv_bad = 1;
        if (e_dup) cv_dup = 1;
        if (bwe_q && bre_q) $error("ot_s81ph_ret_root_s: pairing store read and write in one cycle");
        if (qwv_q && q_re && qwa_q == qr) $error("ot_s81ph_ret_root_s: queue array read and write at one address");
        if (sv_add !== sv) $error("ot_s81ph_ret_root_s: adder latency != %0d", LAT);
    end
    initial if ((S != 8 && S != 16) || QD != 128) $fatal(1, "ot_s81ph_ret_root_s: S / QD");
`endif
endmodule

// Candidate-only valid copy: genuine consumed state, same D/reset/edge as SV.
(* keep_hierarchy = 1, dont_touch = 1 *)
module ot_s81ph_candidate_valid(input wire clk, input wire rst_n, input wire d,
    (* keep = 1, dont_touch = 1 *) output reg q);
`ifdef S81PH_MUT_SELECT_RESET_PHASE
    always @(posedge clk) // mutant: misses a short asynchronous reset
`else
    always @(posedge clk or negedge rst_n)
`endif
        if (!rst_n) q <= 1'b0; else q <= d;
endmodule

// Exact parent-node one-hot, including original k=7 three-bit wrap semantics.
(* keep_hierarchy = 1, dont_touch = 1 *)
module ot_s81ph_heap_decode(input wire [31:0] t, output reg [31:0] hot);
    always @* case (t[7:5])
        3'd0: hot = 32'h00010000 << t[12:9];
        3'd1: hot = 32'h00000100 << t[12:10];
        3'd2: hot = 32'h00000010 << t[12:11];
        3'd3: hot = 32'h00000004 << t[12];
        3'd4: hot = 32'h00000002;
        3'd7: hot = 32'h00000001 << t[12:8];
        default: hot = 32'h00000001;
    endcase
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_root_ram: 1R1W array with a registered read (q <= mem[ra] when re, holds otherwise).  The caller never
// reads and writes one address in one cycle.  KIND 0: flops (bench / flat reference).  KIND 1: the 128 x 66 macro,
// KIND 2: the 512 x 34 macro, KIND 3: the 256 x 34 macro (physical/s81_ph_views/macros; repair inputs tied off, every
// mask bit written).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_root_ram #(
    parameter integer W = 66,
    parameter integer DEPTH = 128,
    parameter integer KIND = 0,
    parameter integer AW = $clog2(DEPTH)
) (
    input  wire          clk,
    input  wire          we,
    input  wire [AW-1:0] wa,
    input  wire [W-1:0]  wd,
    input  wire          re,
    input  wire [AW-1:0] ra,
    output wire [W-1:0]  q
);
    generate if (KIND == 1) begin : g_q
        ot_sram_1r1w_128x66_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(q), .w_ce_in(we),
            .w_addr_in(wa), .wd_in(wd), .w_mask_in({66{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(14'd0));
    end else if (KIND == 2) begin : g_b
        wire [8:0] wa9 = {{(9-AW){1'b0}}, wa};
        wire [8:0] ra9 = {{(9-AW){1'b0}}, ra};
        ot_sram_1r1w_512x34_m4_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra9), .rd_out(q), .w_ce_in(we),
            .w_addr_in(wa9), .wd_in(wd), .w_mask_in({34{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(12'd0));
    end else if (KIND == 3) begin : g_b8
        ot_sram_1r1w_256x34_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(q), .w_ce_in(we),
            .w_addr_in(wa), .wd_in(wd), .w_mask_in({34{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(12'd0));
    end else begin : g_ff
        reg [W-1:0] mem [0:DEPTH-1];
        reg [W-1:0] q_r;
        always @(posedge clk) begin
            if (we) mem[wa] <= wd;
            if (re) q_r <= mem[ra];
        end
        assign q = q_r;
    end endgenerate
`ifndef SYNTHESIS
    initial if ((KIND == 1 && (W != 66 || DEPTH != 128)) || (KIND == 2 && (W != 34 || DEPTH > 512)) ||
                (KIND == 3 && (W != 34 || DEPTH != 256)))
        $fatal(1, "ot_s81ph_root_ram: KIND %0d does not match W %0d DEPTH %0d", KIND, W, DEPTH);
`endif
endmodule
