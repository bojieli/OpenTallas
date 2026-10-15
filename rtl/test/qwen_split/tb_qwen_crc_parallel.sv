`timescale 1ns/1ps
module tb_qwen_crc_parallel;
 parameter integer DW=567,CW=16;
 reg [DW-1:0] d;
 wire [CW-1:0] q;
 integer n,k,errors=0;
 reg [CW-1:0] c;
 reg f;
 ot_qwen_crc_parallel #(.DW(DW),.CW(CW)) dut(.d(d),.q(q));
 initial begin
  for(n=0;n<256;n=n+1)begin
   for(k=0;k<DW;k=k+1)d[k]=$random;
   c={CW{1'b1}};
   for(k=DW-1;k>=0;k=k-1)begin
    f=c[CW-1]^d[k];
    c={c[CW-2:0],1'b0}^(f?(CW==32?CW'(32'h04c11db7):CW'(16'h1021)):{CW{1'b0}});
   end
   #1;
   if(q!==c)errors=errors+1;
  end
  if(errors==0)$display("CRC_MATRIX_PASS DW%0d CW%0d compares256",DW,CW);
  else $display("CRC_MATRIX_FAIL DW%0d CW%0d errors%0d",DW,CW,errors);
  $finish;
 end
endmodule
