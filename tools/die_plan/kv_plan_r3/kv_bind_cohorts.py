#!/usr/bin/env python3
"""Declare exact reported physical pad cohorts, preserving geometry/cycles."""
import argparse,copy,hashlib,json
p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('landing');p.add_argument('report');p.add_argument('--out',required=True);p.add_argument('--landing-out',required=True);a=p.parse_args()
d=json.load(open(a.plan));land=json.load(open(a.landing));report=json.load(open(a.report));parts={p['name']:p for p in d['partitions']};made=[]
for split in report['type_splits']:
 old=split['type'];assert old in d['partition_types']
 for names in split['variants'][1:]:
  new=old+'__rq'+hashlib.sha256(','.join(sorted(names)).encode()).hexdigest()[:8]
  assert new not in d['partition_types'];t=copy.deepcopy(d['partition_types'][old]);t['module']=new;t['note']=t.get('note','')+'; exact B42 VQ receiver pad cohort, same geometry/mission cycles'
  d['partition_types'][new]=t
  if old in d['reset'].get('in_sites',{}):d['reset']['in_sites'][new]=copy.deepcopy(d['reset']['in_sites'][old])
  land['collector']['types'][new]=copy.deepcopy(land['collector']['types'][old])
  for pn in names:assert parts[pn]['type']==old;parts[pn]['type']=new
  made.append(dict(type=new,from_type=old,parts=names))
for path,obj in [(a.out,d),(a.landing_out,land)]:
 with open(path,'w') as f:json.dump(obj,f,indent=1);f.write('\n')
print(json.dumps(dict(cohorts=made,added_types=len(made),geometry_change=0,cycles_change=0)))
