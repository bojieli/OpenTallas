`timescale 1ns/1ps
module tb_hbm_coll_face_pipe512;
 reg clk=0; always #5 clk=~clk;
 reg [511:0] d;
 wire [511:0] q, baseline;
 ot_hbm_coll_face_pipe512 u(.clk(clk),.d(d),.q(q));
 for(genvar b=0;b<512;b=b+1) begin:golden
  // Original immutable die wrapper cell, one instance for each real pin bit.
  ot_hfd_oreg5 g(.clk(clk),.d(d[b]),.q(baseline[b]));
 end
 integer cycles=0,checked=0;
 initial begin
  d=0;
  repeat(2048) begin
   @(negedge clk);
   for(integer j=0;j<16;j=j+1)d[32*j+:32]=$random;
   @(posedge clk); #1;
   cycles=cycles+1;
   if(cycles>8)begin
    checked=checked+512;
    if(q!==baseline)begin $display("COLL_FACE FAIL cycle=%0d checked=%0d",cycles,checked);$fatal(1);end
   end
  end
  $display("COLL_FACE PASS checked=%0d cycles=%0d",checked,cycles);$finish;
 end
endmodule
