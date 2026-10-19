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
                      parameter integer NRT = 2, parameter integer MUT = 0, parameter integer HEAD_STAGE = 0, parameter integer COMPACT_PTR = 0, parameter integer CHECK_STAGE = 0, parameter integer LIVE_COUNT = 0, parameter integer RAW_SELECT = 0, parameter integer LOCAL_BOOT = 0) (
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
    localparam integer MEM_EVENT_RBASE=MEM_RBASE+7+NC_REC+4;
    localparam integer MEM_EVENT_STRIDE=9+NC_REC;
    localparam integer COPY_RBASE=MEM_EVENT_RBASE+NEV*MEM_EVENT_STRIDE;
    localparam integer SEL_RBASE=COPY_RBASE+NEV*7+NRT*NC_REC;
    localparam integer COPY_END=SEL_RBASE+NEP*NEV*4+NEP;
    localparam integer RESET_EXTRA=COPY_END+1+((RAW_SELECT!=0)?NEP*NEV:0);
    localparam integer SLOT_RG=(NSLOT+23)/24, C_RG=(NEP*34+23)/24, R_RG=(NEP*11+23)/24;
    localparam integer RTIME_BASE=RESET_EXTRA, ROUT_BASE=RTIME_BASE+3;
    localparam integer RPTR_BASE=ROUT_BASE+C_RG+R_RG, RCTRL_BASE=RPTR_BASE+6*SLOT_RG+1;
    localparam integer RWRITE_BASE=RCTRL_BASE+6, RLM_BASE=RWRITE_BASE+4*SLOT_RG;
    localparam integer RBOOT_BASE=RLM_BASE+NEV*SLOT_RG;
    localparam integer RESET_REGIONS=RBOOT_BASE+((LOCAL_BOOT!=0)?NEV:0);
    wire [RESET_REGIONS-1:0] rr; dsdv_mu_reset_tree #(.REGIONS(RESET_REGIONS)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
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
    // sl stays OH0 until arming: directly use the same slot state, avoiding a broadcast mux.
    wire [NSLOT-1:0] ss = sl;
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
    dsdv_mu_mem #(.W(24),.AW(SI)) u_gap(.ck(ck),.rst_n(rr[MEM_RBASE +: 3]),
        .we(mc_q[25] && !mc_q[24] && !armed && table_empty && gn != SJ'(NSLOT)),
        .wa(gn[SI-1:0]),.wd(mc_q[23:0]-24'd1),.ra(gxb),.q(ng));
    dsdv_mu_mem #(.W(32),.AW(SI)) u_retire(.ck(ck),.rst_n(rr[MEM_RBASE+3 +: 4]),
        .we(rec_q),.wa(ssqb),.wd(tsq),.ra(rpb),.q(h_rts));
    always @(posedge ck) tmr <= tm1 - {8'd0,crm};
    // ---- event rows
    wire [31:0] ts_event[0:NEV-1], tm_event[0:NEV-1];
    wire [23:0] rl_event[0:NEV-1]; wire [NEV-1:0] idle_event, rec_local;
    wire [SI-1:0] cfg_addr[0:NEV-1];
    wire [1:0] cfg_attr[0:NEV-1];
    wire [NEV-1:0] invalid_event;
    wire [SI-1:0] lw_event[0:NEV-1]; wire [NSLOT-1:0] lm_event[0:NEV-1];
    wire [30:0] rt_compare[0:NRT*NC_REC-1];
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
            if (invalid_event[e]) bad_d = 1'b1;
        for (e = 0; e < NEV; e = e + 1) begin
            ok[e] = evld[e] && |(pe[e] & vld & ~fd[e]);
            hold[e] = (st && |(pe[e] & ss)) || (|(pe[e] & rec_slot));
            fire[e] = okq[e] && h_fr[e] && eqn[e];
            lt[e] = okq[e] && h_fr[e] && ltn[e];
            dl = h_ts[e] - tm_event[e]; dlm[e] = dl[31];
            adv[e] = fire[e] || (!ok[e] && !hold[e]);
        end
    end
    integer e4;
    always @(posedge ck) for (e4 = 0; e4 < NEV; e4 = e4 + 1) begin
        for(integer fs=0;fs<NSLOT;fs=fs+1) fd[e4][fs] <= (fd[e4][fs] || (fire[e4] && pe[e4][fs])) && !(rec_event[e4][fs/24] && ssq[fs]);   // no reset: cleared at the staged record, read only on valid entries
        okq[e4] <= ok[e4];                                  // = ok on the next edge while the head stays fresh (legal config)
        // head compares one edge ahead: h_ts == tm + 1 - D (fire on the next edge) / h_ts - (tm + 1 - D) < 0 (late);
        // used only while the head stays fresh across both edges (h_fr now and next), so the entry is the same
        eqn[e4] <= h_fr[e4] && h_ts[e4] == tm_event[e4];
        ltn[e4] <= h_fr[e4] && dlm[e4];
    end
    // outputs from the fired heads: on each endpoint the highest-numbered firing event wins (the former loop order)
    reg fq0, fq1;
    reg rtbad, m; reg [NEP*34-1:0] c_n, c_q; reg [NEP*11-1:0] rc_n, rc_q; wire col_w;
    reg [NEV-1:0] tx, rpl, sc, sr, lc, lr; integer e3, k3, p3;
    assign mu_c = c_q; assign mu_rc = rc_q;
    always @* begin
        rtbad = 1'b0;
        for (r = 0; r < NRT; r = r + 1) begin
            m = 1'b0;
            for (p = 0; p < NSLOT; p = p + 1)
                if (vld[p] && eu[p] == rt_compare[r*NC_REC+p/24][30:21] && ep[p] == rt_compare[r*NC_REC+p/24][20:0]) m = 1'b1;
            if (rt_q[32*r + 31] && !m) rtbad = 1'b1;
        end
        c_n = {NEP*34{1'b0}}; rc_n = {NEP*11{1'b0}};
        for(p3=0;p3<NEP;p3=p3+1) for(e3=0;e3<NEV;e3=e3+1) begin
            for(k3=0;k3<34;k3=k3+1)
                c_n[34*p3+k3] = c_n[34*p3+k3] | (c_select[p3*3+k3/12][e3] && output_word[e3][k3]);
            rc_n[11*p3+:11] = rc_n[11*p3+:11] | ({11{r_select[p3][e3]}} & {output_word[e3][12:3],1'b1});
        end
    end
    // A head that stays fresh has the same payload after this edge. Register the
    // exact next-edge fire decision and winning endpoint selects beside each
    // <=12-bit output slice, at the same edge as eqn/okq/fresh. No output edge added.
    wire [33:0] head_word[0:NEV-1], output_word[0:NEV-1];
    wire [NEV-1:0] c_select[0:NEP*3-1], r_select[0:NEP-1];
    wire [NEV-1:0] c_state[0:NEP*3-1], r_state[0:NEP-1];
    wire [NEV-1:0] collision_c[0:NEP-1],collision_r[0:NEP-1];
    wire [NEV-1:0] next_fire;
    wire [NEV-1:0] attr_boot;
    reg [NEP-1:0] next_collision;
    wire [NEP-1:0] collision_q; assign col_w=|collision_q;
    genvar oe,op,og;
    generate for(oe=0;oe<NEV;oe=oe+1) begin:g_fire_lookahead
        assign next_fire[oe]=ok[oe] && h_fr[oe] && h_ts[oe]==tm_event[oe]
            && !adv[oe] && !(|(pe[oe]&rec_slot));
        assign head_word[oe]={h_ep[oe],h_eu[oe],h_at[oe][1],(MUT==3)?1'b0:h_at[oe][0],1'b1};
        if(HEAD_STAGE!=0) begin:g_payload_stage
            // Unconditional capture beside the registered winning selects. A
            // selected head is fresh on both edges, so this is the same payload
            // the original output consumes. No event edge or D bound changes.
            reg [33:0] payload_q;
            always @(posedge ck) payload_q<=head_word[oe];
            assign output_word[oe]=payload_q;
        end else begin:g_payload_direct
            assign output_word[oe]=head_word[oe];
        end
    end endgenerate
    wire [NEV-1:0] nsc[0:NEP-1], nsr[0:NEP-1];
    generate for(op=0;op<NEP;op=op+1) begin:g_output_select
        for(oe=0;oe<NEV;oe=oe+1) begin:g_event
            assign nsc[op][oe]=next_fire[oe] && !ek[oe] && eep[oe]==PI'(op);
            assign nsr[op][oe]=next_fire[oe] && ek[oe] && (h_at[oe][1] || MUT==4) && eep[oe]==PI'(op);
            wire higher_c,higher_r;
            if(oe==NEV-1) begin:g_last
                assign higher_c=1'b0; assign higher_r=1'b0;
            end else begin:g_prior
                assign higher_c=|nsc[op][NEV-1:oe+1]; assign higher_r=|nsr[op][NEV-1:oe+1];
            end
            for(og=0;og<3;og=og+1) begin:g_slice
                (* keep *) reg select_r; assign c_state[op*3+og][oe]=select_r;
                if(RAW_SELECT!=0 && oe<NEV-1) begin:g_priority
                    assign c_select[op*3+og][oe]=select_r && !(|c_state[op*3+og][NEV-1:oe+1]);
                end else begin:g_unmasked assign c_select[op*3+og][oe]=select_r; end
                always @(posedge ck or negedge rr[SEL_RBASE+(op*NEV+oe)*4+og])
                    if(!rr[SEL_RBASE+(op*NEV+oe)*4+og]) select_r<=1'b0;
                    else select_r<=nsc[op][oe] && ((RAW_SELECT!=0) || !higher_c);
            end
            (* keep *) reg replay_r; assign r_state[op][oe]=replay_r;
            if(RAW_SELECT!=0 && oe<NEV-1) begin:g_replay_priority
                assign r_select[op][oe]=replay_r && !(|r_state[op][NEV-1:oe+1]);
            end else begin:g_replay_unmasked assign r_select[op][oe]=replay_r; end
            always @(posedge ck or negedge rr[SEL_RBASE+(op*NEV+oe)*4+3])
                if(!rr[SEL_RBASE+(op*NEV+oe)*4+3]) replay_r<=1'b0;
                else replay_r<=nsr[op][oe] && ((RAW_SELECT!=0) || !higher_r);
            if(RAW_SELECT!=0) begin:g_collision_raw
                reg tx_r,rp_r;
                always @(posedge ck or negedge rr[COPY_END+1+op*NEV+oe])
                    if(!rr[COPY_END+1+op*NEV+oe]) begin tx_r<=0;rp_r<=0;end
                    else begin tx_r<=nsc[op][oe];rp_r<=nsr[op][oe];end
                assign collision_c[op][oe]=tx_r;assign collision_r[op][oe]=rp_r;
            end else begin:g_collision_direct
                assign collision_c[op][oe]=nsc[op][oe];assign collision_r[op][oe]=nsr[op][oe];
            end
        end
    end endgenerate
    integer cp,ca,cb;
    always @* begin
        next_collision={NEP{1'b0}};
        for(cp=0;cp<NEP;cp=cp+1) for(ca=0;ca<NEV;ca=ca+1) for(cb=ca+1;cb<NEV;cb=cb+1)
            next_collision[cp]=next_collision[cp] || (collision_c[cp][ca] && collision_c[cp][cb]) || (collision_r[cp][ca] && collision_r[cp][cb]);
    end
    generate for(op=0;op<NEP;op=op+1) begin:g_collision_region
        if(RAW_SELECT!=0) begin:g_current
            assign collision_q[op]=next_collision[op];
        end else begin:g_delayed
            reg collision_r; assign collision_q[op]=collision_r;
            always @(posedge ck or negedge rr[SEL_RBASE+NEP*NEV*4+op])
                if(!rr[SEL_RBASE+NEP*NEV*4+op]) collision_r<=1'b0; else collision_r<=next_collision[op];
        end
    end endgenerate
    wire wv = mw_q[25];
    wire table_empty;
    wire [6:0] global_count;
    generate if(LIVE_COUNT!=0) begin:g_live_count
        reg [SJ-1:0] count_r;
        assign table_empty=(count_r==0); assign global_count=7'(count_r);
        always @(posedge ck or negedge rr[COPY_END])
            if(!rr[COPY_END]) count_r<=0;
            else count_r<=count_r+SJ'(|rec_slot)-SJ'(due);
`ifdef DSDV_MU_POINTER_ASSERT
        always @(posedge ck) if(rn && rr[COPY_END])
            if(count_r!==SJ'($countones(vld))) $fatal(1,"live-count differs from valid table");
`endif
    end else begin:g_live_direct
        assign table_empty=~(|vld); assign global_count=(|vld)?7'd1:7'd0;
    end endgenerate
    wire idle = !armed && table_empty;
    always @(posedge ck or negedge rr[RCTRL_BASE+5])
        if(!rr[RCTRL_BASE+5]) evld<={NEV{1'b0}};
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
                2'd0: esel <= mw_q[EI-1:0];
                2'd1: ; // reset-distinct event-local boot writes below
                2'd2: ; // SRAM attribute write below
                default: ;
            endcase
    end
    genvar ws, wc;
    generate for(wc=0;wc<NC_REC;wc=wc+1) begin:g_compare_copy
        (* keep *) reg [9:0] cmp_r; assign cmp_user[wc]=cmp_r;
        always @(posedge ck or negedge rr[MEM_RBASE+7+wc])
            if(!rr[MEM_RBASE+7+wc]) cmp_r<=10'd0; else cmp_r<=f_ks[51:42];
    end endgenerate
    generate for(ws=0;ws<NSLOT;ws=ws+1) begin:g_write_slot
        assign rec_slot[ws]=id_we[ws][3];
        for(wc=0;wc<4;wc=wc+1) begin:g_copy
            (* keep *) reg we_r; assign id_we[ws][wc]=we_r;
            always @(posedge ck or negedge rr[RWRITE_BASE+wc*SLOT_RG+ws/24])
                if(!rr[RWRITE_BASE+wc*SLOT_RG+ws/24]) we_r<=1'b0; else we_r<=rec && ss[ws];
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
        wire [NSLOT-1:0] pe_r;
        reg [SI-1:0] pb_r; reg fresh_r;
        assign pe[se]=pe_r; assign pbi[se]=pb_r; assign h_fr[se]=fresh_r;
        if(COMPACT_PTR!=0) begin:g_binary_head
            // pb_r was the exact same-edge shadow of the original one-hot pe_r.
            // Decode its current state; the SRAM read and event edges stay fixed.
            localparam integer SPLIT=(NSLOT+1)/2;
            (* keep *) reg [SI-1:0] upper_pointer_r;
            wire [NSLOT-1:0] lower_decode=OH0 << pb_r;
            wire [NSLOT-1:0] upper_decode=OH0 << upper_pointer_r;
            assign pe_r={upper_decode[NSLOT-1:SPLIT],lower_decode[SPLIT-1:0]};
            always @(posedge ck or negedge rr[COPY_RBASE+7*se+6])
                if(!rr[COPY_RBASE+7*se+6]) upper_pointer_r<=SI'(0);
                else if(adv[se]) upper_pointer_r<=((|(pe_r&lm_event[se])) || pe_r[NSLOT-1])?SI'(0):upper_pointer_r+1'b1;
        end else begin:g_onehot_head
            reg [NSLOT-1:0] pointer_r;
            assign pe_r=pointer_r;
            always @(posedge ck or negedge rr[se+1])
                if(!rr[se+1]) pointer_r<=OH0;
                else if(adv[se]) pointer_r<=rot(pointer_r,lm_event[se]);
        end
        always @(posedge ck or negedge rr[se+1])
            if(!rr[se+1]) begin pb_r<=SI'(0); fresh_r<=1'b0; end
            else begin
                if(adv[se]) pb_r<=((|(pe_r&lm_event[se])) || pe_r[NSLOT-1])?SI'(0):pb_r+1'b1;
                fresh_r<=!adv[se] && !(|(pe_r&rec_slot));
            end
        for(rce=0;rce<NC_REC;rce=rce+1) begin:g_record_copy
            (* keep *) reg rec_r; assign rec_event[se][rce]=rec_r;
            always @(posedge ck or negedge rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se+9+rce])
                if(!rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se+9+rce]) rec_r<=1'b0; else rec_r<=rec_local[se];
        end
        wire [62:0] head;
        wire [31:0] due_at_start=ts_event[se]+{11'd0,eD[se]};
        dsdv_mu_mem #(.W(63),.AW(SI)) u_payload(.ck(ck),.rst_n(rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se +: 8]),.we(rec_event[se][0]),
            .wa(ssqb),.wd({due_at_start,spq,suq}),.ra(pbi[se]),.q(head));
        dsdv_mu_mem #(.W(2),.AW(SI)) u_attr(.ck(ck),.rst_n(rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se+8]),
            .we(attr_boot[se]),
            .wa(cfg_addr[se]),.wd(cfg_attr[se]),.ra(pbi[se]),.q(h_at[se]));
        assign h_ts[se]=head[62:31]; assign h_ep[se]=head[30:10]; assign h_eu[se]=head[9:0];
    end endgenerate
    // Same-edge physical copies: independent event address, due-time, compare-time,
    // boot bounds and wrap state. Distinct reset roots prevent cross-event merging.
    genvar ce, rcg;
    generate for(ce=0;ce<NEV;ce=ce+1) begin:g_event_broadcast
        (* keep *) reg [31:0] ts_r, time_r;
        (* keep *) reg [23:0] rl_r;
        (* keep *) reg [SI-1:0] lw_r;
        (* keep *) reg [NSLOT-1:0] lm_r;
        (* keep *) reg arm_r;
        // Decode at the existing input landing edge, independently per event.
        // Sharing mc_valid/type AND empty-table produced a 400-load boot enable.
        (* keep *) reg cfg_gap_r,cfg_rl_r,start_r,cfg_w0_r,cfg_w1_r,cfg_w2_r;
        (* keep *) reg [SI-1:0] cfg_addr_r;
        (* keep *) reg [EI-1:0] cfg_kind_r;
        (* keep *) reg [1:0] cfg_attr_r;
        assign cfg_addr[ce]=cfg_addr_r; assign cfg_attr[ce]=cfg_attr_r;
        assign rec_local[ce]=start_r && on_cal && !col && !udup && !(!armed && hcfg_bad);
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce+6])
            if(!rr[COPY_RBASE+7*ce+6]) begin cfg_gap_r<=1'b0;cfg_rl_r<=1'b0;start_r<=1'b0;cfg_w0_r<=0;cfg_w1_r<=0;cfg_w2_r<=0;cfg_addr_r<=0;cfg_kind_r<=0;cfg_attr_r<=0;end
            else begin cfg_w0_r<=f_mw[25] && f_mw[22:21]==2'd0;cfg_w1_r<=f_mw[25] && f_mw[22:21]==2'd1;cfg_w2_r<=f_mw[25] && f_mw[22:21]==2'd2;cfg_gap_r<=f_mc[25] && !f_mc[24];cfg_rl_r<=f_mc[25] && f_mc[24];start_r<=f_ks[52];cfg_addr_r<=f_mw[SI-1:0];cfg_kind_r<=f_mw[EI-1:0];cfg_attr_r<=f_mw[11:10];end
        wire [6:0] boot_count;
        wire d_write,d_check,attr_write,kind_write,rl_write,rl_check,gap_write;
        if(LOCAL_BOOT!=0) begin:g_boot_local
            (* keep *) reg [SJ-1:0] count_r;
            always @(posedge ck or negedge rr[RBOOT_BASE+ce])
                if(!rr[RBOOT_BASE+ce]) count_r<=0;
                else count_r<=count_r+SJ'(rec_event[ce][NC_REC-1])-SJ'(due);
            assign boot_count=7'(count_r);
`ifdef DSDV_MU_POINTER_ASSERT
            always @(posedge ck) if(rr[RBOOT_BASE+ce])
                if(count_r!==SJ'($countones(vld))) $fatal(1,"event boot count differs event%0d",ce);
`endif
            (* keep=1 *) dsdv_mu_boot_enable u_dwrite(.count(boot_count),.armed(arm_r),.valid(cfg_w1_r),.match(esel==EI'(ce)),.en(d_write));
            (* keep=1 *) dsdv_mu_boot_enable u_dcheck(.count(boot_count),.armed(arm_r),.valid(cfg_w1_r),.match(esel==EI'(ce)),.en(d_check));
            (* keep=1 *) dsdv_mu_boot_enable u_attr(.count(boot_count),.armed(arm_r),.valid(cfg_w2_r),.match(esel==EI'(ce)),.en(attr_write));
            (* keep=1 *) dsdv_mu_boot_enable u_kind(.count(boot_count),.armed(arm_r),.valid(cfg_w0_r),.match(cfg_kind_r==EI'(ce)),.en(kind_write));
            (* keep=1 *) dsdv_mu_boot_enable u_rlwrite(.count(boot_count),.armed(arm_r),.valid(cfg_rl_r),.match(1'b1),.en(rl_write));
            (* keep=1 *) dsdv_mu_boot_enable u_rlcheck(.count(boot_count),.armed(arm_r),.valid(cfg_rl_r),.match(1'b1),.en(rl_check));
            (* keep=1 *) dsdv_mu_boot_enable u_gap(.count(boot_count),.armed(arm_r),.valid(cfg_gap_r),.match(gn!=SJ'(NSLOT)),.en(gap_write));
        end else begin:g_boot_direct
            assign boot_count=global_count;
            assign d_write=wv && idle_event[ce] && mw_q[22:21]==2'd1 && esel==EI'(ce);
            assign d_check=d_write;
            assign attr_write=wv && idle_event[ce] && mw_q[22:21]==2'd2 && esel==EI'(ce);
            assign kind_write=wv && idle_event[ce] && mw_q[22:21]==2'd0 && mw_q[EI-1:0]==EI'(ce);
            assign rl_write=cfg_rl_r && idle_event[ce];assign rl_check=rl_write;
            assign gap_write=cfg_gap_r && idle_event[ce] && gn!=SJ'(NSLOT);
        end
        assign attr_boot[ce]=attr_write;
        if(CHECK_STAGE!=0) begin:g_check_lookahead
            wire set_d=d_check;
            wire [20:0] next_d=set_d?mw_q[20:0]:eD[ce];
            wire [SI-1:0] next_lw=(gap_write)?
                ((gn==0)?SI'(NSLOT-1):gn[SI-1:0]):lw_r;
            wire [23:0] next_rl=(rl_check)?mc_q[23:0]:rl_r;
            wire next_enabled=evld[ce] || d_check;
            reg invalid_r;
            // The next-state values above are exactly the values the direct
            // checker observes after this edge. Fault remains on first start.
            always @(posedge ck or negedge rr[COPY_RBASE+7*ce+6])
                if(!rr[COPY_RBASE+7*ce+6]) invalid_r<=1'b0;
                else invalid_r<=next_enabled && ({3'd0,next_d} < (24'(next_lw)+24'd3) || {3'd0,next_d}+24'd2 > next_rl);
            assign invalid_event[ce]=invalid_r;
        end else begin:g_check_direct
            assign invalid_event[ce]=evld[ce] && ({3'd0,eD[ce]} < (24'(lw_r)+24'd3) || {3'd0,eD[ce]}+24'd2 > rl_r);
        end
        assign ts_event[ce]=ts_r; assign tm_event[ce]=time_r;
        assign rl_event[ce]=rl_r; assign lw_event[ce]=lw_r;
        assign lm_event[ce]=lm_r; assign idle_event[ce]=!arm_r && table_empty;
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce])
            if(!rr[COPY_RBASE+7*ce]) ts_r<=32'd0; else ts_r<=tm;
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce+1])
            if(!rr[COPY_RBASE+7*ce+1]) time_r<=32'd1; else time_r<=tm2;
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce+2])
            if(!rr[COPY_RBASE+7*ce+2]) rl_r<=24'd0;
            else if(rl_write) rl_r<=mc_q[23:0];
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce+3])
            if(!rr[COPY_RBASE+7*ce+3]) lw_r<=SI'(NSLOT-1);
            else if(gap_write)
                lw_r<=(gn==0)?SI'(NSLOT-1):gn[SI-1:0];
        for(genvar lb=0;lb<NSLOT;lb=lb+1) begin:g_limit_reset
            always @(posedge ck or negedge rr[RLM_BASE+ce*SLOT_RG+lb/24])
                if(!rr[RLM_BASE+ce*SLOT_RG+lb/24]) lm_r[lb]<=(lb==NSLOT-1);
                else lm_r[lb]<=(lw_r==SI'(lb));
        end
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce+5])
            if(!rr[COPY_RBASE+7*ce+5]) arm_r<=1'b0;
            else if(st && !arm_r && !hcfg_bad) arm_r<=1'b1;
        always @(posedge ck) begin
            if(kind_write) begin
                ek[ce]<=mw_q[8]; eep[ce]<=mw_q[9+:PI];
            end
            if(d_write) eD[ce]<=mw_q[20:0];
        end
    end endgenerate
    generate for(rcg=0;rcg<NRT*NC_REC;rcg=rcg+1) begin:g_rx_compare_copy
        (* keep *) reg [30:0] rt_r; assign rt_compare[rcg]=rt_r;
        always @(posedge ck or negedge rr[COPY_RBASE+NEV*7+rcg])
            if(!rr[COPY_RBASE+NEV*7+rcg]) rt_r<=31'd0;
            else rt_r<=mu_rt[32*(rcg/NC_REC)+:31];
    end endgenerate
    // Every relay below releases on the same original third edge. Word and
    // pointer slices carry independent reset pins, each with at most32 sinks.
    always @(posedge ck or negedge rr[RTIME_BASE]) if(!rr[RTIME_BASE]) tm<=0; else tm<=tm1;
    always @(posedge ck or negedge rr[RTIME_BASE+1]) if(!rr[RTIME_BASE+1]) tm1<=1; else tm1<=tm2;
    always @(posedge ck or negedge rr[RTIME_BASE+2]) if(!rr[RTIME_BASE+2]) tm2<=2; else tm2<=tm2+32'd1;
    generate for(genvar ob=0;ob<NEP*34;ob=ob+1) begin:g_output_reset
        always @(posedge ck or negedge rr[ROUT_BASE+ob/24])
            if(!rr[ROUT_BASE+ob/24]) c_q[ob]<=0; else c_q[ob]<=c_n[ob];
    end
    for(genvar ob=0;ob<NEP*11;ob=ob+1) begin:g_replay_output_reset
        always @(posedge ck or negedge rr[ROUT_BASE+C_RG+ob/24])
            if(!rr[ROUT_BASE+C_RG+ob/24]) rc_q[ob]<=0; else rc_q[ob]<=rc_n[ob];
    end
    for(genvar pb=0;pb<NSLOT;pb=pb+1) begin:g_pointer_reset
        wire step_slot=armed && ph==cg;
        wire step_gap=step_slot || (st && !armed && !hcfg_bad);
        wire [NSLOT-1:0] sl_next=rot(sl,lm),rp_next=rot(rp,lm);
        always @(posedge ck or negedge rr[RPTR_BASE+pb/24])
            if(!rr[RPTR_BASE+pb/24]) sl[pb]<=(pb==0); else if(step_slot) sl[pb]<=sl_next[pb];
        always @(posedge ck or negedge rr[RPTR_BASE+SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+SLOT_RG+pb/24]) rp[pb]<=(pb==0); else if(radv) rp[pb]<=rp_next[pb];
        always @(posedge ck or negedge rr[RPTR_BASE+2*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+2*SLOT_RG+pb/24]) gx[pb]<=(pb==0); else if(step_gap) gx[pb]<=gxn[pb];
        always @(posedge ck or negedge rr[RPTR_BASE+3*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+3*SLOT_RG+pb/24]) gm[pb]<=0;
            else if(mc_q[25] && idle && !mc_q[24] && gn!=SJ'(NSLOT)) gm[pb]<=(gn[SI-1:0]==SI'(pb));
        always @(posedge ck or negedge rr[RPTR_BASE+4*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+4*SLOT_RG+pb/24]) lm[pb]<=(pb==NSLOT-1); else lm[pb]<=(lw==SI'(pb));
        always @(posedge ck or negedge rr[RPTR_BASE+5*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+5*SLOT_RG+pb/24]) vld[pb]<=0; else vld[pb]<=(vld[pb] && !(due && rp[pb])) || rec_slot[pb];
    end endgenerate
    always @(posedge ck or negedge rr[RPTR_BASE+6*SLOT_RG])
        if(!rr[RPTR_BASE+6*SLOT_RG]) begin slb<=0;rpb<=0;gxb<=0;end
        else begin
            if(armed && ph==cg) slb<=((|(sl&lm)) || sl[NSLOT-1])?SI'(0):slb+1'b1;
            if((armed && ph==cg) || (st && !armed && !hcfg_bad))
                gxb<=(MUT==5 || {1'b0,gxb}+1'b1>=gn)?SI'(0):gxb+1'b1;
            if(radv) rpb<=((|(rp&lm)) || rp[NSLOT-1])?SI'(0):rpb+1'b1;
        end
    always @(posedge ck or negedge rr[RCTRL_BASE])
        if(!rr[RCTRL_BASE]) ph<=0;
        else if(st && !armed && !hcfg_bad) ph<=1;
        else if(armed) ph<=(ph==cg)?24'd0:ph+24'd1;
    always @(posedge ck or negedge rr[RCTRL_BASE+1])
        if(!rr[RCTRL_BASE+1]) cs<=0;
        else if(mc_q[25] && idle && !mc_q[24] && gn!=SJ'(NSLOT) && (gn==0 || mc_q[23:0]<cs)) cs<=mc_q[23:0];
    always @(posedge ck or negedge rr[RCTRL_BASE+2])
        if(!rr[RCTRL_BASE+2]) crl<=0; else if(mc_q[25] && idle && mc_q[24]) crl<=mc_q[23:0];
    always @(posedge ck or negedge rr[RCTRL_BASE+3])
        if(!rr[RCTRL_BASE+3]) crm<=24'hffffff; else if(mc_q[25] && idle && mc_q[24]) crm<=mc_q[23:0]-24'd1;
    always @(posedge ck or negedge rr[RCTRL_BASE+4])
        if(!rr[RCTRL_BASE+4]) cg<=0;
        else if((armed && ph==cg) || (st && !armed && !hcfg_bad)) cg<=ng;
    always @(posedge ck or negedge rn)
        if(!rn) begin
            armed<=1'b0;
            t_wf<=2'd0; gn<={SJ{1'b0}}; lw<=SI'(NSLOT-1);
            rec_q<=1'b0; h_rfr<=1'b0; fq0<=1'b0; fq1<=1'b0;
        end else begin
            if(mc_q[25] && idle) begin
                if(!mc_q[24] && gn!=SJ'(NSLOT)) begin
                    gn<=gn+1'b1;
                    lw<=(gn==0)?SI'(NSLOT-1):gn[SI-1:0];
                end
            end
            if(st && !armed) begin
                if(bad_d) t_wf[1]<=1'b1;
                if(!hcfg_bad) armed<=1'b1;
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
    dsdv_mu_hwin #(.NSLOT(47), .NEV(16), .NEP(4), .NRT(2), .HEAD_STAGE(1), .COMPACT_PTR(1), .CHECK_STAGE(1), .LIVE_COUNT(1), .RAW_SELECT(1), .LOCAL_BOOT(1)) u_win (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_mc(mc), .f_mw(mw),
        .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0n, mu_rt_7n}), .t_wf(wf));
    assign t_mf = {hmf[3] | wf[1], hmf[2] | wf[0], hmf[1:0]};
endmodule

// Fixed combinational boundary retained per <=24-bit consumer group. No state
// or edge: prevents equivalent boot controls merging into one broad enable.
(* keep_hierarchy="yes" *) module dsdv_mu_boot_enable(input wire [6:0] count,input wire armed,valid,match,output wire en);
 assign en=(count==0) && !armed && valid && match;
endmodule
