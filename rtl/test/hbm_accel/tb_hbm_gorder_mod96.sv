`timescale 1ns/1ps
// sys-takeover 2026-10-09: exhaustive check of the FAST id%96 digit-sum form used by ot_hbm_index_global_order FAST=1.
module tb_hbm_gorder_mod96;
 function automatic [6:0] mod96(input [16:0] id);
  reg [11:0] q; reg [4:0] sum; reg [1:0] r3; integer d;
  begin q=id[16:5]; sum=0; for(d=0;d<6;d=d+1) sum=sum+q[2*d+:2]; r3=sum%3; mod96={r3,id[4:0]}; end
 endfunction
 integer v, bad=0;
 initial begin
  for(v=0;v<131072;v=v+1) if(mod96(17'(v))!=7'(v%96)) bad=bad+1;
  if(bad) $fatal(1,"MOD96 mismatches %0d",bad);
  $display("PASS_MOD96 exhaustive 131072"); $finish;
 end
endmodule
