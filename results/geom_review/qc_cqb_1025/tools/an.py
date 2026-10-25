import collections,statistics as S
def load(c):
    D=collections.defaultdict(list)
    for l in open(f"dump_{c}.tsv"):
        t=l.rstrip("\n").split("\t"); D[t[0]].append(t[1:])
    return D
U=lambda s:s.replace("\\","")
ff=load("ff"); tt=load("tt")
ins={U(r[0]):r for r in ff["INST"]}
macros=[U(r[0]) for r in ff["INST"] if r[2]=="macro"]
ck={U(r[0]):float(r[1]) for r in ff["CK"] if r[1]}
ckt={U(r[0]):float(r[1]) for r in tt["CK"] if r[1]}
pin=set(U(r[1]) for r in ff["PINREG"])
def inst(p): return p.rsplit("/",1)[0]
def ckof(i,d=ck):
    for k in ("CLK","clk"):
        if f"{i}/{k}" in d: return d[f"{i}/{k}"]
print("macro clk FF/TT:",[(m,ckof(m),ckof(m,ckt)) for m in macros])
def kind(i):
    if i in macros: return "macro"
    return "pinreg" if i in pin else "internal"
def pos(i):
    r=ins.get(i); 
    return ((float(r[3])+float(r[5]))/2,(float(r[4])+float(r[6]))/2) if r else None
rows=[]
for ep,sp,sl,clk in ff["HOLD"]:
    ei,si=inst(ep),inst(sp)
    rows.append((float(sl),ep,sp,kind(ei),kind(si),ckof(si),ckof(ei),pos(si),pos(ei)))
c=collections.Counter((r[3],r[4]) for r in rows); print(c)
sk=[r[6]-r[5] for r in rows if r[5] and r[6]]
print("capture-launch skew FF on violators: mean %.1f min %.1f max %.1f"%(S.mean(sk),min(sk),max(sk)))
for r in sorted(rows)[:12]: print("%.2f %s <- %s %s<-%s L%.1f C%.1f"%(r[0],r[1],r[2],r[3],r[4],r[5],r[6]), r[7], r[8])
bym=collections.Counter(r[1].split("/")[0] if r[3]=="macro" else "flop" for r in rows); print(bym)
bypin=collections.Counter(r[1].split("/")[1].split("[")[0] for r in rows if r[3]=="macro"); print(bypin)
# internal flop endpoints
for r in sorted(rows):
    if r[3]!="macro": print("  F %.2f %s <- %s L%.1f C%.1f d=%.0fum"%(r[0],r[1],r[2],r[5],r[6], abs(r[7][0]-r[8][0])+abs(r[7][1]-r[8][1])) ); 
