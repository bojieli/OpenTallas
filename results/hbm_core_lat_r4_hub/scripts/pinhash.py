# per hard-core module: set of pin-table hashes (sorted name/layer/x/y) in each plan; read-only
import json,hashlib,os,sys,collections
def load(plan):
    d=json.load(open(f"{plan}/die_plan.json")); pt=d.get("partition_types",{})
    inst=collections.Counter(p["type"] for p in d.get("partitions",[]))
    out=collections.defaultdict(lambda: collections.Counter()); outl=collections.defaultdict(set)
    for k,t in pt.items():
        for h in t.get("hard_cores",[]):
            m=h["module"]; f=h.get("pins_file"); n=inst.get(k,0) or 1
            if not f: out[m]["NONE"]+=n; continue
            p=f"{plan}/{f}"
            if not os.path.exists(p): out[m]["MISSING"]+=n; continue
            j=json.load(open(p)); pins=j if isinstance(j,list) else j.get("pins",[])
            sig=hashlib.sha256(json.dumps(sorted((q["name"],q["layer"],round(q["x"],4),round(q["y"],4)) for q in pins)).encode()).hexdigest()[:10]
            out[m][sig]+=n; outl[m].add(tuple(h.get("outline_um") or ()))
    return out,outl
A,Ao=load(sys.argv[1]); 
for pl in sys.argv[2:]:
    B,Bo=load(pl); print("##",sys.argv[1],"vs",pl)
    for m in sorted(set(A)|set(B)):
        a=set(A.get(m,{})); b=set(B.get(m,{}))
        st="IDENTICAL" if a and a==b and "NONE" not in a and "MISSING" not in a and Ao[m]==Bo[m] else ("ONLY_B2o" if not b else ("ONLY_U" if not a else "DIFF"))
        print(f"{st}\t{m}\tB2o={dict(A.get(m,{}))}\tU={dict(B.get(m,{}))}\toutl_same={Ao[m]==Bo[m]}")
