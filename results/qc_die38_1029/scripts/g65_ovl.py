import json,sys
from collections import defaultdict,Counter
d=json.load(open(sys.argv[1]))
cells=d['cells']
grid=defaultdict(list)
B=5000
leaf=[c for c in cells if 'CKINVDC' in c['master']]
print('leaf-master cells',len(leaf),Counter(c['master'] for c in leaf))
for i,c in enumerate(cells):
  x0,y0,x1,y1=c['bbox_dbu']
  for gx in range(x0//B,x1//B+1):
    for gy in range(y0//B,y1//B+1): grid[(gx,gy)].append(i)
ov=set()
for k,l in grid.items():
  for a in range(len(l)):
    A=cells[l[a]]['bbox_dbu']
    for b in range(a+1,len(l)):
      Bb=cells[l[b]]['bbox_dbu']
      if A[0]<Bb[2] and Bb[0]<A[2] and A[1]<Bb[3] and Bb[1]<A[3]: ov.add((min(l[a],l[b]),max(l[a],l[b])))
ovleaf=[p for p in ov if 'CKINVDC' in cells[p[0]]['master'] or 'CKINVDC' in cells[p[1]]['master']]
print('overlap pairs',len(ov),'involving leaf cells',len(ovleaf))
for p in list(ovleaf)[:5]: print(cells[p[0]]['inst'][-40:],cells[p[0]]['bbox_dbu'],cells[p[1]]['inst'][-40:],cells[p[1]]['bbox_dbu'])
offrow=sum(1 for c in leaf if c['bbox_dbu'][1]%270); offsite=sum(1 for c in leaf if c['bbox_dbu'][0]%54)
print('leaf off-row',offrow,'off-site',offsite)
print('leaf orient',Counter(c.get('orient') for c in leaf))
print('leaf soft_OBS hosts',Counter(len(c.get('soft_OBS_hosts',[]))>0 for c in leaf))
