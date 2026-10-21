#!/usr/bin/env python3
"""Plan external controller copies and reconnect their exact scalar ABI.

Uses actual mapped child terminal counts. Reset copies are assigned only within
reviewed ot_host_reset_bank instances with identical clock/async source and the
same two-edge reset contract. Every rebind is recorded. Raw reset is never
exempted from final independent census. This is private source construction,
not cold-reset/equivalence or physical qualification.
"""
import argparse,collections,functools,hashlib,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--abi',type=Path,required=True);p.add_argument('--projection',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--generation',type=Path);p.add_argument('--native',type=Path);p.add_argument('--out',type=Path);p.add_argument('--record',type=Path);a=p.parse_args()
j=json.load(open(a.parent));mods=j['modules'];parent=mods['qkd_hr_ingest_qm'];oldname,old=next((n,c) for n,c in parent['cells'].items() if c['type']=='native_soft');abi=json.load(open(a.abi))['pin_map'];proj={c['new_port']:c for c in json.load(open(a.projection))['changes'] if c['new_port']}
@functools.lru_cache(None)
def weight(typ,pn,i):
 if typ not in mods or not mods[typ].get('cells'):return 1
 m=mods[typ];b=m['ports'][pn]['bits'][i]
 return sum(weight(c['type'],p,k) for c in m['cells'].values() for p,bs in c['connections'].items() if c['port_directions'][p]=='input' for k,v in enumerate(bs) if v==b)
def outer(port,bit):
 if port in proj:
  c=proj[port];return old['connections'][c['port']][c['kept_indices'][0 if bit is None else bit]]
 return old['connections'][port][0 if bit is None else bit]
pinbits={q['pin']:outer(q['port'],q['bit']) for q in abi}
endpoints=collections.defaultdict(list)
for cn,c in parent['cells'].items():
 if cn==oldname:continue
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]!='input':continue
  for i,b in enumerate(bs):
   if isinstance(b,int):endpoints[b].append(dict(cell=cn,port=pn,index=i,loads=weight(c['type'],pn,i)))
if a.generation is None:
 seen=set();plan={}
 for q in abi:
  b=pinbits[q['pin']]
  if q['direction']!='output' or not isinstance(b,int) or b in seen:continue
  seen.add(b);eps=endpoints.get(b,[])
  if not eps:continue
  assert all(e['loads']<=32 for e in eps),('single protected input exceeds native cap',q,eps)
  groups=[];used=0
  for e in eps:
   if not groups or used+e['loads']>32:groups.append([]);used=0
   groups[-1].append(e);used+=e['loads']
  # Dedicate EXTRA copies to all protected loads. Original output may retain
  # an independent top-level consumer and its internal controller fanout.
  plan[q['pin']]=dict(parent_bit=b,copies=len(groups)+1,groups=groups)
 a.plan.write_text(json.dumps(plan,indent=1)+'\n');print('EXTERNAL_OUTPUT_COPY_PLAN',len(plan));raise SystemExit(0)
plan=json.load(open(a.plan));g=json.load(open(a.generation));native=json.load(open(a.native));assert native['status']=='PASS'
loads={x['driver']:x['loads'] for x in native['driver_counts'] if x['driver_role']=='input_port'}
assert g.get('allowed_heavy_inputs')==[]
# Enumerate each reviewed final-stage bank output by its real parent binding.
bank_groups=collections.defaultdict(list);bank_of={};banks=[]
for cn,c in parent['cells'].items():
 if 'ot_host_reset_bank' not in c['type']:continue
 key=(tuple(c['connections']['clk']),tuple(c['connections']['async_rst_n']))
 bits=c['connections']['sync_rst_n'];assert all(isinstance(b,int) for b in bits)
 banks.append(dict(instance=cn,type=c['type'],clock=key[0],async_source=key[1],outputs=bits))
 for b in bits:bank_groups[key].append(b);bank_of[b]=key
hardload={b:sum(e['loads'] for e in es) for b,es in endpoints.items()}
for q in parent['ports'].values():
 if q['direction']=='output':
  for b in q['bits']:
   if isinstance(b,int):hardload[b]=hardload.get(b,0)+1
nextbit=max([0]+[b for m in mods.values() for n in m['netnames'].values() for b in n['bits'] if isinstance(b,int)])+1
def fresh():
 global nextbit
 b=nextbit;nextbit+=1;return b
connections={};dirs={};records=[];seenout=set()
for q in abi:
 pn=q['pin'];b=pinbits[pn];dirs[pn]=q['direction']
 if q['direction']=='input':connections[pn]=[b]
 elif isinstance(b,int) and b not in seenout:connections[pn]=[b];seenout.add(b)
 else:connections[pn]=[fresh()] # preserve existing parent constants/duplicate cut aliases
# Assign every non-clock soft input (and each explicit replica) to its original
# net, except exact stage-equal reviewed bank outputs with measured capacity.
for q in abi:
 if q['direction']!='input':continue
 pn=q['pin'];b=pinbits[pn];n=g.get('port_copies',{}).get(pn,1)
 for k in range(n):
  name=pn if k==0 else f'{pn}__c{k}';amount=loads.get(name,0);chosen=b
  if b in bank_of and amount:
   choices=[v for v in bank_groups[bank_of[b]] if hardload.get(v,0)+amount<=32]
   assert choices,('reset-bank capacity exhausted',name,amount,bank_of[b])
   chosen=min(choices,key=lambda v:hardload.get(v,0));hardload[chosen]=hardload.get(chosen,0)+amount
  elif isinstance(b,int):hardload[b]=hardload.get(b,0)+amount
  connections[name]=[chosen];dirs[name]='input'
  if chosen!=b:records.append(dict(pin=name,original=b,selected=chosen,loads=amount,contract='reviewed two-edge bank; same domain and async assertion'))
for pn,item in plan.items():
 assert g['output_copies'][pn]==item['copies']
 for k,group in enumerate(item['groups'],1):
  name=f'{pn}__c{k}';b=fresh();connections[name]=[b];dirs[name]='output'
  for e in group:parent['cells'][e['cell']]['connections'][e['port']][e['index']]=b
  records.append(dict(pin=name,new_net=b,loads=sum(e['loads'] for e in group),endpoints=group))
parent['cells'][oldname]=dict(hide_name=0,type=g['top'],parameters={},attributes={},port_directions=dirs,connections=connections)
del mods['native_soft']
a.out.write_text(json.dumps(j,separators=(',',':'))+'\n')
@functools.lru_cache(None)
def flop_count(typ):
 if typ.startswith('DFF'):return 1
 if typ not in mods:return 0
 return sum(flop_count(c['type']) for c in mods[typ].get('cells',{}).values())
fixed=[c for c in parent['cells'].values() if c['type']=='qkc_afifo_w1a4s2_1021']
assert len(fixed)==64,('fixed FIFO instances lost',len(fixed))
retention=dict(instances=len(fixed),flops_per_leaf=flop_count('qkc_afifo_w1a4s2_1021'),total_flops=sum(flop_count(c['type']) for c in fixed))
assert retention['total_flops']==4160,('FIFO state was merged',retention)
a.record.write_text(json.dumps(dict(qualified=False,retention=retention,parent_sha256=hashlib.sha256(a.parent.read_bytes()).hexdigest(),abi_sha256=hashlib.sha256(a.abi.read_bytes()).hexdigest(),generation_sha256=hashlib.sha256(a.generation.read_bytes()).hexdigest(),banks=banks,reconnections=records,estimated_mapped_root_loads=sorted([dict(bit=b,loads=n) for b,n in hardload.items() if n>32],key=lambda x:-x['loads']),raw_reset_has_no_exemption=True),indent=1)+'\n')
print('EXACT_SCALAR_RECONNECTION',len(records),'INDEPENDENT_WHOLE_NATIVE_REQUIRED')
