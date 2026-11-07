`timescale 1ns/1ps
module tb_hsf;
  reg ck=0; always #5 ck=~ck;
  reg rst_n=0, start_i=0, adapter_fault=0, lep_f=0, draft_slot_free=1;
  reg [1103:0] ri=0; reg [31:0] mu_rt=0; reg [10:0] lw=0; reg [564:0] sn_i=0, ss_i=0;
  reg [5:0] mrx_v=0; reg [6*553-1:0] mrx_d=0; reg [23:0] mflt=0; reg [1:0] hrx_v=0; reg [2*553-1:0] hrx_d=0; reg [7:0] hflt=0;
  reg [0:0] drx_v=0; reg [552:0] drx_d=0; reg [3:0] dflt=0;
  reg [1:0] ngrp=0, grp=0;
`define PORTS(o) .start_i(start_i),.adapter_fault(adapter_fault),.job_active_o(o``_job),.ck(ck),.rst_n(rst_n),.ri(ri),.mu_rt(mu_rt),.lw(lw),.lep_f(lep_f), \
   .ro(o``_ro),.mu_c(o``_muc),.mu_rc(o``_murc),.ctl_f(o``_ctlf),.sn_o(o``_sno),.ss_o(o``_sso),.sn_i(sn_i),.ss_i(ss_i),.mtx_v(o``_mtxv),.mtx_d(o``_mtxd), \
   .mrx_v(mrx_v),.mrx_d(mrx_d),.mflt(mflt),.htx_v(o``_htxv),.htx_d(o``_htxd),.hrx_v(hrx_v),.hrx_d(hrx_d),.hflt(hflt),.dtx_v(o``_dtxv),.dtx_d(o``_dtxd), \
   .drx_v(drx_v),.drx_d(drx_d),.dflt(dflt),.draft_slot_free(draft_slot_free),.draft_valid_o(o``_dvo),.draft_frame_o(o``_dfo)
`define WIRES(o) wire o``_job, o``_ctlf, o``_dvo; wire [1103:0] o``_ro; wire [33:0] o``_muc; wire [10:0] o``_murc; wire [564:0] o``_sno, o``_sso; \
   wire [5:0] o``_mtxv; wire [6*553-1:0] o``_mtxd; wire [1:0] o``_htxv; wire [2*553-1:0] o``_htxd; wire [0:0] o``_dtxv; wire [552:0] o``_dtxd; wire [552:0] o``_dfo; \
   wire [9000:0] o``_all = {o``_job,o``_ctlf,o``_dvo,o``_ro,o``_muc,o``_murc,o``_sno,o``_sso,o``_mtxv,o``_mtxd,o``_htxv,o``_htxd,o``_dtxv,o``_dtxd,o``_dfo};
  `WIRES(a) `WIRES(b) `WIRES(c)
  ot_s81hd_ctl_hsf0_static_O #(.ING_STAGE(1),.SEQ_WB(1),.SEQ_FAN(1),.SEQ_RST(1),.SRAM_RAW_CAPTURE(1)) u0 (`PORTS(a));
  `NEWMOD #(.ING_STAGE(1),.SEQ_WB(1),.SEQ_FAN(1),.SEQ_RST(1),.SRAM_RAW_CAPTURE(1),.CTL_PRE(1)) u1 (`PORTS(b));
  `NEWMOD #(.ING_STAGE(1),.SEQ_WB(1),.SEQ_FAN(1),.SEQ_RST(1),.SRAM_RAW_CAPTURE(1),.CTL_PRE(0)) u2 (`PORTS(c));
  initial begin force u0.c_ngrp = ngrp; force u1.c_ngrp = ngrp; force u2.c_ngrp = ngrp; force u0.c_grp = grp; force u1.c_grp = grp; force u2.c_grp = grp;
    force u0.c_run = 1'b1; force u1.c_run = 1'b1; force u2.c_run = 1'b1;
    force u0.c_iss_per = 16'd40; force u1.c_iss_per = 16'd40; force u2.c_iss_per = 16'd40;
    force u0.c_iss_off = 16'd30; force u1.c_iss_off = 16'd30; force u2.c_iss_off = 16'd30;
    force u0.c_merge_dl = 16'd200; force u1.c_merge_dl = 16'd200; force u2.c_merge_dl = 16'd200; end
  integer cyc=0, seed, NC, mism=0, ninv=0, nop=0, nblk=0, niss=0, nret=0, nrst=0, j;
  initial begin if(!$value$plusargs("seed=%d",seed)) seed=1; if(!$value$plusargs("n=%d",NC)) NC=100000; end
  always @(negedge ck) begin
    cyc = cyc + 1;
    if (cyc > 12 && a_all !== b_all) begin mism=mism+1; if (mism<5) $display("MISMATCH on cycle %0d", cyc); end
    if (cyc > 12 && a_all !== c_all) begin mism=mism+1; if (mism<5) $display("MISMATCH off cycle %0d", cyc); end
    if (cyc > 12 && u1.op_pre_p1 !== (u1.p1_xb && !u1.p1_own && u1.p1_tv)) begin mism=mism+1; if (mism<5) $display("INVARIANT op_q1 cycle %0d", cyc); end
    if (cyc > 12 && (u1.p1_xb && !u1.p1_own && u1.p1_tv) === 1'b1) ninv=ninv+1;
    if (u1.p1_op === 1'b1) nop=nop+1; if (u1.blk === 1'b1) nblk=nblk+1; if (u1.start === 1'b1) niss=niss+1; if (u1.token_retire === 1'b1) nret=nret+1;
    rst_n = (cyc > 8) && !(cyc % 20011 > 20000);
    if (!rst_n) nrst = nrst + 1;
    start_i = cyc > 40;
    if ((cyc & 1023) == 0) begin ngrp = $random(seed); grp = $random(seed) % 3; end
    ri[0] = $random(seed) & 1; ri[3:1] = (($random(seed) & 1) ? 3'd2 : $random(seed));
    for (j = 4; j < 1104; j = j + 32) ri[j +: 32] = $random(seed);
    ri[19:13] = $random(seed) % 90;
    mu_rt = {$random(seed)}; 
    sn_i = {18{$random(seed)}}; ss_i = {18{$random(seed)}};
    mrx_v = ($random(seed) & 7) == 0 ? $random(seed) : 0; for (j = 0; j < 6*553; j = j + 32) mrx_d[j +: 32] = $random(seed);
    hrx_v = ($random(seed) & 7) == 0 ? $random(seed) : 0; for (j = 0; j < 2*553; j = j + 32) hrx_d[j +: 32] = $random(seed);
    drx_v = ($random(seed) & 7) == 0; for (j = 0; j < 553; j = j + 32) drx_d[j +: 32] = $random(seed);
    lw = $random(seed); lep_f = ($random(seed) & 1023) == 0; draft_slot_free = $random(seed);
    if (cyc == NC) begin
      $display("HSF seed %0d cycles %0d mismatches %0d op_term_true %0d p1_op %0d blk %0d start %0d token_retire %0d reset_cycles %0d", seed, cyc, mism, ninv, nop, nblk, niss, nret, nrst);
      if (mism == 0 && nop > 0 && ninv > 100) $display("HSF_PASS"); else $display("HSF_FAIL");
      $finish;
    end
  end
endmodule
