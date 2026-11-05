import json,collections,re,sys
def load(bl,plan):
    d=json.load(open(bl)); pl=json.load(open(plan))["latency"]["lanes"]
    out=collections.defaultdict(dict)  # (src,dst,leafport) -> max cycles
    for v in d["buses"]:
        s,t=v["src"],v["dst"]
        if not ((("hub" in s) and "_su" in t) or ("_su" in s and "hub" in t)): continue
        cy=pl.get(v["lane"],{}).get("cycles")
        for sb in v["source_bits"]:
            if sb[0]=="leaf": leaf=re.sub(r"__cut_\w+","CUT",str(sb[1])); port=str(sb[2])
            else: leaf=str(sb[0]); port=str(sb[1])
            sl = s if "_su" in s else t
            slc = sl[:5]+sl[-2]  # NW_su2
            cls=(slc, "dn" if "hub" in s else "up", re.sub(r"_(NW|NE)\d?","",leaf)+"."+port)
            out[cls][v["lane"]]=cy
    return out
a=load(*sys.argv[1:3]); b=load(*sys.argv[3:5])
rows=[]
for k in sorted(set(a)|set(b)):
    ma=max([x for x in a.get(k,{}).values() if x is not None],default=None); mb=max([x for x in b.get(k,{}).values() if x is not None],default=None)
    print("\t".join(map(str,k)), ma, mb, (mb-ma) if (ma is not None and mb is not None) else "", sep="\t")
