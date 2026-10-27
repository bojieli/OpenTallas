import json,collections,hashlib,os,sys
plan=sys.argv[1]; cand={s:json.load(open(f"{sys.argv[2]}/cand_{s}.json")) for s in ("NW","NE")}
d=json.load(open(f"{plan}/die_plan.json")); pt=d["partition_types"]
inst=collections.Counter(p["type"] for p in d["partitions"])
def pinsig(f):
    p=f"{plan}/{f}"
    if not os.path.exists(p): return ("MISSING",0,None)
    j=json.load(open(p)); pins=j if isinstance(j,list) else j.get("pins",[])
    clk=tuple((q["name"],q["layer"],q["x"],q["y"]) for q in pins if q["name"].lower().startswith("clk"))
    sig=hashlib.sha256(json.dumps(sorted((q["name"],q["layer"],q["x"],q["y"]) for q in pins)).encode()).hexdigest()[:8]
    top=max((q["layer"] for q in pins),default=None)
    return (sig,len(pins),top,clk[:3])
for m in sys.argv[3].split(","):
    b=[];u=[]
    for k,t in pt.items():
        for h in t.get("hard_cores",[]):
            if h["module"]==m: b+= [(k,h.get("outline_um"),pinsig(h.get("pins_file","")))]*inst.get(k,1)
    for s,c in cand.items():
        for h in c["hard_cores"]:
            if h["module"]==m: u.append((s,h["outline_um"],pinsig(h["pins_file"])))
    bs=collections.Counter(x[2][0] for x in b); us=collections.Counter(x[2][0] for x in u)
    outl=set(tuple(x[1]) for x in b)|set(tuple(x[1]) for x in u)
    parts=sorted(set(x[0] for x in b))
    print(f"{m}: B2o inst {len(b)} parts {parts} | U-hub inst {len(u)} | outlines {outl} | pinmaps B2o {len(bs)} U {len(us)} same={set(bs)==set(us) if u else 'n/a'} | npins {b[0][2][1] if b else '-'} top {b[0][2][2] if b else '-'} clk {b[0][2][3] if b else '-'}")
