import odb, os, re, collections
db = odb.read_db(odb.dbDatabase.create(), os.environ["ODB"]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
L=[34.572,354.252,725.772,1045.452]; H=267.84; X0=190.092
def grp(n):
    m=re.match(r"u_bound\.(u_b(?:out|in)_\w+?)/",n.replace("\\",""))
    return m.group(1) if m else None
G=collections.defaultdict(set)
for i in b.getInsts():
    g=grp(i.getName())
    if g:
        for it in i.getITerms():
            n=it.getNet()
            if n and n.getSigType() not in ("POWER","GROUND","CLOCK"): G[g].add(n.getName())
for g in sorted(G):
    cr=collections.Counter(); ex=collections.Counter(); ends=collections.Counter()
    for nn in G[g]:
        n=b.findNet(nn); P=[]
        for it in n.getITerms():
            ok,x,y=it.getAvgXY()
            if ok: P.append((x/u,y/u,it.getInst()))
        for bt in n.getBTerms():
            bb=bt.getBBox(); P.append(((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u,None))
        for k,l in enumerate(L):
            lo=[p for p in P if p[1]<=l+0.5]; hi=[p for p in P if p[1]>=l+H-0.5]
            if lo and hi:
                cr[k]+=1
                if max(p[0] for p in lo+hi)>X0+5: ex[k]+=1
                for p in lo+hi:
                    ends["PORT" if p[2] is None else ("MACRO:"+p[2].getName() if p[2].getMaster().isBlock() else "cell")]+=1
    print(g, "nets",len(G[g]), "straddle lane k:",dict(cr), " with a pin east of x195:",dict(ex), dict(ends))
