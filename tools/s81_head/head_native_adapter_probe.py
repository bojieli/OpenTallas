#!/usr/bin/env python3
"""Smallest native-interface coupon: real CV reset/output stages, shared arithmetic cut.
Arithmetic source is unchanged. This coupon tests clock alias, cycle preservation and all FT arcs.
"""
from pathlib import Path
import argparse,subprocess,json,hashlib

def main():
 a=argparse.ArgumentParser();a.add_argument('root',type=Path);a.add_argument('out',type=Path);a.add_argument('--mutant',action='store_true');o=a.parse_args();o.out.mkdir(parents=True,exist_ok=False)
 r=o.root/'rtl/dsrom_sys/s81_head';g=(r/'ot_s81hd_elem_cv.sv').read_text().replace('module ot_s81hd_elemA_cv','module gold_A').replace('module ot_s81hd_elemB_cv','module gold_B');n=(r/'ot_s81hd_elem_cv_native.sv').read_text()
 if o.mutant:n=n.replace('wire clk = ft_mstrap_i;', 'wire clk = ft_ck0_i;')
 (o.out/'gold.sv').write_text(g);(o.out/'native.sv').write_text(n);(o.out/'oreg.sv').write_text((r/'ot_s81hd_oreg.sv').read_text())
 stub='''module ot_s81hd_elem #(parameter LV=8,PAD=0,JOIN=1,ROWS=32,CUT=511,SPLIT9=1,INSTANCE="",IOREG=1,SAFE=1,FADD_L4=0)(input clk,rst_n,go,input[16:0]row0,input[255:0]x,input b_v,input[31:0]b_d,output o_v,l_v,done,fault,output[31:0]o_d,l_d,best_bits,best_key,head_d,output[16:0]best_row,head_row,output head_v);
assign o_v=go;assign l_v=b_v;assign done=go;assign o_d=x[31:0]^b_d^{15'd0,row0};assign l_d=x[63:32]+b_d;assign best_row=row0;assign best_bits=x[95:64];assign best_key=x[127:96];assign fault=x[255]^go^rst_n;assign head_d=x[159:128];assign head_row=row0;assign head_v=go;endmodule
'''
 (o.out/'cut.sv').write_text(stub)
 common='.rst_n(rst_n),.go(go),.x(x)';ac=common+',.row0(row0),.b_v(b_v),.b_d(b_d)';an=['o_v','o_d','l_v','l_d','done','best_row','best_bits','best_key','fault'];bn=['o_v','o_d','fault']
 code='''`timescale 1ps/1ps
module tb; reg clk=0; initial forever begin #416 clk=1;#417 clk=0;end
reg rst_n=0,go=0,b_v=0;reg[16:0]row0=0;reg[255:0]x=0;reg[31:0]b_d=0;reg[3:0]fi=0;wire[3:0]fa,fb;
'''
 for k,names in [('ag',an),('an',an),('bg',bn),('bn',bn)]:
  for p in names:
   w='[31:0]' if p in ('o_d','l_d','best_bits','best_key') else '[16:0]' if p=='best_row' else ''
   code+='wire '+w+' '+k+'_'+p+';\n'
 for k,mod,names,con,native in [('ag','gold_A',an,ac,False),('an','ot_s81hd_elemA_cv',an,ac,True),('bg','gold_B',bn,common,False),('bn','ot_s81hd_elemB_cv',bn,common,True)]:
  cc=('.ft_mstrap_i(clk)' if native else '.clk(clk)')+','+con
  if native:
   for i,p in enumerate(('ck0','ck1','mesh','rst')):cc+=',.ft_'+p+'_i(fi['+str(i)+']),.ft_'+p+'_o('+('fa' if k=='an' else 'fb')+'['+str(i)+'])'
  cc+=','+','.join('.'+p+'('+k+'_'+p+')' for p in names);code+=mod+' u_'+k+'('+cc+');\n'
 code+='initial begin for(integer c=0;c<256;c++)begin @(negedge clk);rst_n=(c>3);go=(c%3==0);b_v=(c%5==0);row0=c*19;x={8{32\'(c*2909+51)}};b_d=c*77;fi=4\'(c*7+2);@(posedge clk);#1;if(c>6)begin\n'
 code+='if({'+','.join('ag_'+p for p in an)+'}!=={'+','.join('an_'+p for p in an)+'})$fatal(1,"A cycle mismatch %0d",c);\n'
 code+='if({'+','.join('bg_'+p for p in bn)+'}!=={'+','.join('bn_'+p for p in bn)+'})$fatal(1,"B cycle mismatch %0d",c);\n'
 code+='if(fa!==fi||fb!==fi)$fatal(1,"FT passthrough mismatch");end end $display("NATIVE_ADAPTER_LOCKSTEP_PASS 249 cycles 8 FT arcs 0 added cycles");$finish;end endmodule\n'
 (o.out/'tb.sv').write_text(code)
 cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',str(o.out/'obj'),'-j','4']+[str(o.out/f) for f in ('tb.sv','gold.sv','native.sv','oreg.sv','cut.sv')]
 with (o.out/'build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (o.out/'run.log').open('w')as f:z=subprocess.run([str(o.out/'obj/Vtb')],stdout=f,stderr=subprocess.STDOUT)
 print((o.out/'run.log').read_text());return z.returncode
if __name__=='__main__':raise SystemExit(main())
