`timescale 1ns/1ps
// ELEM-GAPS/HBMB 10-18: die-master bench of ot_hbm_idx_rootctl_static (d4g idx_ctl, port-identical, no parameters).
// Lockstep against the benched reference calendar ot_hbm_idx_calendar_static fed by the UNREGISTERED pins: sel_op
// (issue ? op : 0), sel_pass/sel_addr/link_group (issue edges), link_flush/link_emit, link_clear = start + 2 and done
// must equal the reference 2 edges later on every edge; ingest_v = &selected_v (zero latency); the sticky fault at +2
// edges after a qfault / sf / lf pin pulse or a tree_ev disagreement (+1 at the agreement flop, +1 fault flop);
// SW read-group share: an INDEX request passes to vm_rq on the same edge, the bank response valid reaches only
// index_rr 7 edges later (TOPK idle: busy/done/fault 0, no topk request). Real mapped SRAM behavioural model.
// Mutants (MUT, stimulus side; each must FAIL): 1 one programme bit differs at the DUT only (selector field path);
// 2 the model expects latency 1 (timing); 3 one tree_ev lane disagrees for one edge while the model expects no fault.
module tb_idx_rootctl_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pwe=0,start=0,sf=0,lf=0;reg[7:0]pa=0;reg[255:0]pd=0,pd_dut=0;reg[11:0]len=0;
 reg[3:0]selv=0,tev=0,qfl=0;
 reg[135:0]irq=0,arq=0;reg[2055:0]vrr=0;
 wire[3:0]sop,lgrp;wire[1:0]spass;wire[7:0]saddr;wire lfl,lem,lclr,ingv,done,flt,tbusy,tdone,tfault,shf;
 wire[337:0]cq;wire[1:0]cqs;wire[2055:0]irr,arr;wire[135:0]vrq;
 ot_hbm_idx_rootctl_static dut(.clk_program(clk),.clk_program_mem(clk),.clk_sel(clk),.clk_topk(clk),.clk_pair({4{clk}}),
  .rst_n(rst_n),.program_we(pwe),.program_addr(pa),.program_data(pd_dut),.start(start),.length(len),
  .sel_op(sop),.sel_pass(spass),.sel_addr(saddr),.link_flush(lfl),.link_emit(lem),.link_group(lgrp),.link_clear(lclr),
  .selected_v(selv),.ingest_v(ingv),.tree_ev(tev),.qfault(qfl),.sf(sf),.lf(lf),.done(done),.fault(flt),
  .topk_go(1'b0),.topk_k(4'd0),.topk_order(1'b0),.topk_n(20'd0),.topk_m(20'd0),.topk_a_mirror(1'b0),.topk_a_base(18'd0),
  .topk_a_str(18'd0),.topk_o_mirror(1'b0),.topk_o_base(18'd0),.topk_o_str(18'd0),.topk_has_r(1'b0),.topk_r_base(18'd0),
  .topk_r_str(18'd0),.cq(cq),.cq_seq(cqs),.cr(274'd0),.topk_busy(tbusy),.topk_done(tdone),.topk_fault(tfault),
  .index_rq(irq),.index_rr(irr),.argmax_rq(arq),.argmax_rr(arr),.vm_rq(vrq),.vm_rr(vrr),.share_fault(shf));
 wire riv,rdone,rfault;wire[31:0]rins;reg rrst=0;
 ot_hbm_idx_calendar_static ref_cal(.clk(clk),.clk_mem(clk),.rst_n(rrst),.program_we(pwe),.program_addr(pa),
  .program_data(pd),.start(start),.length(len),.issue_v(riv),.instruction(rins),.done(rdone),.fault(rfault));
 localparam integer LAT=(MUT==2)?1:2;
 localparam integer H=8;
 reg[31:0]h_ins[0:H-1];reg h_iv[0:H-1],h_st[0:H-1],h_dn[0:H-1],h_ef[0:H-1];
 reg sticky=0,chk_on=0;integer cyc=0,checked=0,issues=0,errors=0,ingchk=0,shchk=0;
 always @(posedge clk)begin
  for(integer i=H-1;i>0;i=i-1)begin h_ins[i]<=h_ins[i-1];h_iv[i]<=h_iv[i-1];h_st[i]<=h_st[i-1];h_dn[i]<=h_dn[i-1];h_ef[i]<=h_ef[i-1];end
  h_ins[0]<=rins;h_iv[0]<=riv;h_st[0]<=start;h_dn[0]<=rdone;
  // fault events at the pins: qfault/sf/lf (pin flop), tree_ev disagreement (agreement flop) -> fault flop 1 edge later
  h_ef[0]<=(|qfl)|sf|lf|(MUT!=3&&tev!={4{tev[0]}});
  cyc<=cyc+1;
 end
 always @(negedge clk)if(chk_on)begin
  reg[31:0]ei;reg ev;ei=h_ins[LAT-1];ev=h_iv[LAT-1];
  checked++;
  if(sop!==(ev?ei[19:16]:4'd0)||lfl!==(ev&&ei[5])||lem!==(ev&&ei[4]))begin errors++;if(errors<6)$display("op mismatch cyc%0d",cyc);end
  if(ev)begin issues++;if(spass!==ei[15:14]||saddr!==ei[13:6]||lgrp!==ei[3:0])begin errors++;if(errors<6)$display("field mismatch cyc%0d",cyc);end end
  if(lclr!==h_st[LAT-1]||done!==h_dn[LAT-1])begin errors++;if(errors<6)$display("clear/done mismatch cyc%0d",cyc);end
  if(ingv!==(&selv))errors++;else ingchk++;
  if(h_ef[LAT-1])sticky=1;
  if(flt!==sticky)begin errors++;if(errors<6)$display("fault mismatch cyc%0d got%0d exp%0d",cyc,flt,sticky);end
  if(tbusy!==0||tdone!==0||tfault!==0||cq[337]!==0)begin errors++;if(errors<6)$display("topk not idle cyc%0d",cyc);end
 end
 reg[255:0]prog[0:255];
 task automatic frame(input integer n,input integer seed);
  integer rows;integer s;begin
  s=seed;rows=(n+7)/8;
  for(integer r=0;r<rows;r=r+1)for(integer w=0;w<8;w=w+1)begin
   prog[r][w*32+:32]=$random(s);
   if(prog[r][w*32+16+:4]==4'd2)prog[r][w*32+16]=1'b1;   // no selector op 2 here (op 2 checks tree_ev[0], tested below)
  end
  for(integer r=0;r<rows;r=r+1)begin
   pwe=1;pa=8'(r);pd=prog[r];pd_dut=prog[r];
   if(MUT==1&&r==rows/2)pd_dut[16+32*5]=~pd_dut[16+32*5];
   @(negedge clk);
  end
  pwe=0;pd=0;pd_dut=0;repeat(4)@(negedge clk);
  len=12'(n);start=1;@(negedge clk);start=0;
  for(integer c=0;c<n+10;c=c+1)begin
   selv=4'($random(s));tev=(c%5==0)?4'hF:4'h0;
   if(MUT==3&&n==77&&c==30)tev=4'b0111;
   @(negedge clk);
  end
  selv=0;tev=0;
 end endtask
 task automatic share_probe(input integer p,input integer b);   // INDEX request on bank b of pair p, response 7 edges later
  integer ok;begin
  ok=1;
  irq[34*p+17*b+:17]={1'b1,16'h1234};
  #1;if(vrq[34*p+17*b+:17]!=={1'b1,16'h1234}||vrq!=(136'd0|({1'b1,16'h1234}<<(34*p+17*b))))ok=0;
  @(negedge clk);irq=0;
  repeat(6)@(negedge clk);
  vrr[514*p+257*b+:257]={1'b1,{8{32'hA5A50000+32'(p*2+b)}}};
  #1;if(irr[514*p+257*b+256]!==1||arr[514*p+257*b+256]!==0||irr[514*p+257*b+:256]!=={8{32'hA5A50000+32'(p*2+b)}})ok=0;
  @(negedge clk);vrr=0;
  if(!ok)begin errors++;$display("share probe pair%0d bank%0d failed",p,b);end else shchk++;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;rrst=1;
  repeat(6)@(negedge clk);chk_on=1;
  frame(300,11);frame(77,22);frame(2048,33);
  for(integer p=0;p<4;p=p+1)for(integer b=0;b<2;b=b+1)share_probe(p,b);
  if(shf!==0)begin errors++;$display("share fault");end
  qfl=4'b0100;@(negedge clk);qfl=0;repeat(5)@(negedge clk);
  $display("IDX_ROOTCTL_STATIC MUT%0d checked%0d issues%0d ingest%0d share%0d errors%0d fault%0d",MUT,checked,issues,ingchk,shchk,errors,flt);
  if(errors||issues!=300+77+2048||shchk!=8||!flt)$fatal(1,"idx rootctl static lockstep mismatch");
  $display("IDX_ROOTCTL_STATIC_PASS");$finish;
 end
endmodule
