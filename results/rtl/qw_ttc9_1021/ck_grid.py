import sys,collections
rows=[]
for l in open(sys.argv[1]):
  if l.startswith('OT_CKX'):
    p=l.split(); rows.append((int(p[1]),float(p[2]),int(p[3])/1000 if p[3]!='-' else -1,int(p[4])/1000 if p[4]!='-' else -1,p[5],p[6] if len(p)>6 else ''))
for sel,name in ((1,'boundary'),(0,'internal')):
  rs=[r for r in rows if r[0]==sel and not r[5]]
  if not rs: continue
  print(name,len(rs),'arr %.0f..%.0f'%(min(r[1] for r in rs),max(r[1] for r in rs)))
  g=collections.defaultdict(list)
  for r in rs: g[(int(r[2]//86.4),int(r[3]//86.4))].append(r[1])
  ys=sorted({k[1] for k in g},reverse=True); xs=sorted({k[0] for k in g})
  print('      '+' '.join('x%5.0f   '%(x*86.4) for x in xs))
  for y in ys:
    print('y%4.0f '%(y*86.4)+' '.join(('%4.0f-%-4.0f'%(min(g[(x,y)]),max(g[(x,y)])) if (x,y) in g else '    -    ') for x in xs))
print([r for r in rows if r[5]])
