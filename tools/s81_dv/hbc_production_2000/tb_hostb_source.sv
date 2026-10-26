`timescale 1ns/1ps
module tb_hostb_source;
 reg ck=0;always #0.5 ck=~ck;
 reg rn=0,upstream=0;reg[514:0]host=0;reg[52:0]ks=0;reg[2:0]slot=0;
 wire[514:0]issue_host;wire[52:0]issue_ks,egks;wire[2:0]fault;wire armed;
 dsdv_hostb_source #(.HOSTB_ENABLE(1),.STATIC_KS6(1),.STATIC_KS_SPAN(64),.STATIC_KS_GRAPH_TAG(32'h53812000)) dut(
 .ck(ck),.rst_n(rn),.select_hbe(1'b1),.upstream_fault(upstream),.f_host(515'd0),.f_ks(53'd0),
 .hbe_f_host(host),.starter_f_ks(ks),.hbe_ks_slot(slot),.issue_host(issue_host),.issue_ks(issue_ks),
 .engram_f_ks(egks),.hostb_fault(fault),.hb_starter_armed(armed));
 wire [514:0] external_host;wire [52:0] external_ks,external_eg;wire[2:0]external_fault;wire external_armed;
 dsdv_hostb_source #(.HOSTB_ENABLE(1),.STATIC_KS6(0)) external_dut(
 .ck(ck),.rst_n(rn),.select_hbe(1'b1),.upstream_fault(1'b0),.f_host(515'd0),.f_ks(53'd0),
 .hbe_f_host(host),.starter_f_ks(ks),.hbe_ks_slot(slot),.issue_host(external_host),.issue_ks(external_ks),
 .engram_f_ks(external_eg),.hostb_fault(external_fault),.hb_starter_armed(external_armed));
 always @(posedge ck)begin
  #0.01;
  if(rn&&edge_n>30)begin
   if(external_fault||external_armed)$fatal(1,"external booked path manufactured armed/fault");
   if(external_ks!==ks||external_eg!==ks)$fatal(1,"external booked descriptor altered");
   if(external_host[0]!==host[0]||(host[0]&&external_host!==host))$fatal(1,"external booked host word altered");
  end
 end
 integer mode=0,i,edge_n=0,seen=0,last_edge=0;reg[511:0]d;reg[47:0]epoch;
 function[52:0]desc(input integer n);desc={1'b1,10'd37,21'(100+n),21'(200+n)};endfunction
 always @(posedge ck)begin
  edge_n=edge_n+1;
  if(rn)begin
   if(issue_ks!==egks)$fatal(1,"seq/Engram descriptor differs");
   if(issue_host[0]&&issue_host[8:1]>=8'h17&&issue_host[8:1]<=8'h19)$fatal(1,"control CSR leaked");
   if(issue_ks[52])begin
    if(mode==0&&(issue_ks!==desc(seen)||(seen>0&&edge_n-last_edge!=64)))$fatal(1,"descriptor identity or span");
    if(mode==2)$fatal(1,"unarmed descriptor bypassed starter");
    seen=seen+1;last_edge=edge_n;
   end
  end
 end
 task word(input[511:0]x);begin @(negedge ck);host={2'd0,x,1'b1};@(negedge ck);host=0;end endtask
 task pw(input[27:0]v);reg[511:0]x;begin x=0;x[7:0]=8'h10;x[59:32]=v;word(x);end endtask
 initial begin
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  repeat(8)@(negedge ck);rn=1;repeat(8)@(negedge ck);
  d=0;d[7:0]=8'h11;d[39:32]=1;word(d);
  pw((28'd1<<26)|(28'd8<<2));
  pw((28'd3<<26)|(28'd1<<25)|(28'd1<<9));
  repeat(170)@(negedge ck);
  d=0;d[7:0]=8'h19;d[39:8]=32'h53812000;d[87:40]=9000;word(d);
  repeat(3)@(negedge ck);
  if(mode!=2)begin
   @(negedge ck);epoch=dut.g_starter.u_static.global_edge+1;
   d=0;d[7:0]=8'h17;d[39:8]=32'h53812000;d[87:40]=epoch;d[135:88]=epoch+40;
   d[183:136]=epoch+40+4+8;d[193:184]=37;d[195:194]=0;
   host={2'd0,d,1'b1};@(negedge ck);host=0;
   repeat(3)@(negedge ck);
  end
  for(i=0;i<6;i=i+1)begin
   @(negedge ck);ks=desc(i);slot=3'(i);
   if(mode==1&&i==2)slot=3;
   if(mode==3&&i==0)ks[51:42]=38;
   if(mode==5&&i==3)ks=0;
   @(negedge ck);ks=0;
  end
  if(mode==4)upstream=1;
  repeat(600)@(negedge ck);
  if(mode==0)begin
   if(fault!=0||seen!=6||armed)$fatal(1,"positive fault%h seen%0d armed%0d",fault,seen,armed);
   $display("HBC_SOURCE PASS six real descriptors shared by seqhost/Engram; explicit64-edge test profile");
  end else begin
   if(fault==0)$fatal(1,"negative not caught mode%0d seen%0d",mode,seen);
   $display("HBC_SOURCE NEGATIVE CAUGHT mode%0d fault%h seen%0d",mode,fault,seen);
  end
  $finish;
 end
 initial begin #2000;$fatal(1,"timeout");end
endmodule
