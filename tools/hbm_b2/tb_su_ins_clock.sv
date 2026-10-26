`timescale 1ns/1ps
// Functional insertion-line reference: all four related roots carry the same
// clock. The software shift covers every stage, including DMAX193..198.
module tb_su_ins_clock;
 parameter integer DMAX=198,RESET_DATA=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,v=0;reg[15:0]d=0;
 wire vo,coll,busy;wire[15:0]q;
 ot_hbm_su_static_ins #(.W(16),.K(1),.DEPTHS(16'(DMAX)),.DMAX(DMAX),.RESET_DATA(RESET_DATA)) dut(
  .clk({4{clk}}),.rst_n(rst_n),.v(v),.sel(1'b1),.d(d),.vo(vo),.q(q),.coll(coll),.busy(busy));
 localparam integer N=DMAX>0?DMAX:1;
 reg[N:1]rv=0;reg[15:0]data[1:N];integer checked=0;
 always @(posedge clk)begin
  if(!rst_n)rv<=0;
  else begin
   for(integer k=1;k<N;k=k+1)begin rv[k]<=rv[k+1];data[k]<=data[k+1];end
   rv[N]<=v;data[N]<=d;
  end
  #1;
  if(rst_n)begin
   if(vo!==(DMAX==0?v:rv[1]))$fatal(1,"INS_CLOCK valid mismatch DMAX%0d t%0t",DMAX,$time);
   if(vo)begin
    if(q!==(DMAX==0?d:data[1]))$fatal(1,"INS_CLOCK data mismatch DMAX%0d",DMAX);
    checked=checked+1;
   end
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(integer n=0;n<500;n=n+1)begin
   v=n%13==0;d=16'(n*61+21);@(negedge clk);
  end
  v=0;repeat(DMAX+4)@(negedge clk);
  if(checked!=39)$fatal(1,"INS_CLOCK count%0d expected39",checked);
  $display("INS_CLOCK PASS DMAX%0d RESET_DATA%0d checked%0d added_cycles0",DMAX,RESET_DATA,checked);$finish;
 end
endmodule
