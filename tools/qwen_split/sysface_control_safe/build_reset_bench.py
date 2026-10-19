#!/usr/bin/env python3
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--graph',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
m=json.loads(Path(a.graph).read_text())['modules']['qfd_sys_face'];rec=json.loads(Path(a.receipt).read_text())
s=['`timescale 1ns/1ps','module tb_sysface_safe_reset;','reg ck=0;always #0.5 ck=~ck;reg rst_n=1;integer i;']
args=[]
for n,p in m['ports'].items():
 if p['direction']=='input':args.append('.'+n+'('+n+')' if n in ['ck','rst_n'] else '.'+n+'('+str(len(p['bits']))+"'d0)")
s+=['qfd_sys_face #(.ROM_VIAMAP("cold/sim_two_epochs/img/sys_face_cfg.viamap.hex"),.OVL_ROM_DIR("cold/sim_two_epochs/img")) dut('+','.join(args)+');',
 'initial begin #0.113;for(i=0;i<128;i=i+1) begin rst_n=0;#0.001;']
for f in rec['forest']:
 s+=['if(dut.candidate.n'+str(f['q'])+' !== 0) $fatal(1,"SYSFACE_SAFE_ASSERT_FAIL '+f['cell']+'");']
s+=['#(0.013+((i*17)%31)*0.001);rst_n=1;repeat(9) @(negedge ck);#((i%7)*0.017);end',
 'repeat(3000) @(negedge ck);$display("SYSFACE_SAFE_RESET_PASS phases128 release3 async_assert128");$finish;end','endmodule','']
Path(a.out).write_text('\n'.join(s))
