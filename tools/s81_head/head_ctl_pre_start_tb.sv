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

  reg [511:0] token_word=0; reg token_valid=0;
  // Closed SEQ child response boundary only: exercise the real tk_pop,
  // identity comparison, issue arbitration and tag FIFO around that response.
  initial begin
    force u0.c_ngrp=ngrp; force u1.c_ngrp=ngrp; force u2.c_ngrp=ngrp;
    force u0.c_grp=grp; force u1.c_grp=grp; force u2.c_grp=grp;
    force u0.c_run=1'b1; force u1.c_run=1'b1; force u2.c_run=1'b1;
    force u0.c_iss_per=16'd9000; force u1.c_iss_per=16'd9000; force u2.c_iss_per=16'd9000;
    force u0.c_iss_off=16'd16; force u1.c_iss_off=16'd16; force u2.c_iss_off=16'd16;
    force u0.c_merge_dl=16'd60000; force u1.c_merge_dl=16'd60000; force u2.c_merge_dl=16'd60000;
    force u0.tk_hv=token_valid; force u1.tk_hv=token_valid; force u2.tk_hv=token_valid;
    force u0.tk_q=token_word; force u1.tk_q=token_word; force u2.tk_q=token_word;
  end
  integer cyc=0,mism=0,niss=0,nret=0,nop=0,nread=0,npop=0,load2=0,busy_seen=0,first_cycle=0;
  reg sent_best=0;
  task owned(input integer beat,input integer tag);
    integer z;
    begin
      ri=0;ri[0]=1;ri[3:1]=3'd2;ri[19:13]=beat;
      for(z=0;z<32;z=z+1)ri[21+32*z+:32]=32'h9e3779b9*(beat+1)+z*32'h01010101;
      mu_rt=32'h80000000|tag;
    end
  endtask
  always @(posedge ck) begin
    if(rst_n&&u0.start)begin
      niss=niss+1;if(niss==1)first_cycle=cyc;
      if(niss==2&&!u0.token_retire)$fatal(1,"second START did not overlap real matching token retirement");
    end
    if(rst_n&&u0.token_retire)nret=nret+1;
    if(rst_n&&u0.nsf_fire)begin
      npop=npop+1;if(u0.tf_head!==31'd3)$fatal(1,"FIFO first tag identity");
    end
    if(rst_n&&u0.xv0)nread=nread+1;
  end
  always @(negedge ck) begin
    cyc=cyc+1;
    if(cyc>24&&(a_all!==b_all||a_all!==c_all))begin
      mism=mism+1;if(mism<5)$display("MISMATCH cycle %0d",cyc);
    end
    if(cyc>24&&u1.op_pre_p1!==(u1.p1_xb&&!u1.p1_own&&u1.p1_tv))begin
      mism=mism+1;if(mism<5)$display("OP_INVARIANT cycle %0d",cyc);
    end
    if(u1.p1_op)nop=nop+1;
    rst_n=cyc>16&&cyc<9500;
    start_i=cyc>=400&&cyc<9500;
    ri=0;mu_rt=0;sn_i=0;ss_i=0;mrx_v=0;mrx_d=0;hrx_v=0;hrx_d=0;drx_v=0;drx_d=0;lw=0;
    ngrp=(cyc<140)?2:1;grp=0;
    if(cyc>=40&&cyc<120)begin
      ngrp=2;owned(cyc-40,3);
    end
    if(cyc>=200&&cyc<280)owned(cyc-200,3);
    if(niss==1&&u0.stream_busy)busy_seen=1;
    if(niss==1&&busy_seen&&!u0.stream_busy&&load2<80)begin
      if(load2==0&&nread!=8269)$fatal(1,"first stream SRAM reads %0d",nread);
      owned(load2,4);load2=load2+1;
    end
    if(niss==1&&busy_seen&&!u0.stream_busy&&!sent_best)begin
      sn_i[514]=1;ss_i[514]=1;
      sn_i[563:515]={32'h3f800000,17'd7};ss_i[563:515]={32'h3f000000,17'd8};
      sent_best=1;
    end
    token_word=0;token_word[60:40]=21'd3;token_word[39:32]=8'd0;
    token_valid=(u0.u_issue.due_o&&a_job&&u0.xrdy&&!u0.stream_busy);
    if(cyc==400)$display("LOAD_CHECK nbeat=%0d ready=%b fault=%b",u0.nbeat,u0.xrdy,u0.schedule_fault);
    if(cyc==9530)begin
      if(mism||niss!=2||nret!=1||npop!=1||nop<1||load2!=80||a_job||u0.busy||u0.tfn!=0)
        $fatal(1,"HSF_START_FAIL mism=%0d issue=%0d retire=%0d pop=%0d op=%0d load2=%0d",mism,niss,nret,npop,nop,load2);
      $display("HSF_START_PASS cycles=%0d issue=%0d retire=%0d fifo_pop=%0d op=%0d first_start=%0d default_off=PASS reset=PASS",cyc,niss,nret,npop,nop,first_cycle);$finish;
    end
  end
endmodule
