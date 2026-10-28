import json,re,sys
P=json.load(open(sys.argv[1])); lat=P["latency"]["lanes"]; lanes={l["id"]:l for l in P["lanes"]}
bl=json.load(open(sys.argv[2]))["buses"]
runs={n:{r["id"]:r for r in json.load(open(f))["rows"]} for n,f in (a.split("=") for a in sys.argv[3:])}
res={}
for a in bl:
    Ls=" ".join(a["leaves"]); m=re.search(r"(vport_\w+?)\.(vq\d)",Ls)
    if not m: continue
    for c in bl:
        if c["src"]==a["dst"] and c["dst"]==a["src"] and re.search(r"slg_\w+\.rsp"," ".join(c["leaves"])) and c["dst"].startswith("pv"):
            st=sum(lat[l].get("stations",0)+lat[l].get("boundary",0)+lat[l].get("fixed",0) for l in (a["lane"],c["lane"]))
            row=dict(bound=9+a["bound_stages"]+c["bound_stages"], fixed=9+st)
            for n,R in runs.items():
                xs=[R[p] for l in (a["lane"],c["lane"]) for p in lanes[l]["ports"] if p in R]
                row[n]=9+st+sum(x["lat"] for x in xs); row["n_x"]=len(xs); row[n+"_lp"]=sum(1 for x in xs if not x["on_feed"])
            row["floor"]=9+st+4*row["n_x"]//2*1
            res.setdefault(m.group(1),[]).append(row)
out={}
for vp,rs in sorted(res.items()):
    out[vp]={k:max(r[k] for r in rs) for k in rs[0]}
    print(vp,out[vp])
json.dump(out,open(sys.argv[-1].split("=")[1].rsplit("/",1)[0]+"/vport_rt_est.json","w"),indent=1)
