import json,re,collections,sys
d=sys.argv[1]
ev=json.load(open(d+"/ev.json")); P=json.load(open("w/plan_A.json")); st=json.load(open(d+"/street_full.json"))
cnt={r["type"]:r["counts"] for r in st["rows"]}
for r in ev["rows"]:
    hc=[c["inst"].split(".",1)[1] for c in P["partition_types"][r["type"]]["hard_cores"]]
    print(r["type"][4:40],"applied",r["applied"],"links",r["links"],"tviol",r["timing_violations_end"],"stn",r["stations_report"]["need_more_idx"],"street",cnt.get(r["type"]))
    c=collections.Counter(); ex={}
    for t in r["timing_over"]:
        ia=re.match(r"\((\d+|None)",t["a"]).group(1); ib=re.match(r"\((\d+|None)",t["b"]).group(1)
        a=hc[int(ia)] if ia!="None" else "FACE"; b=hc[int(ib)] if ib!="None" else "FACE"
        k=(re.sub(r"\d+","#",a),re.sub(r"\d+","#",b),t["kind"]); c[k]+=1
        if k not in ex or t["len_um"]>ex[k][2]: ex[k]=(a,b,t["len_um"],t["limit_um"],t["bits"])
    for k,v in c.most_common(): print("   ",v,k,ex[k])
c=collections.Counter()
for r in st["rows"]:
    for it in r.get("worst") or []:
        if it.get("kind") in ("sliver","outline_sliver"): continue
        a=it.get("a","").split(".")[-1]; b=it.get("b","").split(".")[-1]
        c[(r["type"][4:26] if "__pv" not in r["type"] else "pv",it["kind"],re.sub(r"\d+","#",a),re.sub(r"\d+","#",b),it.get("gap"),str(it.get("pins")))]+=1
for k,v in sorted(c.items(),key=lambda x:(x[0][0],-x[1])): print(v,k)
