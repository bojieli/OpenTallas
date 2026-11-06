`timescale 1ns/1ps
`default_nettype none
// lock-step: ot_hidx_s3_q (old, from git) vs new, same random pins, all outputs cycle exact after reset
module tb #(parameter integer DMUT=0)();
 reg clk=0,rst_n=0; always #1 clk=~clk;
 reg [13:0] cw=0,ties=0; reg [15:0] thr=0; reg [591:0] in_line=0;
 wire [24:0] ra,rb; wire fa,fb,va,vb; wire [591:0] la,lb;
 old_hidx_s3_q ua(.clk(clk),.rst_n(rst_n),.cw(cw),.thr(thr),.ties(ties),.in_line(in_line),.ret(ra),.qfault_o(fa),.selected_v_o(va),.selected_line_o(la));
 ot_hidx_s3_q #(.DMUT(DMUT)) ub(.clk(clk),.rst_n(rst_n),.cw(cw),.thr(thr),.ties(ties),.in_line(in_line),.ret(rb),.qfault_o(fb),.selected_v_o(vb),.selected_line_o(lb));
 integer cyc=0,err=0,sel=0,tiehi=0,sat=0,ehit=0,opseq=0; reg [15:0] keys[0:3];
 function automatic [15:0] orderkey(input [15:0] x); orderkey=x[15]?~x:(x^16'h8000); endfunction
 integer eg=0;
 always @(negedge clk) if(rst_n && cyc>40) begin
  if({ra,fa,va,la}!=={rb,fb,vb,lb}) begin err=err+1; if(err<6) $display("DIFF cyc %0d ret %h %h v %b %b f %b %b",cyc,ra,rb,va,vb,fa,fb); end
  if(va) sel=sel+1;
  if(ub.gtie[0].tavail>=32 && ub.s2v_t[0]) tiehi=tiehi+1;
  if(ub.s2v_t[0] && ub.gtie[0].ecnt!=0 && ub.gtie[0].ecnt>ub.gtie[0].tavail) sat=sat+1;
  if(ub.s2v_t[0] && ub.gtie[0].ecnt!=0) ehit=ehit+1;
 end
 initial begin
  for(int i=0;i<4;i++) keys[i]=$urandom;
  repeat(12) @(negedge clk); rst_n=1;
  repeat(`CYC) begin @(negedge clk); cyc=cyc+1;
   // run of random ops; scans of a lightly written memory, thr on one of 4 keys so ties and gt both occur
   case($urandom%16) 0,1: cw[3:0]=2; 2: cw[3:0]=1; 3,4,5,6,7,8,9,10: cw[3:0]=4; 11,12: cw[3:0]=6; 13: cw[3:0]=7; 14: cw[3:0]=3; default: cw[3:0]=0; endcase
   cw[5:4]=$urandom%3; cw[13:6]=$urandom%32;
   thr=orderkey(keys[$urandom%4]);
   if($urandom%32==0) case($urandom%4) 0: ties=$urandom&14'h3f; 1: ties=$urandom; 2: ties=33+$urandom%12; default: ties=$urandom%18; endcase
   for(int l=0;l<16;l++) begin in_line[l*37+:37]=37'({$urandom,$urandom}); in_line[l*37+1+:16]=keys[$urandom%4]; in_line[l*37]=($urandom%8!=0); end
  end
  $display("S3Q cyc %0d err %0d selected %0d tavail_hi %0d ecnt_nz %0d saturate %0d qfault %b",cyc,err,sel,tiehi,ehit,sat,fa);
  if(err!=0) $fatal(1,"FAIL"); $display("PASS"); $finish;
 end
endmodule
`default_nettype wire
