`timescale 1ns/1ps
`ifndef SMUT
`define SMUT 0
`endif
module tb_hgi_hc_chunk_store32;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,clr=0;reg[1:0]wr_v=0;reg[9:0]wr_tag=0;reg[63:0]wr_data=0;
 reg scan_v=0;reg[1:0]scan_group=0;wire scan_o_v,full,fault;wire[255:0]scan_data;
 integer errors=0;integer n,g,k;reg[31:0]expected[0:31];
 ot_hgi_hc_chunk_store32 #(.MUT(`SMUT))u(.*);
 task edge0;begin @(negedge clk);end endtask
 task clear_store;begin edge0();clr=1;wr_v=0;scan_v=0;repeat(4)edge0();clr=0;repeat(4)edge0();if(full||fault)errors++;end endtask
 task fill(input integer seed0);begin
  for(n=0;n<16;n=n+1)begin
   edge0();wr_v=3;wr_tag={5'(31-n),5'(n)};
   expected[n]=32'h3f800000+32'(seed0+n);expected[31-n]=32'hbf800000+32'(seed0+n);
   wr_data={expected[31-n],expected[n]};
  end
  edge0();wr_v=0;repeat(5)edge0();if(!full||fault)errors++;
 end endtask
 task check_scan;begin
  for(g=0;g<4;g=g+1)begin
   edge0();scan_v=1;scan_group=2'(g);edge0();scan_v=0;
   @(posedge clk);#0.001;
   if(!scan_o_v)errors++;
   for(k=0;k<8;k=k+1)if(scan_data[k*32+:32]!==expected[g*8+k])errors++;
   repeat(2)edge0();
  end
 end endtask
 initial begin
  repeat(5)edge0();rst_n=1;repeat(6)edge0();clear_store();fill(0);check_scan();
  edge0();wr_v=1;wr_tag=5'd7;wr_data=64'h12345678;edge0();wr_v=0;repeat(4)edge0();if(!fault)errors++;
  clear_store();fill(77);check_scan();
  clear_store();edge0();wr_v=3;wr_tag={5'd9,5'd9};edge0();wr_v=0;repeat(4)edge0();if(!fault)errors++;
  $display("HC_CHUNK_STORE rows=2 scans=8 errors=%0d",errors);
  if(errors==0)$display("HC_CHUNK_STORE PASS");else $display("HC_CHUNK_STORE FAIL");$finish;
 end
endmodule
