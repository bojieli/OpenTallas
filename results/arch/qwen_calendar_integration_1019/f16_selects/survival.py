import json,re,collections
from pathlib import Path
j=json.load(open('native.json'))['modules']['qfd_dv_typed_witness_control'];rev={};drivers={}
for n,c in j['cells'].items():
 out=[b for p,bs in c['connections'].items() if c['port_directions'].get(p)=='output' for b in bs]
 inp=[b for p,bs in c['connections'].items() if c['port_directions'].get(p)=='input' for b in bs]
 if re.match(r'^(BUF|INV|HB)[x0-9_]',c['type'],re.I):
  for b in out:rev[b]=inp
 elif re.search('DFF',c['type'],re.I):
  for p,bs in c['connections'].items():
   if c['port_directions'].get(p)=='output':
    for k,b in enumerate(bs):drivers[b]=f'{n}/{p}[{k}]'
loads={l.split('\t')[0]:int(l.split('\t')[2]) for l in Path('native_census.tsv').read_text().splitlines()[1:]}
def root(b):
 seen=set();q=[b];r=set()
 while q:
  x=q.pop()
  if x in seen:continue
  seen.add(x)
  if x in drivers:r.add(drivers[x])
  q.extend(rev.get(x,[]))
 return sorted(r)
ans={}
for kind,pat in [('select',r'template_select\['),('publish',r'publish_enable\['),('counter',r'cycle\[')]:
 nets={n:v['bits'] for n,v in j['netnames'].items() if re.search(pat,n)}
 roots={x for bs in nets.values() for b in bs for x in root(b)}
 ans[kind]={'vectors':len(nets),'alias_bits':sum(map(len,nets.values())),'distinct_ff_roots':len(roots),'max_transparent_loads':max([loads[r] for r in roots],default=0),'roots':{r:loads[r] for r in sorted(roots)}}
Path('survival.json').write_text(json.dumps(ans,indent=2)+'\n')
print(json.dumps({k:{a:b for a,b in v.items() if a!='roots'} for k,v in ans.items()}))
