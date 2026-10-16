`timescale 1ns/1ps
// S-ELEM-PQ/HOST 2026-10-16: dsfd_host_c +OT_S81_HOST_ONECLK (one 1.2 GHz root, no lockup latches, HOST address
// prefix/carry-save arithmetic) against the unchanged legacy PHASESAFE+BOOT300 dsfd_host_c (generated ref_* copy of
// the same sources, legacy arithmetic) run with ck_ingest = {ck, ck}. Fixed external host slots: no observed
// ready/credit/status chooses a slot or moves the final verification edge. Every ck edge compares the per-stack
// write face hw and the completion pulse {t_v, t_d}; only off-chip HBM storage/ACKs and expected images are modelled.
module tb_host_c_oneclk;
 parameter integer MUT=0;
 reg ck=0,cv=0,rst=0;always #3 ck=~ck;always #4 cv=~cv;
 reg[1:0]div=1;always @(posedge ck)div<=div+1'b1;wire cb=div[1];
 reg[514:0]packets[0:4095];reg[255:0]mem[0:65535],expected_mem[0:65535];
 integer np=0,cyc=0,sent=0,emits=0,dones=0,compared=0,emit_fd,completion_fd,stage_seen=0,pq_seen=0,boot_cmp=0;
 reg[514:0]f=0;reg[8:0]hc=0;
 wire[291:0]hw,refhw;wire[76:0]t,reft;wire[35:0]sp,pq,rsp,rpq;wire[7:0]plen,rplen;
 dsfd_host_c #(.MUT(MUT))dut(.ck(ck),.ckv(cv),.ck_boot(cb),.rst(rst),.rsv(rst),.f_collective(f),.f_lf(4'b0101),.t_collective(t),.t_sseq_pw(sp),.t_pq_pw(pq),.t_sseq_plen(plen),.f_sseq_st(6'd0),.f_wfc_ft(4'd0),.hw(hw),.hc(hc));
 ref_dsfd_host_c ref_dut(.ck(ck),.ckv(cv),.ck_boot(cb),.ck_ingest({ck,ck}),.rst(rst),.rsv(rst),.f_collective(f),.f_lf(4'b0101),.t_collective(reft),.t_sseq_pw(rsp),.t_pq_pw(rpq),.t_sseq_plen(rplen),.f_sseq_st(6'd0),.f_wfc_ft(4'd0),.hw(refhw),.hc(hc));
 initial begin
  emit_fd=$fopen($sformatf("emit_calendar_m%0d.tsv",MUT),"w");
  $fdisplay(emit_fd,"edge%csector_addr%chw292",9,9);
  completion_fd=$fopen($sformatf("completion_calendar_m%0d.tsv",MUT),"w");
  $fdisplay(completion_fd,"edge%cactual_completion64",9);
  if(!$value$plusargs("NP=%d",np))$fatal(1,"HOST_ONECLK missing NP");
  $readmemh("packets.mem",packets,0,np-1);$readmemh("init.mem",mem);$readmemh("exp.mem",expected_mem);
  #29 rst=1;
 end
 always @(negedge ck)if(rst)begin
  cyc=cyc+1;f=0;hc={7'd0,hw[0],hw[0]};
  if(cyc>100&&cyc%32==0&&sent<np)begin f=packets[sent];sent=sent+1;end
  if(cyc==60000)begin
   if(sent!=np||emits==0||dones==0||stage_seen!=1||pq_seen!=1||plen!=4||t[75]||reft[75])$fatal(1,"HOST_ONECLK FAIL counts/fault sent=%0d/%0d emits=%0d dones=%0d stage=%0d pq=%0d plen=%0d fault=%b/%b",sent,np,emits,dones,stage_seen,pq_seen,plen,t[75],reft[75]);
   for(integer i=0;i<65536;i=i+1)if(mem[i]!==expected_mem[i])$fatal(1,"HOST_ONECLK FAIL external memory sector=%0d",i);
   if(rn_!=dn)$fatal(1,"HOST_ONECLK FAIL boot word count %0d/%0d",dn,rn_);
   $display("HOST_ONECLK PASS exact_calendar=%0d real_packets=%0d sectors=%0d completions=%0d boot_words=%0d boot_delta_ckv=%0d..%0d",compared,sent,emits,dones,dn,dmin,dmax);$finish;
  end
 end
 always @(posedge ck)if(rst)begin
  #0.01;
  if(cyc>10)begin
   compared=compared+1;
   if(hw[0]!==refhw[0] || (hw[0]&&hw!==refhw) || t[64]!==reft[64] || (t[64]&&t[63:0]!==reft[63:0]))
    $fatal(1,"HOST_ONECLK FAIL exact producer/calendar edge=%0d",cyc);
   if(hw[0])begin
    if(!hw[289]||hw[291:290]!=0||hw[288:257]>=65536)$fatal(1,"HOST_ONECLK FAIL unsupported external write");
    mem[hw[288:257]]=hw[256:1];emits=emits+1;
    $fdisplay(emit_fd,"%0d%c%0d%c%h",cyc,9,hw[288:257],9,hw);
   end
   if(dut.u_h.host.h_v && dut.u_h.host.h_cls==0 &&
      (dut.u_h.host.h_d[7:0]==8'h10 || dut.u_h.host.h_d[7:0]==8'h11 || dut.u_h.host.h_d[7:0]==8'h12))
    $fatal(1,"HOST_ONECLK FAIL interceptedCSR reached native ingest port");
   if(t[64])begin
    $fdisplay(completion_fd,"%0d%c%h",cyc,9,t[63:0]);
    if(t[63:56]!=1)$fatal(1,"HOST_ONECLK FAIL non-DONE physical completion");
    dones=dones+1;
   end
  end
 end
 // Boot words: the latch-free ck -> ck_boot -> ckv crossing must deliver the SAME words, kinds and length, in the same
 // order, never later than the legacy PHASESAFE build (whose lockup latches defer each pointer half a source cycle).
 // The boot crossing is a phase-dependent initialization FIFO (tb_host_boot300: 8 serial phases, stopped boot clock,
 // over-capacity); the per-word ckv-edge delta against the legacy build is recorded, not hidden.
 reg[35:0]dq[0:63];integer de[0:63];integer dn=0,rn_=0,dmax=-1000,dmin=1000,delta;
 always @(posedge cv)if(rst)begin
  #0.01;boot_cmp=boot_cmp+1;
  if(sp[35]&&pq[35])$fatal(1,"HOST_ONECLK FAIL duplicate boot kind");
  if(sp[35]||pq[35])begin dq[dn]=sp[35]?{1'b0,sp[34:0]}:{1'b1,pq[34:0]};de[dn]=boot_cmp;dn=dn+1;end
  if(rsp[35]||rpq[35])begin
   if(rn_>=dn)$fatal(1,"HOST_ONECLK FAIL boot word later than legacy (ref word %0d at ckv edge %0d)",rn_,boot_cmp);
   if(dq[rn_]!==(rsp[35]?{1'b0,rsp[34:0]}:{1'b1,rpq[34:0]}))$fatal(1,"HOST_ONECLK FAIL boot payload/kind word=%0d",rn_);
   delta=de[rn_]-boot_cmp;if(delta>dmax)dmax=delta;if(delta<dmin)dmin=delta;
   $display("HOST_ONECLK BOOT word=%0d kind=%0d dut_edge=%0d ref_edge=%0d delta_ckv=%0d",rn_,dq[rn_][35],de[rn_],boot_cmp,delta);
   rn_=rn_+1;
  end
  if(plen!==rplen&&!(plen==4&&rplen==0))$fatal(1,"HOST_ONECLK FAIL boot length plen=%0d/%0d",plen,rplen);
  if(sp[35])stage_seen=stage_seen+1;
  if(pq[35])pq_seen=pq_seen+1;
 end
endmodule
