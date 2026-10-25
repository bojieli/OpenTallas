import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp, collections, sys
exec(open("an.py").read().split("for nm,c")[0])
ins={U(r[0]):r for r in F["INST"]}
def pos(i):
    r=ins.get(i); return ((float(r[3])+float(r[5]))/2,(float(r[4])+float(r[6]))/2) if r else None
die=[float(x) for x in F["DIE"][0]]
fig,axs=plt.subplots(1,2,figsize=(17,8.6))
cols={"ot_ctap_SE":"tab:orange","ot_ctap_SW":"tab:brown","ot_ctap_E0":"tab:red","ot_ctap_E1":"tab:pink","ot_ctap_W0":"tab:blue","ot_ctap_W1":"tab:cyan"}
for ax,(nm,c) in zip(axs,(("TT",ct),("FF",cf))):
    ax.add_patch(mp.Rectangle((die[0],die[1]),die[2]-die[0],die[3]-die[1],fill=False,lw=1))
    for k,r in ins.items():
        if r[2]=="macro":
            x0,y0,x1,y1=map(float,r[3:7]); ax.add_patch(mp.Rectangle((x0,y0),x1-x0,y1-y0,color="0.88")); ax.text((x0+x1)/2,(y0+y1)/2,k,ha="center",fontsize=8)
    g=collections.defaultdict(list)
    for i,(a,b,t) in c.items():
        p=pos(i)
        if p: g[t].append((p,a))
    for t,v in g.items():
        if t.startswith("ot_ctap"):
            ax.scatter([p[0] for p,a in v],[p[1] for p,a in v],s=2,c=cols.get(t,"k"),alpha=.35)
            mean=sum(a for p,a in v)/len(v); tp=pos(t)
            if tp: ax.plot(*tp,"k^",ms=9); ax.text(tp[0]+2,tp[1]+2,"%s %.0f"%(t[8:],mean),fontsize=9,weight="bold")
        else:
            for p,a in v: ax.plot(*p,"ms",ms=8); ax.text(p[0]+2,p[1]-7,"macro clk %.0f\n(own root branch)"%a,fontsize=8,color="m")
    ax.set_xlim(-5,die[2]+5); ax.set_ylim(-5,die[3]+5); ax.set_aspect("equal")
    ax.set_title("f56c routed RCX %s: register clock arrival by regional tap (mean ps), macro clk pins"%nm,fontsize=9)
ax=axs[1]
cat=collections.Counter()
for ep,sp,sl in F["HOLD"]:
    e=U(ep).rsplit("/",1)[0]; s=U(sp).rsplit("/",1)[0]
    ps=pos(s); pe=pos(e) if e in ins else None
    col="r" if "u_m" in e else ("g" if pe else "orange")
    if ps and pe: ax.plot([ps[0],pe[0]],[ps[1],pe[1]],"-",c=col,lw=.5,alpha=.6)
    elif ps: ax.plot(*ps,"x",c=col,ms=4)
ax.text(2,-3,"FF hold -13.22/200: red=E1 regs->g_crb[1] wd_in (120), x orange=W0 q pin-reg->port vs vclk I (67), green=W0->W1 regs (12)",fontsize=7)
plt.tight_layout(); plt.savefig(sys.argv[1],dpi=100); print("ok")
