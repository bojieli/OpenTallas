`timescale 1ns/1ps
module tb_sfu_literal_relay #(parameter integer R=23,MUT=0);
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg [33:0] rq=0;reg [561:0] wq=0;reg [513:0] rr=0;reg[1:0] done=0;
wire[33:0] lq;wire[561:0] lw;wire[513:0] cr;wire[1:0] cd;
ot_hgi_sfu_lg_hbfd_relay #(.R(R+(MUT==1))) dut(.clk(clk),.rst_n(rst_n),.c_rq(rq),.c_wq(wq),.c_rr(cr),.c_w_done(cd),.l_rq(lq),.l_wq(lw),.l_rr(rr),.l_w_done(done));
reg[623:0] ef[0:255],eb[0:255];integer count=0;
initial begin
 repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 for(integer n=0;n<200;n=n+1)begin
  rq={2'b11,32'(n*17+3)};wq={18{32'(n*771+19)}};rr={17{32'(n*297+17)}};done=2'(n);
  ef[n]={28'd0,wq,rq};eb[n]={108'd0,done,rr};
  @(posedge clk);#1;
  if(n>=R-1)begin
   if({28'd0,lw,lq}!==ef[n-R+1]||{108'd0,cd,cr}!==eb[n-R+1])$fatal(1,"LITERAL_RELAY timing/data mismatch n%0d R%0d",n,R);
   count=count+1;
  end
  @(negedge clk);
 end
 $display("LITERAL_RELAY PASS R=%0d checks=%0d exactbothways",R,count);$finish;
end
endmodule
