import json,sys,collections
s=json.load(open(sys.argv[1])); e=json.load(open(sys.argv[2]))["rows"]; kinds=sys.argv[3].split(",")
cs=s["cell_sites"]
g={}
for k,v in cs.items(): g.setdefault(v["group"],[]).append(v)
def gx(i):
    v=g[i][0]; return (v["origin_um"][0]+v["w"]/2, v["origin_um"][1], v["kind"])
V=[]  # vertical M9 nets
for n in s["nets"]:
    if n["layer"]=="M9" and n["load"].startswith("g"):
        a=gx(int(n["drv"][1:])); b=gx(int(n["load"][1:]))
        V.append((a[0],min(a[1],b[1]),max(a[1],b[1]),n["namespace"]+n["ndr"]))
C=collections.Counter(); seen=set()
for r in e:
    c=cs[r["name"][6:]]
    if c["kind"] not in kinds or r["name"] in seen: continue
    seen.add(r["name"])
    x=c["origin_um"][0]+c["w"]/2; y=c["origin_um"][1]
    hit=sorted({v[3] for v in V if abs(v[0]-x)<4 and v[1]-3<=y<=v[2]+3})
    C[(c["kind"],r["detail"][:16],tuple(hit))]+=1
for k,v in C.most_common(20): print(v,k)
