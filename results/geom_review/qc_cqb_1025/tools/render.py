import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp, statistics as S
import io,contextlib
with contextlib.redirect_stdout(io.StringIO()): exec(open("an.py").read())
def ld(c): return {r.split("\t")[1]:float(r.split("\t")[2]) for r in open(f"ckest_{c}.tsv") if r.startswith("CK") and r.split("\t")[2].strip()}
est_tt=ld("tt")
die=[float(x) for x in ff["DIE"][0]]
cnets=[(U(r[1]),[U(s) for s in r[3].split()] if len(r)>3 else []) for r in ff["CNET"]]
drv=set(d for d,_ in cnets)
def P(i): return pos(i)
def base(ax,t):
    ax.add_patch(mp.Rectangle((die[0],die[1]),die[2]-die[0],die[3]-die[1],fill=False,lw=1))
    for m in macros:
        r=ins[m]; x0,y0,x1,y1=map(float,r[3:7]); ax.add_patch(mp.Rectangle((x0,y0),x1-x0,y1-y0,color="0.85"))
        ax.text((x0+x1)/2,(y0+y1)/2,m,ha="center",fontsize=7)
    ax.set_xlim(die[0]-5,die[2]+5); ax.set_ylim(die[1]-5,die[3]+5); ax.set_aspect("equal"); ax.set_title(t,fontsize=9)
fig,axs=plt.subplots(1,3,figsize=(24,8.6))
ax=axs[0]; base(ax,"vmr routed 6_final: ports(black) pin-regs(green) clock tree(red) FF hold violators launch->capture (macro wd_in magenta, flop->flop orange)")
px=[(float(r[1]),float(r[2])) for r in ff["PORT"]]; ax.scatter(*zip(*px),s=1,c="k")
regs=[inst(k) for k in ck if inst(k) not in macros]
g=[P(i) for i in regs if i in pin and P(i)]; o=[P(i) for i in regs if i not in pin and P(i)]
ax.scatter(*zip(*o),s=1,c="0.6"); ax.scatter(*zip(*g),s=1,c="g")
for d,sinks in cnets:
    if d.startswith("PORT:") or d not in ins: continue
    a=P(d)
    for s in sinks:
        si=s.rsplit("/",1)[0]
        if si in drv or si in macros:
            b=P(si); ax.plot([a[0],b[0]],[a[1],b[1]],c="r",lw=0.4)
cb=[P(d) for d in drv if d in ins]; ax.scatter(*zip(*cb),s=4,c="r",marker="s")
for r in rows:
    a,b=r[7],r[8]
    if r[3]=="macro":
        mi=ins[r[1].split("/")[0]]; b=(a[0],float(mi[4]))  # macro bottom edge above launch
        ax.annotate("",xy=b,xytext=a,arrowprops=dict(arrowstyle="->",color="m",lw=0.6))
    else: ax.annotate("",xy=b,xytext=a,arrowprops=dict(arrowstyle="->",color="orange",lw=0.9))
for m in macros:
    d=[dd for dd,ss in cnets if any(s.startswith(m+"/") for s in ss)]
    if d: q=P(d[0]); ax.plot(*q,"b*",ms=12); ax.text(q[0]+2,q[1]+2,"macro clk drv",fontsize=7,color="b")
ax=axs[1]; base(ax,"FF RCX clock arrival at register/macro clock pins (ps, source latency 0)")
ks=[k for k in ck if P(inst(k))]; sc=ax.scatter([P(inst(k))[0] for k in ks],[P(inst(k))[1] for k in ks],c=[ck[k] for k in ks],s=3,cmap="viridis")
plt.colorbar(sc,ax=ax,fraction=0.04)
for m in macros: q=P(m); ax.text(q[0],q[1]-10,"clk FF %.1f"%ckof(m),ha="center",fontsize=8,color="b")
ax=axs[2]; base(ax,"TT clock arrival: GRT-estimate minus RCX (ps) -- non-uniform 11.6..45.2: skew moves after route")
ks=[k for k in ckt if k in est_tt and P(inst(k))]; sc=ax.scatter([P(inst(k))[0] for k in ks],[P(inst(k))[1] for k in ks],c=[est_tt[k]-ckt[k] for k in ks],s=3,cmap="magma")
plt.colorbar(sc,ax=ax,fraction=0.04)
plt.tight_layout(); plt.savefig("vmr_cqb_routed_review.png",dpi=110)
print("ok")
