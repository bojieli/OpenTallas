# DIE-KV-41: clk_clk_phy sink census on a placed SD kit odb (geometry only). args: odb out.json
import sys, json, collections, odb
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron()
bt = blk.findBTerm("clk_clk_phy") or blk.findBTerm("clk_clk_phy[0]")
if bt is None: print("BTERMS", [b.getName() for b in blk.getBTerms() if "phy" in b.getName()][:20]); sys.exit(0)
net = bt.getNet()
sinks = []; seen = set(); stack = [net]; bufs = 0
while stack:
    n = stack.pop()
    if n.getId() in seen: continue
    seen.add(n.getId())
    for it in n.getITerms():
        if it.isOutputSignal(): continue
        inst = it.getInst(); m = inst.getMaster(); mn = m.getName()
        if m.isBlock():
            sinks.append(("macro", inst.getName(), it.getMTerm().getName(), *[v/u for v in it.getAvgXY()[1:]])); continue
        if it.getMTerm().getName() in ("CLK",):
            x, y = inst.getLocation(); sinks.append(("ff", inst.getName(), mn, x/u, y/u)); continue
        if mn.startswith(("BUF", "INV", "CKINV", "HB")):
            bufs += 1
            for o in inst.getITerms():
                if o.isOutputSignal() and o.getNet(): stack.append(o.getNet())
        else:
            x, y = inst.getLocation(); sinks.append(("other", inst.getName(), mn + "/" + it.getMTerm().getName(), x/u, y/u))
ff = [s for s in sinks if s[0] == "ff"]
rq = [s for s in ff if "rq_d" in s[1]]
mac = [s for s in sinks if s[0] == "macro"]
bb=bt.getBBox(); print("port", bt.getName(), bb.xMin()/u, bb.yMin()/u, "bufs_on_tree", bufs)
print("sinks", collections.Counter(s[0] for s in sinks), "macro", mac[:3])
print("rq_d ffs", len(rq), "x", (min(s[3] for s in rq), max(s[3] for s in rq)) if rq else None, "y", (min(s[4] for s in rq), max(s[4] for s in rq)) if rq else None)
# bins of ff positions (rim strips)
b = collections.Counter()
for s in ff:
    x, y = s[3], s[4]
    b["E" if x > 1866 else ("S" if y < 54 else ("N" if y > 1026 else ("W" if x < 17.3 else "IN")))] += 1
print("ff by strip", dict(b))
hx = collections.Counter(int(s[3] // 200) * 200 for s in ff if s[4] < 54); print("S strip x-hist", sorted(hx.items()))
hy = collections.Counter(int(s[4] // 100) * 100 for s in ff if s[3] > 1866); print("E strip y-hist", sorted(hy.items()))
# rx_flit macro pins
mi = [i for i in blk.getInsts() if i.getMaster().isBlock()][0]
rx = []
for it in mi.getITerms():
    if it.getMTerm().getName().startswith("rx_flit"):
        ok, x, y = it.getAvgXY(); rx.append((x/u, y/u))
print("rx_flit pins", len(rx), "x", (min(p[0] for p in rx), max(p[0] for p in rx)), "y", (min(p[1] for p in rx), max(p[1] for p in rx)))
others = collections.Counter(s[2] for s in sinks if s[0] == "other"); print("other sinks", others.most_common(5))
json.dump(dict(sinks=sinks, rx=rx), open(sys.argv[2], "w"))
