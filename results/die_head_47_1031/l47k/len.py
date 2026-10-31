import sys, odb
from openroad import Design, Tech
t=Tech(); t.readLef("/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef"); t.readLef("/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef")
d=Design(t); d.readDb(sys.argv[1]); b=d.getBlock(); fh=open(sys.argv[2],"w")
for n in b.getNets():
  xs=[];ys=[]
  for it in n.getITerms():
    ok,x,y=it.getAvgXY()
    if ok: xs.append(x); ys.append(y)
  for bt in n.getBTerms():
    bb=bt.getBBox(); xs.append((bb.xMin()+bb.xMax())//2); ys.append((bb.yMin()+bb.yMax())//2)
  if len(xs)<2: continue
  w=n.getWire(); L=w.getLength() if w else -1
  fh.write("L %s %d %d %d\n"%(n.getName(),len(xs),max(xs)-min(xs)+max(ys)-min(ys),L))
