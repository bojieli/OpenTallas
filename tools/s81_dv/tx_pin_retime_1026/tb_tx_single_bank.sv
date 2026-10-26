`timescale 1ns/1ps
module tb_tx_single_bank;
 reg ck=0;always #5 ck=~ck;
 reg re=0,we=0;reg[12:0]ra=0,wa=0;reg[255:0]wd=0,wm=0;
 wire[255:0]a[0:1],b[0:1],m[0:1];
 genvar g;
 generate for(g=0;g<2;g=g+1)begin:c
  localparam integer D=g==0?1024:8192,AW=g==0?10:13;
  dsdv_idx_txm__reference #(.D(D),.SRAM_MACRO(1))u0(.ck(ck),.re(re),.ra(ra[AW-1:0]),.rd(a[g]),.we(we),.wa(wa[AW-1:0]),.wd(wd),.wm(wm));
  dsdv_idx_txm #(.D(D),.SRAM_MACRO(1))u1(.ck(ck),.re(re),.ra(ra[AW-1:0]),.rd(b[g]),.we(we),.wa(wa[AW-1:0]),.wd(wd),.wm(wm));
  dsdv_idx_txm #(.D(D),.SRAM_MACRO(1))um(.ck(ck),.re(re),.ra(ra[AW-1:0]^(AW'(1)<<(AW-1))),.rd(m[g]),.we(we),.wa(wa[AW-1:0]),.wd(wd),.wm(wm));
 end endgenerate
 integer cyc=0,mut0=0,mut1=0;
 always @(posedge ck)begin
  #1;cyc=cyc+1;
  for(integer j=0;j<2;j=j+1)if(a[j]!==b[j])begin $display("TX_BANK_MISMATCH case=%0d cycle=%0d",j,cyc);$fatal(1);end
  if(a[0]!==m[0])mut0=mut0+1;if(a[1]!==m[1])mut1=mut1+1;
 end
 initial begin
  for(integer n=0;n<30000;n=n+1)begin
   @(negedge ck);we=n%5!=0;re=n%7!=0;wa=13'(n);ra=13'(n-4);
   for(integer j=0;j<256;j=j+32)begin wd[j+:32]=$urandom;wm[j+:32]=(n%4==0)?32'hffffffff:$urandom;end
  end
  @(negedge ck);
  $display("TX_BANK_PASS cycles=%0d bits=%0d mutant0=%0d mutant1=%0d",cyc,cyc*512,mut0,mut1);
  if(mut0<100||mut1<100)$fatal(1,"MUTANT_NOT_CAUGHT");
  $finish;
 end
endmodule
