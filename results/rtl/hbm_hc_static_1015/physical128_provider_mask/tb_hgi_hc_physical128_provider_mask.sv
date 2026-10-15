`timescale 1ns/1ps
// Independent primitive semantics test; expected words never drive the macro.
module tb_hgi_hc_physical128_provider_mask;
 reg clk=0;always #5 clk=~clk;
 reg r_ce_in=0,w_ce_in=0;reg [6:0] r_addr_in=0,w_addr_in=0;
 reg [255:0] wd_in=0,w_mask_in=0;
 wire [255:0] physical_data,ideal_data;
 reg use_ideal=0;wire [255:0] observed=use_ideal?ideal_data:physical_data;
 reg [255:0] expected[0:127];integer checked=0;
 ot_sram_1r1w_128x256_m1_r2c2 physical(
  .clk(clk),.r_ce_in(r_ce_in),.r_addr_in(r_addr_in),.rd_out(physical_data),
  .w_ce_in(w_ce_in),.w_addr_in(w_addr_in),.wd_in(wd_in),.w_mask_in(w_mask_in),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_mask_ideal_mutant ideal(
  .clk(clk),.r_ce_in(r_ce_in),.r_addr_in(r_addr_in),.rd_out(ideal_data),
  .w_ce_in(w_ce_in),.w_addr_in(w_addr_in),.wd_in(wd_in),.w_mask_in(w_mask_in),
  .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(16'b0));
 task tick;begin @(posedge clk);#1;end endtask
 task write_word(input integer addr,input [255:0] data,input [255:0] mask,input bit enable_);
  begin @(negedge clk);w_addr_in=7'(addr);wd_in=data;w_mask_in=mask;w_ce_in=enable_;
   tick();@(negedge clk);w_ce_in=0;
  end
 endtask
 task check_word(input integer addr,input [255:0] wanted,input integer phase);
  begin @(negedge clk);r_addr_in=7'(addr);r_ce_in=1;tick();
   if(observed!==wanted)$fatal(1,"MASK_SEMANTICS_MISMATCH phase%0d address%0d ideal%0d",phase,addr,use_ideal);
   checked=checked+1;@(negedge clk);r_ce_in=0;
  end
 endtask
 initial begin:test
  reg [255:0] data,mask,prior,held;
  use_ideal=$test$plusargs("IDEAL_MUTANT");
  for(integer a=0;a<128;a=a+1)begin
   data={8{32'h12340000+32'(a)}};expected[a]=data;
   write_word(a,data,{256{1'b1}},1);
  end
  for(integer a=0;a<128;a=a+1)check_word(a,expected[a],0);
  for(integer a=0;a<128;a=a+1)begin
   data=~expected[a];
   for(integer b=0;b<256;b=b+1)mask[b]=(b%7)!=(a%7);
   prior=expected[a];expected[a]=(prior&~mask)|(data&mask);
   write_word(a,data,mask,1);
  end
  for(integer a=0;a<128;a=a+1)check_word(a,expected[a],1);
  for(integer a=0;a<128;a=a+1)write_word(a,~expected[a],0,1);
  for(integer a=0;a<128;a=a+1)check_word(a,expected[a],2);
  for(integer a=0;a<128;a=a+1)write_word(a,~expected[a],{256{1'b1}},0);
  for(integer a=0;a<128;a=a+1)check_word(a,expected[a],3);
  @(negedge clk);r_ce_in=1;r_addr_in=17;w_ce_in=1;w_addr_in=17;
  wd_in=~expected[17];w_mask_in={256{1'b1}};prior=expected[17];tick();
  if(observed!==prior)$fatal(1,"READ_BEFORE_WRITE_MISMATCH");
  expected[17]=~prior;@(negedge clk);w_ce_in=0;r_ce_in=0;
  check_word(17,expected[17],4);held=observed;repeat(3)tick();
  if(observed!==held)$fatal(1,"READ_ENABLE_HOLD_MISMATCH");
  $display("HC_PHYSICAL128_PROVIDER_MASK PASS addresses128 checked%0d perbit_masks zero_mask write_enable read_before_write read_hold",checked);$finish;
 end
 initial begin #100000;$fatal(1,"provider mask timeout");end
endmodule
