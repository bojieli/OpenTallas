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
// ---------------------------------------------------------------------------------------------------------------------
// LA (HARD-S81-SERDES-1 2026-11-13, default 0 = unchanged; 1 under `define OT_S81_SH_WIN_LA): two-candidate LOOKAHEAD of
// the pointer compares, 0 cycles, same outputs on every edge for every input.  seqhost__t1 attempt_9 placement: pe[e] ->
// 47:1 x 32-b ts mux -> + eD -> == tm -> fire -> pointer / fd / c_q was 24 cells 777 ps (TT -586, 606 endpoints), rp -> due
// the same (-457), and lw -> nw -> hcfg_bad -> rec -> 47 x 63 table write enables 3488 endpoints (-239).
//   A pointer only stays or steps to nxt(p).  One edge early, for BOTH candidates j, the registered key
//   keyE[e] = tm + 1 - eD[e] turns "ts[j] + eD == tm" of the next edge into ts[j] == keyE[e] (no adder after the mux); the
//   step / stay bit of that edge (registered) picks one of the two registered results at the edge of use.  An entry written by rec this edge (ts <= tm)
//   is not in the table yet: its result is the constant eD == 1 (lt: eD == 0; due: crl == 2).  eD / crl only change
//   while no entry is valid, and the first entry after such a write is that rec entry, so the keys use the next-state eD / crl.
//   hcfg_bad / bad_d are registered from the NEXT-STATE configuration (same value on every edge).
// LA 2 / 3 (bench mutants, must FAIL the lock-step): 2 = no rec bypass, 3 = event key one edge late.
module dsdv_mu_hwin #(parameter integer NSLOT = 47, parameter integer NEV = 8, parameter integer NEP = 4,
                      parameter integer NRT = 2, parameter integer MUT = 0,
`ifdef OT_S81_SH_WIN_LA
                      parameter integer LA = 1
`else
                      parameter integer LA = 0
`endif
                      ) (
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
    // ---- start table: the same record rule / slot timer / due edge as dsdv_mu_hslot
    reg [23:0] cs, crl; reg [31:0] tm; reg armed; reg [23:0] ph; reg [SI-1:0] sl, rp;
    // MU-S81-2/SEQ (10-19): slot gap table, the same as dsdv_mu_hslot's (same f_mc words, same walk).  The record calendar (dv_mu_calendar --phase-q 4) has NON-uniform slots
    // (AR 46: shift_k = 4 floor(k (P/4) / 46) -> gaps 21,312 / 21,316; MTP 10 + filler: 10 x 124,524 then 58,160), so
    // one period S cannot hold it (user 3's start lands 4 edges off a uniform 21,312 grid -> t_mf[1] on the real unit).
    // Each sel-0 word APPENDS one slot gap g[k] (cycles from slot k's start edge to slot k+1's); the slot timer walks
    // g[0..n-1] cyclically (n = words written), and the slot entries wrap at nw = n (n >= 2) so the entry index IS the
    // calendar slot.  One sel-0 word (n = 1) = the former uniform period S with nw = NSLOT: the previous behaviour.
    // cs = the smallest gap.
    reg [23:0] gt [0:NSLOT-1]; reg [SI:0] gn; reg [SI-1:0] gx, lw; reg [23:0] cg, ng;
    reg [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1]; reg [31:0] ts [0:NSLOT-1];
    wire [SI-1:0] ss = armed ? sl : {SI{1'b0}};
    wire on_cal = !armed || ph == 24'd0;
    reg udup; integer i;
    always @* begin udup = 1'b0; for (i = 0; i < NSLOT; i = i + 1) if (vld[i] && eu[i] == su) udup = 1'b1; end
    wire col = vld[ss];
    wire [23:0] nw = {{(23-SI){1'b0}}, lw} + 24'd1;     // slot entries in use (= calendar slots per period)
    wire hcfg_bad = gn == 0 || cs < nw || crl <= nw;                     // hslot's own arming rule
    wire hcfg_bad_u, bad_d_u, due_u; wire [NEV-1:0] fire_u, lt_u;        // the values used below (LA: lookahead forms)
    wire [20:0] pl_ep [0:NEV-1]; wire [9:0] pl_eu [0:NEV-1]; wire [1:0] pl_at [0:NEV-1];   // payload under pe (LA: registered)
    wire rec = st && on_cal && !col && !udup && !(!armed && hcfg_bad_u);
    wire due = vld[rp] && ts[rp] + {8'd0, crl} - 32'd1 == tm;             // hslot's return edge: the entry retires
    function automatic [SI-1:0] nxt(input [SI-1:0] p);
        nxt = (p == lw) ? {SI{1'b0}} : p + 1'b1;
    endfunction
    wire [SI-1:0] gxn = (MUT == 5 || {1'b0, gx} == gn - 1'b1) ? {SI{1'b0}} : gx + 1'b1;   // MUT 5: gap table index stuck at 0
    always @(posedge ck) ng <= gt[gx] - 24'd1;          // next slot's gap, prefetched (gx = the slot after the current one)
    always @(posedge ck) if (mc_q[25] && !mc_q[24] && !armed && !(|vld) && gn != SJ'(NSLOT)) gt[gn[SI-1:0]] <= mc_q[23:0];
    // ---- event rows
    reg [NEV-1:0] ek; reg [PI-1:0] eep [0:NEV-1]; reg [20:0] eD [0:NEV-1]; reg [EI-1:0] esel;
    reg [1:0] eat [0:NEV-1][0:NSLOT-1];                  // {land / replay-en, ab} per event and calendar slot
    reg [NSLOT-1:0] fd [0:NEV-1];                         // fired flags
    reg [SI-1:0] pe [0:NEV-1];
    integer e, p;
    reg bad_d; reg [NEV-1:0] fire, lt;
    always @* begin
        bad_d = cs <= nw + 24'd1;
        for (e = 0; e < NEV; e = e + 1)
            if ({3'd0, eD[e]} < nw + 24'd2 || {3'd0, eD[e]} + 24'd2 > crl) bad_d = 1'b1;
        for (e = 0; e < NEV; e = e + 1) begin
            fire[e] = vld[pe[e]] && !fd[e][pe[e]] && ts[pe[e]] + {11'd0, eD[e]} == tm;
            lt[e] = vld[pe[e]] && !fd[e][pe[e]] && (ts[pe[e]] + {11'd0, eD[e]} - tm) > 32'h7fffffff;
        end
    end
    reg rtbad, m; reg [NEP*34-1:0] c_n, c_q; reg [NEP*11-1:0] rc_n, rc_q; reg col_w;
    assign mu_c = c_q; assign mu_rc = rc_q;
    always @* begin
        rtbad = 1'b0;
        for (r = 0; r < NRT; r = r + 1) begin
            m = 1'b0;
            for (p = 0; p < NSLOT; p = p + 1)
                if (vld[p] && eu[p] == rt_q[32*r + 21 +: 10] && ep[p] == rt_q[32*r +: 21]) m = 1'b1;
            if (rt_q[32*r + 31] && !m) rtbad = 1'b1;
        end
        c_n = {NEP*34{1'b0}}; rc_n = {NEP*11{1'b0}}; col_w = 1'b0;
        for (e = 0; e < NEV; e = e + 1) if (fire_u[e]) begin
            if (!ek[e]) begin
                if (c_n[34*eep[e]]) col_w = 1'b1;
                c_n[34*eep[e] +: 34] = {pl_ep[e], pl_eu[e], pl_at[e][1], (MUT == 3) ? 1'b0 : pl_at[e][0], 1'b1};
            end else if (pl_at[e][1] || MUT == 4) begin
                if (rc_n[11*eep[e]]) col_w = 1'b1;
                rc_n[11*eep[e] +: 11] = {pl_eu[e], 1'b1};
            end
        end
    end
    wire wv = mw_q[25];
    wire idle = !armed && !(|vld);
    generate if (LA != 0) begin : g_la
        // ---- next-state configuration (the same update rules as the registers below)
        wire        cfg_c = mc_q[25] && idle;
        wire        crl_w = cfg_c && mc_q[24];
        wire        gap_w = cfg_c && !mc_q[24] && gn != SJ'(NSLOT);
        wire [23:0] mcd   = mc_q[23:0];
        wire [23:0] nw_n  = gap_w ? ((gn == 0) ? 24'(NSLOT) : {{(24-SI){1'b0}}, gn[SI-1:0]} + 24'd1) : nw;
        wire        cs_sel = gap_w && (gn == 0 || mcd < cs);            // cs takes the word
        wire        hcfg_n = (gap_w ? 1'b0 : gn == 0) || (cs_sel ? mcd < nw_n : cs < nw_n) || (crl_w ? mcd <= nw_n : crl <= nw_n);
        wire        ed_w  = wv && idle && mw_q[22:21] == 2'd1;
        wire [23:0] crl_n = crl_w ? mcd : crl;
        reg [20:0] eDn [0:NEV-1]; reg bad_n; integer k;
        always @* begin
            bad_n = cs_sel ? mcd <= nw_n + 24'd1 : cs <= nw_n + 24'd1;
            for (k = 0; k < NEV; k = k + 1) begin
                eDn[k] = (ed_w && esel == EI'(k)) ? mw_q[20:0] : eD[k];
                if ({3'd0, eDn[k]} < nw_n + 24'd2 || (crl_w ? {3'd0, eDn[k]} + 24'd2 > mcd : {3'd0, eDn[k]} + 24'd2 > crl)) bad_n = 1'b1;
            end
        end
        // ---- keys and the two-candidate compares.  Both candidate results are registered; the step / stay bit (adv_q)
        //      and the rec bypass (rec_q, ss_q, constants c1_q / c0_q / cr2_q) select at the edge of use, so the start
        //      cone (udup -> rec) reaches these flops only through the 1-bit adv / rec registers.
        reg hcfg_q, badd_q; reg [31:0] keyE [0:NEV-1]; reg [31:0] keyE_d [0:NEV-1]; reg [31:0] keyR;
        reg [NEV-1:0] eA_q, eB_q, lA_q, lB_q, adv_q, c1_q, c0_q; reg dA_q, dB_q, advr_q, cr2_q, rec_q; reg [SI-1:0] ss_q;
        reg [NEV-1:0] ea_n, eb_n, la_n, lb_n, adv; reg dra_n, drb_n, advr;
        // pointer copies (kept registers, same next state as pe / rp; R-RTL-2): pe / rp drove every 47:1 mux of the table
        // (668 ps of fanout buffers on the first LA placement).  *_ta = the pointer, *_tb = nxt(pointer) under the
        // next-state lw, for the two candidate ts muxes; pe_d for the payload muxes (ep / eu / eat).
        // The payload {ep, eu, eat} of both candidates is registered the same way (pyA_q / pyB_q; rec bypass = the start
        // word of that edge ksu_q / ksp_q and the slot's attribute atS_q; eat uses its next-state value), from the copies
        // pe_pa / pe_pb, so no table mux sits behind pe in the firing edge.
        (* keep *) reg [NEV*SI-1:0] pe_ta, pe_tb, pe_pa, pe_pb; (* keep *) reg [SI-1:0] rp_ta, rp_tb;
        reg [NEV*33-1:0] pyA_q, pyB_q; reg [NEV*2-1:0] atS_q; reg [9:0] ksu_q; reg [20:0] ksp_q;
        wire at_w = wv && idle && mw_q[22:21] == 2'd2;
        reg [NEV*33-1:0] pya_n, pyb_n; reg [NEV*2-1:0] ats_n; reg [SI-1:0] ka, kb; integer y;
        always @* begin
            for (y = 0; y < NEV; y = y + 1) begin
                ka = pe_pa[y*SI +: SI]; kb = pe_pb[y*SI +: SI];
                pya_n[y*33 +: 33] = {ep[ka], eu[ka], (at_w && esel == EI'(y) && mw_q[SI-1:0] == ka) ? mw_q[11:10] : eat[y][ka]};
                pyb_n[y*33 +: 33] = {ep[kb], eu[kb], (at_w && esel == EI'(y) && mw_q[SI-1:0] == kb) ? mw_q[11:10] : eat[y][kb]};
                ats_n[y*2 +: 2]   = (at_w && esel == EI'(y) && mw_q[SI-1:0] == ss) ? mw_q[11:10] : eat[y][ss];
            end
        end
        always @(posedge ck) begin pyA_q <= pya_n; pyB_q <= pyb_n; atS_q <= ats_n; ksu_q <= su; ksp_q <= sp; end
        wire [SI-1:0] lw_n = gap_w ? ((gn == 0) ? SI'(NSLOT - 1) : gn[SI-1:0]) : lw;
        function automatic [SI-1:0] nxtn(input [SI-1:0] p);
            nxtn = (p == lw_n) ? {SI{1'b0}} : p + 1'b1;
        endfunction
        reg [SI-1:0] ja, jb; reg [31:0] ta, tb, da, db, ky;
        integer q;
        always @* begin
            for (q = 0; q < NEV; q = q + 1) begin
                ja = pe_ta[q*SI +: SI]; jb = pe_tb[q*SI +: SI]; ta = ts[ja]; tb = ts[jb]; ky = (LA == 3) ? keyE_d[q] : keyE[q];
                da = ta - ky; db = tb - ky;
                ea_n[q] = ta == ky; la_n[q] = da[31]; eb_n[q] = tb == ky; lb_n[q] = db[31];
                adv[q] = fire_u[q] || ((!vld[pe[q]] || fd[q][pe[q]]) && !(rec && ss == pe[q]));
            end
            dra_n = ts[rp_ta] == keyR; drb_n = ts[rp_tb] == keyR;
            advr = due_u || (!vld[rp] && !(rec && ss == rp));
        end
        integer w;
        always @(posedge ck or negedge rn)
            if (!rn) begin
                hcfg_q <= 1'b1; badd_q <= 1'b1; keyR <= 32'd0; rec_q <= 1'b0; ss_q <= {SI{1'b0}};
                eA_q <= {NEV{1'b0}}; eB_q <= {NEV{1'b0}}; lA_q <= {NEV{1'b0}}; lB_q <= {NEV{1'b0}}; adv_q <= {NEV{1'b0}};
                c1_q <= {NEV{1'b0}}; c0_q <= {NEV{1'b0}}; dA_q <= 1'b0; dB_q <= 1'b0; advr_q <= 1'b0; cr2_q <= 1'b0;
                for (w = 0; w < NEV; w = w + 1) begin
                    keyE[w] <= 32'd0; keyE_d[w] <= 32'd0;
                    pe_ta[w*SI +: SI] <= {SI{1'b0}}; pe_pa[w*SI +: SI] <= {SI{1'b0}};
                    pe_tb[w*SI +: SI] <= SI'(1); pe_pb[w*SI +: SI] <= SI'(1);                // nxt(0) at reset (lw = NSLOT - 1 >= 1)
                end
                rp_ta <= {SI{1'b0}}; rp_tb <= SI'(1);
            end else begin
                rp_ta <= advr ? nxt(rp) : rp; rp_tb <= advr ? nxtn(nxt(rp)) : nxtn(rp);
                hcfg_q <= hcfg_n; badd_q <= bad_n;
                eA_q <= ea_n; eB_q <= eb_n; lA_q <= la_n; lB_q <= lb_n; adv_q <= adv; dA_q <= dra_n; dB_q <= drb_n; advr_q <= advr;
                rec_q <= (LA != 2) && rec; ss_q <= ss; cr2_q <= crl_n == 24'd2;
                keyR <= tm + 32'd3 - {8'd0, crl_n};
                for (w = 0; w < NEV; w = w + 1) begin
                    keyE[w] <= tm + 32'd2 - {11'd0, eDn[w]}; keyE_d[w] <= keyE[w];
                    c1_q[w] <= eDn[w] == 21'd1; c0_q[w] <= eDn[w] == 21'd0;
                    pe_ta[w*SI +: SI] <= adv[w] ? nxt(pe[w]) : pe[w]; pe_pa[w*SI +: SI] <= adv[w] ? nxt(pe[w]) : pe[w];
                    pe_tb[w*SI +: SI] <= adv[w] ? nxtn(nxt(pe[w])) : nxtn(pe[w]); pe_pb[w*SI +: SI] <= adv[w] ? nxtn(nxt(pe[w])) : nxtn(pe[w]);
                end
            end
        genvar ge;
        for (ge = 0; ge < NEV; ge = ge + 1) begin : g_f
            wire bp = rec_q && ss_q == pe[ge];                       // the entry under the pointer was written last edge
            wire on = vld[pe[ge]] && !fd[ge][pe[ge]];
            assign fire_u[ge] = on && (bp ? c1_q[ge] : adv_q[ge] ? eB_q[ge] : eA_q[ge]);
            assign lt_u[ge]   = on && (bp ? c0_q[ge] : adv_q[ge] ? lB_q[ge] : lA_q[ge]);
            assign {pl_ep[ge], pl_eu[ge], pl_at[ge]} = bp ? {ksp_q, ksu_q, atS_q[ge*2 +: 2]}
                                                          : adv_q[ge] ? pyB_q[ge*33 +: 33] : pyA_q[ge*33 +: 33];
        end
        assign due_u = vld[rp] && ((rec_q && ss_q == rp) ? cr2_q : advr_q ? dB_q : dA_q);
        assign hcfg_bad_u = hcfg_q; assign bad_d_u = badd_q;
    end else begin : g_nola
        assign fire_u = fire; assign lt_u = lt; assign due_u = due; assign hcfg_bad_u = hcfg_bad; assign bad_d_u = bad_d;
        genvar gn0;
        for (gn0 = 0; gn0 < NEV; gn0 = gn0 + 1) begin : g_pd
            assign pl_ep[gn0] = ep[pe[gn0]]; assign pl_eu[gn0] = eu[pe[gn0]]; assign pl_at[gn0] = eat[gn0][pe[gn0]];
        end
    end endgenerate
    // event-row config + entry payload (no reset: written before arming / at the start that sets vld)
    always @(posedge ck) begin
        if (rec) begin eu[ss] <= su; ep[ss] <= sp; ts[ss] <= tm; end
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
            tm <= 32'd0; armed <= 1'b0; ph <= 24'd0; sl <= {SI{1'b0}}; rp <= {SI{1'b0}}; vld <= {NSLOT{1'b0}};
            cs <= 24'd0; crl <= 24'd0; t_wf <= 2'd0; gn <= {SJ{1'b0}}; gx <= {SI{1'b0}}; lw <= SI'(NSLOT - 1); cg <= 24'd0; c_q <= {NEP*34{1'b0}}; rc_q <= {NEP*11{1'b0}};
            for (e = 0; e < NEV; e = e + 1) begin pe[e] <= {SI{1'b0}}; fd[e] <= {NSLOT{1'b0}}; end
        end else begin
            tm <= tm + 32'd1;
            if (mc_q[25] && idle) begin if (mc_q[24]) crl <= mc_q[23:0]; else begin
                    if (gn != SJ'(NSLOT)) begin
                        gn <= gn + 1'b1;
                        if (gn == 0 || mc_q[23:0] < cs) cs <= mc_q[23:0];
                        lw <= (gn == 0) ? SI'(NSLOT - 1) : gn[SI-1:0];             // nw = n for n >= 2
                    end
                end end
            if (armed) begin
                if (ph == cg) begin ph <= 24'd0; sl <= nxt(sl); cg <= ng; gx <= gxn; end else ph <= ph + 24'd1;
            end
            if (st && !armed) begin
                if (bad_d_u) t_wf[1] <= 1'b1;
                if (!hcfg_bad_u) begin armed <= 1'b1; ph <= 24'd1; cg <= ng; gx <= gxn; end
            end
            if (due_u) begin vld[rp] <= 1'b0; rp <= nxt(rp); end
            else if (!vld[rp] && !(rec && ss == rp)) rp <= nxt(rp);
            if (rec) vld[ss] <= 1'b1;
            c_q <= c_n; rc_q <= rc_n;
            for (e = 0; e < NEV; e = e + 1) begin
                if (rec) fd[e][ss] <= 1'b0;
                if (fire_u[e]) begin fd[e][pe[e]] <= 1'b1; pe[e] <= nxt(pe[e]); end
                else if ((!vld[pe[e]] || fd[e][pe[e]]) && !(rec && ss == pe[e])) pe[e] <= nxt(pe[e]);
            end
            if (rtbad || (|lt_u)) t_wf[0] <= 1'b1;
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
module dsdv_seq_host_mux #(
    // S81/H23 (10-24, COORD H3): 1 = the on-die SEL_IDS relay (bk_sel's top-k index words -> svc entries, dsdv_sh_selr in
    // L0); the die master carries it.  Cost: s_hw_w / s_hw_e leave one edge later (host-write path + 1).  0 = as before.
    parameter integer SELR = 1,
    parameter integer STATIC_KS6 = 0,
    parameter integer STATIC_KS_SPAN = 1259408,
    parameter [31:0] STATIC_KS_GRAPH_TAG = 32'h218d375d
) (
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
    wire [52:0] issue_ks;
    wire [514:0] issue_host;
    wire [3:0] ks_fault;
    generate if (STATIC_KS6 != 0) begin : g_static_ks6
        wire [52:0] timed_ks;
        wire selected, armed, done;
        wire control_csr = csr && (f_host[8:1] == 8'h17 ||
                                  f_host[8:1] == 8'h18 || f_host[8:1] == 8'h19);
        dsdv_static_ks6 #(.SPAN(STATIC_KS_SPAN), .GRAPH_TAG(STATIC_KS_GRAPH_TAG)) u_static (
            .ck(ck), .rst_n(rst_n), .f_host(f_host), .f_ks(f_ks),
            .upstream_fault(|hmf), .timed_ks(timed_ks), .selected(selected),
            .armed(armed), .done(done), .fault(ks_fault));
        // ARM consumes no descriptor. Real descriptors subsequently enter
        // u_static, and only its immutable-date output reaches BOTH issuers.
        assign issue_ks = (selected || (csr && f_host[8:1] == 8'h17)) ? timed_ks : f_ks;
        assign issue_host = control_csr ? 515'd0 : f_host;
    end else begin : g_external_ks
        assign issue_ks = f_ks;
        assign issue_host = f_host;
        assign ks_fault = 4'd0;
    end endgenerate
    dsdv_seq_host_mu #(.NSLOT(47), .SELR(SELR)) u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(issue_host), .t_host(t_host), .f_lf(f_lf), .f_ks(issue_ks),
        .t_kd(t_kd), .f_mc(mc), .t_mf(hmf), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w),
        .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v),
        .cw_a(cw_a), .cw_d(cw_d));
    dsdv_mu_hwin #(.NSLOT(47), .NEV(8), .NEP(4), .NRT(2)) u_win (.ck(ck), .rst_n(rst_n), .f_ks(issue_ks), .f_mc(mc), .f_mw(mw),
        .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0n, mu_rt_7n}), .t_wf(wf));
    assign t_mf = {hmf[3] | wf[1] | (|ks_fault), hmf[2] | wf[0], hmf[1:0]};
endmodule
