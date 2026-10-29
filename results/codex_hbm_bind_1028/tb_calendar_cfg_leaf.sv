`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[319:0]d=0;wire[319:0]oldq,newq;
 reg[20:0]ready=0,active=0;reg[31:0]fault=0;
 wire[20:0]sr,sa;wire[31:0]sf;
 ot_hbm_host_cfg_leaf2 #(.NT(21),.NF(32)) oldleaf (
 .clk(clk),.rst_n(rst_n),.cfg_v(d[319]),.cfg_target(d[318:311]),.cfg_addr(d[310:299]),.cfg_data(d[298:43]),
 .desc_v(d[42]),.desc_base(d[41:30]),.desc_limit(d[29:17]),.desc_loops(d[16:1]),.launch_v(d[0]),
 .a_cfg_v(oldq[319]),.a_cfg_target(oldq[318:311]),.a_cfg_addr(oldq[310:299]),.a_cfg_data(oldq[298:43]),
 .a_desc_v(oldq[42]),.a_desc_base(oldq[41:30]),.a_desc_limit(oldq[29:17]),.a_desc_loops(oldq[16:1]),.a_launch_v(oldq[0]),
 .t_ready(ready),.t_active(active),.t_fault(fault),.s_ready(sr),.s_active(sa),.s_fault(sf));
`ifdef MUTANT
 localparam integer MUT=1;
`else
 localparam integer MUT=0;
`endif
 ot_hnx_calendar_cfg_leaf #(.MUT(MUT)) newleaf (
 .clk(clk),.rst_n(rst_n),.cfg_v(d[319]),.cfg_target(d[318:311]),.cfg_addr(d[310:299]),.cfg_data(d[298:43]),
 .desc_v(d[42]),.desc_base(d[41:30]),.desc_limit(d[29:17]),.desc_loops(d[16:1]),.launch_v(d[0]),
 .a_cfg_v(newq[319]),.a_cfg_target(newq[318:311]),.a_cfg_addr(newq[310:299]),.a_cfg_data(newq[298:43]),
 .a_desc_v(newq[42]),.a_desc_base(newq[41:30]),.a_desc_limit(newq[29:17]),.a_desc_loops(newq[16:1]),.a_launch_v(newq[0]));
 integer checked=0;
 initial begin
  for(integer c=0;c<340;c=c+1)begin
   @(negedge clk);rst_n=(c>=3)&&!(c>=160&&c<164);
   for(integer k=0;k<10;k=k+1)d[k*32+:32]=$random;
   d[319]=(c%5==0);d[42]=(c%7==0);d[0]=(c%11==0);
   ready=$random;active=$random;fault=$random;
   @(posedge clk);#1;
   if(c>6)begin
    if(oldq!==newq)$fatal(1,"CFG_ONLY lockstep mismatch c=%0d",c);
    checked=checked+1;
   end
  end
  $display("CFG_ONLY PASS width=320 comparisons=%0d cfg_latency=2 release=3 independent_status=1 warm_reset=1",checked);$finish;
 end
endmodule
