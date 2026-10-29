# geometric check: other-net M8/M9 shapes vs ck_mesh shapes (overlap / gap < NDR spacing 0.32)
import odb, sys
db = odb.dbDatabase.create()
odb.read_db(db, sys.argv[1])
blk = db.getChip().getBlock()
def shapes(n):
    out=[]
    w=n.getWire()
    if not w: return out
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath()
    while it.getNextPath(p):
        ps = odb.dbWirePathShape()
        while it.getNextShape(ps):
            s=ps.shape
            if s.isVia(): continue
            L=s.getTechLayer().getName()
            if L in ("M8","M9"): out.append((L,s.xMin(),s.yMin(),s.xMax(),s.yMax()))
    return out
mesh=shapes(blk.findNet("ck_mesh"))
bad=0
for n in blk.getNets():
    nn=n.getName()
    if nn=="ck_mesh": continue
    for (L,x0,y0,x1,y1) in shapes(n):
        for (L2,a0,b0,a1,b1) in mesh:
            if L!=L2: continue
            dx=max(a0-x1,x0-a1,0); dy=max(b0-y1,y0-b1,0)
            # parallel-run: vertical M9 -> gap in x with y overlap
            if L=="M9" and dy==0 and dx<320 or L=="M8" and dx==0 and dy<320:
                ov = (L=="M9" and x1>a0 and x0<a1) or (L=="M8" and y1>b0 and y0<b1)
                run = (min(y1,b1)-max(y0,b0)) if L=="M9" else (min(x1,a1)-max(x0,a0))
                print("HIT %s %s %s gap_um=%.3f run_um=%.2f overlap=%s shape=(%.3f %.3f %.3f %.3f)"%(sys.argv[1].split('/')[-2],nn,L,(dx if L=="M9" else dy)/1000,run/1000,ov,x0/1000,y0/1000,x1/1000,y1/1000))
                bad+=1
print("SUMMARY",sys.argv[1],"hits",bad)
