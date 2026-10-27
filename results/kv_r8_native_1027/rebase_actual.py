#!/usr/bin/env python3
"""Rebase existing authoritative KV tables on exact native-bind depths; retain position/PV contracts."""
import argparse,copy,json,sys
from collections import Counter,defaultdict
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('bus_groups',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
sys.path.insert(0,str(a.root/'tools/die_plan'));import r8
R=json.loads((a.root/'physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv_2350.json').read_text())
P=json.loads((a.root/'physical/die_plan/qwen_kvsys/die_plan.json').read_text())
B=json.loads(a.bus_groups.read_text());types={x['name']:x['type'] for x in P['partitions']}
paths=[R['land_r8']]+R['land_r8_extra'];tabs=[json.loads((a.root/x).read_text()) for x in paths]
eff={m['id']:(k,m) for k,t in enumerate(tabs) for m in t['members'] if not m['id'].startswith('INNER:')}
actual={r8.mkey(g,m):(g,m) for g in B['landing'] for m in g['members']}
missing=sorted(set(eff)-set(actual));assert not missing,missing[:12]
r8.configure();N,uf,_=r8.classes(B,P,'type','leaf');cls={r8.mkey(g,m):uf.find(i) for i,(_,g,m) in enumerate(N)}
key={i:cls.get(i,('solo',i)) for i in eff};shift=defaultdict(int);required={}
for i,(k,m) in eff.items():
 g,n=actual[i];assert m['asbuilt']==n.get('asbuilt_lane_stages',n['asbuilt_stages']),(i,m['asbuilt'],n['asbuilt_stages'])
 need=1 if types[g['sink_part']]=='kv3_pc_v1' and n['sink_port']=='vreq' else 0
 required[i]=need
 shift[key[i]]=max(shift[key[i]],n['bound_stages']-m['landed'])
changes=[];pos=[];cost=0
for i,(k,m) in eff.items():
 g,n=actual[i];bound=n['bound_stages'];landed=m['landed']+max(0,shift[key[i]]);pad=landed-bound
 # vport vq0/vq1 are separate boot-programmed request calendars. Make each
 # complete valid/tag word use the same one-stage structure in every pc_v1.
 # Do not union their distinct calendars through raw generic classes.
 if required[i]:
  pad=1;landed=bound+1
 assert pad>=required[i],(i,pad,required[i])
 if n.get('position_bank'):
  assert pad==m['pad'],('position bank changed',i,m['pad'],pad)
  pos.append(i)
 if tabs[k].get('kind')=='pv_exact_asbuilt_calendar':assert landed==m['asbuilt'],('PV calendar moved',i)
 if (bound,pad,landed)!=(m['bound'],m['pad'],m['landed']):
  changes.append(dict(id=i,table=paths[k],bound=[m['bound'],bound],pad=[m['pad'],pad],landed=[m['landed'],landed]))
  cost+=(pad-m['pad'])*r8.nbits(m['sink_bits'])
  m.update(bound=bound,pad=pad,landed=landed,lane=n.get('lane'))
vreq=defaultdict(set)
for i,(k,m) in eff.items():
 g,n=actual[i]
 if required[i]:vreq[g['sink_part']].add(m['pad'])
assert len(vreq)==24 and all(v=={1} for v in vreq.values()),dict(vreq)
a.out.mkdir(parents=True,exist_ok=True)
for path,t in zip(paths,tabs):
 t['native_depth_rebase']=dict(source='codex/kv-native-bind-1027@db605b665d bind3/bus_groups.json',uniform_vreq_pad=1,position_banks_preserved=True,pv_exact_calendar_preserved=True)
 (a.out/Path(path).name).write_text(json.dumps(t,indent=0)+'\n')
report=dict(source='codex/kv-native-bind-1027@db605b665d bind3',effective_members=len(eff),all_ids_matched=True,
 actual_bound_changed=sum(c['bound'][0]!=c['bound'][1] for c in changes),changed=len(changes),extra_pad_flops=cost,
 position_bank_members_preserved=len(pos),vreq_types=24,uniform_vreq_pad=1,
 model=dict(EST_EN_ES_added=2,EST_WN_WS_added=0,extra_VREQ_added=1,pv_calendar_cycles_added=0,steady_token_exposed='final native programme decides overlap'),changes=changes)
(a.out/'rebase_report.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=1))
