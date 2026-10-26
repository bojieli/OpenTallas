`timescale 1ns/1ps
module tb_s81_vp_norepair;
 reg clk=0;always #0.4165 clk=~clk;
 reg re=0,we=0;reg[8:0]ra=0,wa=0;reg[127:0]wd=0,mask=0;wire[127:0]a,b;
 integer seed=17,checks=0,errors=0,mut=0,same=0,partial=0;integer i,j;
 ot_sram_1r1w_512x128_m4_r2c2 old(.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(a),.w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
 ot_sram_1r1w_512x128_m4_r0c0 replacement(.clk(clk),.r_ce_in(re),.r_addr_in(ra^(mut?9'd1:9'd0)),.rd_out(b),.w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask));
 task tick;begin @(posedge clk);#0.05;if(re)begin checks++;if(a!==b)errors++;end @(negedge clk);end endtask
 initial begin
  if($test$plusargs("MUT"))mut=1;
  for(i=0;i<512;i++)begin we=1;wa=9'(i);mask='1;for(j=0;j<4;j++)wd[j*32+:32]=$random(seed);tick;end
  for(i=0;i<8192;i++)begin re=1;we=$random(seed);ra=9'($random(seed));wa=(i%4==0)?ra:9'($random(seed));if(we&&ra==wa)same++;for(j=0;j<4;j++)begin wd[j*32+:32]=$random(seed);mask[j*32+:32]=$random(seed);end if(we&&mask!='1&&mask!=0)partial++;tick;end
  $display("VP_NOREPAIR checks=%0d mismatches=%0d read_write_same=%0d partial=%0d mutant=%0d",checks,errors,same,partial,mut);
  if(errors!=0)$fatal(1,"VP_NOREPAIR mismatch");if(same==0||partial==0)$fatal(1,"missing coverage");$display("VP_NOREPAIR_PASS");$finish;
 end
endmodule
