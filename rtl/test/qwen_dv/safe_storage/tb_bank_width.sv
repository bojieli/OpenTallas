`timescale 1ns/1ps
module tb_bank_width;
 reg ck=0;always #5 ck=~ck;
 reg re=0,we=0;reg[4:0] ra=0,wa=0;
 reg[545:0] data=0,mask=0;
 wire[511:0] q512;wire[513:0] q514;wire[545:0] q546;
 qfd_dv_sram_bank64 #(.W(512)) u512(ck,re,we,ra,wa,q512,data[511:0],mask[511:0]);
 qfd_dv_sram_bank64 #(.W(514)) u514(ck,re,we,ra,wa,q514,data[513:0],mask[513:0]);
 qfd_dv_sram_bank64 #(.W(546)) u546(ck,re,we,ra,wa,q546,data,mask);
 reg[545:0] reference[0:31],expected;
 reg[31:0] seed=32'h934c1267;
 integer cycle=0;
 function automatic[31:0] step(input[31:0] x);
  reg[31:0] y;begin y=x^(x<<13);y=y^(y>>17);step=y^(y<<5);end
 endfunction
 always @(negedge ck) begin
  wa=5'(cycle);ra=5'(cycle+7);
  we=(cycle<=32)||(cycle%3!=0);re=(cycle>=40)&&(cycle%11!=0);
  for(integer b=0;b<546;b=b+1) begin
   if(b%32==0) seed=step(seed);
   data[b]=seed[b%32];
  end
  for(integer b=0;b<546;b=b+1) begin
   if(b%32==0) seed=step(seed);
   mask[b]=(cycle<=32)?1'b1:seed[b%32];
  end
 end
 always @(posedge ck) begin
  if(re) expected=reference[ra];
  if(we) for(integer b=0;b<546;b=b+1) if(mask[b]) reference[wa][b]=data[b];
  #1;
  if(cycle>=40&&(q512!==expected[511:0]||q514!==expected[513:0]||q546!==expected))
   $fatal(1,"BANK_WIDTH_OR_MASK cycle%0d",cycle);
  if(u514.g_bank[8].u_m.w_mask_in[63:2]!==62'd0||u546.g_bank[8].u_m.w_mask_in[63:34]!==30'd0)
   $fatal(1,"BANK_PADDING_MASK");
  cycle=cycle+1;
  if(cycle==1200) begin $display("NATIVE_BANK_WIDTH PASS W512/514/546 mask/readhold1200cycles exact1edge read clock37wrap");$finish;end
 end
endmodule
