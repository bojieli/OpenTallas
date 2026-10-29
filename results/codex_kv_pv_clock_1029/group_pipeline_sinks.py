#!/usr/bin/env python3
"""Plan-time lane-atomic ownership for PV pair's existing four CTS roots.
No RTL/pin/island/node/clock-latency changes. Input sink ownership came from
an individual-flop equal-load spatial solve; whole pipelines must stay intact.
Usage: group_pipeline_sinks.py SLICE.json GEOM.tsv OUT_SLICE.json REPORT.json
"""
import collections,copy,json,re,sys
from pathlib import Path

def norm(s):return s.replace(chr(92),'')
def family(s):
 m=re.match(r'^(u_s[01]\.u_slice\.g_lane\[\d+\])\.',norm(s))
 return m[1] if m else None

def apply(doc, geom):
 d=copy.deepcopy(doc);leaves=d['core_tree']['leaves'];reg=[x for x in leaves if x.get('cts_open')]
 assert len(reg)==4 and len({x['node'] for x in reg})==4
 nodes={x['name']:x for x in d['core_tree']['nodes']}
 own={};groups=collections.defaultdict(collections.Counter);members=collections.defaultdict(list)
 for l in reg:
  for s in l['sinks']:
   assert s not in own,('duplicate',s)
   own[s]=l['node'];f=family(s)
   if f:groups[f][l['node']]+=1;members[f].append(s)
 assert len(groups)==32,('unexpected lane census',len(groups))
 # The majority is the spatial preference from the existing pre-build solve.
 # Preserve geometry intent, but relax its exact per-flop count balancing:
 # splitting a pipeline to save a few sinks creates unshared clock delay.
 target={f:sorted(c,key=lambda n:(-c[n],n))[0] for f,c in groups.items()}
 after={s:target.get(family(s),n) for s,n in own.items()}
 moved=[dict(sink=s,old=own[s],new=n,family=family(s))for s,n in after.items()if n!=own[s]]
 for l in reg:
  l['sinks']=[s for s,n in after.items()if n==l['node']];l['domain_sinks']=len(l['sinks'])
 assert set(after)=={s for l in reg for s in l['sinks']}
 before=collections.Counter(own.values());counts=collections.Counter(after.values())
 pos={}
 for line in Path(geom).read_text().splitlines():
  a=line.split('\t')
  if a[0]=='C' and len(a)>=9:
   pos[norm(a[8])]=((float(a[4])+float(a[6]))/2,(float(a[5])+float(a[7]))/2)
 reach=collections.defaultdict(list);missing=[];total_before=total_after=0
 for s,n in after.items():
  name=norm(s).rsplit('/',1)[0]
  if name not in pos:missing.append(s);continue
  x,y=pos[name];cx,cy=nodes[n]['xy_um'];ox,oy=nodes[own[s]]['xy_um']
  dist=abs(x-cx)+abs(y-cy);reach[n].append(dist)
  total_after+=dist;total_before+=abs(x-ox)+abs(y-oy)
 witnesses=[]
 for f in sorted(groups):
  byname={norm(s):s for s in members[f]}
  a=next((s for k,s in byname.items()if '.u_prod.s1_bad$'in k),None)
  b=next((s for k,s in byname.items()if '.u_prod.s2_bad$'in k),None)
  if a and b:witnesses.append(dict(family=f,launch=a,capture=b,before=[own[a],own[b]],after=[after[a],after[b]]))
 rep=dict(status='STATIC_PLAN_SUCCESSOR_NOT_ROUTED',register_sinks=len(own),families=32,
  split_families_before=sum(len(c)>1 for c in groups.values()),split_families_after=0,
  before_counts=dict(before),after_counts=dict(counts),moved_sinks=len(moved),
  peak_load_change_pct=100*(max(counts.values())/max(before.values())-1),
  total_stub_L1_before_um=total_before,total_stub_L1_after_um=total_after,
  max_stub_L1_um={n:max(ds)for n,ds in reach.items()},
  over405=sum(v>405 for ds in reach.values()for v in ds),missing_positions=missing,
  families_detail=[dict(family=f,old=dict(groups[f]),new=target[f],sinks=len(members[f]))for f in sorted(groups)],
  witness_flag_pairs=witnesses,changed_sinks=moved,cycles_added=0,
  unchanged=['pins','macro ownership/leaves','nodes/positions/masters/stages','islands','clock entry/IO budget','RTL'])
 d['plan']=d.get('plan','')+' | CODEX PV-LANE-ATOMIC: complete FP pipeline register families share one CTS island; no per-flop exact-load split'
 d['core_tree']['form']=d['core_tree'].get('form','')+' | whole-lane sink ownership, geometric-majority root'
 d.setdefault('plan_prediction',{})['lane_atomic']=dict(register_sinks=len(own),root_counts=dict(counts),
  missing_positions=len(missing),stub_L1_max_um=rep['max_stub_L1_um'],over405=rep['over405'],
  label='STATIC geometric bound; existing placement census, not measured successor timing/maze reach')
 return d,rep

if __name__=='__main__':
 src,geom,out,report=map(Path,sys.argv[1:]);d,r=apply(json.loads(src.read_text()),geom)
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(d,indent=1)+'\n');report.write_text(json.dumps(r,indent=1)+'\n')
 print(json.dumps({k:r[k]for k in ['register_sinks','families','split_families_before','split_families_after','before_counts','after_counts','moved_sinks','peak_load_change_pct','max_stub_L1_um','over405']}))
