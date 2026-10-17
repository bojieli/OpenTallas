`timescale 1ns/1ps
module tb_qwen_romleaf_1552;
 reg clk=0; always #0.41665 clk=~clk;
 reg rst_n=0,ce=0,any_ce=0;
 reg [11:0] addr=0;
 wire [1023:0] ref_q;
 wire [25:0] req;
 wire [265:0] rd0,rd1;
 wire [511:0] q0,q1;
 ot_qwen_tile_romleaf a(.clk(clk),.rst_n(rst_n),.ce_d(ce),.any_d(any_ce),.ad_d(addr),.r_q(q0));
 ot_qwen_tile_romleaf b(.clk(clk),.rst_n(rst_n),.ce_d(ce),.any_d(any_ce),.ad_d(addr),.r_q(q1));
 // Independent established two-column production pipeline as expected-value reference.
 ot_qwen_rpair_logic ref_lg(.clk(clk),.ck_pair(2'b0),.rst_n(rst_n),.ce_d(ce),.any_d(any_ce),.ad_d(addr),.req_m(req),.rd({rd1[255:0],rd0[255:0]}),.r_q(ref_q));
 ot_rom_4096x266_m8 ref0(.clk(clk),.ce_in(req[12]),.addr_in(req[11:0]),.rd_out(rd0));
 ot_rom_4096x266_m8 ref1(.clk(clk),.ce_in(req[25]),.addr_in(req[24:13]),.rd_out(rd1));
 integer row,col,t,checks=0,nonzero=0,mut=0;
 reg [2127:0] mask0,mask1;
 reg [511:0] prev;
 initial begin
  void'($value$plusargs("MUT=%d",mut));
  #0.01;
  // Populate physical via-mask cells at the declared component input boundary.
  // Covers all 4096 addresses, each of 256 payload bits, distinct column masks.
  for(row=0;row<512;row=row+1) begin
   for(col=0;col<2128;col=col+1) begin
    mask0[col]=((row*37+col*13+(col>>3))%31)<15;
    mask1[col]=((row*17+col*23+(col>>4))%29)<13;
   end
   a.u_rom.arr[row]=mask0;ref0.arr[row]=mask0;
   b.u_rom.arr[row]=mask1;ref1.arr[row]=mask1;
  end
  for(t=0;t<8300;t=t+1) begin
   @(negedge clk);
   rst_n=(t>=3 && t!=4140 && t!=4141);
   addr=(t<4120)?t[11:0]:(~t[11:0]);
   ce=(t%7!=0);any_ce=(t%11!=0)||ce;
   @(posedge clk); #0.01;
   if(t>15 && !(t>=4140 && t<4155)) begin
    checks=checks+1;
    if (q0!==ref_q[511:0] || q1!==ref_q[1023:512])
     $fatal(1,"ROMLEAF_FAIL edge=%0d mutant=%0d",t,mut);
    if(|q0 || |q1)nonzero=nonzero+1;
   end
   prev=q0;
  end
  if(nonzero<4000)$fatal(1,"ROMLEAF_FAIL vacuous %0d",nonzero);
  $display("ROMLEAF_PASS checks=%0d nonzero=%0d addresses=4096 columns=2",checks,nonzero);$finish;
 end
endmodule
