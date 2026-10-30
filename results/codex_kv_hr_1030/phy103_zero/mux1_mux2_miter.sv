`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.5 clk=~clk;
 reg r_ce=0,w_ce=0;reg[8:0]ra=0,wa=0;reg[127:0]wd=0,wm=0;wire[127:0]q1,q2;
 integer cycle=0,checks=0,mutant_caught=0,i;reg[31:0]rng=32'h814a09d3;
 ot_sram_1r1w_512x128_m1_r2c2 m1(.clk(clk),.r_ce_in(r_ce),.r_addr_in(ra),.rd_out(q1),.w_ce_in(w_ce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(wm),.rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(14'b0));
 ot_sram_1r1w_512x128_m2_r2c2 m2(.clk(clk),.r_ce_in(r_ce),.r_addr_in(ra),.rd_out(q2),.w_ce_in(w_ce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(wm),.rr_en(2'b0),.rr_addr(16'b0),.cr_en(2'b0),.cr_sel(14'b0));
 function[31:0]next_rng(input[31:0]x);reg[31:0]z;begin z=x^(x<<13);z=z^(z>>17);next_rng=z^(z<<5);end endfunction
 task step;
 begin
  @(posedge clk);#0.001;cycle=cycle+1;checks=checks+128;
  if(q1!==q2)begin $display("FAIL cycle%0d ra%0d wa%0d wce%0d rce%0d q1%h q2%h",cycle,ra,wa,w_ce,r_ce,q1,q2);$fatal;end
  if((q2^128'b1)!==q1)mutant_caught=mutant_caught+1;
  @(negedge clk);
 end
 endtask
 initial begin
  @(negedge clk);
  // Cover every logical address, including mux2 row/column boundaries.
  for(i=0;i<512;i=i+1)begin w_ce=1;wa=i;wd={4{32'hcd103055^i}};wm=~128'b0;r_ce=1;ra=i;step;end
  w_ce=0;
  for(i=0;i<512;i=i+1)begin ra=i;r_ce=1;step;end
  // Both read enables, same-edge collisions, arbitrary bit masks and data.
  for(i=0;i<4096;i=i+1)begin
   rng=next_rng(rng);r_ce=rng[0];w_ce=rng[1];ra=rng[10:2];wa=(i%8==0)?ra:rng[19:11];
   rng=next_rng(rng);wd[31:0]=rng;rng=next_rng(rng);wd[63:32]=rng;rng=next_rng(rng);wd[95:64]=rng;rng=next_rng(rng);wd[127:96]=rng;
   rng=next_rng(rng);wm={rng,~rng,rng^32'h55555555,rng^32'haaaaaaaa};step;
  end
  if(mutant_caught==0)$fatal(1,"mutant not caught");
  $display("MUX1_MUX2_LOCKSTEP PASS cycles%0d bitchecks%0d mutant_caught%0d added_cycles0 repair_disabled_actual_binding",cycle,checks,mutant_caught);$finish;
 end
endmodule
