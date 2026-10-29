#!/usr/bin/env python3
import sys;sys.path.insert(0,"tools")
import geom_rules as G,collections,json,os
D=G.Design('geom.tsv');seq=[i for i,c in D.cells.items() if c[0]=='S'];idx={k:n for n,k in enumerate(seq)}
comb={i for i,c in D.cells.items() if c[0] in 'BLK'};ind=collections.Counter();succ=collections.defaultdict(list);st=collections.defaultdict(int);caps=collections.defaultdict(int)
for i in comb:
 for n in D.drives.get(i,[]):
  for k,j,ck in D.nets[n][2]:
   if k=='i' and not ck and j in comb:succ[i].append(j);ind[j]+=1
for i in seq:
 for n in D.drives.get(i,[]):
  for k,j,ck in D.nets[n][2]:
   if k=='i' and not ck:
    if j in idx:caps[j]|=1<<idx[i]
    elif j in comb:st[j]|=1<<idx[i]
q=collections.deque(i for i in comb if ind[i]==0)
while q:
 i=q.popleft()
 for n in D.drives.get(i,[]):
  for k,j,ck in D.nets[n][2]:
   if k=='i' and not ck:
    if j in idx:caps[j]|=st[i]
    elif j in comb:st[j]|=st[i]
 for j in succ[i]:
  ind[j]-=1
  if not ind[j]:q.append(j)
edges=[]
for j,mask in caps.items():
 while mask:
  b=mask&-mask;mask-=b;i=b.bit_length()-1
  if i!=idx[j]:edges.append((i,idx[j]))
# Exact face-boundary registers (all buffer depths <=8); preserve existing pin placement.
face=set();face_ports={}
def mark(i,p):
 face.add(i);face_ports.setdefault(i,[]).append([p["x"],p["y"],p["name"]])
for p in D.pins:
 if p['sig'] in ('CLOCK','POWER','GROUND') or G.CLOCK_PIN_RE.search(p['name']):continue
 n=D.pin_net.get(p['k'])
 if n is None:continue
 if p['io']=='OUTPUT':
  for _ in range(9):
   dr=D.nets[n][1]
   if not dr or dr[0]!='i':break
   i=dr[1]
   if i in idx:mark(idx[i],p);break
   if D.kind(i)!='B' or not D.cell_in.get(i):break
   n=D.cell_in[i][0][0]
 else:
  front={n};seen={n}
  for _ in range(9):
   nf=set()
   for n in front:
    for k,i,ck in D.nets[n][2]:
     if k!='i' or ck:continue
     if i in idx:mark(idx[i],p)
     elif D.kind(i)=='B':nf.update(D.drives.get(i,[]))
   front=nf-seen;seen|=nf
xy=[G.ctr(D.cells[i]) for i in seq];macros=[c[2:6] for c in D.cells.values() if c[0]=='M']
json.dump(dict(cells=[D.cells[i][6] for i in seq],xy=xy,edges=edges,face=sorted(face),face_ports=face_ports,macros=macros),open('graph.json','w'))
print('GRAPH',len(seq),'FF',len(edges),'EDGES',len(face),'FACE',flush=True)
