#!/usr/bin/env python3
"""Extract actual historical-parent boundary expressions for a lockstep pin miter.

Run at repo root: rtlc_pin_miter.py OUT.sv. The two mutants restore Yosys's
old implicit low-bit truncation on dl_e and bi, respectively. No core internals
are changed by this wiring repair; the oracle retains the old full-word bit IDs.
"""
from pathlib import Path
import re,sys
src=Path('rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp_w3.sv').read_text()
xr=next(x for x in src.splitlines() if re.search(r'\bot_s81sl_xrt3\s+u_xr\b',x))
xf=next(x for x in src.splitlines() if re.search(r'\bot_s81dv_xfin\s+u_xf\b',x))
def expr(line,pin):
 m=re.search(r'\.'+pin+r'\(([^()]*)\)',line)
 assert m,pin
 return m.group(1)
e=[expr(xr,p) for p in ('dl_e','dl_w','dl_vb','ci_b','bi')]+[expr(xf,'s_i')]
sv='''`timescale 1ns/1ps
module tb #(parameter MUT=0);
reg clk=0; always #1 clk=~clk;
reg [1103:0] dl_e,dl_w,ci_b,bi;
reg [275:0] dl_vb;
reg [7:0] x_si;
reg [1074:0] qe,qw;
reg [274:0] qv;
reg [1075:0] qc;
reg [1045:0] qb;
reg [6:0] qs;
reg [1074:0] re,rw;
reg [274:0] rv;
reg [1075:0] rc;
reg [1045:0] rb;
reg [6:0] rs;
integer i,j,errors=0;
always @(posedge clk) begin
'''
sv+=f'qe <= MUT==1 ? dl_e[1074:0] : {e[0]};\nqw <= {e[1]};\nqv <= {e[2]};\nqc <= {e[3]};\nqb <= MUT==2 ? bi[1045:0] : {e[4]};\nqs <= {e[5]};\n'
sv+='''for(integer k=0;k<1075;k=k+1)begin re[k]<=dl_e[k+1];rw[k]<=dl_w[k+1];end
for(integer k=0;k<275;k=k+1)rv[k]<=dl_vb[k+1];
for(integer k=0;k<1076;k=k+1)rc[k]<=ci_b[k];
for(integer k=0;k<1046;k=k+1)begin if(k<7)rb[k]<=bi[k];else rb[k]<=bi[k+30];end
for(integer k=0;k<7;k=k+1)rs[k]<=x_si[k];
end
initial begin
for(i=0;i<2208;i=i+1)begin
 @(negedge clk);
 dl_e=0;dl_w=0;ci_b=0;bi=0;dl_vb=0;x_si=0;
 if(i<1104)begin dl_e[i]=1;dl_w[i]=1;ci_b[i]=1;bi[i]=1;dl_vb[i%276]=1;x_si[i%8]=1;end
 else begin
  for(j=0;j<1104;j=j+32)begin dl_e[j+:32]=$urandom;dl_w[j+:32]=$urandom;ci_b[j+:32]=$urandom;bi[j+:32]=$urandom;end
  for(j=0;j<256;j=j+32)dl_vb[j+:32]=$urandom;
  dl_vb[275:256]=$urandom;x_si=$urandom;
 end
 @(posedge clk);#0.01;
 if({qe,qw,qv,qc,qb,qs}!=={re,rw,rv,rc,rb,rs})errors=errors+1;
end
$display("RTLC_PIN_MITER MUT=%0d edges=%0d errors=%0d",MUT,i,errors);
if((MUT==0 && errors!=0)||(MUT!=0 && errors==0))$fatal(1,"miter/negative-control failed");
$finish;
end
endmodule
'''
Path(sys.argv[1]).write_text(sv)
print('extracted',e)
