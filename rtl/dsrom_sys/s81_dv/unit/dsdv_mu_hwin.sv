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
// ---------------------------------------------------------------------------------------------------------------------
// FABLE-FIX-S81-SEQHOST (2026-11-19, r713 close by construction): 0-cycle restructure, same ports, same outputs on every
// edge.  seqhost__t1 failed TT setup by -853 ps on 4,895 ends, all here: rp / pe[e] (binary) selected a 47:1 x 32-bit
// mux of ts[], then a 32-bit add and a 32-bit compare with tm, then the 8-deep event priority chain and the pointer /
// vld / ep / eu write decode (27 gate levels, 21..32 fanout buffers).  Now:
//   * no ts[] / tm: each entry owns an age counter and the three compares as FLAGS computed one edge early from flops
//     (dsdv_mu_hwin_age: "ts + D == tm", "ts + D - tm negative", "ts + RL - 1 == tm" for every event row);
//   * rp / pe[e] / the record slot have one-hot shadows (rp1h / pe1h / ss1h): every select is one AND-OR level tree;
//   * the event -> endpoint merge is a parallel highest-row select per endpoint (same last-row-wins rule);
//   * the payload / fired-flag / age write of an entry uses st & slot & !vld (the payload of an entry that is not valid
//     is never read), so the full record condition (user duplicate compare) only drives vld and the pointer holds;
//   * the arming checks compare the low SJ+1 bits (nw <= NSLOT).
// Out-of-range pointer values (possible while idle after lw shrinks) read "not valid" and step on, as in the 2-state
// reference.  Proof: unit/test/run_mu_hwin_eq.sh (lockstep against the 11-18 source kept as test/ref, age-cell
// induction, bounded SAT miter).
// ---------------------------------------------------------------------------------------------------------------------
// One table entry's age and its precomputed compares.  With a = (tm - ts) mod 2^32 of the former source (the entry was
// written at tm = ts): b = a + 1; mf[e] = (a == D[e]); lf[e] = bit 31 of (D[e] - a); df = (a == RL - 1).  The flags are
// registered: at an entry write the next age is 1; otherwise the next age is b.  D / RL only change while no entry is
// valid; the *_n inputs carry a same-edge config write to an entry written on that edge.
// keep_hierarchy (both modules): the kit synthesis is flat and ABC recovers area on every cone up to the deepest path
// of the netlist it is given (zero wire), so inside the flat seqhost netlist it turned these trees back into chains
// (the 32-bit lookahead incrementer came back as a 16-stage OR chain, 640 ps).  As kept modules their depth is bounded
// by their own deepest cone.
(* keep_hierarchy *)
module dsdv_mu_hwin_age #(parameter integer NEV = 8) (
    input  wire              ck,
    input  wire              wr,              // the entry is (re)written on this edge
    input  wire [NEV*21-1:0] eD,              // event offsets D
    input  wire [NEV-1:0]    e1n, e0n,        // D == 1 / D == 0 after this edge
    input  wire [31:0]       crlm1,           // RL - 1 (mod 2^32)
    input  wire              c2n,             // RL == 2 after this edge
    output wire [NEV-1:0]    mf,
    output wire [NEV-1:0]    lf,
    output wire              df
);
    reg [31:0] b; reg [NEV-1:0] lm, lq; reg hz, hc, dq; integer e;
    // x + 1 with a 4-bit group lookahead (7 gate levels; a ripple here would be the deepest path of the block)
    function automatic [31:0] inc32(input [31:0] x);
        reg [7:0] g; integer k, i;
        begin
            for (k = 0; k < 8; k = k + 1) g[k] = &x[4*k +: 4];
            for (i = 0; i < 32; i = i + 1)
                inc32[i] = x[i] ^ ((&(g | (8'hff << (i / 4)))) & (&(x[4*(i/4) +: 4] | (4'hf << (i % 4)))));
        end
    endfunction
    always @(posedge ck) begin
        b  <= wr ? 32'd2 : inc32(b);
        hz <= wr ? 1'b1 : b[31:21] == 11'd0;
        hc <= wr ? 1'b0 : b[31:21] == 11'h400;
        dq <= wr ? c2n : b == crlm1;
        for (e = 0; e < NEV; e = e + 1) begin
            lm[e] <= wr ? e1n[e] : b[20:0] == eD[21*e +: 21];
            lq[e] <= wr ? e0n[e] : ((lm[e] & hz) | (lq[e] & ~(lm[e] & hc)));
        end
    end
    assign mf = lm & {NEV{hz}}; assign lf = lq; assign df = dq;
endmodule

(* keep_hierarchy *)
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
    genvar ge, gi, gk, gb;
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
    reg [23:0] cs, crl; reg [31:0] crlm1; reg armed; reg [23:0] ph; reg [SI-1:0] sl, rp; reg [NSLOT-1:0] ss1h, rp1h;
    // MU-S81-2/SEQ (10-19): slot gap table, the same as dsdv_mu_hslot's (same f_mc words, same walk).  The record calendar (dv_mu_calendar --phase-q 4) has NON-uniform slots
    // (AR 46: shift_k = 4 floor(k (P/4) / 46) -> gaps 21,312 / 21,316; MTP 10 + filler: 10 x 124,524 then 58,160), so
    // one period S cannot hold it (user 3's start lands 4 edges off a uniform 21,312 grid -> t_mf[1] on the real unit).
    // Each sel-0 word APPENDS one slot gap g[k] (cycles from slot k's start edge to slot k+1's); the slot timer walks
    // g[0..n-1] cyclically (n = words written), and the slot entries wrap at nw = n (n >= 2) so the entry index IS the
    // calendar slot.  One sel-0 word (n = 1) = the former uniform period S with nw = NSLOT: the previous behaviour.
    // cs = the smallest gap.
    reg [23:0] gt [0:NSLOT-1]; reg [SI:0] gn; reg [SI-1:0] gx, lw; reg [23:0] cg, ng;
    reg [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1];
    function automatic [SI-1:0] nxt(input [SI-1:0] p);
        nxt = (p == lw) ? {SI{1'b0}} : p + 1'b1;
    endfunction
    // 24 / 32-bit x + 1, x - 1 and a < b with group lookahead (ripple forms of these were among the deepest paths)
    function automatic [31:0] inc32(input [31:0] x);
        reg [7:0] g; integer k, i;
        begin
            for (k = 0; k < 8; k = k + 1) g[k] = &x[4*k +: 4];
            for (i = 0; i < 32; i = i + 1)
                inc32[i] = x[i] ^ ((&(g | (8'hff << (i / 4)))) & (&(x[4*(i/4) +: 4] | (4'hf << (i % 4)))));
        end
    endfunction
    function automatic [31:0] dec32(input [31:0] x); dec32 = ~inc32(~x); endfunction
    function automatic [23:0] inc24(input [23:0] x); reg [31:0] t; begin t = inc32({8'd0, x}); inc24 = t[23:0]; end endfunction
    function automatic [23:0] dec24(input [23:0] x); reg [31:0] t; begin t = dec32({8'hff, x}); dec24 = t[23:0]; end endfunction
    function automatic lt24(input [23:0] a, input [23:0] b);
        reg [5:0] l, q; integer k;
        begin
            lt24 = 1'b0;
            for (k = 0; k < 6; k = k + 1) begin l[k] = a[4*k +: 4] < b[4*k +: 4]; q[k] = a[4*k +: 4] == b[4*k +: 4]; end
            for (k = 0; k < 6; k = k + 1) lt24 = lt24 | (l[k] & (&(q | ~(6'h3e << k))));
        end
    endfunction
    function automatic [NSLOT-1:0] dec(input [SI-1:0] p);       // one-hot of p; 0 when p is not an entry
        integer k;
        begin dec = {NSLOT{1'b0}}; for (k = 0; k < NSLOT; k = k + 1) if (p == SI'(k)) dec[k] = 1'b1; end
    endfunction
    wire on_cal = !armed || ph == 24'd0;
    wire [NSLOT-1:0] udv;
    generate for (gi = 0; gi < NSLOT; gi = gi + 1) begin : g_ud assign udv[gi] = vld[gi] && eu[gi] == su; end endgenerate
    wire udup = |udv;
    wire col = |(ss1h & vld);                            // ss1h = one-hot of (armed ? sl : 0)
    reg [SJ-1:0] nwj; reg [SJ:0] nw1, nw2;               // nw = lw + 1 (slot entries in use = calendar slots per period, <= NSLOT), nw + 1, nw + 2: written with lw
    wire hcfg_bad = gn == 0 || (cs[23:SJ] == 0 && cs[SJ-1:0] < nwj) || (crl[23:SJ] == 0 && crl[SJ-1:0] <= nwj);   // hslot's own arming rule: cs < nw || crl <= nw
    wire rec = st && on_cal && !col && !udup && !(!armed && hcfg_bad);
    wire [NSLOT-1:0] wr = {NSLOT{st}} & ss1h & ~vld;     // payload / age / fired-flag write (superset of rec: an entry that stays not valid is never read)
    wire [NSLOT-1:0] dfv;
    wire due = |(rp1h & vld & dfv);                      // hslot's return edge: the entry retires
    wire rpv = |(rp1h & vld);
    wire [SI-1:0] gxn = (MUT == 5 || {1'b0, gx} == gn - 1'b1) ? {SI{1'b0}} : gx + 1'b1;   // MUT 5: gap table index stuck at 0
    always @(posedge ck) ng <= dec24(gt[gx]);          // next slot's gap, prefetched (gx = the slot after the current one)
    always @(posedge ck) if (mc_q[25] && !mc_q[24] && !armed && !(|vld) && gn != SJ'(NSLOT)) gt[gn[SI-1:0]] <= mc_q[23:0];
    // ---- event rows
    reg [NEV-1:0] ek; reg [PI-1:0] eep [0:NEV-1]; reg [20:0] eD [0:NEV-1]; reg [EI-1:0] esel;
    reg [1:0] eat [0:NEV-1][0:NSLOT-1];                  // {land / replay-en, ab} per event and calendar slot
    reg [NSLOT-1:0] fd [0:NEV-1];                         // fired flags
    reg [SI-1:0] pe [0:NEV-1]; reg [NSLOT-1:0] pe1h [0:NEV-1];
    integer e;
    wire wv = mw_q[25];
    wire idle = !armed && !(|vld);
    wire cwd = wv && idle && mw_q[22:21] == 2'd1;        // D word lands on this edge
    wire cwr = mc_q[25] && idle && mc_q[24];             // RL word lands on this edge
    wire c2n = cwr ? mc_q[23:0] == 24'd2 : crl == 24'd2;
    wire [NEV*21-1:0] eDf; wire [NEV-1:0] e1n, e0n, ebad;
    generate for (ge = 0; ge < NEV; ge = ge + 1) begin : g_ed
        assign eDf[21*ge +: 21] = eD[ge];
        assign e1n[ge] = (cwd && esel == EI'(ge)) ? mw_q[20:0] == 21'd1 : eD[ge] == 21'd1;
        assign e0n[ge] = (cwd && esel == EI'(ge)) ? mw_q[20:0] == 21'd0 : eD[ge] == 21'd0;
        // D < nw + 2 || D + 2 > RL
        assign ebad[ge] = (eD[ge][20:SJ+1] == 0 && eD[ge][SJ:0] < nw2) || crl == 24'd0 || !lt24({3'd0, eD[ge]}, crlm1[23:0]);
    end endgenerate
    wire bad_d = (cs[23:SJ+1] == 0 && cs[SJ:0] <= nw1) || (|ebad);     // cs <= nw + 1 || a bad D
    // ---- entry ages and compare flags; [event][entry] views
    wire [NEV-1:0] mfe [0:NSLOT-1]; wire [NEV-1:0] lfe [0:NSLOT-1];
    wire [NSLOT-1:0] mfv [0:NEV-1]; wire [NSLOT-1:0] lfv [0:NEV-1];
    wire [NSLOT-1:0] epT [0:20]; wire [NSLOT-1:0] euT [0:9];
    generate for (gi = 0; gi < NSLOT; gi = gi + 1) begin : g_en
        dsdv_mu_hwin_age #(.NEV(NEV)) u_a (.ck(ck), .wr(wr[gi]), .eD(eDf), .e1n(e1n), .e0n(e0n), .crlm1(crlm1), .c2n(c2n),
            .mf(mfe[gi]), .lf(lfe[gi]), .df(dfv[gi]));
        for (ge = 0; ge < NEV; ge = ge + 1) begin : g_t assign mfv[ge][gi] = mfe[gi][ge]; assign lfv[ge][gi] = lfe[gi][ge]; end
        for (gb = 0; gb < 21; gb = gb + 1) begin : g_p assign epT[gb][gi] = ep[gi][gb]; end
        for (gb = 0; gb < 10; gb = gb + 1) begin : g_u assign euT[gb][gi] = eu[gi][gb]; end
    end endgenerate
    // ---- per event: fire / late / pointer hold and the selected entry's payload {pos 21, user 10, land, ab}
    wire [NEV-1:0] fire, lt, pv, sse; wire [32:0] pay [0:NEV-1];
    generate for (ge = 0; ge < NEV; ge = ge + 1) begin : g_ev
        wire [NSLOT-1:0] act = pe1h[ge] & vld & ~fd[ge];
        wire [NSLOT-1:0] a1, a0;
        for (gi = 0; gi < NSLOT; gi = gi + 1) begin : g_a assign a1[gi] = eat[ge][gi][1]; assign a0[gi] = eat[ge][gi][0]; end
        assign fire[ge] = |(act & mfv[ge]);
        assign lt[ge] = |(act & lfv[ge]);
        assign pv[ge] = |act;
        assign sse[ge] = |(ss1h & pe1h[ge]);
        for (gb = 0; gb < 21; gb = gb + 1) begin : g_p assign pay[ge][12 + gb] = |(pe1h[ge] & epT[gb]); end
        for (gb = 0; gb < 10; gb = gb + 1) begin : g_u assign pay[ge][2 + gb] = |(pe1h[ge] & euT[gb]); end
        assign pay[ge][1] = |(pe1h[ge] & a1);
        assign pay[ge][0] = (MUT == 3) ? 1'b0 : |(pe1h[ge] & a0);
    end endgenerate
    // ---- RX tag check
    wire [NRT-1:0] rtb;
    generate for (gk = 0; gk < NRT; gk = gk + 1) begin : g_rt
        wire [NSLOT-1:0] mv;
        for (gi = 0; gi < NSLOT; gi = gi + 1) begin : g_m
            assign mv[gi] = vld[gi] && eu[gi] == rt_q[32*gk + 21 +: 10] && ep[gi] == rt_q[32*gk +: 21];
        end
        assign rtb[gk] = rt_q[32*gk + 31] && !(|mv);
    end endgenerate
    wire rtbad = |rtb;
    // ---- endpoint outputs: the highest firing row of a kind on an endpoint wins; two rows on one output = col_w
    wire [NEP*34-1:0] c_n; wire [NEP*11-1:0] rc_n; wire [NEP-1:0] colv;
    reg [NEP*34-1:0] c_q; reg [NEP*11-1:0] rc_q;
    assign mu_c = c_q; assign mu_rc = rc_q;
    generate for (gk = 0; gk < NEP; gk = gk + 1) begin : g_ep
        wire [NEV-1:0] hcv, hrv, sc, sr, dc, dr;
        for (ge = 0; ge < NEV; ge = ge + 1) begin : g_h
            wire here = eep[ge] == PI'(gk);
            assign hcv[ge] = fire[ge] && !ek[ge] && here;
            assign hrv[ge] = fire[ge] && ek[ge] && (pay[ge][1] || MUT == 4) && here;
            assign sc[ge] = hcv[ge] && !(|(hcv >> (ge + 1)));
            assign sr[ge] = hrv[ge] && !(|(hrv >> (ge + 1)));
            assign dc[ge] = hcv[ge] && (|(hcv >> (ge + 1)));
            assign dr[ge] = hrv[ge] && (|(hrv >> (ge + 1)));
        end
        for (gb = 0; gb < 33; gb = gb + 1) begin : g_c
            wire [NEV-1:0] t;
            for (ge = 0; ge < NEV; ge = ge + 1) begin : g_e assign t[ge] = sc[ge] & pay[ge][gb]; end
            assign c_n[34*gk + 1 + gb] = |t;
        end
        assign c_n[34*gk] = |hcv;
        for (gb = 0; gb < 10; gb = gb + 1) begin : g_r
            wire [NEV-1:0] t;
            for (ge = 0; ge < NEV; ge = ge + 1) begin : g_e assign t[ge] = sr[ge] & pay[ge][2 + gb]; end
            assign rc_n[11*gk + 1 + gb] = |t;
        end
        assign rc_n[11*gk] = |hrv;
        assign colv[gk] = (|dc) || (|dr);
    end endgenerate
    wire col_w = |colv;
    // event-row config + entry payload (no reset: written before arming / at the start that sets vld)
    integer i;
    always @(posedge ck) begin
        for (i = 0; i < NSLOT; i = i + 1) if (wr[i]) begin eu[i] <= su; ep[i] <= sp; end
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
            armed <= 1'b0; ph <= 24'd0; sl <= {SI{1'b0}}; rp <= {SI{1'b0}}; vld <= {NSLOT{1'b0}};
            ss1h <= OH0; rp1h <= OH0; crlm1 <= 32'hffffffff; nwj <= SJ'(NSLOT); nw1 <= (SJ+1)'(NSLOT + 1); nw2 <= (SJ+1)'(NSLOT + 2);
            cs <= 24'd0; crl <= 24'd0; t_wf <= 2'd0; gn <= {SJ{1'b0}}; gx <= {SI{1'b0}}; lw <= SI'(NSLOT - 1); cg <= 24'd0; c_q <= {NEP*34{1'b0}}; rc_q <= {NEP*11{1'b0}};
            for (e = 0; e < NEV; e = e + 1) begin pe[e] <= {SI{1'b0}}; pe1h[e] <= OH0; fd[e] <= {NSLOT{1'b0}}; end
        end else begin
            if (mc_q[25] && idle) begin if (mc_q[24]) begin crl <= mc_q[23:0]; crlm1 <= dec32({8'd0, mc_q[23:0]}); end else begin
                    if (gn != SJ'(NSLOT)) begin
                        gn <= gn + 1'b1;
                        if (gn == 0 || lt24(mc_q[23:0], cs)) cs <= mc_q[23:0];
                        lw <= (gn == 0) ? SI'(NSLOT - 1) : gn[SI-1:0];             // nw = n for n >= 2
                        nwj <= (gn == 0) ? SJ'(NSLOT) : gn + 1'b1;
                        nw1 <= (gn == 0) ? (SJ+1)'(NSLOT + 1) : {1'b0, gn} + (SJ+1)'(2);
                        nw2 <= (gn == 0) ? (SJ+1)'(NSLOT + 2) : {1'b0, gn} + (SJ+1)'(3);
                    end
                end end
            if (armed) begin
                if (ph == cg) begin ph <= 24'd0; sl <= nxt(sl); ss1h <= dec(nxt(sl)); cg <= ng; gx <= gxn; end else ph <= inc24(ph);
            end
            if (st && !armed) begin
                if (bad_d) t_wf[1] <= 1'b1;
                if (!hcfg_bad) begin armed <= 1'b1; ph <= 24'd1; cg <= ng; gx <= gxn; end
            end
            if (due || (!rpv && !(rec && (|(ss1h & rp1h))))) begin rp <= nxt(rp); rp1h <= dec(nxt(rp)); end
            vld <= (vld & ~({NSLOT{due}} & rp1h)) | ({NSLOT{rec}} & ss1h);
            c_q <= c_n; rc_q <= rc_n;
            for (e = 0; e < NEV; e = e + 1) begin
                fd[e] <= (fd[e] & ~wr) | ({NSLOT{fire[e]}} & pe1h[e]);
                if (fire[e] || (!pv[e] && !(rec && sse[e]))) begin pe[e] <= nxt(pe[e]); pe1h[e] <= dec(nxt(pe[e])); end
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
