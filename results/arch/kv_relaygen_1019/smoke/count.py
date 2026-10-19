import json,collections
m=json.load(open('post.json'))['modules']['top']
drv={}; 
for cn,c in m['cells'].items():
  for p,b in c['connections'].items():
    if c['port_directions'][p]=='output':
      for x in b: drv[x]=cn
ld=collections.Counter()
for cn,c in m['cells'].items():
  for p,b in c['connections'].items():
    if c['port_directions'][p]=='input':
      for x in set(b):
        if 'relay' in drv.get(x,'') or 'rst_n' in drv.get(x,''): ld[drv[x]]+=1
for k,v in sorted(ld.items()): print('SMOKE', k, v)
print('SMOKE flops', sum(1 for c in m['cells'].values() if 'DFF' in c['type']))
