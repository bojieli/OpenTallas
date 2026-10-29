#!/usr/bin/env python3
"""Replay packed XS intervals on the actual paired-ROM calendar reader.

Consumes an internal captured compile_ops result, compares every original
75-bit action on its absolute edge, and rejects a wrong segment base control.
No source data/clock timing is inferred by this component replay.
"""
import argparse
import importlib.util
import json
import gzip
from pathlib import Path
import pickle
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
TB=r'''`timescale 1ns/100fs
module tb;
reg ck=0,rn=0,prime=0,start=0;always #0.4165 ck=~ck;
reg[11:0]base=0;reg[12:0]length=0;
wire[74:0]action;wire active,primed,fault;
ot_s81_pq_calendar_rom #(.ACTION_BITS(75),.ACTION_IMAGE("action.hex"),.TIME_IMAGE("time.hex")) dut(
.ck(ck),.rst_n(rn),.prime(prime),.stage_start(start),.base(base),.length(length),
.action(action),.active(active),.primed(primed),.fault(fault));
reg[63:0]segs[0:@NS@-1];reg[98:0]expected[0:@NE@-1];
integer c=0,i,seen=0,mut=0;reg[74:0]mask;
initial begin $readmemh("segments.hex",segs);$readmemh("expected.hex",expected);if($value$plusargs("MUT=%d",mut))begin end end
always@(negedge ck)begin
 c++;rn=c>=8;prime=0;start=0;
 for(i=0;i<@NS@;i++)begin
  if(c==80+int'(segs[i][23:0]))begin
   prime=1;base=segs[i][35:24]+12'((mut==1&&i==1)?1:0);length=segs[i][48:36];
  end
  if(c==100+int'(segs[i][23:0]))start=1;
 end
 if(c>@END@)begin
  if(seen!=@NE@||active||fault)$fatal(1,"incomplete/faulted reader seen%0d expected@NE@ fault%b",seen,fault);
  $display("XS_READER_REPLAY PASS events%0d segments@NS@ exact833ps absolute_edges",seen);$finish;
 end
end
always@(posedge ck)begin
 #0.01;
 if(c>30)begin
  if(fault)$fatal(1,"real paired-ROM reader fault c%0d",c);
  if(seen<@NE@&&c==100+int'(expected[seen][98:75])+1)begin
   if(action!==expected[seen][74:0])$fatal(1,"actual action mismatch c%0d event%0d got%h expected%h",c,seen,action,expected[seen][74:0]);
   seen++;
  end else if((action & ~(75'd1<<72))!=0)$fatal(1,"unexpected actual action c%0d",c);
 end
end
endmodule
'''


def run(root,capture,pack_source,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    sys.path[:0]=[str(root/'tools/s81_dv'),str(root/'tools/s81_dv/layer_prog')]
    import xs_calendar_pack as P
    if pack_source:
        spec=importlib.util.spec_from_file_location('candidate_xs_pack',pack_source);candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
        P.pack_layer=candidate.pack_layer
    import xs_field_calendar as F
    from pq_calendar import viamap
    capture=Path(capture)
    if capture.suffix=='.gz':
        r=json.loads(gzip.decompress(capture.read_bytes()))
        for cal in r['cals']:cal['iss']={int(k):v for k,v in cal['iss'].items()}
    else:
        r=pickle.loads(capture.read_bytes())
    lc=F.layer_calendar(r['cals'])
    (out/'packed.json').write_text(json.dumps(lc,indent=1)+'\n')
    starts={w['op']:w['start']for w in lc['windows']}
    raw=[(starts[c['op']]+(w>>75),w&P.ACTION_MASK)for c in r['cals']for w in c['packed']if not w&P.END]
    raw.sort();assert len({t for t,a in raw})==len(raw),'duplicate actual event edges'
    words=lc['packed']+[0]*(4096-len(lc['packed']))
    (out/'action.hex').write_text(viamap([w&((1<<72)-1)for w in words]))
    (out/'time.hex').write_text(viamap([w>>72 for w in words]))
    (out/'expected.hex').write_text(''.join(f'{(t<<75)|a:025x}\n'for t,a in raw))
    (out/'segments.hex').write_text(''.join(f'{s["start"]|(s["base"]<<24)|(s["rows"]<<36):016x}\n'for s in lc['segments']))
    tb=TB.replace('@NS@',str(len(lc['segments']))).replace('@NE@',str(len(raw))).replace('@END@',str(raw[-1][0]+150))
    (out/'tb.sv').write_text(tb)
    files=['rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv','rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv',
      'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v']
    cmd=['verilator','--binary','--timing','-O1','--build-jobs','2','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD',
         '--top-module','tb','-Mdir',str(out/'obj'),'-o','sim',*(str(root/f)for f in files),str(out/'tb.sv')]
    with(out/'build.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    results={}
    for m in [0,1]:
        with(out/f'run{m}.log').open('w')as log:q=subprocess.run([str(out/'obj/sim'),'+MUT='+str(m)],cwd=out,stdout=log,stderr=subprocess.STDOUT)
        text=(out/f'run{m}.log').read_text();ok=(q.returncode==0 and 'XS_READER_REPLAY PASS'in text)if m==0 else(q.returncode!=0 and ('actual action mismatch'in text or 'real paired-ROM reader fault'in text))
        results[m]=dict(PASS=ok,rc=q.returncode)
        if not ok:raise ValueError('calendar reader replay mode'+str(m)+' failed: '+str(out))
    (out/'verdict.json').write_text(json.dumps(dict(PASS=True,rows=lc['rows'],segments=len(lc['segments']),events=len(raw),results=results,
        action_edges_preserved=True,period_ps=833,RTL_added_cycles=0,full_token=False),indent=1)+'\n')
    print('XS_PACK_REPLAY PASS rows',lc['rows'],'events',len(raw),'segments',len(lc['segments']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--capture',type=Path,required=True);p.add_argument('--pack-source',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run(a.root.resolve(),a.capture,a.pack_source,a.out.resolve())
