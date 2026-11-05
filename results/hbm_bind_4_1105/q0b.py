import json,re,collections
R="/srv/opentallas-scratch3/claude/hbm-bind-4/"
P=json.load(open(R+"tstage/die_plan.json"))
T=P["partition_types"]
m=json.load(open(R+"tip/physical/die_plan/hbm/bind/d44v/inputs/map_recovered.json"))["parts"]
ab=json.load(open(R+"tip/physical/die_plan/hbm/bind/d44v/asbuilt.json"))
scl=ab["sub_core_leaf"]
print({k:v for k,v in list(scl.items()) if "pgp" in k or "selector" in k})
tg=set()
for k,v in m.items():
    if isinstance(v,list) and len(v)==2: tg.add((v[0],v[1]))
g=collections.defaultdict(lambda:[0,0.0,set(),0,[]])
tot=0
for part,tn in (("NW_hub","q_hub_nw"),("NE_hub","q_hub_ne")):
  for c in T[tn]["hard_cores"]:
    n=c["inst"]; w,h=c["outline_um"]; a=w*h/1e6; tot+=a
    bound=(part,n) in tg
    # parent stem: strip __c#/__h/__x suffix
    stem=re.sub(r"__[a-z]+\d*$","",n)
    via=(part,stem) in tg
    cl="BOUND" if bound else ("SUB_OF_BOUND" if via else "NO_LEAF")
    if cl=="NO_LEAF" and "__q0" in n:
        twin=(part,re.sub("__q0","__q1",n)) in tg or (part,re.sub(r"__[a-z]+\d*$","",re.sub("__q0","__q1",n))) in tg
        cl="Q0_DUP_OF_Q1" if twin else "NO_LEAF_Q0"
    if part=="NW_hub":
        k=(cl,re.sub(r"\d+","#",n),c["module"])
        e=g[k]; e[0]+=1; e[1]+=a; e[4].append(c["origin_um"])
cls=collections.defaultdict(lambda:[0,0.0])
for k,e in sorted(g.items()):
    cls[k[0]][0]+=e[0]; cls[k[0]][1]+=e[1]
    if k[0]!="BOUND": print(k[0],e[0],k[1][:44],k[2][:40],round(e[1],4),"mm2",e[4][0])
print(dict(cls),tot/2)
print(T["q_hub_nw"]["outline_um"])
