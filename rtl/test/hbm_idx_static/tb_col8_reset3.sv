`timescale 1ns/1ps
`ifndef RESET_MUT
`define RESET_MUT 0
`endif
module tb_col8_reset3;
 reg clk=0,rst=0;always#5 clk=~clk;
 wire[37:0]a,b;integer checks=0;
 ot_rst_relay_l #(.REGIONS(38),.SYNC_STAGES(2),.TREE_STAGES(1))ref_reset(.clk(clk),.rst_n_in(rst),.rst_n(a));
 ot_hidx_rst_tree_3e_f32 #(.REGIONS(38),.MUT(`RESET_MUT))dut(.clk(clk),.rst_n_in(rst),.rst_n(b));
 always@(posedge clk or negedge clk)begin
  #0.01;if(a!==b)$fatal(1,"COL8_RESET3_FAIL checks=%0d ref=%h actual=%h",checks,a,b);
  checks=checks+1;
 end
 initial begin
  #17;rst=1;
  for(integer i=0;i<20;i=i+1)begin
   #(71+i%9);rst=0;#(3+i%7);rst=1;
  end
  #80;$display("COL8_RESET3_PASS checks=%0d regions=38 release_edges=3",checks);$finish;
 end
endmodule
