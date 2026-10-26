`timescale 1ns/1ps
module tb_fixed_repair #(parameter integer MUT=0);
reg clk=0; always #5 clk=~clk;
reg re=0,we=0;reg[8:0] ra=0,wa=0;reg[127:0] wd=0,mask=0;
wire[127:0] a,b;wire[127:0] dm=(MUT==1)?128'hffffffffffffffffffffffffffffffff:mask;
wire[8:0] da=(MUT==2)?(ra^9'd1):ra;
ot_sram_1r1w_512x128_m4_r2c2 refmem(.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(a),.w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
ot_sram_1r1w_512x128_m4_r2c2_nr dut(.clk(clk),.r_ce_in(re),.r_addr_in(da),.rd_out(b),.w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in(dm));
integer i,errors=0,checks=0,same=0,masked=0;integer seed=1713;
initial begin
 i=$urandom(seed);
 for(i=0;i<12000;i=i+1)begin
  @(negedge clk);
  re=1;we=(i<512)||($urandom_range(0,3)!=0);
  wa=(i<512)?i[8:0]:$urandom_range(0,511);ra=(i<512 || i%3==0)?wa:$urandom_range(0,511);
  wd={$urandom,$urandom,$urandom,$urandom};mask=(i<512)?128'hffffffffffffffffffffffffffffffff:{$urandom,$urandom,$urandom,$urandom};
  if(we && ra==wa)same=same+1;if(we && mask!=128'hffffffffffffffffffffffffffffffff)masked=masked+1;
  @(posedge clk);#1;
  checks=checks+1;if(a!==b)begin errors=errors+1;if(errors<3)$display("MISMATCH cycle=%0d got=%h expected=%h",i,b,a);end
 end
 $display("FIXED_REPAIR MUT=%0d checks=%0d errors=%0d same_address=%0d masked_writes=%0d",MUT,checks,errors,same,masked);
 if(checks==12000 && same>1000 && masked>1000 && errors==0)$display("PASS");else $display("FAIL");
 $finish;
end
endmodule
