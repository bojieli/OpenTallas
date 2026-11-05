import json,gzip,sys
def ld(f): return json.load(gzip.open(f) if f.endswith('.gz') else open(f))
a=ld(sys.argv[1]); b=ld(sys.argv[2])
TA,TB=a["partition_types"],b["partition_types"]
hard={t for t,v in TB.items() if v.get("hard")}
pa={p["name"]:(p["type"],p["origin_um"],p.get("orient")) for p in a["partitions"]}; pb={p["name"]:(p["type"],p["origin_um"],p.get("orient")) for p in b["partitions"]}
moved=[n for n in pb if n in pa and pa[n]!=pb[n]]
ch=[]
for t in sorted(set(TA)|set(TB)):
    x,y=TA.get(t),TB.get(t)
    if x==y: continue
    bx={q["name"]:q for q in (x or {}).get("buses",[])}; by={q["name"]:q for q in (y or {}).get("buses",[])}
    sx={q["name"]:q for q in (x or {}).get("ft_slots",[])}; sy={q["name"]:q for q in (y or {}).get("ft_slots",[])}
    ch.append((t, "hard" if t in hard else "soft", f"bus +{len(set(by)-set(bx))} -{len(set(bx)-set(by))} ~{sum(1 for k in set(bx)&set(by) if bx[k]!=by[k])}", f"slot +{len(set(sy)-set(sx))} -{len(set(sx)-set(sy))} ~{sum(1 for k in set(sx)&set(sy) if sx[k]!=sy[k])}"))
print("types changed",len(ch),"hard",sum(1 for c in ch if c[1]=="hard"),"moved partitions",len(moved))
for c in ch: print("\t".join(c))
print("moved:",",".join(moved))
def errs(f):
    d=ld(f); return sorted(x["msg"] for x in d["findings"] if isinstance(x,dict) and x.get("level")=="ERROR")
if len(sys.argv)>4:
    e0=errs(sys.argv[3]); e1=errs(sys.argv[4]); print("G0 base",len(e0),"cand",len(e1),"new",[e for e in e1 if e not in e0],"gone",[e for e in e0 if e not in e1])
