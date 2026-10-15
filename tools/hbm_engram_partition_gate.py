#!/usr/bin/env python3
"""Actual fixed-slot dispatcher and encoded compiler contract gate, not full native Engram."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import numpy as np
import hbm_engram_partition as E

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT/'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_dispatch.sv'


def compiler_gate():
    from hgi_sim import ds_native as D
    from hgi_sim.records import encode_program, decode_program
    class Engram:
        layer_ids = [1, 14]
    class Model:
        engram = Engram()
    result=[]
    for li, nrows in enumerate(E.RELEASED_ROWS):
        rph=(nrows+7)//8
        # Cover every home boundary and worst-case all24 rows on each home.
        cases=[[min(nrows-1,h*rph+i) for i in range(24)] for h in range(8)]
        cases += [[min(nrows-1, h*rph + off) for h in range(8) for off in (0,1,rph-1)]]
        for ids in cases:
            actual=D.eg_host_table(ids,nrows,li)
            assert actual.size==232
            counts=[0]*8
            for j,g in enumerate(ids):
                h=g//rph; local=g%rph; rank=li*8+h; t=counts[h]
                sid=int(actual[j]); assert (sid//8)%96 == rank
                assert (sid//768)*8+sid%8==t
                assert int(actual[40+24*h+t])==local
                counts[h]+=1
            assert list(actual[32:40])==counts
        for rank in range(96):
            x=object.__new__(D.Lower); x.lay=D.Layout(); x.m=Model(); x.rank_now=rank
            D.TABLE_OFF['EGHT']=0
            recs=[]
            def add(r,reads,writes,run=True):
                if run: recs.append(r)
            x.engram_fetch(add,lambda *a,**k:None,E.LAYERS[li])
            encoded=decode_program(encode_program(recs))
            load=next(r for r in encoded if r.tag=='engram.host_table') if any(r.tag=='engram.host_table' for r in encoded) else encoded[0]
            assert load.desc['A'].n==232 and load.desc['O'].n==232
            home_records=[r for r in recs if r.tag=='engram.home_rows']
            assert bool(home_records)==(rank in E.HOMES[li])
            if home_records:
                a=home_records[0].desc['I']; h=rank-li*8
                assert a.base==x.lay.vm['EGID']+40+24*h
                assert a.base+a.stride==x.lay.vm['EGID']+32+h
        result.append(dict(layer=E.LAYERS[li],ranks_checked=96,metadata_cases=len(cases)))
    for ids in ([0]*23, [-1]*24, [E.RELEASED_ROWS[0]]*24):
        try:E.host_table(ids,E.RELEASED_ROWS[0],0)
        except ValueError:pass
        else:raise AssertionError('invalid metadata accepted')
    return result


def vectors():
    rng=random.Random(20261015)
    cases=[]
    for li,nrows in enumerate(E.RELEASED_ROWS):
        rph=(nrows+7)//8
        for h in range(8):
            # Explicit slot23 on each home; list-ID second/third group inversion.
            cases.append((li,[h*rph + (i % min(24,nrows-h*rph)) for i in range(24)]))
        boundaries=[max(0,h*rph-1) for h in range(1,8)] + [h*rph for h in range(8)] + [nrows-1]
        cases.append((li,(boundaries*2)[:24]))
        for _ in range(128):cases.append((li,[rng.randrange(nrows) for _ in range(24)]))
    return cases


def bench(cases):
    lines=['''`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start=0,layer_index=0,row_valid=0; reg[28:0]row_id=0;
wire request_valid,done,fault; wire[6:0]request_rank; wire[36:0]request_address;
wire[25:0]request_local_row; wire[4:0]request_staging_slot,request_list_index; wire[19:0]gather_slot_id;
ot_hbm_engram_home_dispatch #(.MUTANT_RANK(`MUTANT_RANK)) dut(.*);
integer checks=0;
task tick; begin @(posedge clk); #1; end endtask
task put(input[28:0]r,input[6:0]rank,input[25:0]loc,input[4:0]slot,input[19:0]sid,input[4:0]idx);
begin
 @(negedge clk);start=0;row_valid=1;row_id=r;tick;
 if(!request_valid || fault || request_rank!==rank || request_local_row!==loc || request_staging_slot!==slot || gather_slot_id!==sid || request_list_index!==idx || request_address!==(37'd103079215104+37'(loc)*288) || done!==(idx==23))
 $fatal(1,"descriptor mismatch row%0d rank%0d expected%0d index%0d valid%b fault%b local%0d/%0d slot%0d/%0d sid%0d/%0d idx%0d done%b addr%0d",r,request_rank,rank,idx,request_valid,fault,request_local_row,loc,request_staging_slot,slot,gather_slot_id,sid,request_list_index,done,request_address);
 checks=checks+1;
end endtask
initial begin
 repeat(2)tick; @(negedge clk);rst_n=1;''']
    for li,ids in cases:
        lines.append(f'@(negedge clk); start=1; row_valid=0; layer_index={li}; tick;')
        counts=[0]*8;rph=(E.RELEASED_ROWS[li]+7)//8
        for j,r in enumerate(ids):
            h,loc=divmod(r,rph);rank=li*8+h;t=counts[h];sid=(t//8)*768+rank*8+t%8;counts[h]+=1
            lines.append(f'put(29\'d{r},7\'d{rank},26\'d{loc},5\'d{t},20\'d{sid},5\'d{j});')
        lines.append('@(negedge clk);row_valid=0;tick; if(request_valid||done||fault)$fatal(1,"end calendar");')
    lines.append('''// A missing reserved slot faults immediately rather than extending the token.
@(negedge clk);start=1;tick;@(negedge clk);start=0;row_valid=0;tick;
if(!fault || request_valid)$fatal(1,"missing row must fault");
@(negedge clk);rst_n=0;tick;@(negedge clk);rst_n=1;start=1;layer_index=1;tick;
@(negedge clk);start=0;row_valid=1;row_id=384016682;tick;
if(!fault || request_valid)$fatal(1,"row bound must fault");
$display("PASS descriptors=%0d missing-slot and row-bound faults",checks);$finish;
end
endmodule''')
    return '\n'.join(lines)


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    compiler=compiler_gate();cases=vectors();sv=out/'tb.sv';sv.write_text(bench(cases))
    runs=[]
    for name,mutant in [('baseline',0),('rank_mutant',1)]:
        exe=out/name
        cp=subprocess.run(['iverilog','-g2012',f'-DMUTANT_RANK={mutant}','-s','tb','-o',str(exe),str(RTL),str(sv)],capture_output=True,text=True)
        (out/f'{name}.build.log').write_text(cp.stdout+cp.stderr)
        if cp.returncode:raise RuntimeError(cp.stderr)
        p=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        (out/f'{name}.run.log').write_text(p.stdout+p.stderr)
        assert (p.returncode==0)==(mutant==0),p.stdout+p.stderr
        runs.append(dict(name=name,returncode=p.returncode,stdout=p.stdout.strip()))
    manifest=E.allocation_manifest()
    (out/'allocation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    receipt=dict(schema='opentallas.hbm.engram.partition.gate.v1',status='pass',
        compiler=compiler,actual_rtl=runs,token_vectors=len(cases),descriptors=24*len(cases),
        calendar='start at edge0, 24 row inputs/registered descriptors at edges1..24; done edge24; no ready',
        metadata=dict(old_words=144,new_words=232,added_bytes_per_rank=352,old_sectors=18,new_sectors=29),
        max_home_bytes=max(x['stack_local_end'] for x in manifest['intervals']),
        preserved_rows=list(E.RELEASED_ROWS),row_bytes=288,
        native_full_layer_qualified=False,physical_qualified=False,
        limitations=['No actual hash producer hookup','HBM external request descriptors only: DMA return and ROW_GATHER join open',
        'Compiler simulator checkpoint callback remains diagnostic, not on-chip hardware',
        'Full-program static calendar and throughput/route costs unmeasured'],
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [RTL,Path(__file__),ROOT/'tools/hbm_engram_partition.py',ROOT/'tools/hgi_sim/ds_native.py']})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args()
    print(json.dumps(run(args.out),indent=2))
