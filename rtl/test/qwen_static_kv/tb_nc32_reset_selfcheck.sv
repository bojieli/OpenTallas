`timescale 1ps/1fs
module tb_nc32_reset_selfcheck #(parameter integer MUT=0);
 // A falling edge before any rising edge reproduces unrelated power-on copies.
 reg ck=1,rst_n=0;
 always #416.5 ck=~ck;
 wire[783:0]h,h_e;wire fault;
 qkd_kv_es_fan_root2_b_nc32 dut(.ck(ck),.rst_n(rst_n),
 .es(1152'b0),.dest_pc(20'b0),.dest_stack(2'b0),.identity(59'b0),.generation(2'b0),
 .expected_valid(4'b0),.expected_pc(20'b0),.expected_stack(2'b0),.expected_identity(59'b0),
 .expected_generation(2'b0),.expected_address(29'b0),.emb_start(1'b0),.emb_token(18'b0),
 .emb_epoch(16'b0),.cfg_we(1'b0),.cfg_addr(8'b0),.cfg_data(64'b0),.bw(293'b0),
 .h(h),.h_e(h_e),.fault(fault));
 initial begin
  repeat(10)@(negedge ck);rst_n=1;
  repeat(20)@(negedge ck);
  if(h!==h_e)$fatal(1,"released E-face copies differ");
  if(MUT!=0)begin
   force dut.h_e = 784'd1;
   repeat(2)@(negedge ck);
   $fatal(1,"copy mutant escaped reset guard");
  end
  $display("PASS random power-on copies ignored only while reset active; released copies checked");$finish;
 end
endmodule
