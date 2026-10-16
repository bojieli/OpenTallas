`timescale 1ns/1ps
`default_nettype none
// V6 VM-assembly leaf miter (H-NETLIST 1315): ot_hgi_coll_vmasm (bit-interleaved faces, parent permutation reproduced
// here) against the V5 protocol-leaf code it replaced (vm_select_pipe[0..8], vm_raw_data <= vm_rr, assembled pair
// {bank[sel hi], bank[sel lo]}), random selects and data every edge. +N=edges.
module tb_hgi_coll_vmasm_miter;
 reg clk=0;always #1 clk=~clk;
 reg [23:0] sel;reg [2055:0] vm_rr;
 // reference (V5 code)
 reg [23:0] vsp[0:8];reg [2047:0] vraw;reg [2047:0] ref_as;
 always @(posedge clk)begin
  vsp[0]<=sel;for(integer j=1;j<9;j=j+1)vsp[j]<=vsp[j-1];
  for(integer b=0;b<8;b=b+1)vraw[b*256+:256]<=vm_rr[b*257+:256];
  for(integer j=0;j<4;j=j+1)ref_as[j*512+:512]<={vraw[256*int'(vsp[8][j*6+3+:3])+:256],vraw[256*int'(vsp[8][j*6+:3])+:256]};
 end
 // DUT with the parent's wiring
 wire [2047:0] rd_il,as_il,dut_as;
 for(genvar b=0;b<8;b=b+1)for(genvar i=0;i<256;i=i+1)begin:g_i assign rd_il[i*8+b]=vm_rr[b*257+i];end
 for(genvar j=0;j<4;j=j+1)for(genvar i=0;i<256;i=i+1)begin:g_o
  assign dut_as[j*512+i]=as_il[i*8+2*j];assign dut_as[j*512+256+i]=as_il[i*8+2*j+1];end
 ot_hgi_coll_vmasm dut(.clk(clk),.sel(sel),.rd_il(rd_il),.as_il(as_il));
 integer n,bad=0,chk=0;
 initial begin
  if(!$value$plusargs("N=%d",n))n=4000;
  sel=0;vm_rr=0;
  for(integer c=0;c<n;c=c+1)begin
   @(negedge clk);
   sel={$random};for(integer w=0;w<65;w=w+1)vm_rr[w*32+:32]=$random;
   if(c>12)begin chk=chk+1;if(dut_as!==ref_as)begin bad=bad+1;if(bad<4)$display("MISMATCH edge%0d",c);end end
  end
  if(bad==0)$display("VMASM_MITER PASS checks%0d",chk);else $display("VMASM_MITER FAIL mismatches%0d checks%0d",bad,chk);
  $finish;
 end
endmodule
`default_nettype wire
