#!/usr/bin/env python3
"""Native endpoint identities and necessary (not sufficient) face reach bounds."""
import collections,hashlib,itertools,json,sys
from pathlib import Path
mp,vp,fp=sys.argv[1:4]
m=json.loads(Path(mp).read_text())['modules']['qkd_ahub_static_dw_safe_native'];v=json.loads(Path(vp).read_text());f=json.loads(Path(fp).read_text())
coords={x['port']:x for x in f['ports']};d={};inputs={b:(p,i)for p,x in m['ports'].items()if x['direction']=='input'for i,b in enumerate(x['bits'])}
for n,c in m['cells'].items():
 for p,bs in c['connections'].items():
  if c['port_directions'][p]=='output':
   for b in bs:d[b]=(n,p)
def root(b):
 seen=set();pol=0
 while b in d:
  n,p=d[b];c=m['cells'][n]
  if not c['type'].startswith(('INV','BUF','HB')):return ('cell',n,p,pol)
  assert n not in seen;seen.add(n);pol^=c['type'].startswith('INV')
  bs=[b for p,bs in c['connections'].items()if c['port_directions'][p]=='input'for b in bs];assert len(bs)==1;b=bs[0]
 if b in inputs:return ('input',*inputs[b],pol)
 return ('constant',b,pol)
def label(p,i):return p+(f'[{i}]'if len(m['ports'][p]['bits'])>1 else '')
ledger=[];owners=collections.defaultdict(list)
for p,x in m['ports'].items():
 if p in ('ck','rst_n'):continue
 for i,b in enumerate(x['bits']):
  name=label(p,i);face=coords[name];eps=[]
  if x['direction']=='output':
   r=root(b)
   if r[0]=='cell':eps=[{'inst':r[1],'pin':r[2],'polarity':r[3]}]
   else:assert r[0]=='constant' and p.startswith('am') and i==1
  else:
   for n,c in m['cells'].items():
    if c['type'].startswith(('INV','BUF','HB')):continue
    for pin,bs in c['connections'].items():
     if c['port_directions'][pin]!='input':continue
     for bb in bs:
      r=root(bb)
      if r[:3]==('input',p,i):eps.append({'inst':n,'pin':pin,'polarity':r[3]})
  assert eps or (p.startswith('am')and i==1),('unregistered boundary',name)
  for e in eps:
   assert m['cells'][e['inst']]['type'].startswith('DFF'),('nonFF boundary',name,e)
   owners[e['inst']].append((name,face['face'],face['xy']))
  ledger.append({'port':name,'direction':x['direction'],'face':face['face'],'xy':face['xy'],'endpoints':eps})
checks=[]
for inst,ps in owners.items():
 distance=max((abs(a[2][0]-b[2][0])+abs(a[2][1]-b[2][1])for a,b in itertools.combinations(ps,2)),default=0)
 checks.append({'inst':inst,'ports':[x[0]for x in ps],'minimum_possible_max_leg_um':distance/2})
assert max(x['minimum_possible_max_leg_um']for x in checks)<=405, 'shared face source violates necessary reach bound'
assert len(owners)==645,(len(owners),'expected623 historical roles +22 start copies')
print(json.dumps({'schema':'opentallas.ahub.face_identity_geometry.v1','status':'PASS','distinct_boundary_ffs':len(owners),'ff_endpoint_occurrences':sum(len(x['endpoints'])for x in ledger),'all_signal_ports':len(ledger),'ledger':ledger,'necessary_reach_checks':checks,'qualified':False,'scope':'Identity and necessary geometric lower bounds only; internal reach, placement, clock/reset phase, and timing remain unqualified.'},indent=2))
