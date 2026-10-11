`timescale 1ns/1ps
module tb_hgi_att_sector;
 `include "sizes.svh"
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0, v=0; reg [265:0] word='x;
 wire ov; wire [255:0] codes; wire [31:0] mask,bad; wire [7:0] addr;
 reg [265:0] im[0:N-1]; reg [327:0] em[0:N-1];
 reg [327:0] expected; reg [255:0] cm; integer i,j,checked=0;
`ifdef MUT_SECTOR_ADDR
 localparam MA=1;
`else
 localparam MA=0;
`endif
 ot_hgi_att_sector_codec #(.MUT_ADDR(MA)) u(clk,rst_n,v,word[255:0],word[263:256],word[265:264],ov,codes,mask,bad,addr);
 initial begin
  $readmemh("input.mem",im);$readmemh("expected.mem",em);
  repeat(2) @(negedge clk);
  if(ov!==0) $fatal(1,"reset valid unknown");
  rst_n=1;
  for(i=0;i<N;i=i+1) begin
   word=im[i];v=1;@(negedge clk);v=0;word='x;
   @(negedge clk);
   expected=em[i];cm=0;
   for(j=0;j<32;j=j+1) if(expected[256+j] && !expected[288+j]) cm[8*j+:8]=8'hff;
   if(ov!==1 || mask!==expected[287:256] || (bad&mask)!==expected[319:288] || addr!==expected[327:320] ||
      (codes&cm)!==(expected[255:0]&cm)) $fatal(1,"sector %0d mismatch",i);
   checked=checked+1;@(negedge clk);
   if(ov!==0) $fatal(1,"stale valid");
  end
  $display("ATT_SECTOR PASS %0d sectors",checked);$finish;
 end
endmodule
