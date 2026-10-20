`timescale 1ns/1ps
module tb_svc7_chunk_reduce;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,iv=0;reg[255:0]p=0;reg[7:0]pf=0;
 wire ov;wire[31:0]y;wire[2:0]fault_parts;
 ot_s81svc7_chunk_reduce dut(.*);
 wire[255:0]acc;wire[7:0]av,af;
 assign acc[31:0]=p[31:0];assign av[0]=iv;assign af[0]=pf[0];
 genvar k;
 generate for(k=1;k<8;k=k+1)begin:g_ref
  wire[1:0]err;
  ot_s81svc7_add_graph_input u_add(.clk(clk),.rst_n(rst_n),.valid_in(av[k-1]),
    .a(acc[(k-1)*32+:32]),.b(p[k*32+:32]),.y(acc[k*32+:32]),.err(err),.valid_out(av[k]));
  reg[4:0]fh;
  always @(posedge clk)fh<={fh[3:0],af[k-1]|pf[k]};
  assign af[k]=fh[4]|(av[k]&&(|err));
 end endgenerate
 integer cyc=0,checks=0,errors=0,valids=0,j;
 always @(negedge clk)begin
  if(cyc>=4)begin
   checks=checks+1;
   if(ov!==av[7] || (ov&&({y,|fault_parts}!={acc[255:224],af[7]})))begin
    errors=errors+1;$display("SVC7_CHUNK_MISMATCH cycle=%0d valid=%b/%b data=%h/%h fault=%b/%b",cyc,ov,av[7],y,acc[255:224],|fault_parts,af[7]);
   end
   if(ov)valids=valids+1;
  end
  rst_n=(cyc>=12 && !(cyc>=711&&cyc<717)&&!(cyc>=2033&&cyc<2039));
  iv=rst_n&&($urandom_range(0,7)!=0);pf=0;
  for(j=0;j<8;j=j+1)begin p[j*32+:32]=$urandom;p[j*32+23+:8]=8'h7e;end
  if(cyc%29==0)pf[$urandom_range(0,7)]=1;
  if(cyc%97==0)p[32*$urandom_range(0,7)+:32]=32'h7fc00001;
  if(cyc%101==0)p[32*$urandom_range(0,7)+:32]=32'h7f800000;
  cyc=cyc+1;
  if(cyc==7000)begin
   $display("SVC7_CHUNK checks=%0d valid=%0d errors=%0d verdict=%s",checks,valids,errors,errors==0?"PASS":"FAIL");
   if(errors||valids<1000)$fatal(1,"SVC7_CHUNK_FAIL");$finish;
  end
 end
endmodule
