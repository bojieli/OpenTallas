#!/usr/bin/env python3
"""Build only the new Opt4 service/gearbox + ONE unchanged full NC8 SM.

No r2 rebuild. Retained r2 calibrates a different source layout. This coupled
minimum component owns the missing interleave/landing/gearbox observation.
Physical wire latencies are inherited assumptions; SS60/FF25 remains open.
"""
import argparse,hashlib,json,itertools,os,subprocess,sys,time,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dshbm_matched_sm_seq as M
import hdc_golden as G
from dshbm_expert_workgroup_interleave import chunks,paired_rows,compact_stream,expand_stream
from dshbm_expert_workgroup import exported_weight_reader,sm_vectors
import numpy as np

NEW=['rtl/hbm_accel/service/'+n for n in ('ot_hbm_accel_cdc_fifo.sv','ot_hbm_accel_expert_stream_pc_la.sv',
'ot_hbm_accel_expert_fetch_stream_la.sv','ot_hbm_accel_wg_dispatch.sv','ot_hbm_accel_expert_stream_pc_wg.sv',
'ot_hbm_accel_expert_fetch_stream_wg.sv','ot_hbm_accel_wg_gearbox.sv')]
SRC=list(dict.fromkeys([p for p in M.SRC if p!='rtl/test/tb_hbm_accel_sm_v_seq.sv']+NEW+['rtl/test/hbm_accel/tb_hbm_accel_expert_fetch_wg.sv']))

def build(out,top,src,jobs):
 out.mkdir(parents=True,exist_ok=False)
 cmd=['verilator','--binary','--timing','-O2','-Wno-fatal','-j',str(jobs),'--top-module',top,'--Mdir',str(out/'obj')]+[str(ROOT/p) for p in src]
 with (out/'compile.log').open('w') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 return out/'obj'/('V'+top),cmd


def vectors(path):
 with path.open('w') as f:
  f.write(str(7**6)+'\n')
  for sets in itertools.product(range(7),repeat=6):
   ids=tuple(7*k+s for k,s in enumerate(sets));word=sum(e<<(9*k) for k,e in enumerate(ids))
   f.write(f'{word:014x}\n')
   for c in chunks(ids):f.write(f'{c.slot} {c.j0} {c.sectors} {int(c.keep)}\n')


def prepare(out,weights,inputs,L,q):
 ids=tuple(map(int,np.fromfile(inputs/f'L{L}/expert_ids.u32',dtype='<u4')))
 x=G.from_bits(np.fromfile(inputs/f'L{L}/ffn_norm.u32',dtype='<u4'))
 reader=exported_weight_reader(weights/f'L{L}',L,ids);out.mkdir()
 gu=[];expected=[];gold=[];xw=None
 for e in ids:
  p,s=paired_rows(reader,e,0,q);raw=compact_stream(p,s);g=sm_vectors(p,s,x)
  assert expand_stream(raw)==tuple(g['lines'])
  gu += [int.from_bytes(raw[i:i+128],'little') for i in range(0,32768,128)]
  expected+=g['lines'];gold += [int(G.bits(v)) for v in g['gold'][0]];xw=g['xw']
 for name,data,width in (('gu.hex',gu,256),('sm_expected.hex',expected,272),('gold.hex',gold,8),('x.hex',xw,(8*M.XC+2048+3)//4)):
  (out/name).write_text('\n'.join(f'{v:0{width}x}' for v in data)+'\n')
 return ids


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--weights',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
 p.add_argument('--jobs',type=int,default=16);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 rec=dict(status='PREPARING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in SRC+['tools/dshbm_expert_workgroup_interleave.py','tools/dshbm_expert_interleave_native.py','tools/uarch_model.py']},
 original_r2_qualification=False,whole_token=False,ss_ff_closed=False,cases=[],
 w2_scope='pattern transport in this GU arithmetic fixture ONLY; use service-only real W2 payload gate separately; no W2 arithmetic qualification',physical_provider_assumptions=dict(NOC_PS=5000,PHY_CMD_PS=5000,RSP_PS=10000,CL_PS=12500,hclk_ps=1024,stream_clk_ps=833),start_delay_credit_us=0)
 def save(): (a.out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 save()
 try:
  exe,cmd=build(a.out/'dispatch','tb_hbm_accel_wg_dispatch',['rtl/hbm_accel/service/ot_hbm_accel_wg_dispatch.sv','rtl/test/hbm_accel/tb_hbm_accel_wg_dispatch.sv'],a.jobs)
  vec=a.out/'dispatch/reference.txt';vectors(vec)
  for mut in (0,1):
   with (a.out/f'dispatch_mut{mut}.log').open('w') as f: subprocess.run([str(exe),f'+VECTORS={vec}',f'+mut={mut}'],stdout=f,stderr=subprocess.STDOUT,check=True)
  assert 'DISPATCH_PASS patterns=117649 accepted_descriptors=4941258' in (a.out/'dispatch_mut0.log').read_text()
  assert 'DUPLICATE_REJECTED_NO_DESCRIPTOR' in (a.out/'dispatch_mut1.log').read_text()
  rec['dispatch_patterns']=117649;rec['status']='DISPATCH_PASS_BUILDING_CONNECTED';save()
  exe,cmd=build(a.out/'connected','tb_hbm_accel_expert_fetch_wg',SRC,a.jobs)
  rec['command']=cmd;rec['binary_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest();save()
  for L in (20,3):
   for q in range(4):
    d=a.out/f'L{L}_stack{q}';ids=prepare(d,a.weights,a.inputs,L,q)
    for k in range(6):
     log=d/f'slot{k}.log';begin=time.monotonic()
     with log.open('w') as f:
      proc=subprocess.run([str(exe),f'+DIR={d}',f'+sm_slot={k}','+notice_lead_ps=300000']+[f'+id{i}={e}' for i,e in enumerate(ids)],stdout=f,stderr=subprocess.STDOUT)
     text=log.read_text();good=proc.returncode==0 and 'FIRST verdict=PASS' in text
     rec['cases'].append(dict(layer=L,stack=q,slot=k,ids=ids,exit=proc.returncode,exact=good,wall_seconds=time.monotonic()-begin,
       log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),slot_calendar=[line for line in text.splitlines() if line.startswith(('SLOT ','SM ','BW '))]))
     save()
     if not good:raise RuntimeError(f'connected {L=} {q=} {k=} FAILED; preserve {log}')
    # Actual corrupted sector must FAIL on the same immutable binary/input.
    with (d/'sector_corrupt_FAIL.log').open('w') as f:
     proc=subprocess.run([str(exe),f'+DIR={d}','+sm_slot=0','+notice_lead_ps=300000','+mut=1']+[f'+id{i}={e}' for i,e in enumerate(ids)],stdout=f,stderr=subprocess.STDOUT)
    assert proc.returncode!=0 and 'GU sector mismatch' in (d/'sector_corrupt_FAIL.log').read_text()
  rec['status']='PASS_CONNECTED_INTERLEAVE_GEARBOX_ONE_SM_ACTUAL_L20_L3';save()
 except Exception as e:
  rec['status']='FAIL_RETAINED';rec['error']=repr(e);save();raise

if __name__=='__main__':main()
