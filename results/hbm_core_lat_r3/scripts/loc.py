import json,collections,sys,re
plan=sys.argv[1]
d=json.load(open(f"{plan}/die_plan.json")); pt=d["partition_types"]
inst=collections.Counter(p["type"] for p in d["partitions"])
cand={s:json.load(open(f"/tmp/cand_{s}.json")) for s in ("NW","NE")}
where=collections.defaultdict(set); cnt=collections.Counter(); outl={}
for k,t in pt.items():
    for h in t.get("hard_cores",[]):
        where[h["module"]].add(k); cnt[h["module"]]+=inst.get(k,1); outl[h["module"]]=h.get("outline_um")
ucnt=collections.Counter(h["module"] for c in cand.values() for h in c["hard_cores"])
items=[l.rstrip("\n").split("\t") for l in open("/tmp/needskit.tsv")]
for it,kind,rep in items:
    base=re.sub(r"_[0-9a-f]{12}$","",it)
    m=base if base in where else None
    if not m:
        c=[x for x in where if x.startswith(base) or base.startswith(x)]
        m=c[0] if len(c)==1 else (",".join(c[:3]) if c else None)
    w=sorted(where.get(m,[])) if m in where else []
    print(f"{it}\t{kind}\t{m}\t{cnt.get(m,0)}\t{ucnt.get(m,0)}\t{outl.get(m)}\t{','.join(w)[:120]}")
