`timescale 1ns/1ps
// HEAD-92/CTL 11-10: old hd_ctl controller (A, kit form 4 RTL) vs OT_S81HD_CTL_START_Q form (B), full
// ot_s81hd_ctl_hsf0_static incl. real dsfd_mtp_seq_fan, kit parameters (ING_STAGE/SEQ_WB/SEQ_FAN/SEQ_RST/RAW_CAPTURE/
// CTL_PRE/CTL_WINDOW_PRE = 1).  Shared inputs (CSR, START, ri x-store loads); each DUT has its own closed-loop
// environment (N/S finals and the 6 mesh peers answer that DUT's own go / BEST), as the die does.
// MODE 0: B built without the define -> every output identical every cycle.
// MODE 1: B with the define -> x_o/ss_o[563:0], mesh, ro, host, draft, mu_rc, ctl_f = A one cycle later;
//         x_o[564] and mu_c identical; job_active_o rises on the same cycle (START date unchanged), falls one later.
//         Directed: earliest legal x-store reload for B (ri lead LEAD); duplicate of the previous job's token
//         presented in the cycle after START (must not retire in either).  No fault allowed in A or B.
// MODE 2: reload one cycle earlier than B's earliest legal cycle -> B must fault (fset[0]) while A does not
//         (proves the reload window moved by exactly one cycle).
module tb;
 parameter integer MODE=1; parameter integer NJ=5; parameter integer SEED=1;
 localparam integer SK=11, FW=553, NSL=8192+7*SK, NEND=5+NSL;
 reg ck=0; always #0.5 ck=~ck;
 reg rst_n=0, start_i=0;
 reg [1103:0] ri=0; reg [31:0] mu_rt=0; reg [1:0] hrx_v=0; reg [2*FW-1:0] hrx_d=0;
 wire jA,jB; wire [1103:0] roA,roB; wire [33:0] mucA,mucB; wire [10:0] murcA,murcB; wire cfA,cfB;
 wire [564:0] snA,snB,ssA,ssB; wire [564:0] sniA,sniB,ssiA,ssiB;
 wire [5:0] mtvA,mtvB,mrvA,mrvB; wire [6*FW-1:0] mtdA,mtdB,mrdA,mrdB;
 wire [1:0] htvA,htvB; wire [2*FW-1:0] htdA,htdB; wire [0:0] dtvA,dtvB; wire [FW-1:0] dtdA,dtdB;
 wire dvA,dvB; wire [552:0] dfA,dfB;
 ot_s81hd_ctl_hsf0_static #(.SK(SK),.ING_STAGE(1),.SEQ_WB(1),.SEQ_FAN(1),.SEQ_RST(1),.SRAM_RAW_CAPTURE(1),.CTL_PRE(1),.CTL_WINDOW_PRE(1)) A (
  .start_i(start_i),.adapter_fault(1'b0),.job_active_o(jA),.ck(ck),.rst_n(rst_n),.ri(ri),.mu_rt(mu_rt),.lw(11'd0),.lep_f(1'b0),
  .ro(roA),.mu_c(mucA),.mu_rc(murcA),.ctl_f(cfA),.sn_o(snA),.ss_o(ssA),.sn_i(sniA),.ss_i(ssiA),
  .mtx_v(mtvA),.mtx_d(mtdA),.mrx_v(mrvA),.mrx_d(mrdA),.mflt(24'd0),.htx_v(htvA),.htx_d(htdA),.hrx_v(hrx_v),.hrx_d(hrx_d),.hflt(8'd0),
  .dtx_v(dtvA),.dtx_d(dtdA),.drx_v(1'b0),.drx_d({FW{1'b0}}),.dflt(4'd0),.draft_slot_free(1'b1),.draft_valid_o(dvA),.draft_frame_o(dfA));
 ot_s81hd_ctl_hsf0_static_sq #(.SK(SK),.ING_STAGE(1),.SEQ_WB(1),.SEQ_FAN(1),.SEQ_RST(1),.SRAM_RAW_CAPTURE(1),.CTL_PRE(1),.CTL_WINDOW_PRE(1)) B (
  .start_i(start_i),.adapter_fault(1'b0),.job_active_o(jB),.ck(ck),.rst_n(rst_n),.ri(ri),.mu_rt(mu_rt),.lw(11'd0),.lep_f(1'b0),
  .ro(roB),.mu_c(mucB),.mu_rc(murcB),.ctl_f(cfB),.sn_o(snB),.ss_o(ssB),.sn_i(sniB),.ss_i(ssiB),
  .mtx_v(mtvB),.mtx_d(mtdB),.mrx_v(mrvB),.mrx_d(mrdB),.mflt(24'd0),.htx_v(htvB),.htx_d(htdB),.hrx_v(hrx_v),.hrx_d(hrx_d),.hflt(8'd0),
  .dtx_v(dtvB),.dtx_d(dtdB),.drx_v(1'b0),.drx_d({FW{1'b0}}),.dflt(4'd0),.draft_slot_free(1'b1),.draft_valid_o(dvB),.draft_frame_o(dfB));
 // per-job randomized environment answers (shared table; each env indexes by its own job count)
 reg [16:0] nrow[0:15], srow[0:15], prow[0:15][0:2]; reg [31:0] nbit[0:15], sbit[0:15], pbit[0:15][0:2];
 integer fdel[0:15], sdel[0:15], pdel[0:15][0:5];
 reg [9:0] juser[0:15]; reg [20:0] jpos[0:15];
 envm eA(.ck(ck),.go(snA[512]),.mtx_v(mtvA),.mtx_d(mtdA),.sn_i(sniA),.ss_i(ssiA),.mrx_v(mrvA),.mrx_d(mrdA));
 envm eB(.ck(ck),.go(snB[512]),.mtx_v(mtvB),.mtx_d(mtdB),.sn_i(sniB),.ss_i(ssiB),.mrx_v(mrvB),.mrx_d(mrdB));
 integer cyc=0; always @(posedge ck) cyc<=cyc+1;
 // ---------------------------------------------------------------- lockstep comparison
 reg [564:0] snA1,ssA1; reg [5:0] mtvA1; reg [6*FW-1:0] mtdA1; reg [1103:0] roA1; reg [1:0] htvA1; reg [2*FW-1:0] htdA1;
 reg [10:0] murcA1; reg cfA1, dtvA1, dvA1, jA1; reg [FW-1:0] dtdA1; reg [552:0] dfA1;
 integer mask=0, cmp_cycles=0, ev_x=0, ev_ro=0, ev_mt=0, ev_ht=0, errs=0, popsA=0, popsB=0, streamsA=0, streamsB=0;
 reg checking=0; reg jB1=0, jAq=0;
 // Token-loop outputs (ro token beats, host lanes, draft lane, job_active fall) pass the dsfd_mtp_seq grant /
 // credit handshakes, which re-quantize the +1: B must show the same events, same values, same order, each
 // 0..DMAX cycles after A's (never before).
 localparam integer DMAX=8;
 reg [1103:0] qro[0:63]; reg [2*553+1:0] qht[0:63]; reg [553:0] qdt[0:63]; integer tro[0:63], tht[0:63], tdt[0:63], tjf[0:63];
 integer hro=0,wro=0,hht=0,wht=0,hdt=0,wdt=0,hjf=0,wjf=0, nro=0, nht=0, njf=0;
 always @(negedge ck) if(checking && MODE==1) begin
  if(roA[0]) begin qro[wro%64]=roA; tro[wro%64]=cyc; wro=wro+1; end
  if(htvA!=0) begin qht[wht%64]={htvA,htdA}; tht[wht%64]=cyc; wht=wht+1; end
  if(dtvA!=0) begin qdt[wdt%64]={dtvA,dtdA}; tdt[wdt%64]=cyc; wdt=wdt+1; end
  if(!jA && jAq) begin tjf[wjf%64]=cyc; wjf=wjf+1; end
  if(mask==0) begin
   if(roB[0]) begin if(hro>=wro) err("ro token beat in B before A"); else begin
     if(roB!==qro[hro%64]) err("ro token value/order"); if(cyc-tro[hro%64]>DMAX) err("ro token late"); hro=hro+1; nro=nro+1; end end
   if(htvB!=0) begin if(hht>=wht) err("host beat in B before A"); else begin
     if({htvB,htdB}!==qht[hht%64]) err("host value/order"); if(cyc-tht[hht%64]>DMAX) err("host late"); hht=hht+1; nht=nht+1; end end
   if(dtvB!=0) begin if(hdt>=wdt) err("draft beat in B before A"); else begin
     if({dtvB,dtdB}!==qdt[hdt%64]) err("draft value/order"); if(cyc-tdt[hdt%64]>DMAX) err("draft late"); hdt=hdt+1; end end
   if(!jB && jB1) begin if(hjf>=wjf) err("job_active fell in B before A"); else begin
     if(cyc-tjf[hjf%64]>DMAX) err("job_active fall late"); hjf=hjf+1; njf=njf+1; end end
  end else begin
   // directed-duplicate window: the forced pop is the same cycle in A and B; drop it from both queues
   if(roB[0] && hro<wro) hro=hro+1; if(htvB!=0 && hht<wht) hht=hht+1;
  end
  if(mask==0 && (jA&&!jAq)!==(jB&&!jB1)) err("job_active rise not on the same cycle");
  jB1=jB; jAq=jA;
 end
 task err(input [8*48-1:0] m); begin if(errs<12)$display("MISMATCH %0s cycle %0d",m,cyc); errs=errs+1; end endtask
 always @(negedge ck) begin
  if(checking && mask==0 && MODE!=2) begin
   cmp_cycles=cmp_cycles+1;
   if(MODE==0) begin
    if({snA,ssA,mtvA,mtdA,roA,htvA,htdA,murcA,cfA,dtvA,dtdA,dvA,dfA,mucA,jA}!=={snB,ssB,mtvB,mtdB,roB,htvB,htdB,murcB,cfB,dtvB,dtdB,dvB,dfB,mucB,jB})
     err("default-off output");
   end else begin
    if(snB[563:0]!==snA1[563:0]||ssB[563:0]!==ssA1[563:0]) err("x_o/ss_o +1");
    if(snB[564]!==snA[564]||ssB[564]!==ssA[564]) err("x_o[564] fault same-cycle");
    if(mtvB!==mtvA1||mtdB!==mtdA1) err("mesh tx +1");
    // ro[1103:533] carries the unconditional forward-pipeline data (ri, same cycle) while ro[0]=0; a token beat is +1
    if(murcB!==murcA1||cfB!==cfA1) err("mu_rc/ctl_f +1");
    if(mucB!==mucA) err("mu_c same-cycle");
   end
  end
  if(mask>0) mask=mask-1;
  if(snA1[512]) ev_x=ev_x+1; if(roA1[0]) ev_ro=ev_ro+1; if(mtvA1!=0) ev_mt=ev_mt+1; if(htvA1!=0) ev_ht=ev_ht+1;
  if(snA[512]) streamsA=streamsA+1; if(snB[512]) streamsB=streamsB+1;
  if(A.tk_pop) popsA=popsA+1; if(B.tk_pop) popsB=popsB+1;
  snA1=snA; ssA1=ssA; mtvA1=mtvA; mtdA1=mtdA; roA1=roA; htvA1=htvA; htdA1=htdA; murcA1=murcA; cfA1=cfA;
  dtvA1=dtvA; dtdA1=dtdA; dvA1=dvA; dfA1=dfA; jA1=jA;
 end
 // internal: B's job identity follows A's by one cycle; B's tag FIFO head follows A's by one cycle once loaded
 reg [30:0] jidA1, tfhA1;
 always @(negedge ck) begin
  if(checking && MODE==1 && mask==0) begin
   if(B.job_identity!==jidA1) err("job_identity +1");
   if(B.tf_head!==tfhA1) err("tag FIFO head +1");
  end
  jidA1=A.job_identity; tfhA1=A.tf_head;
 end
 task tick; @(negedge ck); endtask
 task csrw(input [7:0] a, input [63:0] d);
  begin hrx_v[1]=1; hrx_d[FW +: FW]={1'b1,464'd0,d,a,8'd0,2'd0,2'd0,4'd6}; tick; hrx_v[1]=0; tick; tick; end
 endtask
 integer seedv,b,k,t,tmp,j,perm[0:79],lead,P,dupdone=0; reg [511:0] lastTok; reg [30:0] prevTag;
 task load(input integer jj);
  begin
   for(k=0;k<80;k=k+1) perm[k]=k;
   for(k=79;k>0;k=k-1) begin t=$urandom%(k+1); tmp=perm[k]; perm[k]=perm[t]; perm[t]=tmp; end
   for(b=0;b<80;b=b+1) begin
    ri=0; ri[0]=1; ri[3:1]=3'd2; ri[8:4]=5'd1; ri[20:13]=perm[b][7:0];
    for(k=0;k<32;k=k+1) ri[21+32*k +: 32]=$urandom;
    mu_rt={1'b1,juser[jj],jpos[jj]};
    tick; ri=0; mu_rt=0;
    if(($urandom%4)==0) repeat(1+$urandom%2) tick;
   end
  end
 endtask
 always @(negedge ck) if(A.tk_pop) lastTok=A.tk_q;
 initial begin
  if(!$value$plusargs("P=%d",P)) P=NSL+900;
  seedv=SEED; tmp=$urandom(seedv);
  for(j=0;j<16;j=j+1) begin
   nrow[j]=$urandom; srow[j]=$urandom; nbit[j]=$urandom&32'h7f7fffff; sbit[j]=$urandom&32'h7f7fffff;
   for(k=0;k<3;k=k+1) begin prow[j][k]=$urandom; pbit[j][k]=$urandom&32'h7f7fffff; end
   fdel[j]=20+$urandom%60; sdel[j]=$urandom%50; for(k=0;k<6;k=k+1) pdel[j][k]=1+$urandom%9;
   juser[j]=$urandom; jpos[j]=$urandom;
  end
  repeat(10) tick; rst_n=1; repeat(20) tick;
  csrw(8'd0,64'd4); csrw(8'd1,64'd8); csrw(8'd2,64'd1); csrw(8'd3,64'h4); csrw(8'd4,64'd1000);
  csrw(8'd5,64'h0201); csrw(8'd9,{32'd0,16'd200,P[15:0]}); csrw(8'd10,64'd12000); csrw(8'd8,64'd1);
  repeat(20) tick; start_i=1; checking=1;
  load(0);
  for(j=1;j<NJ;j=j+1) begin
   // wait for both streams to start, then reload for the next date
   while(!B.busy) tick;
   if(j==2 || MODE==2) begin
    // earliest legal reload for B: ri in the cycle before B.n reaches NEND-1 (first wv2 = first cycle stream_busy low)
    lead = (MODE==2) ? 3 : 2;
    while(!(B.busy && B.n==14'(NEND-1-lead+1))) tick;
   end else begin
    while(B.stream_busy) tick;
    repeat($urandom%25) tick;
   end
   load(j);
   if(j==3 && MODE!=0) begin
    // duplicate of job 2's token offered in the cycle after job 3's START
    prevTag=A.job_identity;
    while(!A.start) tick;
    tick;
`ifdef TB_SQ
    if(MODE==1 && B.start_q!==1'b1) err("start_q not high in the cycle after START");
`endif
    force A.tk_hv=1'b1; force B.tk_hv=1'b1; force A.tk_q=lastTok; force B.tk_q=lastTok;
    mask=6;
    #0.1; if(!A.tk_pop || !B.tk_pop) err("directed duplicate token not popped");
    if(A.token_retire) err("old retired a stale token");
    if(B.token_retire) err("new retired a stale token in the start_q cycle");
    tick; release A.tk_hv; release B.tk_hv; release A.tk_q; release B.tk_q;
    if(!jA || !jB) err("job_active lost after duplicate");
    dupdone=1;
   end
  end
  // stop before the next compiled date (no load follows the last job): wait for both retirements
  if(MODE!=2) begin while(streamsB<NJ) tick; while(jA||jB) tick; repeat(30) tick; end
  else repeat(400) tick;
  if(MODE==2) begin
   if(A.fv!=0) err("A faulted in MODE 2");
   if(!B.fv[0]) err("B did not fault on the early reload");
   if(errs==0) $display("PASS hd_ctl start_q reload floor: A fv=%h B fv=%h (reload 1 cycle early faults only B)",A.fv,B.fv);
   else $display("FAIL hd_ctl start_q floor errs=%0d",errs);
   $finish;
  end
  if(A.fv!=0||B.fv!=0||A.u_issue.fault_o||B.u_issue.fault_o) begin $display("faults A fv=%h B fv=%h",A.fv,B.fv); err("fault"); end
  if(streamsA!=NJ||streamsB!=NJ) err("stream count");
  if(popsA<NJ||popsB!=popsA) err("token pop count");
  if(MODE==1 && dupdone!=1) err("directed duplicate not run");
  if(MODE==1 && (hro!=wro||hht!=wht||hdt!=wdt||hjf!=wjf||nro<NJ||njf<NJ)) err("token-loop event count");
  if(ev_x<NJ||ev_ro<NJ||ev_mt<NJ) err("vacuous events");
  if(errs==0) $display("PASS hd_ctl start_q MODE=%0d jobs=%0d P=%0d cycles=%0d go=%0d ro=%0d mesh=%0d host=%0d pops=%0d/%0d dup=%0d tokq=%0d hostq=%0d jfall=%0d",
                MODE,NJ,P,cmp_cycles,ev_x,ev_ro,ev_mt,ev_ht,popsA,popsB,dupdone,nro,nht,njf);
  else $display("FAIL hd_ctl start_q MODE=%0d errs=%0d",MODE,errs);
  $finish;
 end
 always @(negedge ck) if(checking && MODE!=2 && (A.fv!=0||B.fv!=0) && errs==0) begin $display("fault A fv=%h B fv=%h cycle %0d",A.fv,B.fv,cyc); err("live fault"); end
 initial begin #400000; $display("FAIL hd_ctl start_q timeout"); $finish; end
endmodule

module envm(input wire ck, input wire go, input wire [5:0] mtx_v, input wire [6*553-1:0] mtx_d,
            output reg [564:0] sn_i, output reg [564:0] ss_i, output reg [5:0] mrx_v, output reg [6*553-1:0] mrx_d);
 localparam integer FW=553, NSL=8192+77;
 integer j=0,k; reg [80:0] own;
 initial begin sn_i=0; ss_i=0; mrx_v=0; mrx_d=0; end
 always begin
  @(negedge ck);
  if(go) begin
   repeat(NSL+tb.fdel[j]) @(negedge ck);
   sn_i=0; sn_i[514]=1; sn_i[531:515]=tb.nrow[j]; sn_i[563:532]=tb.nbit[j]; @(negedge ck); sn_i=0;
   repeat(tb.sdel[j]) @(negedge ck);
   ss_i=0; ss_i[514]=1; ss_i[531:515]=tb.srow[j]; ss_i[563:532]=tb.sbit[j]; @(negedge ck); ss_i=0;
   while(mtx_v==6'd0) @(negedge ck);
   own=mtx_d[16 +: 81];
   for(k=0;k<6;k=k+1) begin
    repeat(tb.pdel[j][k]) @(negedge ck);
    mrx_v=0; mrx_v[k]=1;
    mrx_d[k*FW +: FW]={1'b1,455'd0,own[80:50],tb.pbit[j][k/2],tb.prow[j][k/2],1'b1,8'd0,2'd0,2'(k/2+2),4'd1};
    @(negedge ck); mrx_v=0;
   end
   j=j+1;
  end
 end
endmodule
