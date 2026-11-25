import json,sys,re,collections
p=json.load(open(sys.argv[1])); pt=p["partition_types"]
TV,TH=48.18,57.55  # tracks/um M2-M8 from auto_geom
def box(c):
    x,y=c["origin_um"]; w,h=c["outline_um"]
    return x,y,x+w,y+h
out=[]
for n,t in sorted(pt.items()):
    W,H=t["outline_um"]; bx=[box(c) for c in t.get("hard_cores",[])]
    if not bx: continue
    bw={b["name"]:b["width"] for b in t.get("buses",[])}
    lanes=[]
    for s in t.get("internal_stations",[]):
        nm=(s.get("launch","") or "").replace("bus ","").strip(); w=bw.get(nm)
        if w is None:
            c=(s.get("conn","") or "").replace("bus:",""); w=bw.get(c,1)
        pts=[s.get("from_um")]+s.get("regs_um",[])+[s.get("to_um")]
        lanes.append((w,[q for q in pts if q],nm or s.get("conn","")))
    for s in t.get("ft_slots",[]):
        pts=list(s.get("regs_um",[]))
        lanes.append((s.get("width",1),pts,s.get("name")))
    def streets(lo_hi_list,L):
        iv=sorted(lo_hi_list); free=[]; cur=0.0
        for a,b in iv:
            if a>cur: free.append((cur,a))
            cur=max(cur,b)
        if cur<L: free.append((cur,L))
        return free
    worst=(0,None)
    for axis in (0,1):   # axis 1: horizontal cuts y=c (vertical demand); axis 0: vertical cuts x=c
        L=(W,H)[1-axis]; T=(TH,TV)[axis]
        cuts=sorted(set([ (b[axis]+b[axis+2])/2 for b in bx if (b[2]-b[0])*(b[3]-b[1])>20000]))
        for c in cuts:
            blk=[(b[1-axis],b[3-axis]) for b in bx if b[axis]<c<b[axis+2]]
            fr=streets(blk,L)
            dem=collections.Counter(); who=collections.defaultdict(collections.Counter)
            for w,pts,nm in lanes:
                for a,b in zip(pts,pts[1:]):
                    lo,hi=sorted((a[axis],b[axis]))
                    if lo<c<hi:
                        m=(a[1-axis]+b[1-axis])/2
                        k=min(range(len(fr)),key=lambda i:0 if fr[i][0]<=m<=fr[i][1] else min(abs(m-fr[i][0]),abs(m-fr[i][1])))
                        dem[k]+=w; who[k][nm]+=w
            for k,d in dem.items():
                wd=fr[k][1]-fr[k][0]; cap=wd*T*0.6
                r=d/cap if cap>0 else 99
                if r>worst[0]: worst=(r,("V" if axis else "H",round(c),[round(x) for x in fr[k]],d,round(cap),who[k].most_common(3)))
    out.append((n,worst))
for n,(r,d) in out:
    if d: print("%-34s %.2f %s cut=%s street=%s bits=%d cap60=%d %s"%(n,r,d[0],d[1],d[2],d[3],d[4],' '.join('%s:%d'%(a[:38],b) for a,b in d[5])))
