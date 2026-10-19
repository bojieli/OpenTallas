`timescale 1ns/1ps
// MU-S81-2/DIE bench (port of MU-S81/DIE tb_dsdv_mu_win, 908a67c18) for the NEW leaf dsdv_mu_hwin BESIDE the CLOSED
// dsdv_mu_hslot (NEV-free, source untouched): both tap the same start pin f_ks and the same S / RL boot words f_mc;
// the window rows come on hwin's own word stream f_mw (die: host CSR 0x16), so hslot never sees a window word.
// NU users on an NP-slot shift calendar (slot S), 3 events {TX ep0 D 20, TX ep1 D 33, replay ep0 D 47}, per-slot
// {land, ab} attributes.  The unit's return is the stand-in loopback t_kd done = t_ku valid.  Checks:
//   * every event of every start fires exactly once, at start + D + K (K the same constant for every event / start),
//     on its endpoint, with the start's {pos, user} and the slot's {land, ab}; a replay only where land = 1;
//   * RX tags (mu_rt) of outstanding {user, pos} raise no fault; t_ku trace ("KU ...") is printed for the NEV 0 diff;
//   * hslot t_mf stays 0 and hwin t_wf stays 0 (no window word reaches hslot; both tables agree);
//   * BADRT 1: one RX tag of a user that is not outstanding -> hwin t_wf[0] must rise.
// WMUT (RTL mutants of dsdv_mu_hwin): 3 = ab bit dropped, 4 = replay enable ignored -> both must FAIL.
// PASS line "MUWIN PASS".
module tb_dsdv_mu_hwin_early_capture;
`ifndef NEV
    localparam integer NEV = 16;
`else
    localparam integer NEV = `NEV;
`endif
`ifndef BADRT
    localparam integer BADRT = 0;
`else
    localparam integer BADRT = `BADRT;
`endif
`ifndef WMUT
    localparam integer WMUT = 0;
`else
    localparam integer WMUT = `WMUT;
`endif
    `ifndef NSLOT_TEST
    localparam integer NS=8;
`else
    localparam integer NS=`NSLOT_TEST;
`endif
    localparam integer NU=NS, S=
`ifdef SWEEP256
256,
`else
64,
`endif
ROUNDS=4, T0=1000+32*NS;
    localparam integer RL = NS * S - S / 2 - 3;
    localparam integer NE = NEV;
    integer DK [0:NE-1], KD [0:NE-1], EP [0:NE-1];        // D / kind / endpoint per event
    integer cfg_e; initial begin
      for(cfg_e=0;cfg_e<NE;cfg_e=cfg_e+1) begin DK[cfg_e]=20+13*cfg_e; KD[cfg_e]=(cfg_e%3==2); EP[cfg_e]=cfg_e%4; end
`ifdef MIN_D
      for(cfg_e=0;cfg_e<NE;cfg_e=cfg_e+1) DK[cfg_e]=NS+2+13*cfg_e;
`endif
`ifdef BAD_D
      DK[0]=NS+1;
`endif
`ifdef BAD_D_HIGH
      DK[0]=RL-1;
`endif
`ifdef COLLIDE_EVENTS
      DK[1]=DK[0]; KD[1]=0; EP[1]=EP[0];
`endif
    end
    integer first_cfg_fault=-1;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    integer cyc = 0, errs = 0, i, e, nfire = 0, nexp = 0;
    reg [52:0] f_ks = 0; reg [25:0] f_mc = 0, f_mw = 0; reg [2*32-1:0] mu_rt = 0;
    wire [31:0] ku; wire [3:0] hmf; wire [1:0] wf; wire [4*34-1:0] mu_c; wire [4*11-1:0] mu_rc;
    wire [3:0] mf = {hmf[3] | wf[1], hmf[2] | wf[0], hmf[1:0]};      // the die master's t_mf fold
    dsdv_mu_hslot #(.NSLOT(NS), .MUT(0)) u_hs (.ck(ck), .rst_n(rst_n), .f_ks(f_ks),
        .f_kd({ku[31], 53'd0}), .f_mc(f_mc), .t_ku(ku), .t_mf(hmf));
`ifndef ANCHOR_ONLY_REPRO
    dsdv_mu_hwin #(.NSLOT(NS), .NEV(NEV), .NEP(4), .NRT(2), .MUT(WMUT), .HEAD_STAGE(1), .COMPACT_PTR(1), .CHECK_STAGE(1), .LIVE_COUNT(1), .RAW_SELECT(1), .LOCAL_BOOT(1),.EARLY_HEAD_CAPTURE(1)) dut (.ck(ck), .rst_n(rst_n), .f_ks(f_ks),
        .f_mc(f_mc), .f_mw(f_mw), .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(mu_rt), .t_wf(wf));
`endif
    wire [4*34-1:0] anchor_c; wire [4*11-1:0] anchor_rc; wire [1:0] anchor_wf;
    dsdv_mu_hwin #(.NSLOT(NS),.NEV(NEV),.NEP(4),.NRT(2),.MUT(WMUT),
       .HEAD_STAGE(1),.COMPACT_PTR(1),.CHECK_STAGE(1),.LIVE_COUNT(1),.RAW_SELECT(1),.LOCAL_BOOT(1),.EARLY_HEAD_CAPTURE(0)) anchor
       (.ck(ck),.rst_n(rst_n),.f_ks(f_ks),.f_mc(f_mc),.f_mw(f_mw),.mu_c(anchor_c),.mu_rc(anchor_rc),.mu_rt(mu_rt),.t_wf(anchor_wf));
`ifdef ANCHOR_ONLY_REPRO
    assign mu_c=anchor_c; assign mu_rc=anchor_rc; assign wf=anchor_wf;
`else
    integer miter_edges=0,mi;
    always @(negedge ck) begin
`ifdef FOUR_STATE_GUARDS
       if(rst_n && $isunknown({mu_c,mu_rc,wf,anchor_c,anchor_rc,anchor_wf})) begin
          $display("EARLY_X_TELEMETRY c%0d rst%0b dutrn%0b anchorrn%0b dutrr%h anchorrr%h",cyc,rst_n,dut.rn,anchor.rn,dut.rr,anchor.rr);
          $display("EARLY_X_TELEMETRY candidate c=%h rc=%h wf=%b unknown=%b%b%b xor=%b%b%b",mu_c,mu_rc,wf,$isunknown(mu_c),$isunknown(mu_rc),$isunknown(wf),^mu_c,^mu_rc,^wf);
          $display("EARLY_X_TELEMETRY anchor c=%h rc=%h wf=%b unknown=%b%b%b xor=%b%b%b",anchor_c,anchor_rc,anchor_wf,$isunknown(anchor_c),$isunknown(anchor_rc),$isunknown(anchor_wf),^anchor_c,^anchor_rc,^anchor_wf);
          $display("EARLY_X_TELEMETRY count candidate valid=%h evld=%h rec=%b recq=%b armed=%b anchor valid=%h evld=%h rec=%b recq=%b armed=%b",dut.vld,dut.evld,dut.rec,dut.rec_q,dut.armed,anchor.vld,anchor.evld,anchor.rec,anchor.rec_q,anchor.armed);
          $fatal(1,"EARLY_X observable output/fault after external reset release c%0d",cyc);
       end
       if(rst_n && dut.rn && $isunknown({dut.vld,dut.evld,dut.ok,dut.fire,dut.adv,dut.due,dut.radv,dut.armed}))
          $fatal(1,"EARLY_X source-qualified control c%0d",cyc);
`endif
       if({mu_c,mu_rc,wf} !== {anchor_c,anchor_rc,anchor_wf})
          $fatal(1,"EARLY_MITER OUTPUT c%0d actual=%h anchor=%h",cyc,{mu_c,mu_rc,wf},{anchor_c,anchor_rc,anchor_wf});
       if(rst_n && dut.rn && anchor.rn) begin
          if({dut.rp,dut.rpb,dut.rec,dut.rec_q,dut.ok,dut.radv,dut.armed,dut.hold,dut.fire,dut.adv,dut.vld,dut.evld,dut.okq,dut.h_fr,dut.h_rfr,dut.due,dut.rok,dut.rhold,dut.global_count,dut.table_empty} !==
             {anchor.rp,anchor.rpb,anchor.rec,anchor.rec_q,anchor.ok,anchor.radv,anchor.armed,anchor.hold,anchor.fire,anchor.adv,anchor.vld,anchor.evld,anchor.okq,anchor.h_fr,anchor.h_rfr,anchor.due,anchor.rok,anchor.rhold,anchor.global_count,anchor.table_empty})
             $fatal(1,"EARLY_MITER CONTROL c%0d",cyc);
          for(mi=0;mi<NEV;mi=mi+1) begin
`ifdef FOUR_STATE_GUARDS
             if(anchor.ok[mi] && anchor.h_fr[mi] && $isunknown({dut.h_ts[mi],dut.h_ep[mi],dut.h_eu[mi],dut.h_at[mi]}))
                $fatal(1,"EARLY_X qualified head c%0d e%0d",cyc,mi);
             if(anchor.rok && anchor.h_rfr && $isunknown(dut.h_rts))
                $fatal(1,"EARLY_X qualified retirement c%0d",cyc);
`endif
             if({dut.pe[mi],dut.pbi[mi],dut.fd[mi]&dut.vld} !== {anchor.pe[mi],anchor.pbi[mi],anchor.fd[mi]&anchor.vld})
                $fatal(1,"EARLY_MITER POINTER_FD c%0d e%0d",cyc,mi);
             // Raw head contents/compares are unqualified until actual valid/fresh controls.
             if(anchor.okq[mi] && anchor.h_fr[mi] &&
                {dut.eqn[mi],dut.ltn[mi],dut.lt[mi]} !== {anchor.eqn[mi],anchor.ltn[mi],anchor.lt[mi]})
                $fatal(1,"EARLY_MITER QUALIFIED_COMPARE c%0d e%0d",cyc,mi);
             if(anchor.ok[mi] && anchor.h_fr[mi] &&
                {dut.h_ts[mi],dut.h_ep[mi],dut.h_eu[mi],dut.h_at[mi]} !== {anchor.h_ts[mi],anchor.h_ep[mi],anchor.h_eu[mi],anchor.h_at[mi]})
                $fatal(1,"EARLY_MITER QUALIFIED_HEAD c%0d e%0d",cyc,mi);
          end
          if(anchor.rok && anchor.h_rfr && dut.h_rts!==anchor.h_rts)
             $fatal(1,"EARLY_MITER QUALIFIED_RETIRE c%0d",cyc);
       end
       miter_edges=miter_edges+1;
    end
    final $display("EARLY_MITER edges %0d",miter_edges);
`endif
`ifdef HEAD_COMPARE
    wire [4*34-1:0] ref_c; wire [4*11-1:0] ref_rc; wire [1:0] ref_wf;
    integer head_compares=0;
    dsdv_mu_hwin #(.NSLOT(NS),.NEV(NEV),.NEP(4),.NRT(2),.MUT(WMUT),.HEAD_STAGE(0),.COMPACT_PTR(0),.CHECK_STAGE(0),.LIVE_COUNT(0),.RAW_SELECT(0)) ref_direct
        (.ck(ck),.rst_n(rst_n),.f_ks(f_ks),.f_mc(f_mc),.f_mw(f_mw),.mu_c(ref_c),.mu_rc(ref_rc),.mu_rt(mu_rt),.t_wf(ref_wf));
    always @(negedge ck) if(rst_n) begin
        if({mu_c,mu_rc,wf} !== {ref_c,ref_rc,ref_wf})
            $fatal(1,"HEAD_STAGE edge mismatch cycle%0d staged=%h direct=%h",cyc,{mu_c,mu_rc,wf},{ref_c,ref_rc,ref_wf});
        head_compares=head_compares+1;
    end
    final $display("HEAD_STAGE_EQUIV comparisons %0d",head_compares);
`endif
`ifndef ORIGINAL_ASSERT_REPRO
    localparam integer SI=(NS>1)?$clog2(NS):1, EI=(NEV>1)?$clog2(NEV):1;
    localparam [NS-1:0] OH0={{(NS-1){1'b0}},1'b1};
    // Original assertion inventory, qualified only by external reset plus its original enable.
    always @(posedge ck) if(rst_n && anchor.rn && anchor.rr[anchor.COPY_END])
       if(anchor.g_live_count.count_r !== (SI+1)'($countones(anchor.vld))) $fatal(1,"live-count differs from valid table");
    for(genvar ac_anchor=0;ac_anchor<NEV;ac_anchor=ac_anchor+1) begin:g_assert_anchor
       always @(posedge ck) if(rst_n && anchor.rr[anchor.RBOOT_BASE+ac_anchor])
          if(anchor.g_event_broadcast[ac_anchor].g_boot_local.count_r !== (SI+1)'($countones(anchor.vld)))
             $fatal(1,"event boot count differs event%0d",ac_anchor);
       always @(posedge ck) if(rst_n && anchor.rn && anchor.LOCAL_BOOT!=0 && anchor.g_event_broadcast[ac_anchor].cfg_w1_r)
          if(anchor.g_event_broadcast[ac_anchor].cfg_sel_r !== (anchor.esel==EI'(ac_anchor)))
             $fatal(1,"boot selector lookahead mismatch e%0d",ac_anchor);
    end
    integer ae_anchor;
    always @(posedge ck or negedge anchor.rn) if(!anchor.rn) begin end else if(rst_n) begin
       if(anchor.rp !== (OH0 << anchor.rpb)) $fatal(1,"retire SRAM pointer mismatch");
       if(anchor.sl !== (OH0 << anchor.slb)) $fatal(1,"slot SRAM pointer mismatch");
       if(anchor.gx !== (OH0 << anchor.gxb)) $fatal(1,"gap SRAM pointer mismatch");
       for(ae_anchor=0;ae_anchor<NEV;ae_anchor=ae_anchor+1)
          if(anchor.pe[ae_anchor] !== (OH0 << anchor.pbi[ae_anchor])) $fatal(1,"event SRAM pointer mismatch e%0d",ae_anchor);
    end
`ifndef ANCHOR_ONLY_REPRO
    // Original assertion inventory, qualified only by external reset plus its original enable.
    always @(posedge ck) if(rst_n && dut.rn && dut.rr[dut.COPY_END])
       if(dut.g_live_count.count_r !== (SI+1)'($countones(dut.vld))) $fatal(1,"live-count differs from valid table");
    for(genvar ac_dut=0;ac_dut<NEV;ac_dut=ac_dut+1) begin:g_assert_dut
       always @(posedge ck) if(rst_n && dut.rr[dut.RBOOT_BASE+ac_dut])
          if(dut.g_event_broadcast[ac_dut].g_boot_local.count_r !== (SI+1)'($countones(dut.vld)))
             $fatal(1,"event boot count differs event%0d",ac_dut);
       always @(posedge ck) if(rst_n && dut.rn && dut.LOCAL_BOOT!=0 && dut.g_event_broadcast[ac_dut].cfg_w1_r)
          if(dut.g_event_broadcast[ac_dut].cfg_sel_r !== (dut.esel==EI'(ac_dut)))
             $fatal(1,"boot selector lookahead mismatch e%0d",ac_dut);
    end
    integer ae_dut;
    always @(posedge ck or negedge dut.rn) if(!dut.rn) begin end else if(rst_n) begin
       if(dut.rp !== (OH0 << dut.rpb)) $fatal(1,"retire SRAM pointer mismatch");
       if(dut.sl !== (OH0 << dut.slb)) $fatal(1,"slot SRAM pointer mismatch");
       if(dut.gx !== (OH0 << dut.gxb)) $fatal(1,"gap SRAM pointer mismatch");
       for(ae_dut=0;ae_dut<NEV;ae_dut=ae_dut+1)
          if(dut.pe[ae_dut] !== (OH0 << dut.pbi[ae_dut])) $fatal(1,"event SRAM pointer mismatch e%0d",ae_dut);
    end
`endif
`ifdef ASSERT_CORRUPT
    initial begin
       wait(rst_n && anchor.rr[anchor.RBOOT_BASE]); @(negedge ck);
       force anchor.g_event_broadcast[0].g_boot_local.count_r = (SI+1)'(1);
    end
`endif
`endif
    // slot attributes: land = slot[0], ab = slot[1]
    function automatic [1:0] att(input integer sl); att = {sl[0] ? 1'b1 : 1'b0, sl[1] ? 1'b1 : 1'b0}; endfunction
    integer stc [0:NU*ROUNDS-1]; integer stu [0:NU*ROUNDS-1]; integer stp [0:NU*ROUNDS-1]; integer nst = 0;
    integer kconst = -1;
    task automatic cfg(input [25:0] w); begin f_mc = w; @(posedge ck); #0.1; f_mc = 0;
`ifndef FAST_CFG
        @(posedge ck); #0.1;
`endif
    end endtask
    task automatic wcfg(input [25:0] w); begin f_mw = w; @(posedge ck); #0.1; f_mw = 0;
`ifndef FAST_CFG
        @(posedge ck); #0.1;
`endif
    end endtask
    always @(posedge ck) cyc <= cyc + 1;
    // ---- monitor: match every output against the starts
    integer s, d, hit, port; reg [1:0] aa; reg [33:0] want_c; reg [10:0] want_r;
    always @(posedge ck) if (rst_n) begin
        if(wf[1] && first_cfg_fault<0) first_cfg_fault=cyc;
        for(port=0;port<4;port=port+1) begin
            want_c=0; want_r=0;
            for(e=0;e<NE;e=e+1) for(s=0;s<nst;s=s+1)
                if(EP[e]==port && cyc==stc[s]+DK[e]+2) begin
                    aa=att(stu[s]);
                    if(KD[e]==0) want_c={stp[s][20:0],stu[s][9:0],aa,1'b1};
                    else if(aa[1]) want_r={stu[s][9:0],1'b1};
                end
            if(mu_c[34*port] || want_c[0]) begin
                if(mu_c[34*port+:34] !== want_c) begin errs=errs+1; $display("ERR c%0d ev0 start0 mu_c %h",cyc,mu_c[34*port+:34]); end
                if(mu_c[34*port]) nfire=nfire+1;
            end
            if(mu_rc[11*port] || want_r[0]) begin
                if(mu_rc[11*port+:11] !== want_r) begin errs=errs+1; $display("ERR c%0d ev2 start0 mu_rc %h",cyc,mu_rc[11*port+:11]); end
                if(mu_rc[11*port]) nfire=nfire+1;
            end
        end
        kconst=2;
        if(ku[31]) $display("KU c%0d user %0d pos %0d",cyc,ku[30:21],ku[20:0]);
    end
    integer r, u, q, j, traffic_t0=T0, reset_phase=0;
    initial begin
        repeat (4) @(posedge ck); #0.1; rst_n = 1; repeat (4) @(posedge ck); #0.1;
        cfg({1'b1, 1'b0, 24'(S)}); cfg({1'b1, 1'b1, 24'(RL)});
        for (q = 0; q < NE; q = q + 1) begin
            wcfg({1'b1, 1'b0, 1'b0, 2'd0, 10'd0, 2'(EP[q]), 1'(KD[q]), 3'd0, 5'(q)});
            wcfg({1'b1, 1'b0, 1'b0, 2'd1, 21'(DK[q])});
            for (j = 0; j < NS; j = j + 1) wcfg({1'b1, 1'b0, 1'b0, 2'd2, 9'd0, att(j), 10'(j)});
        end
`ifdef OCCUPIED_RESET_STRESS
        // Distinct restart scenario: old outstanding generation is canceled by actual async reset.
        // Existing fixed-date checker observes its outputs until reset; no extra warmup is added.
        if($value$plusargs("reset_phase=%d",reset_phase)) begin end
        while(cyc<T0) begin @(posedge ck); #0.1; end
        f_ks={1'b1,10'd0,21'd0,21'd99};
        stc[0]=cyc;stu[0]=0;stp[0]=99;nst=1;
        @(posedge ck);#0.1;f_ks=0;
        repeat(reset_phase) begin @(posedge ck);#0.1;end
        @(negedge ck);#0.17;rst_n=0; f_mc=0;f_mw=0;mu_rt=0;nst=0;
        #0.01;
        if({mu_c,mu_rc,wf,anchor_c,anchor_rc,anchor_wf}!==0)
           $fatal(1,"EARLY_RESET async assertion did not clear outputs");
        repeat(4) @(posedge ck);#0.1;rst_n=1;
        repeat(4) @(posedge ck);#0.1;
        cfg({1'b1,1'b0,24'(S)});cfg({1'b1,1'b1,24'(RL)});
        for(q=0;q<NE;q=q+1) begin
           wcfg({1'b1,1'b0,1'b0,2'd0,10'd0,2'(EP[q]),1'(KD[q]),3'd0,5'(q)});
           wcfg({1'b1,1'b0,1'b0,2'd1,21'(DK[q])});
           for(j=0;j<NS;j=j+1) wcfg({1'b1,1'b0,1'b0,2'd2,9'd0,att(j),10'(j)});
        end
        // New epoch dates are the actual new starts, retaining original D+2/D+3 gold.
        traffic_t0=cyc+1; nfire=0;errs=0;first_cfg_fault=-1;
        $display("EARLY_RESET phase%0d restart_start%0d",reset_phase,traffic_t0);
`endif
        while (cyc < traffic_t0) begin @(posedge ck); #0.1; end
        for (r = 0; r < ROUNDS; r = r + 1)
            for (u = 0; u < NU; u = u + 1) begin
                while (cyc < traffic_t0 + (r * NS + u) * S) begin @(posedge ck); #0.1; end
                f_ks = {1'b1, 10'(u), 21'd0, 21'(r)};
                stc[nst] = cyc; stu[nst] = u; stp[nst] = r; nst = nst + 1;
                // RX tag of an outstanding start (the previous user), on both returning end slices
                if (nst > 1) mu_rt = {{1'b1, 10'(stu[nst-2]), 21'(stp[nst-2])}, {1'b1, 10'(stu[nst-2]), 21'(stp[nst-2])}};
                if (BADRT && r == 2 && u == 3) mu_rt[31:0] = {1'b1, 10'd77, 21'd5};
                @(posedge ck); #0.1; f_ks = 0; mu_rt = 0;
            end
        repeat (RL + 100) @(posedge ck);
        for(j=0;j<nst;j=j+1) for(e=0;e<NE;e=e+1) if(KD[e]==0 || att(stu[j])/2) nexp=nexp+1;
`ifdef COLLIDE_EVENTS
        nexp=nexp-nst; // two TX rows target one output at the same edge
`endif
        $display("MUWIN starts %0d fires %0d expected %0d K %0d t_mf %b hslot %b hwin %b", nst, nfire, nexp, kconst, mf, hmf, wf);
`ifdef BAD_D
        if(wf[1] && hmf==0) $display("MUWIN BADD PASS"); else $display("MUWIN BADD FAIL");
`elsif BAD_D_HIGH
        if(wf[1] && hmf==0) $display("MUWIN BADD_HIGH PASS"); else $display("MUWIN BADD_HIGH FAIL");
`elsif COLLIDE_EVENTS
        $display("MUWIN COLLISION first %0d expected %0d",first_cfg_fault,stc[0]+DK[0]+3);
        if(errs==0 && nfire==nexp && hmf==0 && wf==2'b10 && first_cfg_fault==stc[0]+DK[0]+3)
            $display("MUWIN COLLISION PASS");
        else $display("MUWIN COLLISION FAIL");
`else
        if (BADRT) begin
            if (wf[0] && mf[2] && hmf == 4'd0) $display("MUWIN BADRT PASS (fault raised)"); else $display("MUWIN BADRT FAIL (no fault)");
        end else if (errs == 0 && nfire == nexp && mf == 4'd0) $display("MUWIN PASS");
        else $display("MUWIN FAIL errs %0d", errs);
 `endif
        $finish;
    end
endmodule
