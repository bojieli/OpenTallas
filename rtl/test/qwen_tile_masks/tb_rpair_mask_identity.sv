`timescale 1ns/1ps
// Binding proof uses real ROM macro models; released numeric contents are
// checked separately by the released-image production bench.
module tb_rpair_mask_identity;
 reg clk=0;always #1 clk=~clk;
 wire[1023:0] q0,q1;
 ot_qwen_tile_rpair #(.ROM_TILE(2),.ROM_BANK(1)) a(.clk(clk),.rst_n(1'b1),.ce_d(1'b1),.any_d(1'b1),.ad_d(12'd0),.r_q(q0));
 ot_qwen_tile_rpair #(.ROM_TILE(7),.ROM_BANK(4)) b(.clk(clk),.rst_n(1'b1),.ce_d(1'b1),.any_d(1'b1),.ad_d(12'd0),.r_q(q1));
 initial begin
  #30;
  if(a.u_rom0.rd_out!=={266{1'b1}} || a.u_rom1.rd_out!==266'd0 ||
     b.u_rom0.rd_out!==266'd0 || b.u_rom1.rd_out!=={266{1'b1}})
    $fatal(1,"tile/bank/column mask identity mismatch");
  $display("RPAIR_MASK_IDENTITY_PASS two actual pairs/four distinct mask IDs");$finish;
 end
endmodule
