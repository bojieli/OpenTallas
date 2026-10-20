`timescale 1ns/1ps
module tb_idx_glue_reset_f32;
 parameter integer MUT=0;
 reg clk=0;always #1 clk=~clk;
 reg rn=0;wire[31:0] old_r,new_r;
 ot_rst_relay_l #(.REGIONS(32),.SYNC_STAGES(2),.TREE_STAGES(1)) u_old(.clk(clk),.rst_n_in(rn),.rst_n(old_r));
 ot_hidx_rst_tree_f32 #(.REGIONS(32),.MUT(MUT)) u_new(.clk(clk),.rst_n_in(rn),.rst_n(new_r));
 reg old_d=0;integer checks=0,epochs=0;
 always @(posedge clk or negedge rn)if(!rn)old_d<=0;else old_d<=old_r[0];
 always @(negedge clk)if(rn)begin
  checks=checks+32;
  if(new_r!=={32{old_d}})$fatal(1,"BOOT_RELEASE_FAIL epoch%0d new%h expected%h",epochs,new_r,{32{old_d}});
 end
 initial begin
  // Reset assertion is checked between clock edges as well as on them.
  for(integer e=0;e<40;e=e+1)begin
   @(negedge clk);#0.13;rn=0;#0.01;
   if(old_r!==0||new_r!==0)$fatal(1,"BOOT_ASYNC_ASSERT_FAIL");
   repeat(2+(e%3))@(negedge clk);
   #0.31;epochs=epochs+1;rn=1;
   repeat(12+(e%7))@(negedge clk);
  end
  if(checks<18000)$fatal(1,"BOOT_COVERAGE_FAIL checks%0d",checks);
  $display("GLUE_RESET_F32_PASS epochs%0d checks%0d extra_release_edges1 leaves32",epochs,checks);$finish;
 end
endmodule
