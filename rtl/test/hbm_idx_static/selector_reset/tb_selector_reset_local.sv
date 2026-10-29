`timescale 1ns/1ps
module tb_selector_reset_local;
 reg clk=0; always #5 clk=~clk;
 reg rn=0; wire w,e,mw,me;
 ot_hbm_idx_selector_reset_local good(.clk(clk),.rst_i_n(rn),.rst_w_n(w),.rst_e_n(e));
 ot_hbm_idx_selector_reset_local #(.MUT(1)) mutant(.clk(clk),.rst_i_n(rn),.rst_w_n(mw),.rst_e_n(me));
 reg [1:0] reference=0;
 integer checked=0,caught=0;
 always @(posedge clk) reference<={reference[0],rn};
 always @(negedge clk)begin
  if(checked>2)begin
   if(w!==reference[1]||e!==reference[1])$fatal(1,"reset relay mismatch");
   if({mw,me}!={w,e})caught=caught+1;
  end
  checked=checked+1;
 end
 initial begin
  repeat(8)@(negedge clk);
  for(integer n=0;n<128;n=n+1)begin rn=(n%19>=4);@(negedge clk);end
  rn=0;repeat(8)@(negedge clk);rn=1;repeat(8)@(negedge clk);
  if(caught<32)$fatal(1,"reset mutant not caught");
  $display("RESET_RELAY_PASS checked=%0d mutant_caught=%0d fixed_latency=2",checked,caught);$finish;
 end
endmodule
