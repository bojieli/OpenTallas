import odb, sys, collections
db=odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); b=db.getChip().getBlock()
rows=b.getRows(); site_w=None; ys=set()
for r in rows:
    ys.add(r.getOrigin()[1]); site_w=r.getSite().getWidth()
new=[i for i in b.getInsts() if i.getName().startswith("start_provider/ot_leaf_")]
bad_row=[i.getName() for i in new if i.getBBox().yMin() not in ys]
x0=min(r.getOrigin()[0] for r in rows)
bad_site=[i.getName() for i in new if (i.getBBox().xMin()-x0)%site_w]
# overlaps of new cells vs any placed std cell (bucketed)
B=collections.defaultdict(list); T=5000
def k(bb):
    return [(x,y) for x in range(bb.xMin()//T,bb.xMax()//T+1) for y in range(bb.yMin()//T,bb.yMax()//T+1)]
for i in b.getInsts():
    if i.getMaster().isBlock() or not i.isPlaced(): continue
    bb=i.getBBox()
    for kk in k(bb): B[kk].append(i)
ov=set()
for i in new:
    bb=i.getBBox()
    for kk in k(bb):
        for j in B[kk]:
            if j.getName()==i.getName(): continue
            c=j.getBBox()
            if bb.xMin()<c.xMax() and c.xMin()<bb.xMax() and bb.yMin()<c.yMax() and c.yMin()<bb.yMax(): ov.add((i.getName(),j.getName()))
print("LEAF_LEGAL new", len(new), "off_row", len(bad_row), "off_site", len(bad_site), "overlap_pairs", len(ov), list(ov)[:5])
