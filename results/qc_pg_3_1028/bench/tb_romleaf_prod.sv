`timescale 1ns/1ps
// QC-PG-3: production states of one A0 ROM leaf (one 4096x266 macro + capture + BF16 expansion).
// A matvec reads one bank (both columns) per cycle, sequential rows, so per cycle 2 of the 10 leaves of a tile read.
//   +MODE=1 ACTIVE: ce_d = any_d = 1 every cycle, sequential addresses (this leaf's bank is the one being read)
//   +MODE=2 OTHER : ce_d = 0, any_d = 1 (another bank of the tile is being read; address bus held)
// ROM image: uniform random bits (random INT8 codes; >= the toggle density of real gaussian weights).
module tb_romleaf_prod;
 reg clk=0; always #0.41665 clk=~clk;
 reg rst_n=0,ce=0,any_ce=0; reg [11:0] addr=0;
 wire [511:0] q0;
 integer mode=1,row,col,t,nz=0;
 reg [2127:0] m;
 ot_qwen_tile_romleaf a(.clk(clk),.rst_n(rst_n),.ce_d(ce),.any_d(any_ce),.ad_d(addr),.r_q(q0));
 initial begin
  void'($value$plusargs("MODE=%d",mode));
  if(mode==1) begin $dumpfile("romleaf_m1.vcd"); end else begin $dumpfile("romleaf_m2.vcd"); end
  $dumpvars(0,tb_romleaf_prod);
  #0.01;
  for(row=0;row<512;row=row+1) begin for(col=0;col<2128;col=col+32) m[col+:32]=$urandom; a.u_rom.arr[row]=m; end
  for(t=0;t<8200;t=t+1) begin
   @(negedge clk);
   rst_n=(t>=3);
   if(mode==1) begin ce=(t>=8); any_ce=(t>=8); addr=t[11:0]; end
   else begin ce=0; any_ce=(t>=8); addr=12'd0; end
   @(posedge clk); #0.01; if(|q0) nz=nz+1;
  end
  if(mode==1 && nz<4000) $fatal(1,"ROMLEAF_PROD vacuous %0d",nz);
  $display("ROMLEAF_PROD_PASS mode=%0d nonzero=%0d",mode,nz); $finish;
 end
endmodule
