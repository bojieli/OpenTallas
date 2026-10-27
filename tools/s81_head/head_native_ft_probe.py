#!/usr/bin/env python3
"""Exercise every one of the 40 exposed tile FT pins independently (arithmetic cut unchanged)."""
from pathlib import Path
import argparse,subprocess
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('root',type=Path);a.add_argument('coupon',type=Path);a.add_argument('out',type=Path);a.add_argument('--mutant',action='store_true');o=a.parse_args();o.out.mkdir(parents=True,exist_ok=False)
 src=o.root/'rtl/dsrom_sys/s81_head/ot_s81hd_bundle_native.sv';t=src.read_text()
 if o.mutant:
  old='.ft_mesh_i(hci``Q``_mesh_i)';assert old in t;t=t.replace(old,'.ft_mesh_i(hci4_mesh_i)')
 (o.out/'bundle.sv').write_text(t)
 (o.out/'cut.sv').write_text((o.coupon/'cut.sv').read_text().replace('SAFE=1)', 'SAFE=1,FADD_L4=0)'))
 con=['.clk(clk)', '.rst_n(rst_n)', '.go(1\'b0)', '.row0(17\'d0)', '.xa(256\'d0)', '.xb(256\'d0)']
 for i in range(5):
  for j,n in enumerate(('ck0','ck1','mesh','rst')):
   for sf,v in [('i','fi'),('o','fo')]:con.append('.hci'+str(i)+'_'+n+'_'+sf+'('+v+'['+str(4*i+j)+'])')
 tb='''`timescale 1ps/1ps
module tb_ft;reg clk=0;initial forever begin#416 clk=1;#417 clk=0;end
reg rst_n=0;reg[19:0]fi=0;wire[19:0]fo;
ot_s81hd_bundle_native #(.CV(1),.IOREG(1)) u('''+', '.join(con)+''');
initial begin for(integer c=0;c<64;c++)begin @(negedge clk);rst_n=(c>3);fi=20'(1<<(c%20)) ^ ((c%2)?20'hfffff:20'd0);#1;if(fo!==fi)$fatal(1,"FT native tile permutation/delay at %0d",c);end $display("NATIVE_ALL40_FT_PASS 64 phases 20 independent arcs 0 extra cycles");$finish;end endmodule
'''
 (o.out/'tb.sv').write_text(tb)
 cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_ft','--Mdir',str(o.out/'obj'),'-j','4',str(o.out/'tb.sv'),str(o.out/'bundle.sv'),str(o.coupon/'native.sv'),str(o.coupon/'oreg.sv'),str(o.out/'cut.sv'),str(o.root/'rtl/hdc/ot_hdc_delay.sv')]
 with(o.out/'build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 with(o.out/'run.log').open('w')as f:r=subprocess.run([str(o.out/'obj/Vtb_ft')],stdout=f,stderr=subprocess.STDOUT)
 print((o.out/'run.log').read_text());raise SystemExit(r.returncode)
