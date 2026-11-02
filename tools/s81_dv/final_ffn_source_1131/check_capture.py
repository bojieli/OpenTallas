#!/usr/bin/env python3
"""Bind actual emitted down tags to the real CAP config/address encoder.

No CAP timing constants or old capture calendars are used. The only cap_model
operation is its address/format decode, checked against the dynamic RD word map
and fresh released-source values. All three selected CAP families stay explicit.
"""
import argparse
from pathlib import Path
import json,os,sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler',required=True,type=Path);p.add_argument('--volume',required=True,type=Path)
p.add_argument('--rank0',required=True,type=Path);p.add_argument('--other-ranks',required=True,type=Path)
p.add_argument('--values',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--mutant-tag',action='store_true')
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
volume=json.load(open(a.volume/'manifest.json'));top=volume['topology'];assert top['enabled'] and len(top['frames_per_slice'])==16
canary=a.volume.parent/'down_pair_canary_retry4';flags=json.load(open(canary/'manifest.json'))['flags']
os.environ.update({k:v for k,v in flags.items() if k.startswith(('OT_S81_','OT_XS_'))})
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
for rel in ('tools','tools/s81_dv','tools/s81_dv/layer_prog','tools/s81'):sys.path.insert(0,str(a.compiler/rel))
import numpy as np
from layer_prog import xs_place as X,xs_calendar as XC,final_ffn as F
from final_ffn_source_1131.check_field import canonical
from cap_model import decode
from field_rank_images import word
X.TP.TOPO=list(top['frames_per_slice']);X.TP.SOURCE=top['die_sha']
values=np.fromfile(a.values/'down_source_bf16_in_fp32.u32',np.uint32).reshape(7,5120)
parts=np.fromfile(a.values/'down_source_kseg5.u32',np.uint32).reshape(7,5120,5)
family={sid:('capc2_w3' if sid//2==3 else 'capc5r_e6' if sid//2 in (0,2,5,7) else 'capc5r_w3') for sid in range(16)}
report=dict(status='RUNNING',scope='source capture configuration, literal image tag and SRAM-address/format map only',actual_topology=top,selected_CAP_family_by_sid=family,CAP_timing_imported=False,arrival_qualified=False,production_enabled=False,ranks=[],images=[])
def save():(a.out/'check.json').write_text(json.dumps(report,indent=2)+'\n')
save();cap0=None
try:
 for rank in range(4):
  fx=X.Fix(a.rank0 if rank==0 else a.other_ranks/f'rank{rank}')
  groups=X.op_groups(fx,'ffn.down');spans=F.source_spans([sorted(r for fr in sl for r in fr) for sl in groups[0]['groups']])
  rec,amap,collisions=XC.cap_emit(X,fx,['ffn.down'],final_ffn=True)
  assert rec['faults']==0
  cfgs={}
  for phase in rec['phases']:
   name=phase['mat'][:-3];slot=F.expert_slot(name,fx.meta['experts'])
   for slice_ in phase['slices']:
    sid=slice_['slice_index'];cfg=slice_['cfg'];assert cfg==F.capture(rank,sid,slot,spans=spans)
    cfgs[slot,sid]=cfg
  count=0
  for move in F.word_transfers(rank,spans=spans):
   slot=move['expert'];name=('shared' if slot==6 else 'exp'+str(fx.meta['experts'][slot]))+'.w2'
   row=move['global_element']-1280*rank
   sid,leaf,address=amap[name,'row',row]
   assert (sid,leaf,address)==(move['source_sid'],move['source_leaf'],4*move['source_row']+move['source_word'])
   cfg=cfgs[slot,sid];raw=canonical(parts[slot,move['global_element']])
   bad,actual_leaf,port,actual_address,data=decode(row<<13,raw,cfg)
   assert not bad and (actual_leaf,actual_address)==(leaf,address)
   assert data==int(values[slot,move['global_element']])
   count+=1
  (a.out/f'capture_rank{rank}.json').write_text(json.dumps(rec,indent=1)+'\n')
  if rank==0:cap0={(ph['mat'],ph['chunk']):ph for ph in rec['phases']}
  report['ranks'].append(dict(rank=rank,source_words=count,configs=sum(len(ph['slices']) for ph in rec['phases']),potential_pairing_slot_collisions=collisions))
  save();print('CAP_SOURCE_MAP_PASS',rank,count,len(collisions),flush=True)
 # Read only completed worker results. No data from advancing field writes.
 for result in volume['results']:
  if result['status'] not in ('PASS_SOURCE_FIELD','REUSED_SOURCE_CANARY'):continue
  frame=result['frame'];directory=a.volume/frame;field=json.load(open(directory/'field.json'));sid=field['slice_index'];fidx=field['frame_index'];banks={};checked=0
  for phase in field['phases']:
   if phase['op']!='ffn.down':continue
   assert phase.get('kslot',1)==1,'literal tag check needs explicit multik-slot addressing before extension'
   cap=cap0[phase['mat'],phase['chunk']];slice_=next(s for s in cap['slices'] if s['slice_index']==sid)
   assert phase['row_index']==slice_['frame_tags'][fidx]
   for placed in phase['placement']:
    for row in placed['rows']:
     if row>=phase['rows']:continue
     # One K-slot per pair: CFG row words are class0, not the global K-segment index.
     cfgword=17 if row%2 else 0;key=placed['pair'],cfgword%7
     if key not in banks:banks[key]=[int(v,16) for v in (directory/'images'/f'{frame}_c{key[0]}_{key[1]}.viamap.hex').read_text().split()]
     tag=word(banks[key],4*phase['phase']+cfgword//7)&0xffff
     if a.mutant_tag and checked==0:tag^=1
     assert tag==phase['row_index'][row],(frame,phase['phase'],placed['pair'],row,tag,phase['row_index'][row])
     checked+=1
  assert checked==5*result['checked_rows']
  report['images'].append(dict(frame=frame,literal_CFG_tags=checked))
 report.update(status='PASS_SOURCE_CAPTURE_ABI',source_words=sum(r['source_words'] for r in report['ranks']),literal_CFG_tags=sum(f['literal_CFG_tags'] for f in report['images']),potential_pairing_slot_collision_count=sum(len(r['potential_pairing_slot_collisions']) for r in report['ranks']))
 save()
except Exception as error:
 report.update(status='FAIL',error=str(error));save();raise
