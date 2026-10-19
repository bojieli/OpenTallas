import json,collections,re
from pathlib import Path
j=json.loads(Path('out/sta_names.json').read_text())['modules']['hidx_coupon1'];aliases=collections.defaultdict(list)
for n,v in j['netnames'].items():
 if n.startswith('on.'):
  for i,b in enumerate(v['bits']):aliases[b].append(n+'['+str(i)+']')
reported=set(re.findall(r'(_[0-9]+_)/',''.join(Path('out/'+n).read_text() for n in ('sta3.log','sta_all.log'))))
r={}
for n in sorted(reported):
 c=j['cells'][n];r[n]=dict(master=c['type'],pins={p:dict(bits=bs,source_aliases=[a for b in bs for a in aliases[b]])for p,bs in c['connections'].items()})
assert r
Path('out/critical_path_ownership.json').write_text(json.dumps(r,indent=2)+'\n')
