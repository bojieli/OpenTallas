import json,sys,re,collections
r=json.load(open(sys.argv[1]))
print([k for k in r.keys()][:40])
rows=[]
for e in r['errors']:
  m=re.match(r'UNPLANNED (\S+) -> (\S+): (\d+) as-built crossing bits with no plan lane path \((\d+) b planned',str(e))
  if m: rows.append((m.group(1),m.group(2),int(m.group(3)),int(m.group(4))))
print('pairs',len(rows),'bits',sum(x[2] for x in rows))
if len(sys.argv)>2:
  base={}
  for e in json.load(open(sys.argv[2]))['errors']:
    m=re.match(r'UNPLANNED (\S+) -> (\S+): (\d+)',str(e))
    if m: base[(m.group(1),m.group(2))]=int(m.group(3))
  new=[x for x in rows if (x[0],x[1]) not in base]; chg=[(x,base[(x[0],x[1])]) for x in rows if (x[0],x[1]) in base and base[(x[0],x[1])]!=x[2]]
  gone=[k for k in base if k not in {(x[0],x[1]) for x in rows}]
  print('base pairs',len(base),'bits',sum(base.values()),'| new',len(new),sum(x[2] for x in new),'| changed',len(chg),'| gone',len(gone),gone[:10])
  for x in sorted(new,key=lambda x:-x[2]): print(' NEW',x)
  for x,b0 in chg: print(' CHG',x,'was',b0)
