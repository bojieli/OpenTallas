`timescale 1ns/1ps
// Arithmetic stubs: this bench proves metadata fail-stop only, never arithmetic.
module ot_gpu_bd_col(input clk,rst_n,v,first,last,fp4,input[15:0]tag,
 input[511:0]wq,xq,input[19:0]we,xe,output ov,output[31:0]y,output[15:0]otag,output fault);
 assign ov=0;assign y=0;assign otag=0;assign fault=0;
endmodule
module ot_hbm_accel_tc16(input clk,rst_n,v,first,last,input[15:0]tag,input[255:0]w,x,
 output ov,output[31:0]y,output[15:0]otag,output fault);
 assign ov=0;assign y=0;assign otag=0;assign fault=0;
endmodule
module leaf_control_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0;wire gv,gf;wire[31:0]gy;wire[15:0]gt;integer i;
 ot_hbrom_smv_leaf_protected #(.PROTECT(1))dut(.clk(clk),.rst_n(rst),.c_in(22'b0),.w_in(788'b0),
 .x_ce(1'b0),.x_addr(7'b0),.b_en(1'b0),.b_addr(7'b0),.b_oh(2'b0),.b_data(2048'b0),.gv(gv),.gy(gy),.gt(gt),.gf(gf));
 task tick;begin @(posedge clk);#1;end endtask
 initial begin
  for(i=0;i<90;i=i+1)begin
   rst=0;tick();@(negedge clk);rst=1;tick();@(negedge clk);
   if(i<22)dut.g_protected.c3[i]=~dut.g_protected.c3[i];
   else if(i<44)dut.g_protected.c4[i-22]=~dut.g_protected.c4[i-22];
   else if(i<66)dut.g_protected.c5[i-44]=~dut.g_protected.c5[i-44];
   else if(i<88)dut.g_protected.c6[i-66]=~dut.g_protected.c6[i-66];
   else if(i==88)dut.g_protected.leaf_fault=~dut.g_protected.leaf_fault;
   else dut.g_protected.leaf_fault_shadow=~dut.g_protected.leaf_fault_shadow;
   #1;if(!dut.g_protected.leaf_stop)$fatal(1,"leaf control fault escaped %0d",i);
   repeat(2)tick();if(!gf||gv)$fatal(1,"leaf control not failclosed %0d",i);
  end
  $display("PASS all90 leaf metadata/latch faults, arithmetic stubbed");$finish;
 end
endmodule
