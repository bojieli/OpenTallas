import json,sys,collections,statistics as st
RD,part=sys.argv[1],sys.argv[2]
t=json.load(open(RD+"/clk/tree.json")); po=t["parent_of"]; S=t["sites"]
A={}
for l in open(RD+"/out_TT/arr_TT.txt"):
    s=l.split()
    if s and s[0] in("T","N"): A[s[1]]=float(s[2])
def ch(x):
    c=[x]
    while x in po: x=po[x]; c.append(x)
    return c
taps=[x for x in t["taps"] if x["part"]==part]
chains={x["port"]:ch("b%d"%x["node"]) for x in taps}
# LCA
common=set(chains[taps[0]["port"]])
for c in chains.values(): common&=set(c)
lca=next(n for n in chains[taps[0]["port"]] if n in common)
md=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
rows=[]
for x in taps:
    c=chains[x["port"]]; c=c[:c.index(lca)+1]
    L=sum(md(S[c[i]],S[c[i+1]]) for i in range(len(c)-1))+md(x["xy"],S[c[0]])
    rows.append((A[x["port"]]-A[lca] if x["port"] in A else None,L,len(c),x["port"],c[0]))
rows=[r for r in rows if r[0] is not None]
rows.sort()
print("lca",lca,"taps",len(rows))
for r in rows[:4]+rows[-4:]: print("  arr %.0f len %.0f stages %d %s leaf %s"%r)
xs=[r[1] for r in rows]; ys=[r[0] for r in rows]
mx,my=st.mean(xs),st.mean(ys); b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/max(1e-9,sum((x-mx)**2 for x in xs))
print("len spread %.0f um, arr spread %.0f, slope %.3f ps/um, resid max %.0f"%(max(xs)-min(xs),max(ys)-min(ys),b,max(abs(y-my-b*(x-mx)) for x,y in zip(xs,ys))*2))
