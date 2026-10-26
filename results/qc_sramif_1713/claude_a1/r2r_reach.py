# PATH-QC-SRAMIF2 geometric reg->reg reach census (openroad -python): ODB=... OUT=...json
# For every flop Q, BFS through combinational cells (any depth <=12) to the next flops/macro pins/output ports;
# record Manhattan launch->capture distance. Reports max, p99, count >200/>290/>405 um and worst 20.
import odb,os,json,re,collections
D=odb.dbDatabase.create();odb.read_db(D,os.environ['ODB']);b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
def ff(m):n=m.getName();return 'DFF' in n or 'DHL' in n or 'SDF' in n
def ctr(i):bb=i.getBBox();return ((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u)
res=[]
for i in b.getInsts():
  m=i.getMaster()
  if not ff(m):continue
  q=[t for t in i.getITerms() if t.isOutputSignal() and t.getNet() is not None]
  if not q:continue
  sx,sy=ctr(i);seen=set();front=[t.getNet() for t in q];caps={};d=0
  while front and d<12:
    nxt=[]
    for n in front:
      if n.getName() in seen or n.getSigType()!='SIGNAL':continue
      seen.add(n.getName())
      for bt in n.getBTerms():
        if str(bt.getIoType())=='OUTPUT':
          bb=bt.getBBox();caps['PORT:'+bt.getName()]=((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u)
      for t in n.getITerms():
        if not t.isInputSignal():continue
        j=t.getInst();mj=j.getMaster()
        if j==i and False:continue
        if mj.isBlock():ok,x,y=t.getAvgXY();caps['MACRO:'+j.getName()+'/'+t.getMTerm().getName()]=(x/u,y/u);continue
        if ff(mj):
          if t.getMTerm().getSigType()=='SIGNAL' and t.getMTerm().getName() in ('D',):caps[j.getName()]=ctr(j)
          continue
        for o in j.getITerms():
          if o.isOutputSignal() and o.getNet() is not None:nxt.append(o.getNet())
    front=nxt;d+=1
  for k,(x,y) in caps.items():res.append((abs(x-sx)+abs(y-sy),i.getName(),k))
res.sort(reverse=True);ds=[r[0] for r in res]
out=dict(pairs=len(res),max=ds[0] if ds else 0,p99=ds[len(ds)//100] if ds else 0,gt200=sum(x>200 for x in ds),gt290=sum(x>290 for x in ds),gt405=sum(x>405 for x in ds),worst=[dict(um=round(a,2),launch=b_,capture=c) for a,b_,c in res[:20]])
json.dump(out,open(os.environ['OUT'],'w'),indent=1);print('R2R',{k:v for k,v in out.items() if k!='worst'})
