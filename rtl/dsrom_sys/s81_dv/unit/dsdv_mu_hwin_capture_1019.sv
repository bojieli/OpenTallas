`timescale 1ns/1ps
// Private exact selected-anchor HWIN source; namespace projection only.
module dsdv_mu_hwin_capture_1019 #(parameter integer NSLOT = 47, parameter integer NEV = 16, parameter integer NEP = 4,
                      parameter integer NRT = 2, parameter integer MUT = 0, parameter integer HEAD_STAGE = 0, parameter integer COMPACT_PTR = 0, parameter integer CHECK_STAGE = 0, parameter integer LIVE_COUNT = 0, parameter integer RAW_SELECT = 0, parameter integer LOCAL_BOOT = 0, parameter integer EARLY_HEAD_CAPTURE = 0, parameter integer CFG_RELAY = 0, parameter integer DUE_COPIES = 0) (
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
    initial if (NSLOT < 2 || NSLOT > 64 || NEV < 1 || NEV > 32) $fatal(1, "dsdv_mu_hwin_capture_1019: NSLOT 2..64, NEV 1..32");
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
    localparam integer NBOOT_GROUPS=(NEV+3)/4;
    localparam integer RBOOT_DATA=RBOOT_BASE+((LOCAL_BOOT!=0)?NEV:0);
    localparam integer RPRED_BASE=RBOOT_DATA+((LOCAL_BOOT!=0)?NBOOT_GROUPS:0);
    localparam integer RMC_LIMIT=RPRED_BASE+((CHECK_STAGE!=0)?NEV:0);
    localparam integer RCFG_BASE=RMC_LIMIT+((CHECK_STAGE!=0)?1:0);
    // HWIN21g CFG_RELAY: 2 relay copies x {f_mw, f_mc}, one reset region each (26 sinks), so the copies stay distinct.
    localparam integer RESET_REGIONS=RCFG_BASE+((CFG_RELAY!=0)?4:0);
    wire [RESET_REGIONS-1:0] rr; dsdv_mu_hwin_capture_1019_reset_tree #(.REGIONS(RESET_REGIONS)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    // HWIN21g CFG_RELAY=1 (opt-in, default 0 = HWIN21cb bytes-equivalent logic): the config word ports f_mw / f_mc
    // land in a relay register stage before ANY consumer, so every config consumer sees the port one edge later
    // (+1 edge on the config path only; f_ks start and mu_rt RX timing unchanged).  Two kept, reset-distinct copies
    // form a balanced 2-way landed tree: copy 0 serves the west events 0..NEV/2-1, the central pin flops (mw_q/mc_q),
    // boot-data groups of the west half and the RL limit payload; copy 1 serves the east events and boot groups.
    // Exactness: DUT(CFG_RELAY=1)(f_mw, f_mc) == DUT(CFG_RELAY=0)(z^-1 f_mw, z^-1 f_mc) every cycle (kit bench miter).
    wire [25:0] mw_in[0:1], mc_in[0:1];
    generate if(CFG_RELAY!=0) begin:g_cfg_relay
        for(genvar rc=0;rc<2;rc=rc+1) begin:g_copy
            (* keep *) reg [25:0] mw_r, mc_r;
            always @(posedge ck or negedge rr[RCFG_BASE+2*rc]) if(!rr[RCFG_BASE+2*rc]) mw_r<=26'd0; else mw_r<=f_mw;
            always @(posedge ck or negedge rr[RCFG_BASE+2*rc+1]) if(!rr[RCFG_BASE+2*rc+1]) mc_r<=26'd0; else mc_r<=f_mc;
            assign mw_in[rc]=mw_r; assign mc_in[rc]=mc_r;
        end
    end else begin:g_cfg_direct
        assign mw_in[0]=f_mw; assign mw_in[1]=f_mw; assign mc_in[0]=f_mc; assign mc_in[1]=f_mc;
    end endgenerate
    // Payload pin flops sample every edge; valid pins are asynchronously held by their
    // landed reset, so the reset does not enter a synchronous data cone.
    reg [51:0] ks_payload; reg [24:0] mc_payload, mw_payload;
    reg ks_valid, mc_valid, mw_valid;
    reg [NRT*31-1:0] rt_payload; reg [NRT-1:0] rt_valid;
    wire [52:0] ks_q={ks_valid,ks_payload};
    wire [25:0] mc_q={mc_valid,mc_payload}, mw_q={mw_valid,mw_payload};
    wire [NRT*32-1:0] rt_q; integer pr,pv,r;
    always @(posedge ck) begin
        ks_payload<=f_ks[51:0]; mc_payload<=mc_in[0][24:0]; mw_payload<=mw_in[0][24:0];
        for(pr=0;pr<NRT;pr=pr+1) rt_payload[31*pr+:31]<=mu_rt[32*pr+:31];
    end
    always @(posedge ck or negedge rn)
        if(!rn) begin ks_valid<=1'b0; mc_valid<=1'b0; mw_valid<=1'b0; rt_valid<={NRT{1'b0}}; end
        else begin
            ks_valid<=f_ks[52]; mc_valid<=mc_in[0][25]; mw_valid<=mw_in[0][25];
            for(pv=0;pv<NRT;pv=pv+1) rt_valid[pv]<=mu_rt[32*pv+31];
        end
    genvar rp_pin;
    generate for(rp_pin=0;rp_pin<NRT;rp_pin=rp_pin+1) begin:g_rx_pin
        assign rt_q[32*rp_pin+:32]={rt_valid[rp_pin],rt_payload[31*rp_pin+:31]};
    end endgenerate
    wire st = ks_q[52]; wire [9:0] su = ks_q[51:42]; wire [20:0] sp = ks_q[20:0];
    // ---- one-hot pointer step: entries wrap at lw (lm = one-hot of lw); a pointer past lw (only while idle, after a
    // config shrink) wraps at NSLOT - 1
    wire [NSLOT-1:0] lm, gm;
    function automatic [NSLOT-1:0] rot(input [NSLOT-1:0] o, input [NSLOT-1:0] l);
        rot = {o[NSLOT-2:0] & ~l[NSLOT-2:0], 1'b0};
        rot[0] = (|(o & l)) | o[NSLOT-1];
    endfunction
    // ---- start table: the same record rule / slot timer / due edge as dsdv_mu_hslot
    reg [23:0] cs, crl, crm; reg [31:0] tm, tm1, tm2, tmr; reg armed; wire [23:0] ph; reg [SI-1:0] lw;
    reg [SI-1:0] slb, rpb, gxb, ssqb; wire [NSLOT-1:0] sl, rp, gx;                           // one-hot: slot, retire pointer, gap-table walker
    // MU-S81-2/SEQ (10-19): slot gap table, the same as dsdv_mu_hslot's (same f_mc words, same walk).  The record calendar (dv_mu_calendar --phase-q 4) has NON-uniform slots
    // (AR 46: shift_k = 4 floor(k (P/4) / 46) -> gaps 21,312 / 21,316; MTP 10 + filler: 10 x 124,524 then 58,160), so
    // one period S cannot hold it (user 3's start lands 4 edges off a uniform 21,312 grid -> t_mf[1] on the real unit).
    // Each sel-0 word APPENDS one slot gap g[k] (cycles from slot k's start edge to slot k+1's); the slot timer walks
    // g[0..n-1] cyclically (n = words written), and the slot entries wrap at nw = n (n >= 2) so the entry index IS the
    // calendar slot.  One sel-0 word (n = 1) = the former uniform period S with nw = NSLOT: the previous behaviour.
    // cs = the smallest gap.  gtm[k] = g[k] - 1 (the timer's compare value).
     reg [SI:0] gn; reg [23:0] cg; wire [23:0] ng;
    wire [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1];
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
    wire hcfg_bad = gn == 0 || cs < nw || crl <= nw;
    localparam integer BAD_GROUPS=(NEV+3)/4;
    wire [BAD_GROUPS-1:0] bad_group;
    generate for(genvar bg=0;bg<BAD_GROUPS;bg=bg+1) begin:g_config_check_region
        if(LOCAL_BOOT!=0) begin:g_local
            (* keep=1 *) dsdv_mu_hwin_capture_1019_cfg_bad u_bad(.count(7'(gn)),.min_gap(cs),.return_gap(crl),.last_slot(6'(lw)),.bad(bad_group[bg]));
        end else begin:g_direct assign bad_group[bg]=hcfg_bad;end
    end endgenerate
                     // hslot's own arming rule
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
    localparam integer PTR_CTL=(NSLOT+7)/8;
    wire [NEV-1:0] event_due;
    wire [PTR_CTL-1:0] pointer_due,pointer_adv,slot_step,gap_step;
    wire [2:0] cg_step,crl_write,crm_write;
    generate if(LOCAL_BOOT!=0) begin:g_control_regions
        // HWIN21h DUE_COPIES=2 (opt-in; 0 = one retire_due per event, HWIN21cb logic): the 32-bit retire==now compare and the
        // 47-bit valid reduce run in 2 kept central copies beside the retire head, and only the 1-bit due leaves for the
        // events (copy 0 -> west events 0..NEV/2-1, copy 1 -> east events; 8 loads each) instead of 16 per-event compares
        // fed by a 64-bit h_rts/tmr broadcast along the band (c21d gate: worst post-GRT cone = event count_r).  Same function, +0 edges.
        if(DUE_COPIES!=0) begin:g_due_central
            wire [1:0] due_c;
            for(genvar dc=0;dc<2;dc=dc+1) begin:g_copy
                (* keep=1 *) dsdv_mu_hwin_capture_1019_retire_due u_due(.valid(rok),.fresh(h_rfr),.retire(h_rts),.now_time(tmr),.due(due_c[dc]));
            end
            for(genvar ed=0;ed<NEV;ed=ed+1) begin:g_event_due
                assign event_due[ed]=due_c[(ed>=NEV/2 && NEV>1)?1:0];
            end
        end else begin:g_due_local
        for(genvar ed=0;ed<NEV;ed=ed+1) begin:g_event_due
            (* keep=1 *) dsdv_mu_hwin_capture_1019_retire_due u_due(.valid(rok),.fresh(h_rfr),.retire(h_rts),.now_time(tmr),.due(event_due[ed]));
        end
        end
        for(genvar pc=0;pc<PTR_CTL;pc=pc+1) begin:g_pointer
            (* keep=1 *) dsdv_mu_hwin_capture_1019_retire_advance u_retire(.valid(rok),.fresh(h_rfr),.hold_head(rhold),.retire(h_rts),.now_time(tmr),.due(pointer_due[pc]),.advance(pointer_adv[pc]));
            (* keep=1 *) dsdv_mu_hwin_capture_1019_slot_step u_step(.phase(ph),.gap(cg),.armed(armed_event[pc%NEV]),.start(start_event[pc%NEV]),.bad(bad_group[(pc/2)%BAD_GROUPS]),.slot(slot_step[pc]),.gap_step(gap_step[pc]));
        end
        for(genvar cc=0;cc<3;cc=cc+1) begin:g_config
            wire unused_slot;
            (* keep=1 *) dsdv_mu_hwin_capture_1019_slot_step u_cg(.phase(ph),.gap(cg),.armed(armed_event[(cc+PTR_CTL)%NEV]),.start(start_event[(cc+PTR_CTL)%NEV]),.bad(bad_group[cc%BAD_GROUPS]),.slot(unused_slot),.gap_step(cg_step[cc]));
            (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_crl(.count(global_count),.armed(armed),.valid(mc_q[25]),.match(mc_q[24]),.en(crl_write[cc]));
            (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_crm(.count(global_count),.armed(armed),.valid(mc_q[25]),.match(mc_q[24]),.en(crm_write[cc]));
        end
    end else begin:g_control_direct
        assign event_due={NEV{due}};assign pointer_due={PTR_CTL{due}};assign pointer_adv={PTR_CTL{radv}};
        assign slot_step={PTR_CTL{armed && ph==cg}};
        assign gap_step={PTR_CTL{(armed && ph==cg) || (st && !armed && !hcfg_bad)}};
        assign cg_step={3{(armed && ph==cg) || (st && !armed && !hcfg_bad)}};
        assign crl_write={3{mc_q[25] && idle && mc_q[24]}};assign crm_write=crl_write;
    end endgenerate

    wire [NSLOT-1:0] gxn = (MUT == 5 || |(gx & gm)) ? OH0 : {gx[NSLOT-2:0], 1'b0};   // MUT 5: gap table index stuck at 0
    dsdv_mu_hwin_capture_1019_mem #(.W(24),.AW(SI)) u_gap(.ck(ck),.rst_n(rr[MEM_RBASE +: 3]),
        .we(mc_q[25] && !mc_q[24] && !armed && table_empty && gn != SJ'(NSLOT)),
        .wa(gn[SI-1:0]),.wd(mc_q[23:0]-24'd1),.ra(gxb),.q(ng));
    wire retire_wrap=(|(rp&lm)) || rp[NSLOT-1];
    // HWIN21cb: SRAM read address after the next edge = inc(next pointer) under the NEXT limit (lm <= decode(lw)),
    // built from registered state; the advance compare only selects between two precomputed candidates.
    wire [SI-1:0] rpb_inc1=rpb+1'b1;   // wraps only where rra_* select 0
    wire [SI-1:0] rra_hold=(rpb==lw || rpb==SI'(NSLOT-1)) ? SI'(0) : rpb_inc1;
    wire [SI-1:0] rra_zero=(lw==SI'(0)) ? SI'(0) : SI'(1);
    wire [SI-1:0] rra_adv=retire_wrap ? rra_zero : (rpb_inc1==lw || rpb_inc1==SI'(NSLOT-1)) ? SI'(0) : rpb_inc1+1'b1;
    wire [SI-1:0] rra_d=!rr[RPTR_BASE+6*SLOT_RG] ? rra_zero : radv ? rra_adv : rra_hold;
    generate if(EARLY_HEAD_CAPTURE==0) begin:g_retire_legacy
    dsdv_mu_hwin_capture_1019_mem #(.W(32),.AW(SI)) u_retire(.ck(ck),.rst_n(rr[MEM_RBASE+3 +: 4]),
        .we(rec_q),.wa(ssqb),.wd(tsq),.ra(rpb),.q(h_rts));
    end else begin:g_retire_early
    dsdv_mu_hwin_capture_1019_mem_early_capture #(.W(32),.AW(SI),.RA_RESET((NSLOT>1)?1:0)) u_retire(.ck(ck),.rst_n(rr[MEM_RBASE+3 +: 4]),
        .we(rec_q),.wa(ssqb),.wd(tsq),.ra_current(rpb),.ra_d(rra_d),.load_d(radv),.q(h_rts));
    end endgenerate
    always @(posedge ck) tmr <= tm1 - {8'd0,crm};
    // ---- event rows
    wire [31:0] ts_event[0:NEV-1], tm_event[0:NEV-1];
    wire [23:0] rl_event[0:NEV-1]; wire [NEV-1:0] idle_event, rec_local, armed_event, start_event;
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
    wire [PTR_CTL-1:0] fire_region[0:NEV-1];
    generate for(genvar fe=0;fe<NEV;fe=fe+1) begin:g_fire_region
        for(genvar fg=0;fg<PTR_CTL;fg=fg+1) begin:g_group
            if(LOCAL_BOOT!=0) begin:g_local
                (* keep=1 *) dsdv_mu_hwin_capture_1019_fire_flag u_fire(.fresh(h_fr[fe]),.ok(okq[fe]),.equal_time(eqn[fe]),.fire(fire_region[fe][fg]));
            end else begin:g_direct assign fire_region[fe][fg]=fire[fe];end
        end
    end endgenerate
    integer e4;
    always @(posedge ck) for (e4 = 0; e4 < NEV; e4 = e4 + 1) begin
        for(integer fs=0;fs<NSLOT;fs=fs+1) fd[e4][fs] <= (fd[e4][fs] || (fire_region[e4][fs/8] && pe[e4][fs])) && !(rec_event[e4][fs/24] && ssq[fs]);   // no reset: cleared at the staged record, read only on valid entries
        okq[e4] <= ok[e4];                                  // = ok on the next edge while the head stays fresh (legal config)
        // head compares one edge ahead: h_ts == tm + 1 - D (fire on the next edge) / h_ts - (tm + 1 - D) < 0 (late);
        // used only while the head stays fresh across both edges (h_fr now and next), so the entry is the same
        eqn[e4] <= h_fr[e4] && h_ts[e4] == tm_event[e4];
        ltn[e4] <= h_fr[e4] && dlm[e4];
    end
    // outputs from the fired heads: on each endpoint the highest-numbered firing event wins (the former loop order)
    reg fq0, fq1;
    reg rtbad, m; reg [NEP*34-1:0] c_n;wire [NEP*34-1:0] c_q;reg [NEP*11-1:0] rc_n;wire [NEP*11-1:0] rc_q; wire col_w;
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
            reg collision_latched_r; assign collision_q[op]=collision_latched_r;
            always @(posedge ck or negedge rr[SEL_RBASE+NEP*NEV*4+op])
                if(!rr[SEL_RBASE+NEP*NEV*4+op]) collision_latched_r<=1'b0; else collision_latched_r<=next_collision[op];
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
    wire [PTR_CTL-1:0] record_group;
    generate for(genvar rg=0;rg<PTR_CTL;rg=rg+1) begin:g_record_control
        if(LOCAL_BOOT!=0) begin:g_local
            (* keep=1 *) dsdv_mu_hwin_capture_1019_record u_record(.start(start_event[rg%NEV]),.on_calendar(on_cal),.collision(col),.duplicate(udup),.armed(armed_event[rg%NEV]),.bad(bad_group[(rg/2)%BAD_GROUPS]),.record(record_group[rg]));
        end else begin:g_direct assign record_group[rg]=rec;end
    end endgenerate
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
                if(!rr[RWRITE_BASE+wc*SLOT_RG+ws/24]) we_r<=1'b0; else we_r<=record_group[ws/8] && ss[ws];
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
            if(NSLOT<=48) begin:g_bounded_decode
                wire [23:0] lower_decode,upper_decode;
                (* keep=1 *) dsdv_mu_hwin_capture_1019_decode24 u_lower(.address(6'(pb_r)),.onehot(lower_decode));
                (* keep=1 *) dsdv_mu_hwin_capture_1019_decode24 u_upper(.address(6'(upper_pointer_r)-6'(SPLIT)),.onehot(upper_decode));
                assign pe_r={upper_decode[NSLOT-SPLIT-1:0],lower_decode[SPLIT-1:0]};
            end else begin:g_full_decode
                wire [NSLOT-1:0] lower_decode=OH0 << pb_r;
                wire [NSLOT-1:0] upper_decode=OH0 << upper_pointer_r;
                assign pe_r={upper_decode[NSLOT-1:SPLIT],lower_decode[SPLIT-1:0]};
            end
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
        wire event_wrap=(|(pe_r&lm_event[se])) || pe_r[NSLOT-1];
        // HWIN21cb: registered read address precompute (see retire): inc(next pointer) under the next limit
        // lm_event <= decode(lw_event); adv only selects between two candidates computed from registers.
        wire [SI-1:0] pb_inc1=pb_r+1'b1;   // wraps only where ra_* select 0
        wire [SI-1:0] ra_hold=(pb_r==lw_event[se] || pb_r==SI'(NSLOT-1)) ? SI'(0) : pb_inc1;
        wire [SI-1:0] ra_zero=(lw_event[se]==SI'(0)) ? SI'(0) : SI'(1);
        wire [SI-1:0] ra_adv=event_wrap ? ra_zero : (pb_inc1==lw_event[se] || pb_inc1==SI'(NSLOT-1)) ? SI'(0) : pb_inc1+1'b1;
        wire [SI-1:0] ra_after=!rr[se+1] ? ra_zero : adv[se] ? ra_adv : ra_hold;
        if(EARLY_HEAD_CAPTURE==0) begin:g_legacy
        dsdv_mu_hwin_capture_1019_mem #(.W(63),.AW(SI)) u_payload(.ck(ck),.rst_n(rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se +: 8]),.we(rec_event[se][0]),
            .wa(ssqb),.wd({due_at_start,spq,suq}),.ra(pbi[se]),.q(head));
        dsdv_mu_hwin_capture_1019_mem #(.W(2),.AW(SI)) u_attr(.ck(ck),.rst_n(rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se+8]),
            .we(attr_boot[se]),
            .wa(cfg_addr[se]),.wd(cfg_attr[se]),.ra(pbi[se]),.q(h_at[se]));
        end else begin:g_early
        dsdv_mu_hwin_capture_1019_mem_early_capture #(.W(63),.AW(SI),.RA_RESET((NSLOT>1)?1:0)) u_payload(.ck(ck),.rst_n(rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se +: 8]),.we(rec_event[se][0]),
            .wa(ssqb),.wd({due_at_start,spq,suq}),.ra_current(pbi[se]),.ra_d(ra_after),.load_d(adv[se]),.q(head));
        dsdv_mu_hwin_capture_1019_mem_early_capture #(.W(2),.AW(SI),.RA_RESET((NSLOT>1)?1:0)) u_attr(.ck(ck),.rst_n(rr[MEM_EVENT_RBASE+MEM_EVENT_STRIDE*se+8]),
            .we(attr_boot[se]),.wa(cfg_addr[se]),.wd(cfg_attr[se]),.ra_current(pbi[se]),.ra_d(ra_after),.load_d(adv[se]),.q(h_at[se]));
        end
        assign h_ts[se]=head[62:31]; assign h_ep[se]=head[30:10]; assign h_eu[se]=head[9:0];
    end endgenerate
    // Same-edge physical copies: independent event address, due-time, compare-time,
    // boot bounds and wrap state. Distinct reset roots prevent cross-event merging.
    wire [20:0] boot_data[0:NBOOT_GROUPS-1];
    generate for(genvar bg=0;bg<NBOOT_GROUPS;bg=bg+1) begin:g_boot_data
        if(LOCAL_BOOT!=0) begin:g_local
            (* keep *) reg [20:0] data_r;
            always @(posedge ck or negedge rr[RBOOT_DATA+bg])
                if(!rr[RBOOT_DATA+bg]) data_r<=0; else data_r<=mw_in[(2*bg)/NBOOT_GROUPS][20:0];
            assign boot_data[bg]=data_r;
        end else begin:g_direct assign boot_data[bg]=mw_q[20:0];end
    end endgenerate
    wire [23:0] mc_limit_input;
    generate if(CHECK_STAGE!=0) begin:g_limit_input
        (* keep *) reg [23:0] payload_r;
        always @(posedge ck or negedge rr[RMC_LIMIT])
            if(!rr[RMC_LIMIT]) payload_r<=0;else payload_r<=mc_in[0][23:0];
        assign mc_limit_input=payload_r;
    end else begin:g_limit_direct assign mc_limit_input=mc_q[23:0];end endgenerate
    wire [23:0] mc_limit_word=mc_limit_input-24'd2;
    wire mc_limit_small=mc_limit_input<24'd2;
    wire [6:0] min_word=(gn==0)?7'(NSLOT+2):7'(gn)+7'd3;
    genvar ce, rcg;
    generate for(ce=0;ce<NEV;ce=ce+1) begin:g_event_broadcast
        wire [25:0] ev_mw=mw_in[(2*ce)/NEV], ev_mc=mc_in[(2*ce)/NEV];
        (* keep *) reg [31:0] ts_r, time_r;
        reg [23:0] rl_r;
        (* keep *) reg [SI-1:0] lw_r;
        wire [NSLOT-1:0] lm_r;
        (* keep *) reg arm_r;
        // Decode at the existing input landing edge, independently per event.
        // Sharing mc_valid/type AND empty-table produced a 400-load boot enable.
        (* keep *) reg cfg_gap_r,cfg_rl_r,start_r,cfg_w0_r,cfg_w1_r,cfg_w2_r,cfg_sel_r;
        (* keep *) reg [SI-1:0] cfg_addr_r;
        wire [EI-1:0] cfg_kind_r;
        if(SI>=EI) begin:g_kind_alias
            assign cfg_kind_r=cfg_addr_r[EI-1:0];
        end else begin:g_kind_extra
            (* keep *) reg [EI-1:0] kind_r;
            always @(posedge ck or negedge rr[COPY_RBASE+7*ce+6])
                if(!rr[COPY_RBASE+7*ce+6]) kind_r<=0;else kind_r<=ev_mw[EI-1:0];
            assign cfg_kind_r=kind_r;
        end
        (* keep *) reg [1:0] cfg_attr_r;
        assign cfg_addr[ce]=cfg_addr_r; assign cfg_attr[ce]=cfg_attr_r;
        assign rec_local[ce]=start_r && on_cal && !col && !udup && !(!arm_r && bad_group[ce/4]);
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce+6])
            if(!rr[COPY_RBASE+7*ce+6]) begin cfg_gap_r<=1'b0;cfg_rl_r<=1'b0;start_r<=1'b0;cfg_w0_r<=0;cfg_w1_r<=0;cfg_w2_r<=0;cfg_sel_r<=0;cfg_addr_r<=0;cfg_attr_r<=0;end
            else begin cfg_sel_r<=((wv && idle && mw_q[22:21]==2'd0)?mw_q[EI-1:0]:esel)==EI'(ce);cfg_w0_r<=ev_mw[25] && ev_mw[22:21]==2'd0;cfg_w1_r<=ev_mw[25] && ev_mw[22:21]==2'd1;cfg_w2_r<=ev_mw[25] && ev_mw[22:21]==2'd2;cfg_gap_r<=ev_mc[25] && !ev_mc[24];cfg_rl_r<=ev_mc[25] && ev_mc[24];start_r<=f_ks[52];cfg_addr_r<=ev_mw[SI-1:0];cfg_attr_r<=ev_mw[11:10];end
        wire [6:0] boot_count;
        wire [2:0] d_write;
        wire attr_write,kind_write,rl_write,gap_write;
        if(LOCAL_BOOT!=0) begin:g_boot_local
            (* keep *) reg [SJ-1:0] count_r;
            always @(posedge ck or negedge rr[RBOOT_BASE+ce])
                if(!rr[RBOOT_BASE+ce]) count_r<=0;
                else count_r<=count_r+SJ'(rec_event[ce][NC_REC-1])-SJ'(event_due[ce]);
            assign boot_count=7'(count_r);
`ifdef DSDV_MU_POINTER_ASSERT
            always @(posedge ck) if(rr[RBOOT_BASE+ce])
                if(count_r!==SJ'($countones(vld))) $fatal(1,"event boot count differs event%0d",ce);
`endif
            for(genvar dg=0;dg<3;dg=dg+1) begin:g_d_enable
                (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_write(.count(boot_count),.armed(arm_r),.valid(cfg_w1_r),.match(cfg_sel_r),.en(d_write[dg]));
            end
            (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_attr(.count(boot_count),.armed(arm_r),.valid(cfg_w2_r),.match(esel==EI'(ce)),.en(attr_write));
            (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_kind(.count(boot_count),.armed(arm_r),.valid(cfg_w0_r),.match(cfg_kind_r==EI'(ce)),.en(kind_write));
            if(CHECK_STAGE==0) begin:g_reference_rl
                (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_rlwrite(.count(boot_count),.armed(arm_r),.valid(cfg_rl_r),.match(1'b1),.en(rl_write));
            end else begin:g_unused_rl assign rl_write=1'b0;end
            (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_gap(.count(boot_count),.armed(arm_r),.valid(cfg_gap_r),.match(gn!=SJ'(NSLOT)),.en(gap_write));
        end else begin:g_boot_direct
            assign boot_count=global_count;
            assign d_write={3{wv && idle_event[ce] && mw_q[22:21]==2'd1 && esel==EI'(ce)}};
            assign attr_write=wv && idle_event[ce] && mw_q[22:21]==2'd2 && esel==EI'(ce);
            assign kind_write=wv && idle_event[ce] && mw_q[22:21]==2'd0 && mw_q[EI-1:0]==EI'(ce);
            assign rl_write=cfg_rl_r && idle_event[ce];
            assign gap_write=cfg_gap_r && idle_event[ce] && gn!=SJ'(NSLOT);
        end
        assign attr_boot[ce]=attr_write;
        if(CHECK_STAGE!=0) begin:g_check_limits
            reg [23:0] limit_r;
            reg small_r;
            reg [6:0] min_r;
            wire [2:0] limit_write;
            for(genvar lg=0;lg<3;lg=lg+1) begin:g_limit_enable
                (* keep=1 *) dsdv_mu_hwin_capture_1019_boot_enable u_write(.count(boot_count),.armed(arm_r),.valid(cfg_rl_r),.match(1'b1),.en(limit_write[lg]));
            end
            for(genvar lb=0;lb<24;lb=lb+1) begin:g_limit_storage
                always @(posedge ck or negedge rr[RPRED_BASE+ce])
                    if(!rr[RPRED_BASE+ce]) limit_r[lb]<=1;
                    else if(limit_write[lb/8]) limit_r[lb]<=mc_limit_word[lb];
            end
            always @(posedge ck or negedge rr[RPRED_BASE+ce])
                if(!rr[RPRED_BASE+ce]) begin small_r<=1;min_r<=7'(NSLOT+2);end
                else begin
                    if(limit_write[0]) small_r<=mc_limit_small;
                    if(gap_write) min_r<=min_word;
                end
            // Limits update at the exact original CSR state edge. The direct
            // checker then observes that current state, exactly CHECK_STAGE0,
            // with the constant RL subtraction removed from its start path.
            assign invalid_event[ce]=evld[ce] && ({3'd0,eD[ce]} < {17'd0,min_r} || small_r || {3'd0,eD[ce]} > limit_r);
        end else begin:g_check_direct
            assign invalid_event[ce]=evld[ce] && ({3'd0,eD[ce]} < (24'(lw_r)+24'd3) || {3'd0,eD[ce]}+24'd2 > rl_r);
        end
        assign ts_event[ce]=ts_r; assign tm_event[ce]=time_r;
        assign rl_event[ce]=rl_r; assign lw_event[ce]=lw_r;
        assign armed_event[ce]=arm_r;assign start_event[ce]=start_r;
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
            (* keep *) reg bit_r;assign lm_r[lb]=bit_r;
            always @(posedge ck or negedge rr[RLM_BASE+ce*SLOT_RG+lb/24])
                if(!rr[RLM_BASE+ce*SLOT_RG+lb/24]) bit_r<=(lb==NSLOT-1);
                else bit_r<=(lw_r==SI'(lb));
        end
        always @(posedge ck or negedge rr[COPY_RBASE+7*ce+5])
            if(!rr[COPY_RBASE+7*ce+5]) arm_r<=1'b0;
            else if(start_r && !arm_r && !bad_group[ce/4]) arm_r<=1'b1;
        for(genvar db=0;db<21;db=db+1) begin:g_d_storage
            always @(posedge ck) if(d_write[db/8]) eD[ce][db]<=boot_data[ce/4][db];
        end
`ifdef DSDV_MU_POINTER_ASSERT
        always @(posedge ck) if(rn && LOCAL_BOOT!=0 && cfg_w1_r)
            if(cfg_sel_r !== (esel==EI'(ce))) $fatal(1,"boot selector lookahead mismatch e%0d",ce);
`endif
        always @(posedge ck) begin
            if(kind_write) begin
                ek[ce]<=boot_data[ce/4][8]; eep[ce]<=boot_data[ce/4][9+:PI];
            end
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
        reg data_r;assign c_q[ob]=data_r;
        always @(posedge ck or negedge rr[ROUT_BASE+ob/24])
            if(!rr[ROUT_BASE+ob/24]) data_r<=0; else data_r<=c_n[ob];
    end
    for(genvar ob=0;ob<NEP*11;ob=ob+1) begin:g_replay_output_reset
        reg data_r;assign rc_q[ob]=data_r;
        always @(posedge ck or negedge rr[ROUT_BASE+C_RG+ob/24])
            if(!rr[ROUT_BASE+C_RG+ob/24]) data_r<=0; else data_r<=rc_n[ob];
    end
    for(genvar pb=0;pb<NSLOT;pb=pb+1) begin:g_pointer_reset
        reg sl_r,rp_r,gx_r,gm_r,lm_bit_r,vld_r;
        assign sl[pb]=sl_r;assign rp[pb]=rp_r;assign gx[pb]=gx_r;
        assign gm[pb]=gm_r;assign lm[pb]=lm_bit_r;assign vld[pb]=vld_r;
        wire step_slot=slot_step[pb/8];
        wire step_gap=gap_step[pb/8];
        wire [NSLOT-1:0] sl_next=rot(sl,lm),rp_next=rot(rp,lm);
        always @(posedge ck or negedge rr[RPTR_BASE+pb/24])
            if(!rr[RPTR_BASE+pb/24]) sl_r<=(pb==0); else if(step_slot) sl_r<=sl_next[pb];
        always @(posedge ck or negedge rr[RPTR_BASE+SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+SLOT_RG+pb/24]) rp_r<=(pb==0); else if(pointer_adv[pb/8]) rp_r<=rp_next[pb];
        always @(posedge ck or negedge rr[RPTR_BASE+2*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+2*SLOT_RG+pb/24]) gx_r<=(pb==0); else if(step_gap) gx_r<=gxn[pb];
        always @(posedge ck or negedge rr[RPTR_BASE+3*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+3*SLOT_RG+pb/24]) gm_r<=0;
            else if(mc_q[25] && idle && !mc_q[24] && gn!=SJ'(NSLOT)) gm_r<=(gn[SI-1:0]==SI'(pb));
        always @(posedge ck or negedge rr[RPTR_BASE+4*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+4*SLOT_RG+pb/24]) lm_bit_r<=(pb==NSLOT-1); else lm_bit_r<=(lw==SI'(pb));
        always @(posedge ck or negedge rr[RPTR_BASE+5*SLOT_RG+pb/24])
            if(!rr[RPTR_BASE+5*SLOT_RG+pb/24]) vld_r<=0; else vld_r<=(vld[pb] && !(pointer_due[pb/8] && rp[pb])) || rec_slot[pb];
    end endgenerate
    always @(posedge ck or negedge rr[RPTR_BASE+6*SLOT_RG])
        if(!rr[RPTR_BASE+6*SLOT_RG]) begin slb<=0;rpb<=0;gxb<=0;end
        else begin
            if(armed && ph==cg) slb<=((|(sl&lm)) || sl[NSLOT-1])?SI'(0):slb+1'b1;
            if((armed && ph==cg) || (st && !armed && !hcfg_bad))
                gxb<=(MUT==5 || {1'b0,gxb}+1'b1>=gn)?SI'(0):gxb+1'b1;
            if(radv) rpb<=((|(rp&lm)) || rp[NSLOT-1])?SI'(0):rpb+1'b1;
        end
    wire [23:0] phase_increment=ph+24'd1;
    wire [2:0] phase_set,phase_clear,phase_step;
    generate for(genvar pg=0;pg<3;pg=pg+1) begin:g_phase_control
        if(LOCAL_BOOT!=0) begin:g_local
            (* keep=1 *) dsdv_mu_hwin_capture_1019_phase_action u_action(.phase(ph),.gap(cg),.armed(armed_event[pg%NEV]),.start(start_event[pg%NEV]),.bad(bad_group[pg%BAD_GROUPS]),
                .set_one(phase_set[pg]),.clear(phase_clear[pg]),.increment(phase_step[pg]));
        end else begin:g_direct
            assign phase_set[pg]=st && !armed && !hcfg_bad;
            assign phase_clear[pg]=armed && ph==cg;assign phase_step[pg]=armed && ph!=cg;
        end
    end
    for(genvar pb=0;pb<24;pb=pb+1) begin:g_phase_state
        reg bit_r;assign ph[pb]=bit_r;
        always @(posedge ck or negedge rr[RCTRL_BASE])
            if(!rr[RCTRL_BASE]) bit_r<=0;
            else if(phase_set[pb/8]) bit_r<=(pb==0);
            else if(phase_clear[pb/8]) bit_r<=0;
            else if(phase_step[pb/8]) bit_r<=phase_increment[pb];
    end endgenerate
    always @(posedge ck or negedge rr[RCTRL_BASE+1])
        if(!rr[RCTRL_BASE+1]) cs<=0;
        else if(mc_q[25] && idle && !mc_q[24] && gn!=SJ'(NSLOT) && (gn==0 || mc_q[23:0]<cs)) cs<=mc_q[23:0];
    wire [23:0] mc_minus_one=mc_q[23:0]-24'd1;
    generate for(genvar cfg_bit=0;cfg_bit<24;cfg_bit=cfg_bit+1) begin:g_config_words
        always @(posedge ck or negedge rr[RCTRL_BASE+2])
            if(!rr[RCTRL_BASE+2]) crl[cfg_bit]<=0; else if(crl_write[cfg_bit/8]) crl[cfg_bit]<=mc_q[cfg_bit];
        always @(posedge ck or negedge rr[RCTRL_BASE+3])
            if(!rr[RCTRL_BASE+3]) crm[cfg_bit]<=1; else if(crm_write[cfg_bit/8]) crm[cfg_bit]<=mc_minus_one[cfg_bit];
        always @(posedge ck or negedge rr[RCTRL_BASE+4])
            if(!rr[RCTRL_BASE+4]) cg[cfg_bit]<=0; else if(cg_step[cfg_bit/8]) cg[cfg_bit]<=ng[cfg_bit];
    end endgenerate
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

(* keep_hierarchy="yes" *) module dsdv_mu_hwin_capture_1019_boot_enable(input wire [6:0] count,input wire armed,valid,match,output wire en);
 assign en=(count==0) && !armed && valid && match;
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_retire_due(input wire valid,fresh,input wire [31:0] retire,now_time,output wire due);
 assign due=valid && fresh && retire==now_time;
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_retire_advance(input wire valid,fresh,hold_head,input wire [31:0] retire,now_time,output wire due,advance);
 assign due=valid && fresh && retire==now_time;
 assign advance=due || (!valid && !hold_head);
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_slot_step(input wire [23:0] phase,gap,input wire armed,start,bad,output wire slot,gap_step);
 assign slot=armed && phase==gap;
 assign gap_step=slot || (start && !armed && !bad);
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_record(input wire start,on_calendar,collision,duplicate,armed,bad,output wire record);
 assign record=start && on_calendar && !collision && !duplicate && !(!armed && bad);
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_decode24(input wire [5:0] address,output wire [23:0] onehot);
 genvar k;generate for(k=0;k<24;k=k+1) begin:g_bit assign onehot[k]=(address==6'(k));end endgenerate
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_fire_flag(input wire fresh,ok,equal_time,output wire fire);
 assign fire=fresh && ok && equal_time;
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_cfg_bad(input wire [6:0] count,input wire [23:0] min_gap,return_gap,input wire [5:0] last_slot,output wire bad);
 wire [23:0] n={18'd0,last_slot}+24'd1;
 assign bad=count==0 || min_gap<n || return_gap<=n;
endmodule

(* keep_hierarchy=1 *) module dsdv_mu_hwin_capture_1019_phase_action(input wire [23:0] phase,gap,input wire armed,start,bad,output wire set_one,clear,increment);
 assign set_one=start && !armed && !bad;
 assign clear=armed && phase==gap;assign increment=armed && phase!=gap;
endmodule
