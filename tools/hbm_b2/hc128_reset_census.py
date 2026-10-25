#!/usr/bin/env python3
"""Count selected-master reset-controlled FF bits and reset delivery stages.
Depth=1 for a flop controlled directly by the core reset port. A local reset
flop whose Q resets downstream control adds another delivery edge. Functional
valid-pipeline length is counted as FF bits, not extra reset fanout depth.
"""
import argparse,collections,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('json',type=Path);ap.add_argument('--top',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();mods=json.loads(a.json.read_text())['modules'];ffs=[];instances=collections.Counter()
def walk(name,path,portmap):
 m=mods[name]
 def net(b):return ('const',b) if isinstance(b,str) else portmap.get(b,(path,b))
 for n,c in m.get('cells',{}).items():
  typ=c['type'];cn={p:[net(b) for b in bs] for p,bs in c['connections'].items()};cp=path+'/'+n;instances[typ]+=1
  if typ in mods and not mods[typ].get('attributes',{}).get('blackbox'):
   child=mods[typ];mp={}
   for p,pv in child['ports'].items():
    assert len(pv['bits'])==len(cn[p]),(cp,p)
    mp.update(zip(pv['bits'],cn[p]))
   walk(typ,cp,mp)
  elif 'Q' in cn:
   rp=next((p for p in ('ARST','SRST','ALOAD') if p in cn),None)
   ffs.append(dict(name=cp,type=typ,Q=cn['Q'],reset=cn[rp][0] if rp else None,reset_port=rp))
root=mods[a.top]['ports']['rst_n']['bits'];assert len(root)==1;rnet=('',root[0]);walk(a.top,'',{root[0]:rnet});resetnets={x['reset'] for x in ffs if x['reset'] is not None};depth={rnet:0};changed=True
while changed:
 changed=False
 for f in ffs:
  if f['reset'] not in depth:continue
  d=depth[f['reset']]+1
  for q in f['Q']:
   if q in resetnets and (q not in depth or depth[q]>d):depth[q]=d;changed=True
counts=collections.Counter();unreached=[];relay=[]
for f in ffs:
 if f['reset'] is None:continue
 if f['reset'] in depth:counts[depth[f['reset']]+1]+=len(f['Q'])
 else:unreached.append(f['name'])
 if any(q in resetnets for q in f['Q']):relay.append(dict(name=f['name'],type=f['type'],bits=len(f['Q']),delivery_depth=depth.get(f['reset'],None)))
r=dict(schema='opentallas.hbm.hc128.reset_census.v1',module=a.top,source_sha='591bcf802',defines=['SYNTHESIS','OT_FP_DATA_NORST'],interpretation='edge count from core rst_n port to reset-controlled state; directly reset flops depth1; reset-source registers add edges',reset_controlled_ff_bits_by_depth=dict(sorted(counts.items())),reset_controlled_ff_bits=sum(counts.values()),plain_ff_bits=sum(len(f['Q']) for f in ffs if f['reset'] is None),max_internal_delivery_depth=max(counts,default=0),reset_source_registers=relay,unreached_reset_domains=unreached,ot_rst_relay_instances=sum(v for k,v in instances.items() if k.endswith('ot_rst_relay') or 'ot_rst_relay' in k),release_status='SOURCE_CENSUS; final native RESET binding and timed recovery still required')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['reset_source_registers','unreached_reset_domains']}))
