`timescale 1ps/1ps
module tb;reg clk=0;reg[2247:0]x=0;always begin #416;clk=1;#417;clk=0;end
wire[280:0]o[0:7];wire of;old_shell i_o(.clk(clk),.x(x),.writer_kq0(o[0]),.writer_kq1(o[1]),.writer_kq2(o[2]),.writer_kq3(o[3]),.writer_kq4(o[4]),.writer_kq5(o[5]),.writer_kq6(o[6]),.writer_kq7(o[7]),.writer_fault(of));
wire[280:0]g[0:7];wire gf;new_shell i_g(.clk(clk),.x(x),.writer_kq0(g[0]),.writer_kq1(g[1]),.writer_kq2(g[2]),.writer_kq3(g[3]),.writer_kq4(g[4]),.writer_kq5(g[5]),.writer_kq6(g[6]),.writer_kq7(g[7]),.writer_fault(gf));
wire[280:0]h[0:7];wire hf;hand_shell i_h(.clk(clk),.x(x),.writer_kq0(h[0]),.writer_kq1(h[1]),.writer_kq2(h[2]),.writer_kq3(h[3]),.writer_kq4(h[4]),.writer_kq5(h[5]),.writer_kq6(h[6]),.writer_kq7(h[7]),.writer_fault(hf));
wire[280:0]s[0:7];wire sf;short_shell i_s(.clk(clk),.x(x),.writer_kq0(s[0]),.writer_kq1(s[1]),.writer_kq2(s[2]),.writer_kq3(s[3]),.writer_kq4(s[4]),.writer_kq5(s[5]),.writer_kq6(s[6]),.writer_kq7(s[7]),.writer_fault(sf));
wire[280:0]l[0:7];wire lf;long_shell i_l(.clk(clk),.x(x),.writer_kq0(l[0]),.writer_kq1(l[1]),.writer_kq2(l[2]),.writer_kq3(l[3]),.writer_kq4(l[4]),.writer_kq5(l[5]),.writer_kq6(l[6]),.writer_kq7(l[7]),.writer_fault(lf));
reg[280:0]prev[0:7];integer i,j,k,err=0,phase_err=0,fault_err=0,short_hit=0,long_hit=0,edge_hit=0,checks=0;initial begin
for(i=0;i<2048;i=i+1)begin @(negedge clk);#2;
if(i>8)begin for(j=0;j<8;j=j+1)begin checks=checks+1;if(g[j]!==h[j])err=err+1;if(g[j]!==prev[j])phase_err=phase_err+1;if(s[j]!==h[j])short_hit=short_hit+1;if(l[j]!==h[j])long_hit=long_hit+1;if(o[j]!==h[j])edge_hit=edge_hit+1;end if(gf!==of)fault_err=fault_err+1;end
for(j=0;j<8;j=j+1)prev[j]=o[j];#2;for(k=0;k<71;k=k+1)x=(x<<32)|$urandom;
@(posedge clk);#2;if(i>8)begin for(j=0;j<8;j=j+1)if(g[j]!==h[j])err=err+1;if(gf!==hf)err=err+1;end end
$display("Q3_FACE checks=%0d generated_vs_hand=%0d old_phase_plus1=%0d other_fault=%0d mutant_short=%0d mutant_long=%0d mutant_oldedge=%0d",checks,err,phase_err,fault_err,short_hit,long_hit,edge_hit);
if(err||phase_err||fault_err||!short_hit||!long_hit||!edge_hit)$fatal(1,"face proof failed");$finish;end endmodule
