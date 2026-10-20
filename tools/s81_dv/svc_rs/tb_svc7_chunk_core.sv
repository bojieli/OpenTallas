`timescale 1ns/1ps
module tb_svc7_chunk_core;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,iv=0;reg[127:0]a=0;reg[143:0]b=0;
 wire ov;wire[31:0]y;wire[2:0]fault_parts;
 ot_s81svc7_chunk_core dut(.*);
 wire[255:0]p,acc;wire[7:0]pf,av,af;
 reg[6:0]vh;
 always @(posedge clk)if(!rst_n)vh<=0;else vh<={vh[5:0],iv};
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:g_refmul
  wire mf;reg[6:0]df;
  ot_s81svc7_bmul_graph_input u_mul(.clk(clk),.rst_n(rst_n),.a(a[k*16+:16]),.b(b[k*18+:16]),.pad(b[k*18+17]),.y(p[k*32+:32]),.flt(mf));
  always @(posedge clk)df<={df[5:0],b[k*18+16]&~b[k*18+17]};
  assign pf[k]=mf|df[6];
 end endgenerate
 assign acc[31:0]=p[31:0];assign av[0]=vh[6];assign af[0]=pf[0];
 generate for(k=1;k<8;k=k+1)begin:g_refadd
  wire[1:0]err;reg[4:0]fh;
  ot_s81svc7_add_graph_input u_add(.clk(clk),.rst_n(rst_n),.valid_in(av[k-1]),.a(acc[(k-1)*32+:32]),.b(p[k*32+:32]),.y(acc[k*32+:32]),.err(err),.valid_out(av[k]));
  always @(posedge clk)fh<={fh[3:0],af[k-1]|pf[k]};
  assign af[k]=fh[4]|(av[k]&&(|err));
 end endgenerate
 integer cyc=0,age=0,checks=0,errors=0,valids=0,j;
 always @(negedge clk)begin
  if(cyc>=4)begin
   checks=checks+1;
   if(ov!==av[7] || (ov&&({y,|fault_parts}!={acc[255:224],af[7]})))begin
    errors=errors+1;$display("SVC7_CORE_MISMATCH cyc=%0d v=%b/%b y=%h/%h f=%b/%b",cyc,ov,av[7],y,acc[255:224],|fault_parts,af[7]);
   end
   if(ov)valids=valids+1;
  end
  rst_n=(cyc>=12&&!(cyc>=711&&cyc<717)&&!(cyc>=2033&&cyc<2039));
  if(!rst_n)age=0;else age=age+1;
  // Legal enclosing-group contract: configuration/reset landing completes
  // before first iv. This constrains input offers, never output comparison.
  iv=rst_n&&age>4&&($urandom_range(0,7)!=0);
  for(j=0;j<8;j=j+1)begin
   a[j*16+:16]=$urandom;a[j*16+7+:8]=8'h7e;
   b[j*18+:18]=$urandom;b[j*18+7+:8]=8'h7e;b[j*18+16+:2]=0;
  end
  if(cyc%29==0)b[18*$urandom_range(0,7)+16]=1;
  if(cyc%97==0)a[16*$urandom_range(0,7)+:16]=16'h7fc1;
  if(cyc%101==0)b[18*$urandom_range(0,7)+17]=1;
  cyc=cyc+1;
  if(cyc==7000)begin
   $display("SVC7_CORE checks=%0d valid=%0d errors=%0d verdict=%s",checks,valids,errors,errors==0?"PASS":"FAIL");
   if(errors||valids<1000)$fatal(1,"SVC7_CORE_FAIL");$finish;
  end
 end
endmodule
