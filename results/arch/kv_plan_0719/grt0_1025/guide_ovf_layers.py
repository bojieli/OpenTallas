import sys,collections,json
# per-(gcell,layer) net count from route.guide vs 25%-share capacity; overflow attributed to partitions + net families
f=sys.argv[1]; plan=sys.argv[2]; G=10.8
cap={'M4':int(G/0.048*0.25),'M5':int(G/0.048*0.25),'M6':int(G/0.064*0.25),'M7':int(G/0.064*0.25)}
d=json.load(open(plan)); parts=[]
for p in d["partitions"]:
    w,h=d["partition_types"][p["type"]]["outline_um"]
    if p.get("orient","R0") in ("R90","R270"): w,h=h,w
    x,y=p["origin_um"]; parts.append((x,y,x+w,y+h,p["name"],p["type"]))
def part_of(x,y):
    for a,b,c,e,n,t in parts:
        if a<=x<c and b<=y<e: return n
    return "-"
cnt={L:collections.Counter() for L in cap}; who={L:collections.defaultdict(collections.Counter) for L in cap}
net=None
for line in open(f):
    s=line.split()
    if len(s)==1 and s[0] not in '()': net=s[0]; continue
    if len(s)!=5 or s[4] not in cap: continue
    x0,y0,x1,y1=[float(v)/1000 for v in s[:4]]; L=s[4]
    i0,i1=int(x0/G+1e-6),max(int(x0/G+1e-6),int(x1/G-1e-6)); j0,j1=int(y0/G+1e-6),max(int(y0/G+1e-6),int(y1/G-1e-6))
    fam=net.split('[')[0]
    for i in range(i0,i1+1):
        for j in range(j0,j1+1): cnt[L][(i,j)]+=1; who[L][(i,j)][fam]+=1
res={}
for L in cap:
    over=collections.Counter(); bypart=collections.Counter(); byfam=collections.Counter(); tot=0; hot=0
    for (i,j),n in cnt[L].items():
        if n>cap[L]:
            o=n-cap[L]; tot+=o; hot+=1; x,y=(i+.5)*G,(j+.5)*G
            over[(round(x/500)*0.5,round(y/500)*0.5)]+=o; bypart[part_of(x,y)]+=o
            for fm,k in who[L][(i,j)].most_common(3): byfam[fm]+=o*k/n
    res[L]=dict(cap=cap[L],est_overflow=tot,hot_gcells=hot,bins=over.most_common(15),parts=bypart.most_common(15),fams=[(a,round(b)) for a,b in byfam.most_common(15)])
    print(L,json.dumps(res[L]))
json.dump(res,open(sys.argv[3],"w"),indent=1)
