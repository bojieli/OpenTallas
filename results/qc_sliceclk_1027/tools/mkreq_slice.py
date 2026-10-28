# per-slice domain requirement: +K only on ports whose src/dst lie in different slice domains (HUB = all non-slice partitions)
import json,collections,re,sys
K=int(sys.argv[1]); mode=sys.argv[2] if len(sys.argv)>2 else "slice"
bg=json.load(open("bind_v7/bus_groups.json"))
ep=set(m["lane"] for g in bg["landing"] for m in g["members"])
X=json.load(open("qc_cross.json"))["rows"]
def dom(p):
    m=re.match(r"(?:c|sl)_([WE]\d)_",p)
    if not m: return "HUB"
    s=m.group(1)
    if mode=="half": return s[0]          # one domain per half (W/E)
    if mode=="pair": return s[0]+str(int(s[1])//2)  # slice pairs
    return s
pp=collections.Counter(); xb=0; xr=[]
for r in X:
    if r["lane"] in ep and dom(r["src"])!=dom(r["dst"]):
        pp[r["lane"]]+=1; xb+=r["bits"]; xr.append(r)
add={l:K*n for l,n in pp.items()}
json.dump(dict(case=f"sliceclk_{mode}_k{K}",scope=f"QC-SLICECLK per-{mode} clock domains; landed only at inter-domain ports, K per port",source_table_sha256="fallback-land-1026 qc_cross.json (plan 54a1aeb5 ports on v7 bind lanes)",crossings=sum(pp.values()),ports=sum(pp.values()),bits=xb,lane_added_cycles=add),open(f"req_{mode}_k{K}.json","w"))
json.dump(xr,open(f"cross_{mode}.json","w"),indent=0)
print(mode,K,"lanes",len(add),"ports",sum(pp.values()),"bits",xb,"added",sum(add.values()))
