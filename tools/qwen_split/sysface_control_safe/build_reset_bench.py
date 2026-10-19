#!/usr/bin/env python3
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--graph',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--out',required=True);ap.add_argument('--img',default='cold/sim_two_epochs/img');a=ap.parse_args()
m=json.loads(Path(a.graph).read_text())['modules']['qfd_sys_face'];rec=json.loads(Path(a.receipt).read_text())
physical=rec.get('physical_wrapper',False)
s=['`timescale 1ns/1ps','module tb_sysface_safe_reset;','reg ck=0;always #0.5 ck=~ck;reg rst_n=1;integer i;']
args=[]
for n,p in m['ports'].items():
 if p['direction']=='input':args.append('.'+n+'('+n+')' if n in ['ck','rst_n'] else '.'+n+'('+str(len(p['bits']))+"'d0)")
s+=['qfd_sys_face #(.ROM_VIAMAP("'+a.img+'/sys_face_cfg.viamap.hex"),.OVL_ROM_DIR("'+a.img+'")) dut('+','.join(args)+');',
 'initial begin #0.113;for(i=0;i<128;i=i+1) begin rst_n=0;']
# physical wrapper: reset reaches the core after the two paid face landing stages (codex/sysface-physical-proof-1019)
s+=['repeat(3) @(negedge ck); #0.001;'] if physical else ['#0.001;']
for f in rec['forest']:
 s+=['if(dut.candidate.'+('core.' if physical else '')+'n'+str(f['q'])+' !== 0) $fatal(1,"SYSFACE_SAFE_ASSERT_FAIL '+f['cell']+'");']
s+=['#(0.013+((i*17)%31)*0.001);rst_n=1;repeat(9) @(negedge ck);#((i%7)*0.017);end',
 'repeat(3000) @(negedge ck);$display("SYSFACE_SAFE_RESET_PASS phases128 release3 face_reset'+('2' if physical else '0')+'");$finish;end','endmodule','']
Path(a.out).write_text('\n'.join(s))
