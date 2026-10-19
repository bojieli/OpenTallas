import json,collections
from pathlib import Path
j=json.loads(Path('out/sta_names.json').read_text())['modules']['hidx_coupon1'];aliases=collections.defaultdict(list)
for n,v in j['netnames'].items():
 if n.startswith('on.'):
  for i,b in enumerate(v['bits']):aliases[b].append(n+'['+str(i)+']')
r={}
for n in ['_06086_','_05925_','_05928_','_05930_','_05936_','_05937_','_05938_','_05939_','_05950_','_05952_','_05958_','_05960_','_05968_','_04542_','_04548_']:
 c=j['cells'][n];r[n]=dict(master=c['type'],pins={p:dict(bits=bs,source_aliases=[a for b in bs for a in aliases[b]])for p,bs in c['connections'].items()})
b=j['cells']['_04542_']['connections']['B'][0]
for n,c in j['cells'].items():
 if any(c.get('port_directions',{}).get(p)=='output' and b in bs for p,bs in c['connections'].items()):
  r['worst_slew_driver']=dict(name=n,master=c['type'],pins={p:dict(bits=bs,source_aliases=[a for x in bs for a in aliases[x]])for p,bs in c['connections'].items()})
Path('out/critical_path_ownership.json').write_text(json.dumps(r,indent=2)+'\n')
