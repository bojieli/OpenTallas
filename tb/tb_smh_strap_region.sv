module tb;
 reg clk=0;
 always #5 clk=~clk;
 reg [25:0] d;
 wire [25:0] q;
 ot_hbm_accel_smh_strap_region #(.MUT(`ifdef MUT 1 `else 0 `endif)) dut(.*);
 initial begin
   d=26'h219513;
   repeat(5) @(negedge clk);
   if(q!==d) $fatal(1,"SMT_STRAP_FAIL startup");
   repeat(32) begin
     @(negedge clk); d={$random} & 26'h3ffffff;
     repeat(5) @(negedge clk);
     if(q!==d) $fatal(1,"SMT_STRAP_FAIL offset");
     repeat(3) @(negedge clk);
     if(q!==d) $fatal(1,"SMT_STRAP_FAIL stable");
   end
   $display("SMT_STRAP_PASS 33 offset vectors five-edge settle"); $finish;
 end
endmodule
