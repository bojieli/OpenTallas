import json,sys
D="/srv/opentallas-scratch2/claude/"
P={"U4f":D+"hbm-kits-1-1027/planU4f","U5e_r":D+"codex-hbm-1027/planU5e_r","U6b":D+"hbm-mu-quad-6-1027/planU6b"}
V={k:{} for k in P}
CE={}
for k,p in P.items():
    for v in json.load(open(D+f"hbm-cores-r7/views/views_{p.split('/')[-1]}.json"))["view_list"]:
        V[k].setdefault(v["module"],[]).append((tuple(v["outline_um"]),v["pins_sha256"][:12],v["placed"],tuple(v["blockers"])))
    ce=json.load(open(p+"/clock_entries.json"))
    d={}
    for part in ce.values():
        if isinstance(part,dict):
            for e in part.values():
                if isinstance(e,dict) and e.get("module"):
                    d.setdefault(e["module"],set()).add((tuple(e["xy_um"]),tuple(e["island_um"]),e.get("port")))
    CE[k]=d
mods=sorted(set().union(*[set(v) for v in V.values()]))
out=[]
for m in mods:
    a=[sorted(V[k].get(m,[])) for k in P]; c=[sorted(CE[k].get(m,set())) for k in P]
    pin_st = "SAME" if a[0]==a[1]==a[2] else ("U5=U6" if a[1]==a[2] else "CHG")
    ce_st = "SAME" if c[0]==c[1]==c[2] else ("U5=U6" if c[1]==c[2] else "CHG")
    out.append(dict(module=m,pins=pin_st,entry=ce_st,ntab=len(a[2]),nentry_forms=len(c[2]),u6=[list(map(str,x)) for x in a[2]]))
    print(f"{m:55s} pins={pin_st:6s} entry={ce_st:6s} tables={len(a[2])} entryforms={len(c[2])} {a[2][0][:2] if a[2] else ''} blk={a[2][0][3] if a[2] else ''}")
json.dump(out,open(D+"hbm-cores-r7/views/cmp.json","w"),indent=1)
