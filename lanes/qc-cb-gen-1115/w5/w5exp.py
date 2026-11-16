import sys,json,copy
sys.path.insert(0,"/srv/opentallas-scratch2/claude/fable-pd-qc-0700")
sys.argv=["x"]
import qft3
Q=qft3.Q
D="/srv/opentallas-scratch2/claude/die-qc-103/r8_s29q103%s.derived.json"
a={m["id"]:m for m in json.load(open(D%"S4Q6BB"))["members"]}
def view(tag="S4Q7CB"):
    return qft3.QView(tag,fix_extra=True)
def tryit(label,v):
    try:
        params,rec=Q.derive(v); print(label,"PASS flops",rec["added_flops_total"])
        return True
    except ValueError as e:
        print(label,"FAIL",str(e)[:90]); return False
def cols(v):
    bad=[]
    for s in Q.SLICES:
        for side in "SN":
            try: Q._column_pads(v,s,side)
            except ValueError: bad.append(s+side)
    return bad
def patch(v,fn):
    for key,ms in v.m.items():
        for m in ms: fn(m)
# which member ids changed (id is not in the QView members; match on lane+sink+source)
b=json.load(open(D%"S4Q7CB"))["members"]
chg={ (m["sink"],m["sink_port"],m["source"],m["lane"]):(m["landed"]-a[m["id"]]["landed"]) for m in b if m["landed"]!=a[m["id"]]["landed"]}
def revert(kind):
    v=view()
    def f(m):
        k=(None,)
    for key,ms in v.m.items():
        for m in ms:
            kk=(key[0],key[1],m.get("source"),m.get("lane"))
            if kk in chg and kind(m["lane"]): m["landed_stages"]-=chg[kk]
    return v
print("baseline bad columns",len(cols(view())))
tryit("7CB as is",view())
v=revert(lambda l:"hc1" in l); print("revert hc1 only: bad cols",len(cols(v))); tryit(" derive",v)
v=revert(lambda l:"hc1" not in l); print("revert cb only: bad cols",len(cols(v))); tryit(" derive",v)
v=revert(lambda l:True); print("revert both: bad cols",len(cols(v))); tryit(" derive",v)
print("changed lanes by group:")
import collections
print(collections.Counter((k[3].split("__")[0].rsplit("_",2)[-2]+"_"+k[3].split("__")[0].rsplit("_",1)[-1] if "hc1" not in k[3] else "hc1", v) for k,v in chg.items()))

print("---- pad experiments (landed +n on sibling lanes, per slice)")
def padset(sel, n_of):
    v=view()
    for key,ms in v.m.items():
        for m in ms:
            l=m.get("lane") or ""
            n=n_of(l) if sel(l) else 0
            if n: m["landed_stages"]+=n
    return v
import re
def base(l): return l.split("__")[0]
# the slice-level delta of the +2/+4 lanes
per = collections.defaultdict(int)
for k,d in chg.items():
    if "hc1" in k[3]: continue
    per[(re.match(r"c_([EW]\d)_",k[3]).group(1), base(k[3]))]=max(per[(re.match(r"c_([EW]\d)_",k[3]).group(1), base(k[3]))],d)
print("cb lane bumps (slice, lane):",dict(per))
def A(l):   # siblings of the bumped lane in the same slice and side get the same bump
    m=re.match(r"c_([EW]\d)_(b|t)(n|f)_(\d\d)",l)
    if not m: return 0
    s,side,nf,q=m.groups()
    bump=per.get((s,f"c_{s}_{side}n_01"),0)
    return bump if (side,nf,q) != ("b","n","01") and q!="01" or (nf=="f") else 0
for name,sel,fn in (
    ("siblings bn_00/10/11 + tn_00/10/11 (near) same bump", lambda l: bool(re.match(r"c_[EW]\d_[bt]n_(00|10|11)",l)), lambda l: per.get((re.match(r"c_([EW]\d)_",l).group(1),f"c_{re.match(r'c_([EW]\d)_',l).group(1)}_{l[l.index('_',2)+1]}n_01"),0)),
    ("all near + far siblings (bn,bf,tn,tf x 00/10/11) same bump", lambda l: bool(re.match(r"c_[EW]\d_[bt][nf]_(00|10|11)",l)), lambda l: per.get((re.match(r"c_([EW]\d)_",l).group(1),f"c_{re.match(r'c_([EW]\d)_',l).group(1)}_{l[l.index('_',2)+1]}n_01"),0)),
    ("all bn/tn/bf/tf lanes of every slice +2", lambda l: bool(re.match(r"c_[EW]\d_[bt][nf]_\d\d",l)), lambda l: 2),
):
    v=padset(sel,fn); print(name,": bad cols",len(cols(v))); tryit("  derive",v)

print("---- which bumped lane group breaks the columns")
def rev(pred):
    v=view()
    for key,ms in v.m.items():
        for m in ms:
            kk=(key[0],key[1],m.get("source"),m.get("lane"))
            if kk in chg and pred(m["lane"],chg[kk]): m["landed_stages"]-=chg[kk]
    return v
for name,pred in (("revert bn_01 only",lambda l,d: "_bn_01" in l),("revert tn_01 only",lambda l,d: "_tn_01" in l),("revert the +4 only",lambda l,d: d==4),("revert +2 cb only (keep +4)",lambda l,d: d==2 and "hc1" not in l)):
    v=rev(pred); b=cols(v); print(name,": bad cols",len(b),b[:6])
# the bumped members: where do they sit
for k,d in list(chg.items())[:0]: pass
for k,d in sorted(chg.items(), key=lambda x:x[0][3])[:0]: print(k,d)
ex=[(k[0].split(".")[0],k[0].split(".")[-1],k[1],k[3],d) for k,d in chg.items() if "hc1" not in k[3]][:6]
for e in ex: print(e)

print("---- equalise the four bcf chain lanes per (slice, side) to their max")
import collections
def equalise(v):
    grp=collections.defaultdict(list)
    for key,ms in v.m.items():
        for m in ms:
            mm=re.match(r"(c16_[EW]\d_\d)\.u_fab\.u_x_(\d)_0$",key[0])
            if mm and key[1]=="b_d" and "bcf" in (m.get("lane") or ""):
                grp[mm.group(1)].append((m,mm.group(2)))
    pads={}
    for g,lst in grp.items():
        t=max(m["landed_stages"] for m,_ in lst)
        for m,c in lst:
            if m["landed_stages"]<t: pads[(m["lane"],g)]=t-m["landed_stages"]; m["landed_stages"]=t
    return pads
v=view(); pads=equalise(v)
print("bad cols",len(cols(v))); ok=tryit("  derive",v)
print("pads (lane, cluster): +n :",len(pads)); 
for k,n in sorted(pads.items())[:40]: print("  ",k,"+%d"%n)
print("sum pad stages x 516 bits ~ flops",sum(pads.values())*516)
json.dump([dict(lane=k[0],cluster=k[1],pad=n) for k,n in sorted(pads.items())],open("/srv/opentallas-scratch2/claude/qc-cb-gen-1115/w5_bcf_pads.json","w"),indent=1)

print("bad after equalise:",cols(v))
for s in ("E0","W5"):
    for side,cl in (("S",0),("N",3)):
        print(s,side,[ (m["lane"].split("__")[-1],m["landed_stages"],m["bound_stages"]) for key,ms in sorted(v.m.items()) for m in ms if key[0].startswith(f"c16_{s}_{cl}.u_fab.u_x_") and key[0].endswith("_0") and key[1]=="b_d" and "bcf" in (m.get("lane") or "")])

print("---- restore the 6BB column relation: pad column c by (max bump - bump_c)")
a_by={ (m["sink"],m["sink_port"],m["source"],m["lane"]):m["landed"] for m in json.load(open(D%"S4Q6BB"))["members"]}
b_all=json.load(open(D%"S4Q7CB"))["members"]
bump=collections.defaultdict(dict)   # cluster -> col -> bump
for m in b_all:
    mm=re.match(r"(c16_[EW]\d_\d)\.u_fab\.u_x_(\d)_0$",m["sink"])
    if mm and m["sink_port"]=="b_d" and "bcf" in m["lane"]:
        k=(m["sink"],m["sink_port"],m["source"],m["lane"])
        bump[mm.group(1)][int(mm.group(2))]=m["landed"]-a_by[k]
v=view(); pads={}
for g,cb in bump.items():
    mx=max(cb.values())
    for c,d in cb.items():
        if mx-d:
            pads[(g,c)]=mx-d
    for key,ms in v.m.items():
        mm=re.match(r"(c16_[EW]\d_\d)\.u_fab\.u_x_(\d)_0$",key[0])
        if mm and mm.group(1)==g and key[1]=="b_d":
            for m in ms:
                if "bcf" in (m.get("lane") or ""): m["landed_stages"]+=mx-cb[int(mm.group(2))]
print("pad entries",len(pads),"stages",sum(pads.values()))
print("bad cols",cols(v)); tryit("  derive",v)
rows=[]
for (g,c),n in sorted(pads.items()):
    ln=[m["lane"] for m in b_all if m["sink"]==f"{g}.u_fab.u_x_{c}_0" and m["sink_port"]=="b_d" and "bcf" in m["lane"]][0]
    rows.append(dict(cluster=g,column=c,lane=ln,pad_stages=n))
json.dump(rows,open("/srv/opentallas-scratch2/claude/qc-cb-gen-1115/w5_bcf_pads.json","w"),indent=1)
print(collections.Counter(r["pad_stages"] for r in rows), rows[:3])
