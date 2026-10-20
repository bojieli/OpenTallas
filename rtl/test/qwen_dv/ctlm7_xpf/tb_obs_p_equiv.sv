`timescale 1ns/1ps
// CTLM7: qkd_program_pw_observer (reference) vs qkd_program_pw_observer_p, all outputs,
// 400k structured-random vectors (per slice mask zero / full / partial; both banks).
// +MUT=1 compares the twin against a reference whose full_word ignores bank 1 (must FAIL).
module tb_obs_p_equiv;
 reg [1:0] ce; reg [11:0] row; reg [1023:0] md,mk;
 wire va,vb,fa,fb; wire [9:0] aa,ab; wire [63:0] da,db;
 integer MUT,n,err,s,k,nfull; reg [1:0] mce;
 qkd_program_pw_observer   r(.macro_ce(MUT==1?mce:ce),.macro_row(row),.macro_data(md),.macro_mask(mk),.consumed_v(va),.consumed_addr(aa),.consumed_data(da),.full_word(fa));
 qkd_program_pw_observer_p d(.macro_ce(ce),.macro_row(row),.macro_data(md),.macro_mask(mk),.consumed_v(vb),.consumed_addr(ab),.consumed_data(db),.full_word(fb));
 initial begin
  if(!$value$plusargs("MUT=%d",MUT))MUT=0; err=0; nfull=0;
  for(n=0;n<400000;n=n+1)begin
   ce=$urandom; row=$urandom; mce={1'b0,ce[0]};
   for(k=0;k<32;k=k+1)md[32*k +:32]=$urandom;
   for(s=0;s<16;s=s+1)begin
    k=$urandom%16;
    mk[64*s +:64]=(k<11)?64'd0:(k<14)?64'hffffffffffffffff:{$urandom,$urandom};
   end
   #1;
   if({va,aa,da,fa}!=={vb,ab,db,fb})begin err=err+1; if(err<5)$display("MISMATCH ce=%b ref a%h f%b dut a%h f%b",ce,aa,fa,ab,fb); end
   if(fb)nfull=nfull+1;
  end
  $display("OBS_P_EQUIV %s MUT=%0d vectors=%0d errors=%0d full_word_true=%0d",(err==0)?"PASS":"FAIL",MUT,n,err,nfull);
  $finish;
 end
endmodule
