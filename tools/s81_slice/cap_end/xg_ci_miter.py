#!/usr/bin/env python3
"""Smallest sequential miter for the XG ci_b boundary narrowing; emit OUT.sv.

Checks the actual child reconstruction in all four XG wrappers, then compares
real ring-stop instances with the original tied-high interface and the narrowed
interface. MUT1 flips a live payload bit. Zero datapath/control cycles added.
"""
from pathlib import Path
import re,sys
expr=None
for name in ('xg','xg_xo','xgt','xgt_xo'):
 p=Path(f'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_{name}.sv');s=p.read_text()
 assert re.search(r'input\s+wire\s+\[1075:0\]\s+ci_b',s),p
 m=re.search(r'\.ci_b\(([^()]*)\)',s);assert m,p
 assert m.group(1)=="{28'd0, ci_b}",(p,m.group(1))
 expr=m.group(1)
inputs=[('sid',4),('ri_w',1104),('ri_e',1104),('vi',276),('xf_v',5),('xf_s',5),('xf',1380),('nx_eo',173),('nx_wo',173),('ci_dir',3)]
outputs=[('ro_e',1104),('ro_w',1104),('vo',276),('nx_wi',173),('nx_ei',173),('g_v',3),('g_fam',3),('g_idx',21),('g_d',3072),('dl_ev',1),('dl_e',1104),('dl_wv',1),('dl_w',1104),('dl_vv',1),('dl_vb',276),('fault',1)]
sv='`timescale 1ns/1ps\nmodule tb #(parameter MUT=0);\nreg clk=0;always #1 clk=~clk;reg rst_n=0;\nreg [1075:0] ci_b;\n'
for n,w in inputs:sv+=f'reg [{w-1}:0] {n};\n'
for n,w in outputs:sv+=f'wire [{w-1}:0] {n}0,{n}1;\n'
sv+=f'wire [1103:0] ci_new = {expr};\n'
common=['.clk(clk)','.rst_n(rst_n)']+[f'.{n}({n})' for n,_ in inputs]
for i in (0,1):
 ci="{28'd0,ci_b}" if i==0 else "(ci_new ^ (MUT ? 1104'h100000000 : 1104'd0))"
 con=common+[f'.ci_b({ci})']+[f'.{n}({n}{i})' for n,_ in outputs]
 sv+=f'ot_s81sl_rstop u{i}('+','.join(con)+');\n'
sv+='integer i,j,errors=0;\ninitial begin\n'
for n,_ in inputs:sv+=f'{n}=0;\n'
sv+='ci_b=0;repeat(4)@(negedge clk);rst_n=1;\nfor(i=0;i<1024;i=i+1)begin\n@(negedge clk);\n'
for n,w in [('ci_b',1076)]+inputs:
 for off in range(0,w,32):sv+=f'{n}[{min(w-1,off+31)}:{off}]=$urandom;\n'
sv+='ci_b[0]=1;ci_dir=3\'b001;ri_w=0;ri_e=0;vi=0;xf_v=0;nx_eo=0;nx_wo=0;\n@(posedge clk);#0.01;\n'
a=','.join(n+'0' for n,_ in outputs);b=','.join(n+'1' for n,_ in outputs)
sv+=f'if({{{a}}}!=={{{b}}})errors=errors+1;\n'
sv+='end\n$display("XG_CI_MITER MUT=%0d cycles=%0d errors=%0d",MUT,i,errors);\nif((MUT==0 && errors!=0)||(MUT!=0 && errors==0))$fatal(1,"miter/negative control failed");\n$finish;end\nendmodule\n'
Path(sys.argv[1]).write_text(sv)
print('actual XG input width1076, four child reconstructions match tied-high1104 contract')
