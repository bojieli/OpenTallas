#!/usr/bin/env python3
"""BUF/INV-transparent terminal-pin census from actual independent native JSON."""
import sys,json,collections,functools,hashlib
j=json.load(open(sys.argv[1]));m=j['modules'][sys.argv[2]];loads=collections.defaultdict(list);drivers={};transparent={};names={}
for n,v in m['netnames'].items():
 for b in v['bits']:
  if isinstance(b,int):names.setdefault(b,n)
for n,c in m['cells'].items():
 ins=[(p,k,b) for p,bs in c['connections'].items() if c['port_directions'][p]=='input' for k,b in enumerate(bs)]
 outs=[(p,k,b) for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for k,b in enumerate(bs)]
 for p,k,b in ins:
  if isinstance(b,int):loads[b].append((n,p,k))
 for p,k,b in outs:
  if isinstance(b,int):drivers[b]=(n,c['type'],p,k)
 if c['type'].startswith(('BUF','INV')):
  assert len(ins)==len(outs)==1,(n,'unmodeled buffer/inverter')
  transparent[n]=outs[0][2]
clocks=set(m['ports']['ck']['bits'])
# Constants propagate only through explicitly modeled BUF/INV cells.
constants={b for b,d in drivers.items() if d[1].startswith(('TIEHI','TIELO'))}
changed=True
while changed:
 changed=False
 for b in tuple(constants):
  for n,p,k in loads[b]:
   if n in transparent and transparent[n] not in constants:constants.add(transparent[n]);changed=True
@functools.lru_cache(None)
def terminals(b,seen=frozenset()):
 assert b not in seen,('transparent cycle',b)
 out=set()
 for n,p,k in loads.get(b,[]):
  if n in transparent:out.update(terminals(transparent[n],seen|{b}))
  else:out.add((n,p,k))
 return frozenset(out)
port_ins={b:(n,k) for n,p in m['ports'].items() if p['direction']=='input' for k,b in enumerate(p['bits'])}
port_outs=collections.defaultdict(list)
for n,p in m['ports'].items():
 if p['direction']=='output':
  for k,b in enumerate(p['bits']):port_outs[b].append((n,k))
rows=[]
for b in set(loads)|set(drivers)|set(port_ins):
 ls=loads.get(b,[])
 d=drivers.get(b,('PORT','PORT','',0));end=terminals(b)
 role='clock' if b in clocks else 'constant' if b in constants else 'top_input' if b in port_ins else 'FF' if d[1].startswith('DFF') else 'macro' if d[1].startswith('ot_sram_') else 'BUF_INV' if d[1].startswith(('BUF','INV')) else 'comb'
 rows.append(dict(bit=b,name=names.get(b),driver=d,role=role,feeds_reset=any(p in ('RESETN','SETN','R','rst_n') for n,p,k in end),direct_loads=len(ls),terminal_loads=len(end),output_ports=port_outs.get(b,[])))
rows.sort(key=lambda x:-x['terminal_loads']);viol=[x for x in rows if x['terminal_loads']>32 and x['role'] not in ('clock','constant')]
owners=[]
for n,p in m['ports'].items():
 if p['direction']!='output':continue
 for k,b in enumerate(p['bits']):
  y=b;parity=0;seen=set()
  while y in drivers and drivers[y][1].startswith(('BUF','INV')):
   assert y not in seen;seen.add(y);dn,dt,dp,dk=drivers[y];c=m['cells'][dn];ins=[z for pn,bs in c['connections'].items() if c['port_directions'][pn]=='input' for z in bs];assert len(ins)==1;parity^=dt.startswith('INV');y=ins[0]
  owners.append(dict(port=n,bit=k,source_bit=y,source_driver=drivers.get(y,('PORT','PORT','',0)),inversion_parity=parity))
print(json.dumps(dict(source_json_sha256=hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),top=sys.argv[2],max=max(x['terminal_loads'] for x in rows if x['role'] not in ('clock','constant')),violations=viol,rows_over24=[x for x in rows if x['terminal_loads']>24],all_roots=rows,output_ownership=owners,roles=collections.Counter(x['role'] for x in rows),qualified=False),indent=2))
