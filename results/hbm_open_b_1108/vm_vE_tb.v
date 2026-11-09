`timescale 1ns/1ps
module tb;
 reg clk=0; always #0.4165 clk=~clk;
 reg [23:0] vmasm_sel=0; reg [2047:0] vmasm_rd_il=0; reg writer_rst_n=0; reg [1:0] writer_sid=0; reg [3:0] writer_rgx_v=0; reg [159:0] writer_rgx_addr=0;
 reg [511:0] writer_rgx_data0=0, writer_rgx_data1=0, writer_rgx_data2=0, writer_rgx_data3=0; reg writer_rgx_vm=0; reg writer_tkw_v=0; reg [567:0] writer_tkw_d=0; reg [4:0] writer_ingress_slot=0; reg [7:0] writer_slot_valid=0; reg [31:0] writer_slot_owner=0;
 wire [2047:0] vmasm_as_il; wire [280:0] writer_kq0,writer_kq1,writer_kq2,writer_kq3,writer_kq4,writer_kq5,writer_kq6,writer_kq7; wire writer_fault;
 ot_hfd_coll_q3_vm_core dut(.*);
 integer i,j,f,seed=32'h1234;
 function [511:0] r512; input integer dummy; integer k; begin for(k=0;k<16;k=k+1) r512[k*32+:32]=$random(seed); end endfunction
 initial begin f=$fopen(`OUTF,"w");
  for(i=0;i<3000;i=i+1) begin
   @(negedge clk); #0.05;
   if(i==8) writer_rst_n=1; if(i==1500) writer_rst_n=0; if(i==1510) writer_rst_n=1;
   vmasm_sel=$random(seed); writer_sid=$random(seed); writer_rgx_v=$random(seed); writer_rgx_vm=$random(seed); writer_tkw_v=$random(seed);
   writer_ingress_slot=$random(seed); writer_slot_valid=$random(seed); writer_slot_owner=$random(seed);
   writer_rgx_addr={5{$random(seed)}}; writer_rgx_data0=r512(0); writer_rgx_data1=r512(0); writer_rgx_data2=r512(0); writer_rgx_data3=r512(0);
   writer_tkw_d={r512(0),r512(0)}; for(j=0;j<4;j=j+1) vmasm_rd_il[j*512+:512]=r512(0);
   @(posedge clk);
   $fdisplay(f,"%h %h %h %h %h %h %h %h %h %b",vmasm_as_il,writer_kq0,writer_kq1,writer_kq2,writer_kq3,writer_kq4,writer_kq5,writer_kq6,writer_kq7,writer_fault);
  end
  $fclose(f); $finish; end
endmodule
