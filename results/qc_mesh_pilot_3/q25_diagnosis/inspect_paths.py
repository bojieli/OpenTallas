import json,math,collections,sys
from pathlib import Path
R=Path(sys.argv[1])
for trial in ('trial24','trial25'):
 t=json.load(open(R/trial/'tree.json')); n={int(k):v for k,v in t['nodes'].items()}; nb={int(k):v for k,v in t['node_buf'].items()}; a={}; taps={}
 for l in open(R/trial/'arr_TT.txt'):
  v=l.split()
  if v[0] in ('T','N'): a[v[1]]=list(map(float,v[2:]))
 ts=[q for q in t['taps'] if q['part']=='c_E2_bf_10' and not q['tap'].startswith('clk_c')]
 ts.sort(key=lambda q:a[q['port']][0]);print('\n',trial,'spread',a[ts[-1]['port']][0]-a[ts[0]['port']][0])
 for q in (ts[0],ts[-1]):
  i=q['node'];chain=[]
  while n[i].get('dme'):
   nd=n[i];p=nd.get('parent'); pa=n.get(p,{}); nm=nb[i];pnm=nb.get(p);snake=nd.get('snake');route=nd.get('route');pts=[(pa.get('x',nd['x']),pa.get('y',nd['y']))]+(snake or [])+[(nd['x'],nd['y'])]
   if route and not snake:pts=route
   seg=[abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(pts,pts[1:])];L=sum(seg);st=len(seg) if snake else max(2,math.ceil(L/250)+(math.ceil(L/250)%2))
   meas=(a[nm][0]-a[pnm][0]) if pnm in a else None
   chain.append(dict(id=i,buf=nm,L=round(L,1),st=st,kids=len(nd.get('kids',[])),snake=bool(snake),route=bool(route),actual=round(meas,2) if meas else None,xy=[nd['x'],nd['y']]))
   if p is None:break
   i=p
  print(q['tap'],a[q['port']], '\n', json.dumps(list(reversed(chain)),indent=1))
