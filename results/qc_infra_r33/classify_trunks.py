import json,sys,collections
s=json.load(open(sys.argv[1])); e=json.load(open(sys.argv[2]))["rows"]
cs=s["cell_sites"]
g0={}
for k,v in cs.items():
    if v["group"] not in g0: g0[v["group"]]=(k,v)
def gxy(g):
    k,v=g0[g]; return (v["origin_um"][0]+v["w"]/2, v["origin_um"][1], v["kind"], k)
H=[]
for n in s["nets"]:
    if not n["load"].startswith("g"): continue
    a=gxy(int(n["drv"][1:])); b=gxy(int(n["load"][1:]))
    if abs(b[0]-a[0])>=abs(b[1]-a[1]) and abs(b[0]-a[0])>1:
        H.append((min(a[0],b[0]),max(a[0],b[0]),a[1],n["namespace"]+":"+a[2]+">"+b[2]+":"+n["ndr"],a[3],b[3]))
import bisect
H.sort(key=lambda h:h[2]); ys=[h[2] for h in H]
C=collections.Counter()
for r in e:
    c=cs[r["name"][6:]]; x=c["origin_um"][0]+c["w"]/2; y=c["origin_um"][1]
    i=bisect.bisect_left(ys,y-5.5); tl=[]
    while i<len(H) and H[i][2]<=y+5.5:
        h=H[i]; i+=1
        if h[4]==r["name"][6:] or h[5]==r["name"][6:]: continue
        if h[0]-1<=x<=h[1]+1: tl.append(h[3])
    C[(c["kind"],r["detail"].split(" M")[0][:18],tuple(sorted(tl)))]+=1
for k,v in C.most_common(40): print(v,k)
