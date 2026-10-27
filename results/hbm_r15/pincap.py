import json,sys
d=json.load(open(sys.argv[1]))
for r in d["records"]:
    if r["verdict"]=="PASS": continue
    W,H=r["outline_um"]; out=[]; fix="RESPREAD"
    for f,n in r["counts_by_face"].items():
        if f=="area": continue
        L=(H if f in "EW" else W)-2*8.64
        dens=n/L
        tag="ok" if dens<=5.5 else "OVER"
        if tag=="OVER": fix="OUTLINE/FACE"
        out.append(f"{f}:{n}/{L:.0f}um={dens:.2f}{'' if tag=='ok' else '!'}(pk{r['peaks'].get(f,{}).get('pins_per_um','-')})")
    print(fix, r["kind"], r["type"], r.get("instances"), r["outline_um"], " ".join(out))
