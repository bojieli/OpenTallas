import json,sys,collections,re
d=json.load(open(sys.argv[1]))
def grp(p):
    if p in("root",) or p.startswith("vsN"): return "SEAM"
    if p.startswith("PHY"): return "PHY"
    return p[:2] if p[:3] in("NW_","NE_") else p
tot=0; m=collections.Counter(); lanes=collections.defaultdict(int)
for po in d["ports"]:
    s=po["src"]["part"]; t=po["dst"]["part"]; w=po["width"]
    lane=po["id"].rsplit("_",1)[0]
    lanes[lane]=max(lanes[lane],w)
    m[(grp(s),grp(t))]+=w
print("lane bits (max per lane)",sum(lanes.values()),"lanes",len(lanes))
for k,v in sorted(m.items(),key=lambda x:-x[1]): print(k,v)
