# DIE-KV-33 clock leg check: per CLOCK net, Manhattan driver->sink pin distance (um) from the KV-006 placed source; limit 405.
import json, collections
from openroad import Design, Tech
t=Tech(); d=Design(t); d.readDb("/n/grt/grt.odb"); b=d.getBlock(); D=b.getDbUnitsPerMicron()
def loc(it):
    ok,x,y=it.getAvgXY()
    if ok: return x/D,y/D
    bb=it.getBBox(); return (bb.xMin()+bb.xMax())/2/D,(bb.yMin()+bb.yMax())/2/D
def bloc(bt):
    for p in bt.getBPins():
        bb=p.getBBox(); return (bb.xMin()+bb.xMax())/2/D,(bb.yMin()+bb.yMax())/2/D
rows=[]; kinds=collections.Counter()
for n in b.getNets():
    if n.getSigType()!="CLOCK": continue
    drv=None; sinks=[]
    for it in n.getITerms():
        (drv:=None) if False else None
        if it.isOutputSignal(): drv=("i",it)
        else: sinks.append(("i",it))
    for bt in n.getBTerms():
        if bt.getIoType()=="INPUT": drv=("b",bt)
        else: sinks.append(("b",bt))
    if drv is None or not sinks: kinds["nodrv_or_nosink"]+=1; continue
    dx,dy=loc(drv[1]) if drv[0]=="i" else bloc(drv[1])
    best=(0,None)
    for k,s in sinks:
        sx,sy=loc(s) if k=="i" else bloc(s)
        dd=abs(sx-dx)+abs(sy-dy)
        if dd>best[0]: best=(dd,(s.getInst().getName()+"/"+s.getMTerm().getName()) if k=="i" else s.getName())
    dn=(drv[1].getInst().getMaster().getName()) if drv[0]=="i" else "PORT"
    rows.append((round(best[0],2),n.getName(),dn,len(sinks),best[1]))
rows.sort(reverse=True)
out=dict(nets=len(rows),skipped=dict(kinds),over_405=sum(r[0]>405 for r in rows),over_350=sum(r[0]>350 for r in rows),max=rows[0][0],worst=rows[:15],
 by_driver={k:max(r[0] for r in rows if r[2]==k) for k in set(r[2] for r in rows)})
json.dump(out,open("/w/legs.json","w"),indent=1); print(json.dumps({k:v for k,v in out.items() if k!="worst"})); print(rows[:5])
