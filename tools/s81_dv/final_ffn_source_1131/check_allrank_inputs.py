#!/usr/bin/env python3
"""Compute released down source values for all TP4 logical rows, without placement.

Uses actual compiler matrix decoding and five K-segment golden kernels. This
is a source-input arithmetic witness, not emitted-field/native RTL execution,
CAP delivery, SRAM residency or a programme/calendar admission.
"""
import argparse
from pathlib import Path
import hashlib
import json
import os
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler',required=True,type=Path);p.add_argument('--rank0',required=True,type=Path)
p.add_argument('--other-ranks',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
for rel in ('tools','tools/s81_dv','tools/s81_dv/layer_prog','tools/s81'):
 sys.path.insert(0,str(a.compiler/rel))
import numpy as np
from layer_prog import xs_place as X
from frame_return_plan import golden_vals
from final_ffn_source_1131.check_field import canonical
import hdc_golden_v41 as G

report=dict(status='RUNNING',scope='source-input arithmetic only; no old80 map or physical placement used',cases=[],production_enabled=False)
def save():(a.out/'check.json').write_text(json.dumps(report,indent=2)+'\n')
save();words=np.zeros((7,5120),dtype=np.uint32);partials=np.zeros((7,5120,5),dtype=np.uint32)
try:
 for rank in range(4):
  fx=X.Fix(a.rank0 if rank==0 else a.other_ranks/f'rank{rank}')
  assert fx.meta['rank']==rank and fx.meta['tp']==4
  names=[f'exp{e}' for e in fx.meta['experts']]+['shared']
  for slot,name in enumerate(names):
   raw=fx.w(name+'.w2');sc=fx.sc(name+'.w2')
   mat=X.FMat(name+'.w2',X.fmt_of(fx,name+'.w2'),raw,sc,list(range(1280)),'ffn.down')
   prefix='ffn.shared' if name=='shared' else 'ffn.experts.'+name[3:]
   x=G.to_bf16(fx.op(prefix+('.swiglu' if name=='shared' else '.route_w')))
   vals=golden_vals(mat,x,5)
   expected=fx.op(prefix+'.down').astype(np.float32).view(np.uint32).reshape(-1)[1280*rank:1280*(rank+1)]
   result=[]
   for row in range(1280):
    value=canonical(vals[row]);bf=(value+0x7fff+((value>>16)&1))&0xffff0000
    if bf!=int(expected[row]):raise ValueError(f'source mismatch rank{rank} {name} row{row}: {bf:08x}!={int(expected[row]):08x}')
    result.append(bf);partials[slot,1280*rank+row]=vals[row]
   words[slot,1280*rank:1280*(rank+1)]=result
   report['cases'].append(dict(rank=rank,expert=name,rows=1280,status='PASS'))
   save();print('SOURCE_INPUT_PASS',rank,name,1280,flush=True)
   if rank==0 and slot==0:
    row=next(i for i,v in enumerate(expected) if int(v)&0x7fffffff)
    mutant_sc=sc.copy();assert (mutant_sc[row]<254).all();mutant_sc[row]+=1
    mutant=X.FMat(name+'.w2','fp4',raw,mutant_sc,[row],'ffn.down')
    wrong=canonical(golden_vals(mutant,x,5)[0]);wrong=(wrong+0x7fff+((wrong>>16)&1))&0xffff0000
    assert wrong!=int(expected[row]),'source scale control was not caught'
    report['weight_scale_control']=dict(rank=0,expert=name,row=row,want=f'{int(expected[row]):08x}',mutant=f'{wrong:08x}',caught=True)
 words.tofile(a.out/'down_source_bf16_in_fp32.u32');partials.tofile(a.out/'down_source_kseg5.u32')
 report.update(status='PASS_SOURCE_INPUT_ARITHMETIC',rows_checked=35840,canonical_K_segments=5,output_order='expert routedIDs ascending then shared; global_element0..5119',bf16_sha256=hashlib.sha256(words.tobytes()).hexdigest(),partial_sha256=hashlib.sha256(partials.tobytes()).hexdigest(),image_publication_qualified=False,native_runtime_qualified=False,arrival_residency_qualified=False)
 save()
except Exception as error:
 report.update(status='FAIL',error=str(error));save();raise
