# QC-SLICECLK-2: slice domains split vertically. v2 = split at y 13133 (sl centre), v3 = c-bottom / sl band / c-top.
import json,collections,re,sys
K=int(sys.argv[1]); mode=sys.argv[2]
bg=json.load(open("bind_v7/bus_groups.json"))
ep=set(m["lane"] for g in bg["landing"] for m in g["members"])
X=json.load(open("qc_cross.json"))["rows"]
LOW_SL={"su_c","su_l0","su_l1","fw","fe","sc","stm"}
def dom(p):
    m=re.match(r"(c|sl)_([WE]\d)_(.*)$",p)
    if not m: return "HUB"
    k,s,r=m.groups()
    if k=="c": band="b" if r.startswith("b") else "t"
    elif mode=="v2": band="b" if r in LOW_SL else "t"
    else: band="m"
    if mode=="v2" and k=="sl": pass
    return s+band
pp=collections.Counter(); xb=0; xr=[]; kinds=collections.Counter()
for r in X:
    if r["lane"] in ep and dom(r["src"])!=dom(r["dst"]):
        pp[r["lane"]]+=1; xb+=r["bits"]; xr.append(r); kinds[(dom(r["src"])[2:] or "H",dom(r["dst"])[2:] or "H")]+=1
add={l:K*n for l,n in pp.items()}
json.dump(dict(case=f"sliceclk_{mode}_k{K}",scope=f"QC-SLICECLK-2 per-slice vertical split {mode}; landed only at inter-domain ports, K per port",source_table_sha256="fallback-land-1026 qc_cross.json",crossings=sum(pp.values()),ports=sum(pp.values()),bits=xb,lane_added_cycles=add),open(f"req_{mode}_k{K}.json","w"))
json.dump(xr,open(f"cross_{mode}.json","w"),indent=0)
print(mode,K,"lanes",len(add),"ports",sum(pp.values()),"bits",xb,"added",sum(add.values()),dict(kinds))
