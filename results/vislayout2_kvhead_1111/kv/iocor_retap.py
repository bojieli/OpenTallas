# VISLAYOUT2 io_cor_v1 RF1: load-balanced clock taps (same 40 tap IDs, positions only).
# Recursive coordinate bisection of the placed clk flops (attempt_11 3_place) into K equal-count clusters; each tap
# sits at its cluster's coordinate-wise median; tap IDs are matched to clusters by least total displacement (greedy).
import json,sys,math
plan,geom,out=sys.argv[1],sys.argv[2],sys.argv[3]
p=json.load(open(plan)); t=p["partition_types"]["kv3_io_cor_v1"]; c=t["clock"]; W,H=t["outline_um"]
taps=[["clk"]+list(c["tap_um"])]+[[a["name"]]+list(a["xy"]) for a in c["added_taps"]]
pts=[]
for l in open(geom):
    if l.startswith("C\t") and "DFF" in l:
        f=l.split("\t"); n=f[8]
        if "u_ring.s_d" in n or "sd_c" in n: continue      # fclk ring storage: not on the clk taps
        pts.append(((float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2))
def rcb(P,k):
    if k==1: return [P]
    xs=[q[0] for q in P]; ys=[q[1] for q in P]
    ax=0 if (max(xs)-min(xs))>=(max(ys)-min(ys)) else 1
    P=sorted(P,key=lambda q:q[ax]); k1=k//2; m=round(len(P)*k1/k)
    return rcb(P[:m],k1)+rcb(P[m:],k-k1)
cl=rcb(pts,len(taps))
med=lambda v: sorted(v)[len(v)//2]
cen=[(med([q[0] for q in s]),med([q[1] for q in s])) for s in cl]
pairs=sorted((math.dist(taps[i][1:],cen[j]),i,j) for i in range(len(taps)) for j in range(len(cen)))
ui,uj,m={},set(),{}
for d,i,j in pairs:
    if i in ui or j in uj: continue
    ui[i]=j; uj.add(j)
g=lambda v,s,lo,hi: min(max(round(round(v/s)*s,3),lo),hi)
moves={}
for i,(n,x,y) in enumerate(taps):
    j=ui[i]; s=cl[j]; cx,cy=cen[j]
    nx,ny=g(cx,0.54,8.64,W-8.64),g(cy,0.27,8.64,H-8.64)
    dm=max(math.dist((nx,ny),q) for q in s)
    moves[n]=[[x,y],[nx,ny],len(s),round(dm)]
c["tap_um"]=moves["clk"][1]
for a in c["added_taps"]: a["xy"]=moves[a["name"]][1]
print("flops",len(pts),"per tap",min(v[2] for v in moves.values()),max(v[2] for v in moves.values()),"reach max",max(v[3] for v in moves.values()))
for n,v in sorted(moves.items(),key=lambda q:-math.dist(*q[1][:2])): print(n,[round(z) for z in v[0]],"->",[round(z) for z in v[1]],v[2],"reach",v[3])
json.dump(p,open(out,"w"),indent=1)
json.dump({"kv3_io_cor_v1":{"clock.tap_um/added_taps.xy":{n:v[:2] for n,v in moves.items()}}},open(out+".delta.json","w"),indent=1)
