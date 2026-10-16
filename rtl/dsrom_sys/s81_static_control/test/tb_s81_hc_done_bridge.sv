`timescale 1ns/1ps
module tb_s81_hc_done_bridge;
 reg sc=0,dc=0,rn=0,sv=0;reg[7:0]sd=0;wire dv;wire[7:0]dd;
 initial begin #12;forever begin sc=1;#3;sc=0;#3;end end
 initial begin #12;forever begin dc=1;#4;dc=0;#4;end end
 ot_s81_fixed_mailbox #(.W(8))dut(.s_clk(dc),.s_rst_n(rn),.s_v(sv),.s_d(sd),.d_clk(sc),.d_rst_n(rn),.d_v(dv),.d_d(dd));
 integer st=-1,dt=-1,next=0,seen=0;
 initial begin rn=1;#1;rn=0;#9;rn=1;end
 // Three different serial phases, with source tags supplied only at this
 // declared completion boundary. No HC arithmetic/timing claim is made.
 always @(negedge dc)begin
  sv=0;
  if(next<30&&dt+1==5+next*7)begin sv=1;sd=8'(next*13);next=next+1;end
 end
 always @(posedge dc)if(rn)dt=dt+1;
 always @(posedge sc)if(rn)begin
  st=st+1;#1;
  if(dv)begin
   if(st!=((5+seen*7)*4)/3+3||dd!==8'(seen*13))$fatal(1,"fixed completion mailbox age/tag moved st%0d seen%0d",st,seen);
   seen=seen+1;
  end
  if(seen==30)begin $display("HC_DONE_BRIDGE PASS completions30 all3serialphases fixededges tags");$finish;end
 end
 initial begin #5000;$fatal(1,"missing fixed completion");end
endmodule
