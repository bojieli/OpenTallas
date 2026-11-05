#!/usr/bin/env python3
"""HBM-BIND-4: rename the autoid cells of a tip elab (after DCE, memory_map, fused splice) to the frozen elab's names, so compose
and map keep working.  Match per module by (normalised name, type, port widths), rank by autoid; a net bijection over every cell proves it.
usage: rename.py FROZEN TIP OUT RECEIPT"""
import json,re,sys,collections
F=json.load(open(sys.argv[1]))["modules"]; Tj=json.load(open(sys.argv[2])); T=Tj["modules"]
def base(n): return re.sub(r"^\$paramod\$[0-9a-f]+\\|^\$paramod\\","",n).split("\\")[0]
def strip(n):
    n=re.sub(r"\$\d+$","",n); n=re.sub(r"/srv/[^ ]*?/(rtl|physical)/","",n); n=re.sub(r"(die_plan/hbm/bind/r18h5_bundle/rtl/|physical/die_plan/hbm/bind/r18h5_bundle/rtl/)","",n)
    return re.sub(r":\d+(\.\d+-\d+\.\d+)?","",n)
def ty(t): return base(t) if t.startswith("$paramod") else t
def key(cn,x):
    return (strip(cn),ty(x["type"]),tuple(sorted((k,len(v)) for k,v in x["connections"].items())))
def aid(n):
    m=re.search(r"\$(\d+)$",n); return int(m.group(1)) if m else -1
def ln(x):
    m=re.search(r":(\d+)\.(\d+)",str(x.get("attributes",{}).get("src","")))
    return (int(m.group(1)),int(m.group(2))) if m else (0,0)
ga,gb=collections.defaultdict(list),collections.defaultdict(list)
for n,m in F.items(): ga[base(n)].append((n,m))
for n,m in T.items(): gb[base(n)].append((n,m))
ren={}; rep=collections.OrderedDict(); bad=[]
pairs=[]
for b in gb:
    if b not in ga: rep[b]="only_tip"; continue
    A=[x for x in ga[b] if x[1].get("cells")]; B=[x for x in gb[b] if x[1].get("cells")]
    if not B: continue
    if len(A)!=len(B): rep[b]=f"variants {len(A)} vs {len(B)}"
    # pair variants by cell-key multiset
    def ms(m): return collections.Counter(key(c,x) for c,x in m["cells"].items())
    used=set()
    for tn,tm in B:
        best=None
        for fn,fm in A:
            if fn in used: continue
            d=sum(((ms(fm)-ms(tm))+(ms(tm)-ms(fm))).values())
            if best is None or d<best[0]: best=(d,fn,fm)
        if best is None: continue
        used.add(best[1]); pairs.append((tn,best[1],best[0]))
        ka,kb=collections.defaultdict(list),collections.defaultdict(list)
        for c,x in best[2]["cells"].items(): ka[key(c,x)].append(c)
        for c,x in tm["cells"].items(): kb[key(c,x)].append(c)
        for k,cs in kb.items():
            fs=sorted(ka.get(k,[]),key=lambda c:(ln(best[2]["cells"][c]),aid(c))); cs=sorted(cs,key=lambda c:(ln(tm["cells"][c]),aid(c)))
            if len(fs)!=len(cs): bad.append((tn[:60],str(k[0])[:80],k[1][:30],len(fs),len(cs)))
            for c,f in zip(cs,fs):
                if c!=f: ren[(tn,c)]=f
        if best[0]: rep[tn]=f"diff {best[0]}"
# apply
n=0
for tn,tm in T.items():
    if not tm.get("cells"): continue
    new={}
    for c,x in tm["cells"].items():
        f=ren.get((tn,c),c)
        if f in new: raise SystemExit(f"collision {tn} {f}")
        new[f]=x; n+= f!=c
    tm["cells"]=new
# bijection proof by module
biji=[]
for tn,fn,d in pairs:
    tm=T[tn]; fm=F[fn]; fw={}; bw={}; err=0
    for c,x in tm["cells"].items():
        y=fm["cells"].get(c)
        if y is None: continue
        for p,bits in x["connections"].items():
            for u,v in zip(bits,y["connections"].get(p,[])):
                if isinstance(u,str) or isinstance(v,str):
                    err+= u!=v and not ((isinstance(u,str) and isinstance(v,str)) and False); continue
                if fw.setdefault(u,v)!=v or bw.setdefault(v,u)!=u: err+=1
    if err or d: biji.append((tn[:70],d,err))
json.dump(Tj,open(sys.argv[3],"w"))
json.dump(dict(renamed=n,variant_pairs=len(pairs),count_mismatch=bad,module_notes=rep,not_identical=biji),open(sys.argv[4],"w"),indent=1)
print("renamed",n,"pairs",len(pairs),"count_mismatch",len(bad),"not_identical",len(biji))
for b in bad[:25]: print(" M",b)
for b in biji[:25]: print(" B",b)
print(dict(list(rep.items())[:20]))
