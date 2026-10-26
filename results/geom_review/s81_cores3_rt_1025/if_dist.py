# S81-CORES3/RT: macro interface-register distance census (odb only): for every signal pin of every block macro, walk
# through buffers/inverters (<=4 levels) to the nearest flop; Manhattan distance pin->flop origin, plus the pin edge.
import odb, json, os, collections
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); blk = db.getChip().getBlock(); dbu = blk.getDbUnitsPerMicron()
def isff(i): return i.getMaster().getName().startswith(("DFF","SDF","ASYNC_DFF"))
def isbuf(i): return not i.getMaster().isBlock() and not isff(i) and not i.getMaster().getName().startswith("TIE")
import glob, re
PINS = {}
for f in glob.glob("/work/macros/*.lef"):
    mac = None; cur = None
    for ln in open(f):
        t = ln.split()
        if t[:1] == ["MACRO"]: mac = t[1]; PINS[mac] = {}
        elif t[:1] == ["PIN"]: cur = t[1]
        elif t[:1] == ["RECT"] and cur and cur not in PINS[mac]: PINS[mac][cur] = ((float(t[1])+float(t[3]))/2, (float(t[2])+float(t[4]))/2)
        elif t[:1] == ["END"] and len(t) > 1 and t[1] == cur: cur = None

out = []
for m in blk.getInsts():
    if not m.getMaster().isBlock(): continue
    bb = m.getBBox(); x0,y0,x1,y1 = bb.xMin()/dbu, bb.yMin()/dbu, bb.xMax()/dbu, bb.yMax()/dbu
    for it in m.getITerms():
        n = it.getNet()
        if n is None or n.getSigType() in ("POWER","GROUND","CLOCK"): continue
        mt = it.getMTerm(); nm = mt.getName()
        if nm in ("clk","CLK"): continue
        # pin location: centre of the first geometry
        lx0, ly0 = m.getLocation(); r = PINS[m.getMaster().getName()].get(nm); px, py = (lx0/dbu + r[0], ly0/dbu + r[1]) if r else (None, None)
        if px is None: continue
        edge = min([(px-x0,"W"),(x1-px,"E"),(py-y0,"S"),(y1-py,"N")])[1]
        best = None; front = [n]; seen=set()
        for dep in range(4):
            nxt=[]
            for net in front:
                if net is None or net.getName() in seen: continue
                seen.add(net.getName())
                drv = None
                for t in net.getITerms():
                    i = t.getInst()
                    if i.getName()==m.getName(): continue
                    if isff(i):
                        lx, ly = i.getLocation(); d = abs(lx/dbu-px)+abs(ly/dbu-py)
                        if best is None or d < best[0]: best = (d, i.getName(), dep)
                    elif isbuf(i):
                        for t2 in i.getITerms():
                            if t2.getNet() is not None and t2.getNet().getName()!=net.getName() and t2.getSigType() not in ("POWER","GROUND"): nxt.append(t2.getNet())
            if best: break
            front = nxt
        if n.getName().startswith(("TIE","net")) and best is None: pass
        out.append(dict(macro=m.getName(), pin=nm, dir="out" if it.isOutputSignal() else "in", edge=edge, x=round(px,2), y=round(py,2),
                        dist=None if best is None else round(best[0],2), reg=None if best is None else best[1], levels=None if best is None else best[2]))
json.dump(out, open(os.environ["OUT"],"w"), indent=0)
c = collections.defaultdict(list)
for r in out: c[(r["macro"], r["edge"], r["dir"])].append(r["dist"])
for k,v in sorted(c.items()):
    vv = sorted(d for d in v if d is not None)
    print("IFDIST", k, "n", len(v), "unmatched", len(v)-len(vv), "max", vv[-1] if vv else None, "p90", vv[int(.9*len(vv))] if vv else None, ">20um", sum(d>20 for d in vv))
