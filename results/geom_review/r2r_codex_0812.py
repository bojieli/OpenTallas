import os,odb,json,sys
sys.setrecursionlimit(1000000)
db=odb.dbDatabase.create(); odb.read_db(db,os.environ['ODB']); b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
ffs=[]; fi={}; xy=[]
for i in b.getInsts():
 if 'DFF' in i.getMaster().getName().upper():
  fi[i.getId()]=len(ffs);ffs.append(i);bb=i.getBBox();xy.append(((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u))
inputs={};drivers={};dnets=[]
for i in b.getInsts():
 iid=i.getId();ins=[];outs=[]
 for t in i.getITerms():
  n=t.getNet()
  if not n or n.getSigType() in ['POWER','GROUND']:continue
  if t.getIoType()=='INPUT':
   ins.append(n.getId())
   if iid in fi and t.getMTerm().getName() in ['D','D0','D1']:dnets.append((fi[iid],n.getId()))
  elif t.getIoType()=='OUTPUT':outs.append(n.getId())
 if iid in fi:
  for nid in outs:drivers[nid]=[(True,fi[iid])]
 elif i.getMaster().getType()!='BLOCK':
  for nid in outs:drivers.setdefault(nid,[]).extend((False,x) for x in ins)
memo={};active=set();loops=0
def sources(n):
 global loops
 if n in memo:return memo[n]
 if n in active:loops+=1;return 0
 active.add(n);bits=0
 for isff,k in drivers.get(n,[]):bits|=(1<<k) if isff else sources(k)
 active.remove(n);memo[n]=bits;return bits
pairs=0;over=0;worst=[];maxd=0
for dst,n in dnets:
 bits=sources(n);pairs+=bits.bit_count();x,y=xy[dst]
 while bits:
  bit=bits&-bits;src=bit.bit_length()-1;bits-=bit
  d=abs(x-xy[src][0])+abs(y-xy[src][1]);maxd=max(maxd,d)
  if d>405:over+=1;worst.append((round(d,3),ffs[src].getName(),ffs[dst].getName()))
print('R2R_RESULT '+json.dumps(dict(flops=len(ffs),data_pins=len(dnets),pairs=pairs,max_manhattan_um=round(maxd,3),over405=over,combinational_loops=loops,worst=sorted(worst,reverse=True)[:10])))
