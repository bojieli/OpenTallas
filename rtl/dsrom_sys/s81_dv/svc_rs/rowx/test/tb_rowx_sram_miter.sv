`timescale 1ns/1ps
module tb_rowx_sram_miter;
reg clk=0, rst_n=0;
always #5 clk=~clk;
reg iv=0, pop=0; reg [1023:0] id=0;
wire [1023:0] lg,ls,lm;wire lgf,lgo,lsf,lso,lmf,lmo;
dsdv_rowx_lc #(.W(1024),.D(16)) gold_lc(clk,rst_n,iv,id,pop,lg,lgf,lgo);
dsdv_rowx_lc_sram #(.W(1024),.D(16)) good_lc(clk,rst_n,iv,id,pop,ls,lsf,lso);
dsdv_rowx_lc_sram #(.W(1024),.D(16),.MUT_BYPASS(1)) bad_lc(clk,rst_n,iv,id,pop,lm,lmf,lmo);
reg go=0,xv=0;reg[512:0] xd=0;
wire gv,sv,mv,gf,sf,mf;wire[511:0] gd,sd,md;
dsdv_rowx_rp gold_rp(clk,rst_n,go,16'd8,12'd640,xv,xd,gv,gd,gf);
dsdv_rowx_rp_sram good_rp(clk,rst_n,go,16'd8,12'd640,xv,xd,sv,sd,sf);
dsdv_rowx_rp_sram #(.MUT_BYPASS(1)) bad_rp(clk,rst_n,go,16'd8,12'd640,xv,xd,mv,md,mf);
integer c,k,bad=0,ml=0,mr=0,rp_words=0;
reg[31:0] rng=32'h79a31e57;
initial begin
repeat(6) @(negedge clk);rst_n=1;
for(c=0;c<1900;c=c+1) begin
  go=(c==0);xv=(c>=8&&c<648);
  rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
  // Directed empty push/last-pop+push, then saturation and arbitrary interleaving.
  if(c<10) begin iv=(c==0||c==2||c==3||c==6);pop=(c==3||c==4||c==7||c==8);end
  else if(c<50) begin iv=1;pop=(c>=35);end
  else begin iv=rng[0];pop=rng[3];end
  for(k=0;k<32;k=k+1) id[32*k+:32]=rng^(32'hb36241d9*k)^c;
  for(k=0;k<16;k=k+1) xd[32*k+:32]=32'h83619ac7^(32'h9e3779b9*c)^(k*32'h47c391ab);
  xd[512]=(c==8);
  @(posedge clk);#1;
  if(lg!==ls || {lgf,lgo}!=={lsf,lso}) begin bad=bad+1;if(bad<5)$display("LC_MISMATCH c=%0d",c);end
  if({gv,gf}!=={sv,sf} || gd!==sd) begin bad=bad+1;if(bad<5)$display("RP_MISMATCH c=%0d v=%0d/%0d",c,gv,sv);end
  if(lg!==lm)ml=ml+1;
  if(gv&&gd!==md)mr=mr+1;
  if(gv)rp_words=rp_words+1;
  @(negedge clk);
end
$display("ROWX_SRAM_MITER bad=%0d rp_words=%0d lc_mutant=%0d rp_mutant=%0d rp_fault=%0d",bad,rp_words,ml,mr,gf);
if(bad || rp_words!=640 || ml==0 || mr==0 || gf)$fatal(1,"ROWX SRAM miter failed");
$finish;
end
endmodule
