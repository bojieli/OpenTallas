import json,re,collections,sys
A=json.load(open("/srv/opentallas-scratch3/claude/hbm-bind-3/w1/asbuilt.json"))["modules"]
B=json.load(open("/srv/opentallas-scratch3/claude/hbm-bind-4/te/asbuilt.json"))["modules"]
def base(n): return re.sub(r"^\$paramod\$[0-9a-f]+\\|^\$paramod\\","",n).split("\\")[0]
def strip(n):
    n=re.sub(r"\$\d+$","",n)
    n=re.sub(r"/srv/[^ ]*?/(rtl|physical)/","",n)
    n=re.sub(r":\d+(\.\d+-\d+\.\d+)?","",n)
    return n
def ty(t): return base(t) if t.startswith("$paramod") else t
def sig(m):
    c=collections.Counter()
    for cn,x in m.get("cells",{}).items():
        c[(strip(cn) if cn.startswith("$") else re.sub(r"\[\d+\]","[]",cn),ty(x["type"]),tuple(sorted((k,len(v)) for k,v in x["connections"].items())) if x["type"].startswith("$") else "")]+=1
    return c
# group paramods by base name; compare sets of signatures
ga,gb=collections.defaultdict(dict),collections.defaultdict(dict)
for n,m in A.items(): ga[base(n)][n]=m
for n,m in B.items(): gb[base(n)][n]=m
print("frozen bases",len(ga),"tip bases",len(gb))
print("only frozen base",sorted(set(ga)-set(gb)))
print("only tip base",sorted(set(gb)-set(ga)))
for b in sorted(set(ga)&set(gb)):
    sa=sorted(json.dumps(sorted(map(str,sig(m).items()))) for m in ga[b].values())
    sb=sorted(json.dumps(sorted(map(str,sig(m).items()))) for m in gb[b].values())
    pa=sorted(json.dumps(sorted((k,v["direction"],len(v["bits"])) for k,v in m.get("ports",{}).items())) for m in ga[b].values())
    pb=sorted(json.dumps(sorted((k,v["direction"],len(v["bits"])) for k,v in m.get("ports",{}).items())) for m in gb[b].values())
    fl=[]
    if pa!=pb: fl.append("PORTS")
    if sa!=sb: fl.append("CELLS")
    if fl:
        # cells diff for the first pair if counts equal
        da=collections.Counter(); db=collections.Counter()
        for m in ga[b].values(): da+=sig(m)
        for m in gb[b].values(): db+=sig(m)
        x=(da-db); y=(db-da)
        print(b,fl,len(ga[b]),len(gb[b]),"cells -",sum(x.values()),"+",sum(y.values()),"| e.g.-",[str(k)[:70] for k in list(x)[:2]],"+",[str(k)[:70] for k in list(y)[:2]])
        if "PORTS" in fl and pa and pb and len(pa)==len(pb):
            for u,v in zip(pa,pb):
                if u!=v:
                    U,V=set(map(tuple,json.loads(u))),set(map(tuple,json.loads(v)))
                    print("    ports -",sorted(U-V)[:6],"+",sorted(V-U)[:6]); break
