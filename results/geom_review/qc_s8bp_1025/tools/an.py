import collections,statistics as S,sys
k=sys.argv[1]
def load(c):
    D=collections.defaultdict(list)
    for l in open(f"/tmp/s8bp/{k}/dump_{c}.tsv"):
        t=l.rstrip("\n").split("\t"); D[t[0]].append(t[1:])
    return D
U=lambda s:s.replace("\\","")
tt=load("tt"); ff=load("ff")
ins={U(r[0]):r for r in tt["INST"]}
macros=[U(r[0]) for r in tt["INST"] if r[2]=="macro"]
def ckd(D): return {U(r[0]):float(r[1]) for r in D["CK"] if r[1]}
ckt,ckf=ckd(tt),ckd(ff)
pin=set(U(r[1]) for r in tt["PINREG"])
inst=lambda p:p.rsplit("/",1)[0]
for nm,ck in (("TT",ckt),("FF",ckf)):
    fl=[v for p,v in ck.items() if inst(p) not in macros]
    pr=[v for p,v in ck.items() if inst(p) in pin]
    mc={inst(p):v for p,v in ck.items() if inst(p) in macros}
    print(f"{nm}: flops n{len(fl)} min {min(fl):.1f} mean {S.mean(fl):.1f} max {max(fl):.1f}; pinreg I n{len(pr)} mean {S.mean(pr):.1f} [{min(pr):.1f}..{max(pr):.1f}]; macros",{m:round(v,1) for m,v in mc.items()})
# clock tree depth to macro clk
cn=[(U(r[1]),[U(s) for s in r[3].split()] if len(r)>3 else []) for r in tt["CNET"]]
par={}
for d,ss in cn:
    for s in ss: par[inst(s)]=d
for m in macros:
    ch=[];x=m
    while x in par and len(ch)<40: x=par[x]; ch.append(x)
    def pos(i):
        r=ins.get(i); return (round((float(r[3])+float(r[5]))/2),round((float(r[4])+float(r[6]))/2)) if r else None
    print(m, ins[m][3:5], "depth",len(ch), [ (c,ins[c][1] if c in ins else '',pos(c)) for c in ch[:12]])
for tag in ("HOLD","SETUP"):
  for D,nm in ((tt,"TT"),(ff,"FF")):
    rows=D[tag]
    def kind(i): return "macro" if i in macros else ("pin" if i in pin else ("port" if "/" not in i else "int"))
    c=collections.Counter((kind(inst(U(r[1])) if "/" in r[1] else U(r[1])),kind(inst(U(r[0])) if "/" in r[0] else U(r[0]))) for r in rows)
    print(tag,nm,len(rows),"worst",min([float(r[2]) for r in rows],default=None),dict(c))
