`timescale 1ns/1ps
module tb_reset;
 reg clk=0;always #5 clk=~clk;
 reg raw=0;reg[8:0]ref9;wire[511:0]good,bad;
 integer checks=0,errors=0,mutant=0;reg[31:0]rng=32'h2198ac55;
 ot_s81svc_reset9_n32 dut(.clk(clk),.reset_early9(raw),.reset_leaf(good));
 ot_s81svc_reset9_n32 #(.MUT(1)) neg(.clk(clk),.reset_early9(raw),.reset_leaf(bad));
 always@(posedge clk)ref9<={ref9[7:0],raw};
 initial begin
  // Ignore first9 serial samples: no assumption about uninitialized data flops.
  for(integer c=0;c<4000;c=c+1)begin
   @(negedge clk);rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
   if(c<20)raw=0;else if(c<40)raw=1;else if(c<41)raw=0;else if(c<60)raw=1;else if(c<72)raw=0;else raw=rng[0];
   @(posedge clk);#1;
   if(c>=9)begin checks=checks+1;if(good!=={512{ref9[8]}})errors=errors+1;if(bad!=={512{ref9[8]}})mutant=mutant+1;end
  end
  $display("RESET9_SAMEAGE checks=%0d leaves=512 errors=%0d shortpath_mismatches=%0d",checks,errors,mutant);
  if(checks!=3991||errors||mutant<1000)$fatal(1,"reset-age proof");$finish;
 end
endmodule
