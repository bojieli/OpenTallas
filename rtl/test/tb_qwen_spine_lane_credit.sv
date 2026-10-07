`timescale 1ns/1ps
module tb_qwen_spine_lane_credit;
 parameter integer NEG=0;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg in_v=0,out_cr=0;
 reg [1535:0] data=0;
 reg [3:0] split=7;
 reg [31:0] tag=0;
 wire [1535:0] d=NEG?{data[1535:96],data[63:32],data[95:64],data[31:0]}:data;
 wire in_cr,out_v,fault;wire [1535:0] result;wire [31:0] result_tag;
 ot_qwen_spine_lane_credit dut(clk,rst_n,in_v,d,split,tag,in_cr,out_v,result,result_tag,out_cr,fault);
 function automatic [31:0] fp;
  input integer value;integer k,j;reg [31:0] m;
  begin k=0;for(j=0;j<30;j=j+1)if(value>=(1<<j))k=j;
   m=(value-(1<<k))<<(23-k);fp=value==0?0:((127+k)<<23)|m;end
 endfunction
 integer values[0:47],tmp[0:47];
 integer sent=0,received=0,credits=32,remote_pending=0;
 integer cyc,p,lv,s,stalled=0,first_issue=-1,first_retire=-1;
 initial begin
  repeat(4) @(posedge clk);@(negedge clk);rst_n=1;
  for(cyc=0;cyc<10000;cyc=cyc+1) begin
   @(negedge clk);
   in_v=(sent<96 && credits>0 && (cyc%5!=2));
   if(in_v) begin
    tag=sent;split=7+(sent%7);
    for(p=0;p<48;p=p+1)data[p*32+:32]=fp(p+1+sent*2);
    if(first_issue<0)first_issue=cyc;
    sent=sent+1;credits=credits-1;
   end
   if(credits==0)stalled=stalled+1;
   // Arbitrary remote backpressure including a long interval that fills all32 reservations.
   out_cr=remote_pending>0 && (cyc>200) && ((cyc%13)>4);
   if(out_cr)remote_pending=remote_pending-1;
   @(posedge clk);#1;
   if(in_cr)credits=credits+1;
   if(out_v) begin
    if(first_retire<0)first_retire=cyc;
    remote_pending=remote_pending+1;
    if(result_tag !== received)begin $display("FAIL credit tag got=%0d expected=%0d",result_tag,received);$fatal(1);end
    s=7+(received%7);
    for(p=0;p<48;p=p+1)values[p]=p+1+received*2;
    for(lv=8;lv<=12;lv=lv+1) begin
     for(p=0;p<48;p=p+1)tmp[p]=values[p];
     if(s>=lv)for(p=0;p<(6144>>lv);p=p+1)tmp[p]=values[2*p]+values[2*p+1];
     for(p=0;p<48;p=p+1)values[p]=tmp[p];
    end
    for(p=0;p<48;p=p+1)if(result[p*32+:32] !== fp(values[p])) begin
     $display("FAIL credit position tag=%0d split=%0d p=%0d got=%h expected=%h",received,s,p,result[p*32+:32],fp(values[p]));$fatal(1);
    end
    received=received+1;
   end
   if(fault)begin $display("FAIL credit unexpected fault cyc=%0d",cyc);$fatal(1);end
   if(received==96)begin
    if(stalled==0)begin $display("FAIL credit no full-window backpressure exercised");$fatal(1);end
    $display("PASS credit packets=%0d held_positions=48 blocked_cycles=%0d first_latency=%0d",received,stalled,first_retire-first_issue);
    $finish;
   end
  end
  $display("FAIL credit deadlock sent=%0d received=%0d",sent,received);$fatal(1);
 end
endmodule
