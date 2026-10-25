import collections,statistics as S,sys
def load(fn):
    D=collections.defaultdict(list)
    for l in open(fn):
        t=l.rstrip("\n").split("\t"); D[t[0]].append(t[1:])
    return D
F=load("routed_ff.tsv"); T=load("routed_tt.tsv")
U=lambda s:s.replace("\\","")
def ck(D):
    r={}
    for p,amax,amin,tap in D["CK"]:
        r[U(p).rsplit("/",1)[0]]=(float(amax),float(amin),tap)
    return r
cf=ck(F); ct=ck(T)
for nm,c in (("TT",ct),("FF",cf)):
    g=collections.defaultdict(list)
    for i,(a,b,t) in c.items(): g[t].append(a)
    for t,v in sorted(g.items()): print(nm,t,len(v),"mean %.1f min %.1f max %.1f"%(S.mean(v),min(v),max(v)))
print(F["WNS"])
cnt=collections.Counter(); ex={}
for ep,sp,sl in F["HOLD"]:
    e=U(ep).rsplit("/",1)[0]; s=U(sp).rsplit("/",1)[0]
    et=cf.get(e,(0,0,"?"))[2]; st=cf.get(s,(0,0,"?"))[2]
    key=(st,et, "macro" if "u_m" in e and "/" not in e.split("u_m")[-1] else ("port" if e==U(ep) else "reg"))
    cnt[key]+=1; ex.setdefault(key,(ep,sp,sl,cf.get(s),cf.get(e)))
for k,v in cnt.most_common(): print(v,k,ex[k])
