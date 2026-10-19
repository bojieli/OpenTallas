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
// CODEX HWIN structural successor (10-19): true independent SRAM read ports for each event's
// precomputed {due=ts+D,pos,user} and attributes, plus separate gap and retirement timestamp SRAMs.
// The registered read and current/previous-write forwarding preserve the previous head/freshness
// edge. Event comparison is only due==tm+1 into a registered fire flag; no serialized head prefetch,
// no new output edge, and original D>=nw+2 / gap>=nw+2 limits are preserved.
// Per-event one-hot pointers retain the original walk; binary SRAM shadows use exactly the same
// registered wrap mask, including during boot-time calendar changes. Optional simulation asserts
// prove correspondence on every edge. Payload copies per<=16 identities have distinct regional
// resets; event, pointer, time, output and control state have local same-edge reset relays.
// 16 rows are available in the die master. A row is enabled by its offset bootword; inactive rows
// do not fire or participate in offset-validity checks. Fault meanings and CSR encoding are unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_mu_hwin #(parameter integer NSLOT = 47, parameter integer NEV = 16, parameter integer NEP = 4,
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
    initial if (NSLOT < 2 || NSLOT > 64 || NEV < 1 || NEV > 32) $fatal(1, "dsdv_mu_hwin: NSLOT 2..64, NEV 1..32");
`endif
    localparam integer ID_C=(NSLOT+15)/16;
    localparam integer NC_REC=(NSLOT+23)/24;
    localparam integer MEM_RBASE=NEV+ID_C+4;
    wire [MEM_RBASE+NEV*5+3:0] rr; ot_rst_relay #(.REGIONS(MEM_RBASE+NEV*5+4)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    // Payload pin flops sample every edge; valid pins are asynchronously held by their
    // landed reset, so the reset does not enter a synchronous data cone.
    reg [51:0] ks_payload; reg [24:0] mc_payload, mw_payload;
    reg ks_valid, mc_valid, mw_valid;
    reg [NRT*31-1:0] rt_payload; reg [NRT-1:0] rt_valid;
    wire [52:0] ks_q={ks_valid,ks_payload};
    wire [25:0] mc_q={mc_valid,mc_payload}, mw_q={mw_valid,mw_payload};
    wire [NRT*32-1:0] rt_q; integer pr,pv,r;
    always @(posedge ck) begin
        ks_payload<=f_ks[51:0]; mc_payload<=f_mc[24:0]; mw_payload<=f_mw[24:0];
        for(pr=0;pr<NRT;pr=pr+1) rt_payload[31*pr+:31]<=mu_rt[32*pr+:31];
    end
    always @(posedge ck or negedge rn)
        if(!rn) begin ks_valid<=1'b0; mc_valid<=1'b0; mw_valid<=1'b0; rt_valid<={NRT{1'b0}}; end
        else begin
            ks_valid<=f_ks[52]; mc_valid<=f_mc[25]; mw_valid<=f_mw[25];
            for(pv=0;pv<NRT;pv=pv+1) rt_valid[pv]<=mu_rt[32*pv+31];
        end
    genvar rp_pin;
    generate for(rp_pin=0;rp_pin<NRT;rp_pin=rp_pin+1) begin:g_rx_pin
        assign rt_q[32*rp_pin+:32]={rt_valid[rp_pin],rt_payload[31*rp_pin+:31]};
    end endgenerate
    wire st = ks_q[52]; wire [9:0] su = ks_q[51:42]; wire [20:0] sp = ks_q[20:0];
    // ---- one-hot pointer step: entries wrap at lw (lm = one-hot of lw); a pointer past lw (only while idle, after a
    // config shrink) wraps at NSLOT - 1
    reg [NSLOT-1:0] lm, gm;
    function automatic [NSLOT-1:0] rot(input [NSLOT-1:0] o, input [NSLOT-1:0] l);
        rot = {o[NSLOT-2:0] & ~l[NSLOT-2:0], 1'b0};
        rot[0] = (|(o & l)) | o[NSLOT-1];
    endfunction
    // ---- start table: the same record rule / slot timer / due edge as dsdv_mu_hslot
    reg [23:0] cs, crl, crm; reg [31:0] tm, tm1, tm2, tmr; reg armed; reg [23:0] ph; reg [SI-1:0] lw;
    reg [SI-1:0] slb, rpb, gxb, ssqb; reg [NSLOT-1:0] sl, rp, gx;                           // one-hot: slot, retire pointer, gap-table walker
    // MU-S81-2/SEQ (10-19): slot gap table, the same as dsdv_mu_hslot's (same f_mc words, same walk).  The record calendar (dv_mu_calendar --phase-q 4) has NON-uniform slots
    // (AR 46: shift_k = 4 floor(k (P/4) / 46) -> gaps 21,312 / 21,316; MTP 10 + filler: 10 x 124,524 then 58,160), so
    // one period S cannot hold it (user 3's start lands 4 edges off a uniform 21,312 grid -> t_mf[1] on the real unit).
    // Each sel-0 word APPENDS one slot gap g[k] (cycles from slot k's start edge to slot k+1's); the slot timer walks
    // g[0..n-1] cyclically (n = words written), and the slot entries wrap at nw = n (n >= 2) so the entry index IS the
    // calendar slot.  One sel-0 word (n = 1) = the former uniform period S with nw = NSLOT: the previous behaviour.
    // cs = the smallest gap.  gtm[k] = g[k] - 1 (the timer's compare value).
     reg [SI:0] gn; reg [23:0] cg; wire [23:0] ng;
    reg [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1]; 
    wire [NSLOT-1:0] ss = armed ? sl : OH0;
    wire on_cal = !armed || ph == 24'd0;
    wire [9:0] cmp_user [0:NC_REC-1];
    wire [3:0] id_we [0:NSLOT-1]; wire [NSLOT-1:0] rec_slot;
    wire [NC_REC-1:0] rec_event [0:NEV-1];
    reg udup; integer i;
    always @* begin udup = 1'b0; for (i = 0; i < NSLOT; i = i + 1) if (vld[i] && eu[i] == cmp_user[i/24]) udup = 1'b1; end
    wire col = |(vld & ss);
    wire [23:0] nw = {{(23-SI){1'b0}}, lw} + 24'd1;     // slot entries in use (= calendar slots per period)
    wire hcfg_bad = gn == 0 || cs < nw || crl <= nw;                     // hslot's own arming rule
    wire rec = st && on_cal && !col && !udup && !(!armed && hcfg_bad);
    // staged record: written one edge after the start edge, with the start edge's tm
    reg rec_q; reg [NSLOT-1:0] ssq; reg [9:0] suq; reg [20:0] spq; reg [31:0] tsq;
    always @(posedge ck) begin ssqb <= slb; ssq <= ss; suq <= su; spq <= sp; tsq <= tm; end
    // retire pointer head (registered read of the entry under rp)
    wire [31:0] h_rts; reg h_rfr;
    wire rok = |(rp & vld);
    wire rhold = (st && |(rp & ss)) || (|(rp & rec_slot));
    wire due = rok && h_rfr && h_rts == tmr;                             // hslot's return edge: the entry retires
    wire radv = due || (!rok && !rhold);
    wire [NSLOT-1:0] gxn = (MUT == 5 || |(gx & gm)) ? OH0 : {gx[NSLOT-2:0], 1'b0};   // MUT 5: gap table index stuck at 0
    dsdv_mu_mem #(.W(24),.AW(SI)) u_gap(.ck(ck),.rst_n(rr[MEM_RBASE +: 2]),
        .we(mc_q[25] && !mc_q[24] && !armed && !(|vld) && gn != SJ'(NSLOT)),
        .wa(gn[SI-1:0]),.wd(mc_q[23:0]-24'd1),.ra(gxb),.q(ng));
    dsdv_mu_mem #(.W(32),.AW(SI)) u_retire(.ck(ck),.rst_n(rr[MEM_RBASE+2 +: 2]),
        .we(rec_q),.wa(ssqb),.wd(tsq),.ra(rpb),.q(h_rts));
    always @(posedge ck) tmr <= tm1 - {8'd0,crm};
    // ---- event rows
    reg [NEV-1:0] evld; reg [NEV-1:0] ek; reg [PI-1:0] eep [0:NEV-1]; reg [20:0] eD [0:NEV-1]; reg [EI-1:0] esel;
    // Attributes are in independent registered SRAM banks.                  // {land / replay-en, ab} per event and calendar slot
    reg [NSLOT-1:0] fd [0:NEV-1];                         // fired flags
    wire [NSLOT-1:0] pe [0:NEV-1];                         // one-hot event pointers
    wire [SI-1:0] pbi [0:NEV-1]; // binary shadow: drives only SRAM address pins                            // tm - D[e] + 1 (next edge's fire compare value)
    reg [NEV-1:0] eqn, ltn, okq;                          // registered head compares / head ok, valid on the next edge
    wire [31:0] h_ts [0:NEV-1]; wire [20:0] h_ep [0:NEV-1]; wire [9:0] h_eu [0:NEV-1]; wire [1:0] h_at [0:NEV-1];
    wire [NEV-1:0] h_fr;
    integer e, p;
    reg bad_d; reg [NEV-1:0] fire, lt, ok, hold, adv;
    reg [31:0] dl; reg [NEV-1:0] dlm;
    always @* begin
        bad_d = cs <= nw + 24'd1;
        for (e = 0; e < NEV; e = e + 1)
            if (evld[e] && ({3'd0, eD[e]} < nw + 24'd2 || {3'd0, eD[e]} + 24'd2 > crl)) bad_d = 1'b1;
        for (e = 0; e < NEV; e = e + 1) begin
            ok[e] = evld[e] && |(pe[e] & vld & ~fd[e]);
            hold[e] = (st && |(pe[e] & ss)) || (|(pe[e] & rec_slot));
            fire[e] = okq[e] && h_fr[e] && eqn[e];
            lt[e] = okq[e] && h_fr[e] && ltn[e];
            dl = h_ts[e] - tm1; dlm[e] = dl[31];
            adv[e] = fire[e] || (!ok[e] && !hold[e]);
        end
    end
    integer e4;
    always @(posedge ck) for (e4 = 0; e4 < NEV; e4 = e4 + 1) begin
        for(integer fs=0;fs<NSLOT;fs=fs+1) fd[e4][fs] <= (fd[e4][fs] || (fire[e4] && pe[e4][fs])) && !(rec_event[e4][fs/24] && ssq[fs]);   // no reset: cleared at the staged record, read only on valid entries
        okq[e4] <= ok[e4];                                  // = ok on the next edge while the head stays fresh (legal config)
        // head compares one edge ahead: h_ts == tm + 1 - D (fire on the next edge) / h_ts - (tm + 1 - D) < 0 (late);
        // used only while the head stays fresh across both edges (h_fr now and next), so the entry is the same
        eqn[e4] <= h_fr[e4] && h_ts[e4] == tm1;
        ltn[e4] <= h_fr[e4] && dlm[e4];
    end
    // outputs from the fired heads: on each endpoint the highest-numbered firing event wins (the former loop order)
    reg fq0, fq1;
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
    always @(posedge ck or negedge rn)
        if(!rn) evld<={NEV{1'b0}};
        else if(wv && idle && mw_q[22:21]==2'd1) evld[esel]<=1'b1;
    integer k4;
    // event-row config + entry payload (no reset: written before arming / at the staged record that sets vld)
    always @(posedge ck) begin
        for(k4=0;k4<NSLOT;k4=k4+1) begin
            if(id_we[k4][0]) eu[k4]<=id_c[k4/16][30:21];
            if(id_we[k4][1]) ep[k4][10:0]<=id_c[k4/16][10:0];
            if(id_we[k4][2]) ep[k4][20:11]<=id_c[k4/16][20:11];
        end
        if (wv && idle)
            case (mw_q[22:21])
                2'd0: begin esel <= mw_q[EI-1:0]; ek[mw_q[EI-1:0]] <= mw_q[8]; eep[mw_q[EI-1:0]] <= mw_q[9 +: PI]; end
                2'd1: eD[esel] <= mw_q[20:0];
                2'd2: ; // SRAM attribute write below
                default: ;
            endcase
    end
    genvar ws, wc;
    generate for(wc=0;wc<NC_REC;wc=wc+1) begin:g_compare_copy
        (* keep *) reg [9:0] cmp_r; assign cmp_user[wc]=cmp_r;
        always @(posedge ck or negedge rr[MEM_RBASE+2+wc])
            if(!rr[MEM_RBASE+2+wc]) cmp_r<=10'd0; else cmp_r<=f_ks[51:42];
    end endgenerate
    generate for(ws=0;ws<NSLOT;ws=ws+1) begin:g_write_slot
        assign rec_slot[ws]=id_we[ws][3];
        for(wc=0;wc<4;wc=wc+1) begin:g_copy
            (* keep *) reg we_r; assign id_we[ws][wc]=we_r;
            always @(posedge ck or negedge rr[MEM_RBASE+4+wc])
                if(!rr[MEM_RBASE+4+wc]) we_r<=1'b0; else we_r<=rec && ss[ws];
        end
    end endgenerate
    // Parallel RX identity fields have one reset-distinct payload copy per <=16 entries.
    // Distinct regional reset pins prevent synthesis from merging these physical fanout copies.
    wire [30:0] id_c [0:ID_C-1];
    genvar ic;
    generate for(ic=0;ic<ID_C;ic=ic+1) begin:g_identity_copy
        (* keep *) reg [30:0] id_r; assign id_c[ic]=id_r;
        always @(posedge ck or negedge rr[NEV+1+ic])
            if(!rr[NEV+1+ic]) id_r<=31'd0; else id_r<={su,sp};
    end endgenerate
    // Every event has independent true SRAM read ports for its due/payload and attributes.
    // There is no arbitration or serialized prefetch: original registered-read/freshness edges hold.
    genvar se, rce;
    generate for(se=0;se<NEV;se=se+1) begin:g_event_mem
        reg [NSLOT-1:0] pe_r; reg [SI-1:0] pb_r; reg fresh_r;
        assign pe[se]=pe_r; assign pbi[se]=pb_r; assign h_fr[se]=fresh_r;
        always @(posedge ck or negedge rr[se+1])
            if(!rr[se+1]) begin pe_r<=OH0; pb_r<=SI'(0); fresh_r<=1'b0; end
            else begin
                if(adv[se]) begin pe_r<=rot(pe_r,lm); pb_r<=((|(pe_r&lm)) || pe_r[NSLOT-1])?SI'(0):pb_r+1'b1; end
                fresh_r<=!adv[se] && !(|(pe_r&rec_slot));
            end
        for(rce=0;rce<NC_REC;rce=rce+1) begin:g_record_copy
            (* keep *) reg rec_r; assign rec_event[se][rce]=rec_r;
            always @(posedge ck or negedge rr[MEM_RBASE+4+5*se+rce])
                if(!rr[MEM_RBASE+4+5*se+rce]) rec_r<=1'b0; else rec_r<=rec;
        end
        wire [62:0] head;
        wire [31:0] due_at_start=tsq+{11'd0,eD[se]};
        dsdv_mu_mem #(.W(63),.AW(SI)) u_payload(.ck(ck),.rst_n(rr[MEM_RBASE+4+5*se +: 4]),.we(rec_event[se][0]),
            .wa(ssqb),.wd({due_at_start,spq,suq}),.ra(pbi[se]),.q(head));
        dsdv_mu_mem #(.W(2),.AW(SI)) u_attr(.ck(ck),.rst_n(rr[MEM_RBASE+8+5*se]),
            .we(wv && idle && mw_q[22:21]==2'd2 && esel==EI'(se)),
            .wa(mw_q[SI-1:0]),.wd(mw_q[11:10]),.ra(pbi[se]),.q(h_at[se]));
        assign h_ts[se]=head[62:31]; assign h_ep[se]=head[30:10]; assign h_eu[se]=head[9:0];
    end endgenerate
    // The former shared reset drove690flops. Time96, outputs180, pointers~206,
    // control~213 now have independent same-edge reset relays; no added schedule cycle.
    wire rtime=rr[NEV+ID_C+1], rptr=rr[NEV+ID_C+2], rout=rr[NEV+ID_C+3];
    always @(posedge ck or negedge rtime)
        if(!rtime) begin tm<=32'd0; tm1<=32'd1; tm2<=32'd2; end
        else begin tm<=tm1; tm1<=tm2; tm2<=tm2+32'd1; end
    always @(posedge ck or negedge rout)
        if(!rout) begin c_q<={NEP*34{1'b0}}; rc_q<={NEP*11{1'b0}}; end
        else begin c_q<=c_n; rc_q<=rc_n; end
    always @(posedge ck or negedge rptr)
        if(!rptr) begin
            slb<=SI'(0); rpb<=SI'(0); gxb<=SI'(0); sl<=OH0; rp<=OH0; vld<={NSLOT{1'b0}};
            gx<=OH0; gm<={NSLOT{1'b0}}; lm<={1'b1,{(NSLOT-1){1'b0}}};
        end else begin
            lm<={NSLOT{1'b0}}; lm[lw]<=1'b1;
            if(mc_q[25] && idle && !mc_q[24] && gn!=SJ'(NSLOT)) begin
                gm<={NSLOT{1'b0}}; gm[gn[SI-1:0]]<=1'b1;
            end
            if(armed && ph==cg) begin
                sl<=rot(sl,lm); slb<=((|(sl&lm)) || sl[NSLOT-1])?SI'(0):slb+1'b1;
                gx<=gxn; gxb<=(MUT==5 || {1'b0,gxb}+1'b1>=gn)?SI'(0):gxb+1'b1;
            end
            if(st && !armed && !hcfg_bad) begin
                gx<=gxn; gxb<=(MUT==5 || {1'b0,gxb}+1'b1>=gn)?SI'(0):gxb+1'b1;
            end
            if(radv) begin rp<=rot(rp,lm); rpb<=((|(rp&lm)) || rp[NSLOT-1])?SI'(0):rpb+1'b1; end
            vld<=(vld & ~(due?rp:{NSLOT{1'b0}})) | rec_slot;
        end
    always @(posedge ck or negedge rn)
        if(!rn) begin
            armed<=1'b0; ph<=24'd0; cs<=24'd0; crl<=24'd0; crm<=24'hffffff;
            t_wf<=2'd0; gn<={SJ{1'b0}}; lw<=SI'(NSLOT-1); cg<=24'd0;
            rec_q<=1'b0; h_rfr<=1'b0; fq0<=1'b0; fq1<=1'b0;
        end else begin
            if(mc_q[25] && idle) begin
                if(mc_q[24]) begin crl<=mc_q[23:0]; crm<=mc_q[23:0]-24'd1; end
                else if(gn!=SJ'(NSLOT)) begin
                    gn<=gn+1'b1;
                    if(gn==0 || mc_q[23:0]<cs) cs<=mc_q[23:0];
                    lw<=(gn==0)?SI'(NSLOT-1):gn[SI-1:0];
                end
            end
            if(armed) begin
                if(ph==cg) begin ph<=24'd0; cg<=ng; end else ph<=ph+24'd1;
            end
            if(st && !armed) begin
                if(bad_d) t_wf[1]<=1'b1;
                if(!hcfg_bad) begin armed<=1'b1; ph<=24'd1; cg<=ng; end
            end
            rec_q<=rec;
            h_rfr<=!radv && !(|(rp&rec_slot));
            fq0<=rtbad || (|lt); fq1<=col_w;
            if(fq0) t_wf[0]<=1'b1;
            if((wv && (!idle || mw_q[22:21]==2'd3)) || fq1) t_wf[1]<=1'b1;
        end
`ifdef DSDV_MU_POINTER_ASSERT
    integer ae;
    always @(posedge ck or negedge rn) if(!rn) begin end else begin
        if(rp !== (OH0 << rpb)) $fatal(1,"retire SRAM pointer mismatch");
        if(sl !== (OH0 << slb)) $fatal(1,"slot SRAM pointer mismatch");
        if(gx !== (OH0 << gxb)) $fatal(1,"gap SRAM pointer mismatch");
        for(ae=0;ae<NEV;ae=ae+1)
            if(pe[ae] !== (OH0 << pbi[ae])) $fatal(1,"event SRAM pointer mismatch e%0d",ae);
    end
`endif
endmodule

// ---------------------------------------------------------------- MU-S81-2/DIE: parameter-free p4l die master (MU dies)
// dsdv_seq_host_mux = dsdv_seq_host_mu NSLOT 47 (the CLOSED dsdv_mu_hslot leaf, NSLOT 47 MUT 0, unchanged) + dsdv_mu_hwin
// (16 window events, 4 end slices: mu_c / mu_rc to s_7N / s_7S / s_0N / s_0S; RX tags back from the 2 N-tier end slices
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
    dsdv_mu_hwin #(.NSLOT(47), .NEV(16), .NEP(4), .NRT(2)) u_win (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_mc(mc), .f_mw(mw),
        .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0n, mu_rt_7n}), .t_wf(wf));
    assign t_mf = {hmf[3] | wf[1], hmf[2] | wf[0], hmf[1:0]};
endmodule
