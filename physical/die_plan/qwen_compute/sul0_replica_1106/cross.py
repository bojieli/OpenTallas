import odb, os, collections
db = odb.read_db(odb.dbDatabase.create(), os.environ["ODB"]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
L=[34.572,354.252,725.772,1045.452]; H=267.84
cross=collections.Counter(); east=collections.Counter(); names=collections.Counter()
for n in b.getNets():
    if n.getSigType() in ("POWER","GROUND"): continue
    pts=[]
    for it in n.getITerms():
        ok,x,y=it.getAvgXY()
        if ok: pts.append((x/u,y/u))
    for bt in n.getBTerms():
        bb=bt.getBBox(); pts.append(((bb.xMin()+bb.xMax())/2/u,(bb.yMin()+bb.yMax())/2/u))
    if len(pts)<2: continue
    for k,l in enumerate(L):
        below=[p for p in pts if p[1]<=l+0.5]; above=[p for p in pts if p[1]>=l+H-0.5]
        if below and above:
            cross[k]+=1
            # both ends east of x 300 -> straight vertical over macro is the Steiner choice
            if min(p[0] for p in below)>250 and min(p[0] for p in above)>250: east[k]+=1
            if k==2: names[n.getName().split("/")[0][:30]]+=1
print("nets with pins on both sides of lane k:",dict(cross))
print("  of which all pins east of x250 on both sides:",dict(east))
print(names.most_common(8))
