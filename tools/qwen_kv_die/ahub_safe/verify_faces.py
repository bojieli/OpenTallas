#!/usr/bin/env python3
"""Independent checker of emitted native state/Boolean and fanout relation.
Reads Yosys-reparsed native source, not generator's claimed port wiring.
Compares every real native cell's entire input tuple, including CLK/SETN/RESETN
and every D-feedback mux input, with original modulo transparent polarity.
"""
import collections,hashlib,json,sys
from pathlib import Path
origpath,newpath,certpath=sys.argv[1:4]
o=json.loads(Path(origpath).read_text())['modules']['qkd_ahub_static_dw_safe']
n=json.loads(Path(newpath).read_text())['modules']['qkd_ahub_static_dw_safe_native']
p=json.loads(Path(certpath).read_text());assert hashlib.sha256(Path(origpath).read_bytes()).hexdigest()==p['input_sha256']
assert {x:(v['direction'],len(v['bits']))for x,v in o['ports'].items()}=={x:(v['direction'],len(v['bits']))for x,v in n['ports'].items()}
def trans(c):return c['type'].startswith(('INV','BUF','HB'))
def drivers(m):
 d={}
 for name,c in m['cells'].items():
  for port,bs in c['connections'].items():
   if c['port_directions'][port]=='output':
    for i,b in enumerate(bs):
     assert b not in d,('multiple drivers',name,port,b)
     d[b]=(name,port,i)
 return d
od,nd=drivers(o),drivers(n)
relations={x['emitted']:x['origin']for x in p['emitted']}
assert len(relations)==len(p['emitted'])
assert set(relations.values())=={k for k,v in o['cells'].items()if not trans(v) and v['type']!='$scopeinfo'}
assert set(relations)=={k for k,v in n['cells'].items()if not trans(v) and v['type']!='$scopeinfo'}
input_o={b:('input',name,i)for name,v in o['ports'].items()if v['direction']=='input' for i,b in enumerate(v['bits'])}
input_n={b:('input',name,i)for name,v in n['ports'].items()if v['direction']=='input' for i,b in enumerate(v['bits'])}
def resolve(m,d,inputs,b,translate,seen=()):
 if not isinstance(b,int):return (('constant',b),0)
 if b in inputs:return (inputs[b],0)
 assert b in d,('undriven',b)
 name,port,i=d[b];c=m['cells'][name]
 if trans(c):
  assert name not in seen
  ib=[x for po,bs in c['connections'].items()if c['port_directions'][po]=='input'for x in bs];assert len(ib)==1
  root,inv=resolve(m,d,inputs,ib[0],translate,seen+(name,))
  return root,inv^int(c['type'].startswith('INV'))
 return (('cell',translate(name),port,i),0)
def ro(b):return resolve(o,od,input_o,b,lambda x:x)
def rn(b):return resolve(n,nd,input_n,b,relations.__getitem__)
state=0;input_checks=0
for name,oname in relations.items():
 a=o['cells'][oname];b=n['cells'][name]
 assert a['type']==b['type'],('master mismatch',name)
 assert a['parameters']==b['parameters'],('parameters mismatch',name)
 assert a['port_directions']==b['port_directions']
 if a['type'].startswith('DFF'):state+=1
 for po,bs in a['connections'].items():
  assert len(bs)==len(b['connections'][po])
  if a['port_directions'][po]=='input':
   for ob,nb in zip(bs,b['connections'][po]):assert ro(ob)==rn(nb),('input/state/reset/clock relation',name,po,ro(ob),rn(nb));input_checks+=1
for po,v in o['ports'].items():
 if v['direction']=='output':
  for a,b in zip(v['bits'],n['ports'][po]['bits']):assert ro(a)==rn(b),('output relation',po)
# No unrecorded initialization on any retained or duplicated state. Real source
# init bits must be preserved at the corresponding output polarity.
def initmap(m):
 z={}
 for v in m['netnames'].values():
  if 'init'in v.get('attributes',{}):
   for b,x in zip(v['bits'],v['attributes']['init'][::-1]):
    if x!='x':
     assert b not in z or z[b]==x;z[b]=x
 return z
oi,ni=initmap(o),initmap(n)
assert not oi and not ni,'explicit native initialization needs supported source mapping'
# Count through arbitrary INV/BUF chains to every first nontransparent input.
loads=collections.defaultdict(list)
for name,c in n['cells'].items():
 if trans(c):continue
 for po,bs in c['connections'].items():
  if c['port_directions'][po]=='input':
   for b in bs:
    rt,pol=resolve(n,nd,input_n,b,lambda x:x);loads[rt].append((name,po))
for po,v in n['ports'].items():
 if v['direction']=='output':
  for b in v['bits']:
   rt,pol=resolve(n,nd,input_n,b,lambda x:x);loads[rt].append(('PORT',po))
viol=[];clock=0;resetmax=0
for rt,ls in loads.items():
 if rt==('input','ck',0):clock=len(ls);continue
 if rt[0]=='constant':continue
 if rt==('input','rst_n',0):resetmax=len(ls)
 if len(ls)>32:viol.append((rt,len(ls)))
assert not viol,('buffer-transparent fanout violations',viol)
# A public registered output owns a unique physical source FF identity.
# Input endpoints are recorded separately: hs_start deliberately has 23 kept
# same-edge copies, and must not be collapsed to the historical single role.
output_owners={};boundary=[]
for po,v in n['ports'].items():
 if v['direction']!='output':continue
 for bi,b in enumerate(v['bits']):
  rt,pol=resolve(n,nd,input_n,b,lambda x:x)
  if rt[0]=='constant':
   boundary.append({'port':po,'bit':bi,'constant':rt[1],'polarity':pol});continue
  assert rt[0]=='cell' and n['cells'][rt[1]]['type'].startswith('DFF'),('output lacks register',po,bi,rt)
  assert rt not in output_owners,('merged public face FF identities',output_owners.get(rt),(po,bi),rt)
  output_owners[rt]=(po,bi)
  boundary.append({'port':po,'bit':bi,'ff':rt[1],'pin':rt[2],'polarity':pol,'origin':relations[rt[1]]})
counts=collections.Counter(x['type']for x in n['cells'].values())
result={'schema':'opentallas.ahub.independent_native_correspondence.v1','status':'PASS','native_state_cells':state,'native_input_relations_checked':input_checks,'original_cells':len(o['cells']),'emitted_cells':len(n['cells']),'original_port_bits':sum(len(x['bits'])for x in o['ports'].values()),'clock_sinks':clock,'reset_input_sinks':resetmax,'nonclock_buffer_transparent_max':max(len(ls)for rt,ls in loads.items()if rt!=('input','ck',0)and rt[0]!='constant'),'violations':viol,'cell_counts':dict(counts),'source_sha256':p['output_sha256'],'init_scope':'all mapped state has no explicit initialization; copied state relation established on common first capture or asynchronous reset; invalid startup payload is not qualified','physical_qualified':False,'output_boundary_ledger':boundary,'distinct_registered_output_identities':len(output_owners)}
print(json.dumps(result,indent=2))
