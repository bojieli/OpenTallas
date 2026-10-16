#!/usr/bin/env python3
"""Observe actual sequencer words AND sticky faults against an offline trace.

This is component replay, not the absent canonical 519-phase production calendar.
The oracle packs literal trace fields independently of the descriptor compiler.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SOURCE='rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv'


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--desc',type=Path,required=True)
    p.add_argument('--trace',type=Path,default=ROOT/'results/rtl/s81_bf_programme_1015/legacy_issue_trace.txt.gz')
    p.add_argument('--advance',type=int,default=0)
    p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
    raw=gzip.decompress(a.trace.read_bytes()).decode() if a.trace.suffix=='.gz' else a.trace.read_text()
    phases=[]
    for line in raw.splitlines():
        f=line.split()
        if f and f[0]=='G':phases.append([])
        elif f and f[0]=='I':
            off,addr,op,seg,half,chain=map(int,f[2:8])
            phases[-1].append((off-a.advance,chain<<34|half<<33|seg<<30|op<<15|addr<<1|1))
    desc=[int(x,16) for x in a.desc.read_text().split()]
    assert len(desc)==len(phases) and any(not x for x in phases)
    body=[]
    for n,(d,events) in enumerate(zip(desc,phases)):
        assert d&16383==len(events)
        body += ['reset_dut();',f'desc=82\'h{d:021x};', 'go=1;', 'tick(); go=0; check_word(0);']
        edge=0
        for off,w in events:
            assert off>edge
            if off-edge>1:body += [f'repeat({off-edge-1}) begin tick(); check_word(0); end']
            body += [f'tick(); check_word(38\'h{w:010x});'];edge=off
        body += ['repeat(3) begin tick(); check_word(0); end',f'if(fault) $fatal(1,"unexpected fault phase {n}");']
    tb='''`timescale 1ns/1ps
module tb;
reg ck=0,rst_n=0,go=0;reg[81:0]desc=0;
wire[37:0]f_prog;wire fault;
ot_s81_bf_prog_seq dut(.*);
task tick; begin #4;ck=1;#1;ck=0;end endtask
task reset_dut;begin rst_n=0;go=0;tick();rst_n=1;end endtask
task check_word(input[37:0]expected);begin
 if(f_prog!==expected) $fatal(1,"word mismatch got %h expected %h",f_prog,expected);
end endtask
initial begin
'''+ '\n'.join(body)+'''
// Empty OFF0 must be silent; nonempty impossible OFF0 must still fault.
reset_dut();desc=82'd1;go=1;tick();
if(!fault) $fatal(1,"missing impossible first edge fault");
reset_dut();desc=82'd1|(82'd8<<15);go=1;tick();go=0;tick();go=1;tick();
if(!fault) $fatal(1,"missing overlapping start fault");
$display("PASS actual sequencer words and faults");$finish;
end endmodule
'''
    (a.work/'tb.sv').write_text(tb)
    cases={}
    for name,define,positive in [('positive',None,True),('empty_fault','OT_S81_BF_PROG_MUT_EMPTY_FAULT',False),('address','OT_S81_BF_PROG_MUT_ADDR',False)]:
        exe=a.work/name
        cmd=['iverilog','-g2012','-s','tb','-o',str(exe)]
        if define:cmd+=['-D'+define]
        b=subprocess.run(cmd+[str(ROOT/SOURCE),str(a.work/'tb.sv')],capture_output=True,text=True)
        assert b.returncode==0,b.stderr
        r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        log=r.stdout+r.stderr;(a.work/(name+'.log')).write_text(log)
        ok=(r.returncode==0 and 'PASS actual' in log) if positive else (r.returncode!=0 and ('unexpected fault phase' in log if name=='empty_fault' else 'word mismatch' in log))
        cases[name]=dict(pass_=ok,returncode=r.returncode,log=log.strip())
    rec=dict(scope='actual sequencer component; canonical519 production calendar remains unavailable',
             source=SOURCE,source_sha256=hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(),
             descriptor_sha256=hashlib.sha256(a.desc.read_bytes()).hexdigest(),
             trace_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),advance=a.advance,
             phases=len(phases),issues=sum(map(len,phases)),empty_phases=[i for i,x in enumerate(phases) if not x],cases=cases,
             pass_=all(c['pass_'] for c in cases.values()))
    (a.work/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2));raise SystemExit(0 if rec['pass_'] else 1)


if __name__=='__main__':main()
