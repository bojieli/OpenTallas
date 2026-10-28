import json,sys
p=json.load(open(sys.argv[1]))
for tn in sys.argv[2].split(","):
    v=p["partition_types"][tn]; hc=v.get("hard_cores",[])
    hcinst={h["inst"] for h in hc}; par={h.get("parent_instance") for h in hc if h.get("parent_instance")}
    hcm={h["module"] for h in hc}
    rows=[]
    for c in v.get("contents",[]):
        k = "hard" if (c.get("inst") in hcinst or c.get("module") in hcm) else ("parent_of_cut" if c.get("inst") in par else "glue")
        rows.append((k,c.get("cells",0),c.get("inst"),c.get("module"),c.get("status")))
    tot={}
    for r in rows: tot[r[0]]=tot.get(r[0],0)+r[1]
    print(tn, tot, "n_lef_hc", sum(1 for h in hc if h.get("lef")), "/", len(hc))
    for r in sorted([r for r in rows if r[0]=="glue"], key=lambda r:-r[1])[:8]: print("  ", r)
