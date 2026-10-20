`timescale 1ns/1ps
module tb_gq_req_chunk_eq;
 parameter integer MUT=0,SEED=1;
 reg clk=0;always #5 clk=~clk;
 reg rst=0;reg[1:0]eq=0,ep=0;reg[7:0]qsel=0;reg[1:0]psel=0;
 reg[103:0]qa=0;reg[2:0]src_hi=0;reg[31:0]pr=0;
 wire[16:0]actual;reg[16:0]expected,n;integer seed=SEED;integer checked=0;
 ot_hgi_coll_gq_req_chunk #(.LO(0),.W(9))lo(.clk(clk),.rst_n(rst),.eq(eq),.ep(ep),.qsel(qsel),.psel(psel),.qa(qa),.src_hi(src_hi),.pr(pr),.q(actual[8:0]));
 ot_hgi_coll_gq_req_chunk #(.LO(MUT==1?8:9),.W(8))hi(.clk(clk),.rst_n(rst),.eq(eq),.ep(ep),.qsel(qsel),.psel(psel),.qa(qa),.src_hi(src_hi),.pr(pr),.q(actual[16:9]));
 always @*begin
  n=0;
  for(integer i=0;i<8;i=i+1)if(eq[i/4]&&qsel[i])n={1'b1,src_hi,qa[i*13+:13]};
  for(integer i=0;i<2;i=i+1)if(ep[i]&&psel[i])n={1'b1,pr[i*16+:16]};
 end
 initial begin
  void'($urandom(seed));
  repeat(3)@(posedge clk);
  for(integer t=0;t<10000;t=t+1)begin
   @(negedge clk);rst=(t%113>=3);eq=$urandom;ep=$urandom;qsel=$urandom;psel=$urandom;
   qa={$urandom,$urandom,$urandom,$urandom};pr=$urandom;src_hi=$urandom;
   #1;expected=rst?n:17'd0;
   @(posedge clk);#1;checked=checked+1;
   if(actual!==expected)begin $display("REQ_CHUNK_EQ_FAIL seed=%0d mut=%0d t=%0d actual=%h expected=%h",SEED,MUT,t,actual,expected);$fatal;end
  end
  $display("REQ_CHUNK_EQ_PASS seed=%0d checked=%0d",SEED,checked);$finish;
 end
endmodule
