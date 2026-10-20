import json,collections,sys
m=json.load(open(sys.argv[1]))['modules']; m=m[[k for k in m if k!='gold'][0]] if len(m)>1 else list(m.values())[0]
drv={}
for cn,c in m['cells'].items():
  for p,b in c['connections'].items():
    if c['port_directions'][p]=='output':
      for x in b: drv[x]=cn
ld=collections.Counter()
for cn,c in m['cells'].items():
  for p,b in c['connections'].items():
    if c['port_directions'][p]=='input':
      for x in set(b):
        if x in drv and m['cells'][drv[x]]['type'].startswith('$_DFF') and ('relay' in drv[x] or 'ot_rl' in drv[x] or 'slice' in drv[x]): ld[drv[x]]+=1
for k,v in sorted(ld.items()):
  if v>4: print('SMOKE2 copy', k, v)
print('SMOKE2 max_copy_loads', max(v for v in ld.values()))
