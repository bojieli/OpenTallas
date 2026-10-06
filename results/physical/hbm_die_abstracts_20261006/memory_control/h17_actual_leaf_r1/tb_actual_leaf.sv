`timescale 1ns/1ps
module tb_actual_leaf;
 parameter integer LBS=2;
 wire gv,gf; wire [31:0] gy; wire [15:0] gt;
 ot_hbm_accel_smv_leaf #(.SUB(4),.LBS(LBS),.LSB(16),.NC(8),.IL(8),
  .TAGW(16),.XD(128),.NBEAT(13),.COL(0),.SP(0),.TCK(1)) u_leaf(
  .clk(1'b0),.rst_n(1'b0),.c_in(22'b0),.w_in({(LBS*266+16*16){1'b0}}),
  .x_ce(1'b0),.x_addr(7'b0),.b_en(1'b0),.b_addr(7'b0),.b_oh(13'b0),
  .b_data(2048'b0),.gv(gv),.gy(gy),.gt(gt),.gf(gf));
 initial begin #1; $display("PASS actual frozen smv_leaf elaboration only"); $finish; end
endmodule
