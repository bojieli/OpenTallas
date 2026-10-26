#!/usr/bin/env python3
"""Export actual canonical placements and calendars, keeping compiler bindings explicit."""
import argparse,gzip,hashlib,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--stage-map',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 plan=json.load(gzip.open(a.plan,'rt') if a.plan.suffix=='.gz' else a.plan.open());stage=json.loads(a.stage_map.read_text());inst={i[0]:dict(zip(('name','master','x','y','width','height','orientation','kind','region'),i)) for i in plan['insts']}
 assert len(inst)==len(plan['insts']), 'duplicate actual instance identity'
 bounds=stage['region_bounds']; npairs=bounds[-1]; nstages=len(stage['PHW_required_by_stage'])
 assert bounds[0]==0 and all(a<b for a,b in zip(bounds,bounds[1:])), 'invalid allocator region bounds'
 assert len(plan['frames'])==len(bounds)-1, 'plan roots differ from allocator'
 assert nstages>0 and len(stage['rank_dies'])==4*nstages
 assert {(r['stage'],r['rank']) for r in stage['rank_dies']}=={(s,r) for s in range(nstages) for r in range(4)}
 assert len({r['die_id'] for r in stage['rank_dies']})==4*nstages
 bf=set(stage['BF_site_IDs']);assert len(bf)==len(stage['BF_site_IDs']) and bf<=set(range(npairs)), 'invalid allocator BF IDs'
 pairs={};roots=[]
 for root,frame in sorted(plan['frames'].items(),key=lambda x:int(x[0])):
  ids=[]
  for pair,kind,slot,lane in frame['elems']:
   assert pair not in pairs and ((kind=='BF')==(pair in bf))
   assert stage['region_bounds'][int(root)]<=pair<stage['region_bounds'][int(root)+1]
   names=[f'e{pair}',f's{pair}']+[f'c{pair}_{j}' for j in range(7)]
   if kind=='BF':names += [f'e{pair}w',f'e{pair}e']
   assert all(n in inst for n in names), (pair,names)
   pairs[pair]=dict(pair_id=pair,root_id=int(root),type=kind,slot=slot,lane=lane,actual_children=[inst[n] for n in names]);ids.append(pair)
  roots.append(dict(root_id=int(root),pair_ids=ids,frame=frame,cfifo=inst[f'cf{root}']))
 assert set(pairs)==set(range(npairs)) and bf <= set(pairs), 'plan pairs differ from allocator'
 rank_bindings=[dict(**r,phase_width_required=stage['PHW_required_by_stage'][r['stage']],actual_su_leaf_home=None,actual_vm_leaf_home=None,programme_id=None,core_epoch=None,start_cycle=None,duration_cycles=None,status='UNBOUND_SOURCE_DEPENDENCY') for r in stage['rank_dies']]
 assert len(rank_bindings)==4*nstages
 result=dict(schema='opentallas.s81.canonical-source-export.v1',scope=plan['scope'],native_qualified=False,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.plan,a.stage_map)},counts=dict(field_pairs=len(pairs),bf_pairs=len(bf),roots=len(roots),stages=len(stage['PHW_required_by_stage']),rank_dies=len(rank_bindings)),pairs=[pairs[k] for k in sorted(pairs)],roots=roots,transport_calendar=plan['calendar'],emitted_parent_reservations=[v for k,v in inst.items() if k.startswith('sp_')],rank_programme_bindings=rank_bindings,provider_homes_reference_only=stage['provider_homes'],provider_homes_are_actual_su_vm_homes=False,limitations=['Parent reservations are emitted geometry, not placed native SU/VM child homes.','Transport station counts are not compiler epochs or native fixed-cycle programme qualification.','Actual rank programmes, core epochs and per-stage native SU/VM assignments remain unbound.'])
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with gzip.open(a.out,'wt') as f:json.dump(result,f,separators=(',',':'))
 print(json.dumps(result['counts']))
if __name__=='__main__':main()
