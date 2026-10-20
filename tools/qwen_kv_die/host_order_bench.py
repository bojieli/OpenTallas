#!/usr/bin/env python3
"""Fleet behavioral lockstep of immutable S2 mapped source and retained copies.

Uses Liberty combinational truth tables and the canonical sequential coupon.
The output-bit source mutants are separate generated circuits, never changes to
the golden model or comparison. Source S2's existing FIFO/credit proofs remain
the production protocol tests; this bench exercises the primitive-copy change.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ap=argparse.ArgumentParser()
ap.add_argument('--mutant',type=int,default=0,choices=[0,1,2])
args=ap.parse_args()
sp=importlib.util.spec_from_file_location('tl','textbook_lint.py')
m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
mods=m.parse_verilog(Path('original.v').read_text())
_,top=m.flatten(mods,None);ports=mods[top]
out=Path('bench_m'+str(args.mutant));out.mkdir(exist_ok=True)
candidate=Path('qkd_hr_core_order_n32.sv').read_text()
if args.mutant:
    import re
    port='hb[0]' if args.mutant==1 else 'chain_f[32]'
    candidate,n=re.subn(r'(assign '+re.escape(port)+r' = )([^;]+);',r'\1~(\2);',candidate)
    assert n==1,(port,n)
(out/'candidate.sv').write_text(candidate)
lines=['`timescale 1ns/1ps','module tb;','reg ck_core=0; always #5 ck_core=~ck_core;','integer cycle=0; integer compares=0;']
connections=[[],[]]
outputs=[]
for port in ports.ports:
    width='' if port not in ports.widths else '[%d:%d] '%ports.widths[port]
    if ports.dirs[port]=='input':
        if port!='ck_core':lines.append('reg '+width+port+" = '0;")
        for con in connections:con.append('.'+port+'('+port+')')
    else:
        outputs.append(port)
        for i,con in enumerate(connections):
            name=port+str(i);lines.append('wire '+width+name+';');con.append('.'+port+'('+name+')')
lines += [top+' gold('+','.join(connections[0])+');', 'qkd_hr_core_order_n32 dut('+','.join(connections[1])+');']
lines += ['always @(negedge ck_core) begin','cycle=cycle+1;',
          'host_rst_n = cycle>16 && (cycle%400)>8;']
for port in ports.ports:
    if ports.dirs[port]!='input' or port in ('ck_core','host_rst_n'):continue
    w=1 if port not in ports.widths else abs(ports.widths[port][0]-ports.widths[port][1])+1
    lines.append(port+' = {'+','.join('$urandom' for _ in range((w+31)//32))+'};')
lines += ['end','always @(posedge ck_core) begin','#1;', 'if(cycle>16) begin','compares=compares+1;']
for port in outputs:lines.append('if('+port+'0 !== '+port+'1) $fatal(1,"HOST_ORDER_COPY FAIL m'+str(args.mutant)+' '+port+' cycle=%0d",cycle);')
lines += ['end','if(cycle==12000) begin $display("HOST_ORDER_COPY PASS m%d cycles=12000 compares=%%0d",compares); $finish; end'%args.mutant,'end','endmodule']
(out/'tb.sv').write_text('\n'.join(lines)+'\n')
verilator=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(verilator),'--binary','--timing','-Wno-fatal','--x-initial','unique','--x-assign','unique','-j','8',
     '--top-module','tb','--Mdir',str(out/'obj'),'-DOT_MEM_NO_INIT',
     'cell_models.v','macro.v','original.v',str(out/'candidate.sv'),str(out/'tb.sv')]
with (out/'build.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
if rc:raise SystemExit(rc)
with (out/'run.log').open('w') as log:rc=subprocess.run([str((out/'obj/Vtb').absolute()),'+verilator+rand+reset+2','+verilator+seed+1020'],stdout=log,stderr=subprocess.STDOUT).returncode
print((out/'run.log').read_text())
raise SystemExit(rc)
