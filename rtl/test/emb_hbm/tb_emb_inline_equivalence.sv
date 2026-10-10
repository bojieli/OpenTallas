`timescale 1ns/1ps
module tb_inline;
parameter integer NEG=0;
import ot_qfd_emb_pkg::*;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,col_v=0,col_we=0,col_sr=0,w_v=0,r_v=0;
reg [255:0] w_d=0;reg [287:0] r_d=0;
wire [287:0] wd0,wd1,kd0,kd1;wire [257:0] ed0,ed1;
wire kv0,kv1,em0,em1,f0,f1;
ot_qfd_emb_pcport a(.clk(clk),.rst_n(rst_n),.col_v(col_v),.col_we(col_we),.col_sr(col_sr),.w_v(w_v),.w_d(w_d),.wd(wd0),.r_v(r_v),.r_d(r_d),.kv_v(kv0),.kv_d(kd0),.em_v(em0),.em_d(ed0),.fault(f0));
ot_qfd_emb_pcport_flat b(.clk(clk),.rst_n(rst_n),.col_v(col_v),.col_we(col_we),.col_sr(col_sr),.w_v(w_v),.w_d(w_d),.wd(wd1),.r_v(r_v),.r_d(r_d),.kv_v(kv1),.kv_d(kd1),.em_v(em1),.em_d(ed1),.fault(f1));
integer i,j,compared=0;reg [255:0] payload;reg [287:0] encoded;
always @(negedge clk) if(rst_n)begin
 if({kv0,em0,f0} !== {kv1,em1,f1} || (kv0 && kd0!==kd1) || (em0 && ed0!==(ed1 ^ 258'(NEG))) || (col_v&&col_we&&col_sr&&wd0!==wd1)) $fatal(1,"FAIL inline equivalence");
 if(kv0||em0)compared=compared+1;
end
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(i=0;i<256;i=i+1)begin
  payload={8{$random}};encoded=enc256(payload);
  // Alternate mutable static writes, embedding reads and KV reads.
  if(i%4==0)begin
   w_v=1;w_d=payload;@(negedge clk);w_v=0;repeat(2)@(negedge clk);
   col_v=1;col_we=1;col_sr=1;@(negedge clk);col_v=0;col_we=0;
  end else begin
   col_v=1;col_we=0;col_sr=(i%4!=1);@(negedge clk);col_v=0;
   repeat(2)@(negedge clk);
   r_v=1;r_d=encoded;if(i%4==2)r_d[5]=~r_d[5];if(i%4==3)begin r_d[7]=~r_d[7];r_d[10]=~r_d[10];end
   @(negedge clk);r_v=0;
  end
  repeat(8)@(negedge clk);
 end
 if(compared!=192)$fatal(1,"FAIL expected192 read responses got%0d",compared);
 $display("PASS inline equivalence writes64 reads192 incl CE UE KV");$finish;
end
endmodule
