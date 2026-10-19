`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// MU-S81-2/DIE (2026-10-19): dsdv_mu_hwin -- the end-slice TX tag windows, landing replays and RX tag check of the
// multi-user S81 die, as a NEW leaf BESIDE the CLOSED dsdv_mu_hslot (view dsdv_mu_hslot-28a8118d5, NSLOT 47 MUT 0).
// MU-S81/DIE 908a67c18 put this logic inside dsdv_mu_hslot (NEV > 0); that changed the closed leaf's source, so the die
// could not bind the closed view.  Here dsdv_mu_hslot.sv is untouched (byte-identical to the view's source) and the
// window logic keeps its own copy of the start table (same record rule, same slot timer, same due edge), fed by the same
// start pin tap f_ks and the same boot words f_mc (slot period S / return latency RL), plus its own boot word stream
// f_mw (host CSR 0x16) for the event rows -- so the closed hslot never sees a window word.
//
// Under the shift calendar every user runs user 0's schedule shifted by its slot, so every per-user event on this die
// sits a FIXED offset D after that user's start capture edge.  NEV boot-loaded event rows {kind, endpoint, D}: kind 0 =
// TX tag window on endpoint ep (mu_c[ep] = {pos 21, user 10, land, ab, v}), kind 1 = landing replay (mu_rc[ep] =
// {user 10, v}, only where the slot's land / replay-enable bit is 1).  Per-slot attributes {land, ab} per event are
// boot-loaded per calendar slot (calendar_ar_q4 rows).  One pointer per event walks the table in start order, so every
// event fires exactly on ts + D: no queue, no ready, no credit, no stall.  RX: every valid tag on mu_rt ({v, user 10,
// pos 21} per returning end slice) must name an outstanding start of the table.
// Faults t_wf (sticky): [0] RX tag of no outstanding start, or an event past its edge (-> die t_mf[2] beside hslot's
// return mismatch); [1] window config: a word while armed / outstanding, sel 3, a D outside [nw + 2, RL - 2] or
// a slot gap <= nw + 1 at the first start (nw = calendar slots per period, MU-S81-2/SEQ gap table), or two events on one endpoint output in one edge (-> die t_mf[3]).
// f_mw = {v, 1'b0, d 24}: d[22:21] = 0 select event d[4:0], kind d[8], endpoint d[10:9]; 1 offset D = d[20:0] of the
// selected event; 2 attribute of the selected event for slot d[9:0] = {land d[11], ab d[10]}; 3 = config fault.
// f_mc = {v, sel, d 24} exactly as dsdv_mu_hslot (sel 0 slot gap words, sel 1 RL); hslot reports its own config faults.
// MU-S81-2/SEQ: the slot entries wrap at nw (calendar slots per period), so eat[event][entry] is the calendar slot's
// attribute in EVERY period (with entries wrapping at NSLOT 47 on a 46-slot AR period they drifted one slot a period).
// MUT (bench negative controls): 3 window ab bit dropped (copy B never selected), 4 replay enable ignored, 5 gap index
// stuck at 0.
// Timing: f_ks / f_mc / f_mw / mu_rt land in pin flops; mu_c / mu_rc / t_wf leave flops.  ot_rst_relay reset.
// MU-S81-2/HWIN (10-19) timing restructure (the REFILL-0730/HWIN gate: binary event pointers pe[e] drove ~3.7k mux
// loads each and pe -> 47:1 ts mux -> + D -> == tm -> mu_c was a 22-level ~895 ps stage).  Same ports, same outputs on
// the same edges (zero added output cycles):
//   * every table pointer (8 event pointers, the retire pointer, the slot / gap-table walkers) is ONE-HOT: a pointer
//     bit drives only its own entry's ~65 mux leaves (no 3.7k-load select net); the 47:1 reads are AND-OR trees;
//   * look-ahead heads: each event row keeps a registered copy of the entry under its pointer {ts, pos, user, land, ab}
//     (h_*), reloaded every edge, with a freshness bit (h_fr: no pointer move and no write at that entry on the last
//     edge).  In a legal config the pointer rests on an entry >= 2 edges before it is due (D >= nw + 2, slot gaps
//     >= nw + 2, pointer walk <= nw - 1 edges), so the head is always fresh on the due edge;
//   * the adders leave the stage: tmd[e] = tm - D[e] and tmr = tm - RL + 1 are registered (tm1 = tm + 1 counter), so
//     fire = (h_ts == tmd) and due = (h_rts == tmr) are plain 32-bit equalities on flops; mu_c / mu_rc are built from
//     the fired heads (later event wins on one endpoint, as before; two on one output still fault t_wf[1]);
//   * the record is staged one edge (rec_q): the start-table write (ts = the start edge's tm), vld set and fd clear
//     land one edge after the start edge, so udup / col / on_cal -> rec no longer fans into ~3k write enables in the
//     same stage.  Pointers hold on a start at their entry and on the staged write (no skip past a new entry).  Event
//     edges are unchanged (ts is the start edge's tm); vld is visible to the RX tag check one edge later (an RX tag
//     returns >= one round after its start);
//   * gate 2 (10-19): the head equality / late compares are registered one edge ahead (eqn / ltn vs tm + 1 - D), so
//     fire is a flop AND; fired flags fd carry no reset (cleared at the staged record, read only on valid entries);
//   * the gap table stores gap - 1 (the prefetch is a one-hot read, no decrement in the stage).
// Illegal configs (already t_wf[1] at arming: D < nw + 2 or a gap <= nw + 1) may raise the late-event fault t_wf[0]
// one edge later than the former RTL; legal configs are edge-exact (MU_HWIN_GATE, SEQHOST_MU_GATE).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_mu_hwin #(parameter integer NSLOT = 47, parameter integer NEV = 8, parameter integer NEP = 4,
                      parameter integer NRT = 2, parameter integer MUT = 0) (
    input  wire              ck,
    input  wire              rst_n,
    input  wire [52:0]       f_ks,            // tap of the unit start pin {start, user 10, tok 21, pos 21}
    input  wire [25:0]       f_mc,            // hslot boot words {v, sel, d 24} (S / RL)
    input  wire [25:0]       f_mw,            // window boot words {v, 0, d 24}
    output wire [NEP*34-1:0] mu_c,            // per end slice: TX tag window {pos 21, user 10, land, ab, v}
    output wire [NEP*11-1:0] mu_rc,           // per end slice: landing replay {user 10, v}
    input  wire [NRT*32-1:0] mu_rt,           // per returning end slice: RX tag {v, user 10, pos 21}
    output reg  [1:0]        t_wf             // sticky faults
);
    localparam integer SI = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    localparam integer SJ = SI + 1;
    localparam integer EI = (NEV > 1) ? $clog2(NEV) : 1;
    localparam integer PI = (NEP > 1) ? $clog2(NEP) : 1;
    localparam [NSLOT-1:0] OH0 = {{(NSLOT-1){1'b0}}, 1'b1};
`ifndef SYNTHESIS
    initial if (NSLOT < 2 || NSLOT > 1023 || NEV < 1 || NEV > 32) $fatal(1, "dsdv_mu_hwin: NSLOT 2..1023, NEV 1..32");
`endif
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    // ---- pin flops (valid bits gated by the relayed reset, payload not)
    reg [52:0] ks_q; reg [25:0] mc_q, mw_q; reg [NRT*32-1:0] rt_q; integer r;
    always @(posedge ck) begin
        ks_q <= {rn & f_ks[52], f_ks[51:0]}; mc_q <= {rn & f_mc[25], f_mc[24:0]}; mw_q <= {rn & f_mw[25], f_mw[24:0]};
        rt_q <= mu_rt;
        for (r = 0; r < NRT; r = r + 1) rt_q[32*r + 31] <= rn & mu_rt[32*r + 31];
    end
    wire st = ks_q[52]; wire [9:0] su = ks_q[51:42]; wire [20:0] sp = ks_q[20:0];
    // ---- one-hot pointer step: entries wrap at lw (lm = one-hot of lw); a pointer past lw (only while idle, after a
    // config shrink) wraps at NSLOT - 1
    reg [NSLOT-1:0] lm, gm;
    function automatic [NSLOT-1:0] rot(input [NSLOT-1:0] o, input [NSLOT-1:0] l);
        rot = {o[NSLOT-2:0] & ~l[NSLOT-2:0], 1'b0};
        rot[0] = (|(o & l)) | o[NSLOT-1];
    endfunction
    // ---- start table: the same record rule / slot timer / due edge as dsdv_mu_hslot
    reg [23:0] cs, crl, crm; reg [31:0] tm, tm1, tmr; reg armed; reg [23:0] ph; reg [SI-1:0] lw;
    reg [NSLOT-1:0] sl, rp, gx;                           // one-hot: slot, retire pointer, gap-table walker
    // MU-S81-2/SEQ (10-19): slot gap table, the same as dsdv_mu_hslot's (same f_mc words, same walk).  The record calendar (dv_mu_calendar --phase-q 4) has NON-uniform slots
    // (AR 46: shift_k = 4 floor(k (P/4) / 46) -> gaps 21,312 / 21,316; MTP 10 + filler: 10 x 124,524 then 58,160), so
    // one period S cannot hold it (user 3's start lands 4 edges off a uniform 21,312 grid -> t_mf[1] on the real unit).
    // Each sel-0 word APPENDS one slot gap g[k] (cycles from slot k's start edge to slot k+1's); the slot timer walks
    // g[0..n-1] cyclically (n = words written), and the slot entries wrap at nw = n (n >= 2) so the entry index IS the
    // calendar slot.  One sel-0 word (n = 1) = the former uniform period S with nw = NSLOT: the previous behaviour.
    // cs = the smallest gap.  gtm[k] = g[k] - 1 (the timer's compare value).
    reg [23:0] gtm [0:NSLOT-1]; reg [SI:0] gn; reg [23:0] cg, ng;
    reg [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1]; reg [31:0] ts [0:NSLOT-1];
    wire [NSLOT-1:0] ss = armed ? sl : OH0;
    wire on_cal = !armed || ph == 24'd0;
    reg udup; integer i;
    always @* begin udup = 1'b0; for (i = 0; i < NSLOT; i = i + 1) if (vld[i] && eu[i] == su) udup = 1'b1; end
    wire col = |(vld & ss);
    wire [23:0] nw = {{(23-SI){1'b0}}, lw} + 24'd1;     // slot entries in use (= calendar slots per period)
    wire hcfg_bad = gn == 0 || cs < nw || crl <= nw;                     // hslot's own arming rule
    wire rec = st && on_cal && !col && !udup && !(!armed && hcfg_bad);
    // staged record: written one edge after the start edge, with the start edge's tm
    reg rec_q; reg [NSLOT-1:0] ssq; reg [9:0] suq; reg [20:0] spq; reg [31:0] tsq;
    always @(posedge ck) begin ssq <= ss; suq <= su; spq <= sp; tsq <= tm; end
    // retire pointer head (registered read of the entry under rp)
    reg [31:0] h_rts; reg h_rfr;
    wire rok = |(rp & vld);
    wire rhold = (st && |(rp & ss)) || (rec_q && |(rp & ssq));
    wire due = rok && h_rfr && h_rts == tmr;                             // hslot's return edge: the entry retires
    wire radv = due || (!rok && !rhold);
    wire [NSLOT-1:0] gxn = (MUT == 5 || |(gx & gm)) ? OH0 : {gx[NSLOT-2:0], 1'b0};   // MUT 5: gap table index stuck at 0
    reg [23:0] ngr; reg [31:0] rts_r; integer k;
    always @* begin
        ngr = 24'd0; rts_r = 32'd0;
        for (k = 0; k < NSLOT; k = k + 1) begin
            if (gx[k]) ngr = ngr | gtm[k];
            if (rp[k]) rts_r = rts_r | ts[k];
        end
    end
    always @(posedge ck) begin
        ng <= ngr;                                         // next slot's gap - 1, prefetched (gx = the slot after the current one)
        h_rts <= rts_r;
        tmr <= tm1 - {8'd0, crm};                          // = tm - RL + 1 on the next edge
    end
    always @(posedge ck) if (mc_q[25] && !mc_q[24] && !armed && !(|vld) && gn != SJ'(NSLOT)) gtm[gn[SI-1:0]] <= mc_q[23:0] - 24'd1;
    // ---- event rows
    reg [NEV-1:0] ek; reg [PI-1:0] eep [0:NEV-1]; reg [20:0] eD [0:NEV-1]; reg [EI-1:0] esel;
    reg [1:0] eat [0:NEV-1][0:NSLOT-1];                  // {land / replay-en, ab} per event and calendar slot
    reg [NSLOT-1:0] fd [0:NEV-1];                         // fired flags
    reg [NSLOT-1:0] pe [0:NEV-1];                         // one-hot event pointers
    reg [31:0] tmd2 [0:NEV-1];                            // tm - D[e] + 1 (next edge's fire compare value)
    reg [NEV-1:0] eqn, ltn;                               // registered head compares, valid on the next edge
    reg [31:0] h_ts [0:NEV-1]; reg [20:0] h_ep [0:NEV-1]; reg [9:0] h_eu [0:NEV-1]; reg [1:0] h_at [0:NEV-1];
    reg [NEV-1:0] h_fr;
    integer e, p;
    reg bad_d; reg [NEV-1:0] fire, lt, ok, hold, adv;
    reg [NEV*32-1:0] hts_r; reg [NEV*21-1:0] hep_r; reg [NEV*10-1:0] heu_r; reg [NEV*2-1:0] hat_r; integer k2;
    reg [31:0] dl; reg [NEV-1:0] dlm;
    always @* begin
        bad_d = cs <= nw + 24'd1;
        for (e = 0; e < NEV; e = e + 1)
            if ({3'd0, eD[e]} < nw + 24'd2 || {3'd0, eD[e]} + 24'd2 > crl) bad_d = 1'b1;
        for (e = 0; e < NEV; e = e + 1) begin
            ok[e] = |(pe[e] & vld & ~fd[e]);
            hold[e] = (st && |(pe[e] & ss)) || (rec_q && |(pe[e] & ssq));
            fire[e] = ok[e] && h_fr[e] && eqn[e];
            lt[e] = ok[e] && h_fr[e] && ltn[e];
            dl = h_ts[e] - tmd2[e]; dlm[e] = dl[31];
            adv[e] = fire[e] || (!ok[e] && !hold[e]);
            hts_r[32*e +: 32] = 32'd0; hep_r[21*e +: 21] = 21'd0; heu_r[10*e +: 10] = 10'd0; hat_r[2*e +: 2] = 2'd0;
            for (k2 = 0; k2 < NSLOT; k2 = k2 + 1) if (pe[e][k2]) begin
                hts_r[32*e +: 32] = hts_r[32*e +: 32] | ts[k2]; hep_r[21*e +: 21] = hep_r[21*e +: 21] | ep[k2];
                heu_r[10*e +: 10] = heu_r[10*e +: 10] | eu[k2]; hat_r[2*e +: 2] = hat_r[2*e +: 2] | eat[e][k2];
            end
        end
    end
    integer e4;
    always @(posedge ck) for (e4 = 0; e4 < NEV; e4 = e4 + 1) begin
        fd[e4] <= (fd[e4] | (fire[e4] ? pe[e4] : {NSLOT{1'b0}})) & ~(rec_q ? ssq : {NSLOT{1'b0}});   // no reset: cleared at the staged record, read only on valid entries
        h_ts[e4] <= hts_r[32*e4 +: 32]; h_ep[e4] <= hep_r[21*e4 +: 21]; h_eu[e4] <= heu_r[10*e4 +: 10]; h_at[e4] <= hat_r[2*e4 +: 2];
        tmd2[e4] <= tm1 + 32'd1 - {11'd0, eD[e4]};          // = tm - D + 1 on the next edge
        // head compares one edge ahead: h_ts == tm + 1 - D (fire on the next edge) / h_ts - (tm + 1 - D) < 0 (late);
        // used only while the head stays fresh across both edges (h_fr now and next), so the entry is the same
        eqn[e4] <= h_fr[e4] && h_ts[e4] == tmd2[e4];
        ltn[e4] <= h_fr[e4] && dlm[e4];
    end
    // outputs from the fired heads: on each endpoint the highest-numbered firing event wins (the former loop order)
    reg rtbad, m; reg [NEP*34-1:0] c_n, c_q; reg [NEP*11-1:0] rc_n, rc_q; reg col_w;
    reg [NEV-1:0] tx, rpl, sc, sr, lc, lr; integer e3, k3, p3;
    assign mu_c = c_q; assign mu_rc = rc_q;
    always @* begin
        rtbad = 1'b0;
        for (r = 0; r < NRT; r = r + 1) begin
            m = 1'b0;
            for (p = 0; p < NSLOT; p = p + 1)
                if (vld[p] && eu[p] == rt_q[32*r + 21 +: 10] && ep[p] == rt_q[32*r +: 21]) m = 1'b1;
            if (rt_q[32*r + 31] && !m) rtbad = 1'b1;
        end
        for (e3 = 0; e3 < NEV; e3 = e3 + 1) begin
            tx[e3] = fire[e3] && !ek[e3];
            rpl[e3] = fire[e3] && ek[e3] && (h_at[e3][1] || MUT == 4);
        end
        c_n = {NEP*34{1'b0}}; rc_n = {NEP*11{1'b0}}; col_w = 1'b0;
        for (p3 = 0; p3 < NEP; p3 = p3 + 1) begin
            for (e3 = 0; e3 < NEV; e3 = e3 + 1) begin sc[e3] = tx[e3] && eep[e3] == PI'(p3); sr[e3] = rpl[e3] && eep[e3] == PI'(p3); end
            for (e3 = 0; e3 < NEV; e3 = e3 + 1) begin
                lc[e3] = 1'b0; lr[e3] = 1'b0;
                for (k3 = e3 + 1; k3 < NEV; k3 = k3 + 1) begin lc[e3] = lc[e3] | sc[k3]; lr[e3] = lr[e3] | sr[k3]; end
                if (sc[e3] && !lc[e3])
                    c_n[34*p3 +: 34] = c_n[34*p3 +: 34] | {h_ep[e3], h_eu[e3], h_at[e3][1], (MUT == 3) ? 1'b0 : h_at[e3][0], 1'b1};
                if (sr[e3] && !lr[e3]) rc_n[11*p3 +: 11] = rc_n[11*p3 +: 11] | {h_eu[e3], 1'b1};
                if ((sc[e3] && lc[e3]) || (sr[e3] && lr[e3])) col_w = 1'b1;
            end
        end
    end
    wire wv = mw_q[25];
    wire idle = !armed && !(|vld);
    integer k4;
    // event-row config + entry payload (no reset: written before arming / at the staged record that sets vld)
    always @(posedge ck) begin
        for (k4 = 0; k4 < NSLOT; k4 = k4 + 1) if (rec_q && ssq[k4]) begin eu[k4] <= suq; ep[k4] <= spq; ts[k4] <= tsq; end
        if (wv && idle)
            case (mw_q[22:21])
                2'd0: begin esel <= mw_q[EI-1:0]; ek[mw_q[EI-1:0]] <= mw_q[8]; eep[mw_q[EI-1:0]] <= mw_q[9 +: PI]; end
                2'd1: eD[esel] <= mw_q[20:0];
                2'd2: eat[esel][mw_q[SI-1:0]] <= mw_q[11:10];
                default: ;
            endcase
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin
            tm <= 32'd0; tm1 <= 32'd1; armed <= 1'b0; ph <= 24'd0; sl <= OH0; rp <= OH0; vld <= {NSLOT{1'b0}};
            cs <= 24'd0; crl <= 24'd0; crm <= 24'hffffff; t_wf <= 2'd0; gn <= {SJ{1'b0}}; gx <= OH0; gm <= {NSLOT{1'b0}};
            lw <= SI'(NSLOT - 1); lm <= {1'b1, {(NSLOT-1){1'b0}}}; cg <= 24'd0; c_q <= {NEP*34{1'b0}}; rc_q <= {NEP*11{1'b0}};
            rec_q <= 1'b0; h_rfr <= 1'b0; h_fr <= {NEV{1'b0}};
            for (e = 0; e < NEV; e = e + 1) pe[e] <= OH0;
        end else begin
            tm <= tm1; tm1 <= tm1 + 32'd1;
            lm <= {NSLOT{1'b0}}; lm[lw] <= 1'b1;
            if (mc_q[25] && idle) begin if (mc_q[24]) begin crl <= mc_q[23:0]; crm <= mc_q[23:0] - 24'd1; end else begin
                    if (gn != SJ'(NSLOT)) begin
                        gn <= gn + 1'b1;
                        gm <= {NSLOT{1'b0}}; gm[gn[SI-1:0]] <= 1'b1;                   // one-hot of the last gap index
                        if (gn == 0 || mc_q[23:0] < cs) cs <= mc_q[23:0];
                        lw <= (gn == 0) ? SI'(NSLOT - 1) : gn[SI-1:0];             // nw = n for n >= 2
                    end
                end end
            if (armed) begin
                if (ph == cg) begin ph <= 24'd0; sl <= rot(sl, lm); cg <= ng; gx <= gxn; end else ph <= ph + 24'd1;
            end
            if (st && !armed) begin
                if (bad_d) t_wf[1] <= 1'b1;
                if (!hcfg_bad) begin armed <= 1'b1; ph <= 24'd1; cg <= ng; gx <= gxn; end
            end
            rec_q <= rec;
            if (radv) rp <= rot(rp, lm);
            h_rfr <= !radv && !(rec_q && |(rp & ssq));
            vld <= (vld & ~(due ? rp : {NSLOT{1'b0}})) | (rec_q ? ssq : {NSLOT{1'b0}});
            c_q <= c_n; rc_q <= rc_n;
            for (e = 0; e < NEV; e = e + 1) begin
                if (adv[e]) pe[e] <= rot(pe[e], lm);
                h_fr[e] <= !adv[e] && !(rec_q && |(pe[e] & ssq));
            end
            if (rtbad || (|lt)) t_wf[0] <= 1'b1;
            if ((wv && (!idle || mw_q[22:21] == 2'd3)) || col_w) t_wf[1] <= 1'b1;
        end
endmodule

// ---------------------------------------------------------------- MU-S81-2/DIE: parameter-free p4l die master (MU dies)
// dsdv_seq_host_mux = dsdv_seq_host_mu NSLOT 47 (the CLOSED dsdv_mu_hslot leaf, NSLOT 47 MUT 0, unchanged) + dsdv_mu_hwin
// (8 window events, 4 end slices: mu_c / mu_rc to s_7N / s_7S / s_0N / s_0S; RX tags back from the 2 N-tier end slices
// s_7N / s_0N -- the S-tier tags carry the same {user, pos} and are not returned: column-4 W lane margin, MU-S81/DIE).
// Boot config rides the host stream as class-0 CSRs decoded from the f_host pin the master already has (0 die wires):
// 0x15 = hslot word (S / RL; also snooped by hwin), 0x16 = window word.  Neither index is intercepted by sh_lk
// (0x10/0x11/0x13/0x14); the ingest ignores class-0 indices other than 0/1/2, so seq_host behaviour is unchanged.
// t_mf = hslot faults with hwin's folded in ([2] |= RX tag / late event, [3] |= window config); it leaves like the
// other block fault outputs (die status fold owed with them).
module dsdv_seq_host_mux (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [3:0]    t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n
);
    // CSR decode (the f_host word {h_cls 2, h_d 512, h_v}; h_d[7:0] index, h_d[57:32] value) into one flop each
    wire csr = f_host[0] && f_host[514:513] == 2'd0;
    reg [25:0] mc, mw;
    always @(posedge ck) begin
        mc <= (csr && f_host[8:1] == 8'h15) ? f_host[58:33] : 26'd0;
        mw <= (csr && f_host[8:1] == 8'h16) ? f_host[58:33] : 26'd0;
    end
    wire [3:0] hmf; wire [1:0] wf;
    dsdv_seq_host_mu #(.NSLOT(47)) u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks),
        .t_kd(t_kd), .f_mc(mc), .t_mf(hmf), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w),
        .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v),
        .cw_a(cw_a), .cw_d(cw_d));
    dsdv_mu_hwin #(.NSLOT(47), .NEV(8), .NEP(4), .NRT(2)) u_win (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_mc(mc), .f_mw(mw),
        .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0n, mu_rt_7n}), .t_wf(wf));
    assign t_mf = {hmf[3] | wf[1], hmf[2] | wf[0], hmf[1:0]};
endmodule
