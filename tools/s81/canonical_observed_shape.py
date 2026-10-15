#!/usr/bin/env python3
"""Observe construction identities and source shape; never fill requirements as facts."""
import argparse,collections,gzip,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as bind

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def observe(die,plan,stage_map,sequencer_source,params=None):
 observed={k:None for k in ('field_pairs','bf_pairs','phase_width','stages','rank_dies')}
 result=dict(schema='opentallas.s81.observed-shape.v1',observed=observed,failures=[],evidence={},source_stage_phase_widths=None,emitted_stage_rank_replicas=None,native_qualified=False)
 def fail(message):result['failures'].append(message)
 for role,path in [('die',die),('plan',plan),('stage_map',stage_map),('sequencer_source',sequencer_source),('params',params)]:
  if path and path.is_file():result['evidence'][role]=dict(path=str(path.resolve()),sha256=sha(path))
  elif role!='params':fail('missing_'+role)
 result['die_sha256']=result['evidence'].get('die',{}).get('sha256')
 em={};nets={};snapshot=None;ids={};plan_instances={};widths=[]
 if die.is_file():
  nets,_,_,instances=bind.parse_die(die)
  counts=collections.Counter(name for master,name,prm,connections in instances if master!='__assign__')
  if any(n!=1 for n in counts.values()):fail('duplicate_emitted_instance_identity')
  em={name:(master,prm,connections) for master,name,prm,connections in instances if master!='__assign__'}
  result['emitted_instances']=len(instances)
 if plan.is_file():
  with (gzip.open(plan,'rt') if plan.suffix=='.gz' else plan.open()) as stream:snapshot=json.load(stream)
  pi=snapshot.get('insts',[]);plan_instances={i[0]:i for i in pi}
  if len(plan_instances)!=len(pi):fail('duplicate_plan_instance_identity')
  for root,frame in snapshot.get('frames',{}).items():
   for pair,kind,slot,lane in frame.get('elems',[]):
    if pair in ids:fail('duplicate_plan_pair_id:'+str(pair))
    ids[pair]=(int(root),kind)
  emitted_pairs={int(n[1:]) for n in em if re.fullmatch(r'e\d+',n)}
  if not ids:fail('empty_plan_pair_identity')
  if emitted_pairs!=set(ids):fail('emitted_plan_pair_identity_mismatch')
  for name,instance in plan_instances.items():
   if name not in em or em[name][0]!=instance[1]:fail('emitted_plan_master_mismatch:'+name)
  if len(result['failures'])==0:
   observed['field_pairs']=len(ids);observed['bf_pairs']=sum(kind=='BF' for root,kind in ids.values())
 if sequencer_source.is_file():
  modules={m.name:m for m in bind.parse_modules(sequencer_source.read_text(),str(sequencer_source))}
  sidecar=json.loads(params.read_text()).get('masters',{}) if params and params.is_file() else {}
  for pair in ids:
   name=f's{pair}';master,inline,connections=em.get(name,(None,{},{}));module=modules.get(master)
   if module is None:fail('missing_actual_sequencer_source:'+name);continue
   env=module.env(dict(sidecar.get(master,{}),**inline));phw=env.get('PHW');nrom=env.get('NROM');expected=module.width('lc',env) if 'lc' in module.ports else None
   connected=bind.expr_bits(connections.get('lc',''),nets)
   if phw is None or not connected or any(n in ('UNDECL','CONST','Z') for n,b in connected) or len(connected)!=expected:
    fail('unproven_sequencer_phase_connection:'+name);continue
   widths.append(phw)
   if type(nrom)!=int or nrom<=0:fail('unproven_sequencer_NROM:'+name);continue
   for bank in range(nrom):
    child=f'c{pair}_{bank}'
    if child not in em or child not in plan_instances or em[child][0]!=plan_instances[child][1]:fail('missing_emitted_CFG_bank:'+child)
  if ids and len(widths)==len(ids) and len(set(widths))==1:observed['phase_width']=widths[0]
  elif ids:fail('inconsistent_or_unproven_emitted_phase_width')
 if stage_map.is_file():
  stages=json.loads(stage_map.read_text());phws=stages.get('PHW_required_by_stage');ranks=stages.get('rank_dies',[]);bounds=stages.get('region_bounds',[]);bf=stages.get('BF_site_IDs',[])
  valid=True
  if not isinstance(phws,list) or not phws or any(type(w)!=int or w<1 for w in phws):fail('invalid_source_stage_phase_widths');valid=False
  keys=[(d.get('stage'),d.get('rank')) for d in ranks];dieids=[d.get('die_id') for d in ranks];rankids={d.get('rank') for d in ranks}
  if not rankids or (phws and set(keys)!={(s,r) for s in range(len(phws)) for r in rankids}) or len(keys)!=len(set(keys)) or len(dieids)!=len(set(dieids)):
   fail('invalid_source_stage_rank_identity');valid=False
  if not ids or len(bounds)<2 or bounds[0]!=0 or set(ids)!=set(range(bounds[-1])) or len(set(bf))!=len(bf) or set(bf)!={p for p,(r,k) in ids.items() if k=='BF'}:
   fail('source_stage_map_pair_or_BF_identity_mismatch');valid=False
  if bounds and any(root+1>=len(bounds) or not bounds[root]<=p<bounds[root+1] for p,(root,k) in ids.items()):fail('source_stage_map_root_identity_mismatch');valid=False
  if valid:
   observed['stages']=len(phws);observed['rank_dies']=len(ranks);result['source_stage_phase_widths']=phws;result['source_rank_dies']=ranks
   if observed['phase_width'] is None or max(phws)>observed['phase_width']:fail('source_phase_width_exceeds_or_lacks_emitted_capacity')
 result['status']='OBSERVED_SOURCE_AND_CONSTRUCTION_SHAPE' if not result['failures'] and all(v is not None for v in observed.values()) else 'SHAPE_UNPROVEN'
 result['scope']='One emitted die construction, source-declared stage/rank inventory and observed sequencer capacity; not replicated physical dies, programmes or native qualification.'
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--die',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--stage-map',type=Path,required=True);ap.add_argument('--sequencer-source',type=Path,required=True);ap.add_argument('--params',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 try:result=observe(a.die,a.plan,a.stage_map,a.sequencer_source,a.params)
 except Exception as exc:result=dict(schema='opentallas.s81.observed-shape.v1',status='SHAPE_UNPROVEN',observed={k:None for k in ('field_pairs','bf_pairs','phase_width','stages','rank_dies')},failures=[repr(exc)],native_qualified=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n');return 0 if result['status']=='OBSERVED_SOURCE_AND_CONSTRUCTION_SHAPE' else 1
if __name__=='__main__':raise SystemExit(main())
