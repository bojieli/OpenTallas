`timescale 1ns/1ps
module ot_sram_1r1w_32x64_m1(input clk,r_ce_in,input [4:0] r_addr_in,output reg [63:0] rd_out,input w_ce_in,input [4:0] w_addr_in,input [63:0] wd_in,w_mask_in);
 reg [63:0] m[0:31];
 always @(posedge clk) begin
  if(r_ce_in) rd_out<=m[r_addr_in];
  if(w_ce_in) m[w_addr_in]<=(m[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in);
 end
endmodule
module tb_orq #(parameter integer D=3, parameter integer W=512, parameter integer MUT=0, parameter integer N=200000);
 reg ck=0; reg rst_n=0; reg [W-1:0] d;
 wire [W-1:0] qa,qb;
 qfd_dv_sram_delay #(.W(W),.D(D)) a(.ck(ck),.rst_n(rst_n),.d(d),.q(qa));
 qfd_dv_sram_delay_orq #(.W(W),.D(D),.MUT(MUT)) b(.ck(ck),.rst_n(rst_n),.d(d),.q(qb));
 integer i=0,err=0,seen=0; integer seed=7;
 always #1 ck=~ck;
 function automatic [W-1:0] rnd(); integer k; begin rnd=0; for(k=0;k<W;k=k+1) rnd[k]=$urandom(); end endfunction
 always @(negedge ck) begin
  i<=i+1;
  // random reset pulses after warm-up, plus the opening reset
  if(i<3) rst_n<=0; else if(i%50021==0) rst_n<=0; else if(i%50021==3) rst_n<=1; else if(i<4) rst_n<=1;
  d<=rnd();
  if(rst_n && i>4) begin
    if(qa!==qb) begin err=err+1; if(err<6) $display("MISMATCH i=%0d qa=%h qb=%h",i,qa[31:0],qb[31:0]); end
    if(^qa===1'bx) seen=seen; else if(qa!=0) seen=seen+1;
  end
  if(i==N) begin
   if(err==0 && seen>100) $display("PASS D=%0d W=%0d MUT=%0d seen=%0d cycles=%0d",D,W,MUT,seen,i);
   else begin $display("FAIL D=%0d MUT=%0d err=%0d seen=%0d",D,MUT,err,seen); end
   $finish;
  end
 end
endmodule
