import argparse,json,collections
import odb
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);a=p.parse_args()
d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock()
def rect(inst,sh):
 sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(inst.getOrient())];x,y=inst.getOrigin();xs=sorted([x+sx*sh.xMin(),x+sx*sh.xMax()]);ys=sorted([y+sy*sh.yMin(),y+sy*sh.yMax()]);return[xs[0],ys[0],xs[1],ys[1]]
macros=[];supplies=[]
for i in b.getInsts():
 if str(i.getMaster().getType()) not in ['BLOCK','BLOCK_BLACKBOX']:continue
 pins=[]
 for it in i.getITerms():
  mt=it.getMTerm()
  if str(mt.getSigType()) not in ['POWER','GROUND']:continue
  shs=[]
  for mp in mt.getMPins():
   for sh in mp.getGeometry():
    l=sh.getTechLayer()
    if l and l.getRoutingLevel()>0:shs.append([l.getName(),*rect(i,sh)])
  pins.append(dict(pin=mt.getName(),net=it.getNet().getName() if it.getNet() else None,kind=str(mt.getSigType()),shapes_dbu=shs))
 bb=i.getBBox();macros.append(dict(inst=i.getName(),master=i.getMaster().getName(),bbox_dbu=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()],orient=str(i.getOrient()),pins=pins))
for n in b.getNets():
 if str(n.getSigType()) not in ['POWER','GROUND']:continue
 for sw in n.getSWires():
  for sh in sw.getWires():
   if sh.isVia():continue
   l=sh.getTechLayer()
   if l and l.getRoutingLevel()>=7:supplies.append([n.getName(),l.getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()])
vs={}
for v in d.getTech().getVias():
 if v.getName()=='VIA78':vs[v.getName()]=[[sh.getTechLayer().getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()] for sh in v.getBoxes()]
x=dict(source=a.odb,dbu=b.getDbUnitsPerMicron(),macros=macros,existing_supplies=supplies,vias=vs)
json.dump(x,open(a.out,'w'),separators=(',',':'))
print(json.dumps(dict(macros=len(macros),terms=sum(len(m['pins']) for m in macros),masters=dict(collections.Counter(m['master'] for m in macros)),pin_layers=dict(collections.Counter(s[0] for m in macros for p in m['pins'] for s in p['shapes_dbu'])),vias=vs),indent=2))
