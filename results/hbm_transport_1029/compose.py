#!/usr/bin/env python3
"""Compose disjoint per-partition transport allocations from one exact geometry.
Rejects duplicate/missing partition results and source-plan/census mismatches.
"""
import argparse,copy,json,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('geometry');ap.add_argument('out');ap.add_argument('shards',nargs='+');ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools);import schema as S
base=Path(a.geometry);out=Path(a.out);out.mkdir(parents=True,exist_ok=False);P=json.loads((base/'die_plan.json').read_text());R=json.loads((base/'report.json').read_text());parts={p['name']:p for p in P['partitions']};seen=set();R.update(ft=[],internal=[],clock_ff_load={},wrapper_transport_ff={},completed_parts=[],allocation_failures=[])
try:
 for directory in a.shards:
  d=Path(directory);r=json.loads((d/'report.json').read_text());p=json.loads((d/'die_plan.json').read_text());pp={q['name']:q for q in p['partitions']}
  if r['status'] not in ('PARTIAL_FT_SITES_ALLOCATED','ACTUAL_FT_SITES_ALLOCATED_PENDING_G0_G1'):raise ValueError('shard has no allocated result: '+str(d))
  for key in ('source_plan_sha256','source_census_sha256'):
   if r[key]!=R[key]:raise ValueError('shard source identity mismatch: '+str(d))
  for pn in r['completed_parts']:
   if pn in seen:raise ValueError('partition allocated twice: '+pn)
   if pn not in R['changed_types']:raise ValueError('unexpected partition: '+pn)
   seen.add(pn);parts[pn].update(pp[pn]);tn=pp[pn]['type'];P['partition_types'][tn]=p['partition_types'][tn];R['changed_types'][pn]=r['changed_types'][pn]
  for key in ('ft','internal','allocation_failures'):R[key]+=r[key]
  for key in ('clock_ff_load','wrapper_transport_ff'):R[key].update(r[key])
 if seen!=set(R['changed_types']):raise ValueError('missing allocated partitions: '+','.join(sorted(set(R['changed_types'])-seen)))
 for tn in list(P['partition_types']):
  if tn.startswith('__transport_') and tn not in {p['type'] for p in P['partitions']}:P['partition_types'].pop(tn)
 m=S.Plan(P);prior=copy.deepcopy(P['latency']['lanes']);R['latency']=[r for r in R['latency'] if r.get('reason')!='actual FT row-site allocation']
 for l in P['lanes']:
  lid=l['id'];row=m.lane_latency(lid);row['param']=prior[lid].get('param','LAT_'+lid.upper());P['latency']['lanes'][lid]=row
  if row['cycles']!=prior[lid]['cycles']:R['latency'].append(dict(lane=lid,old=prior[lid]['cycles'],new=row['cycles'],added=row['cycles']-prior[lid]['cycles'],reason='actual FT row-site allocation'))
 R['completed_parts']=sorted(seen);R['status']='ACTUAL_FT_SITES_ALLOCATED_PENDING_G0_G1';(out/'die_plan.json').write_text(json.dumps(P,separators=(',',':'))+'\n')
except Exception as e:R['status']='FAIL';R['failures'].append(f'{type(e).__name__}: {e}');raise
finally:(out/'report.json').write_text(json.dumps(R,indent=1)+'\n')
