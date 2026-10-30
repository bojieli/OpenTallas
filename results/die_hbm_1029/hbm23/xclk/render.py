import sys,matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.patches as P
sinks,tree,ff,out,ex,ey,W_,H_=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],float(sys.argv[5]),float(sys.argv[6]),float(sys.argv[7]),float(sys.argv[8])
macros=[tuple(map(float,m.split(","))) for m in sys.argv[9:]]
face={l.split("\t")[0].replace("\\",""):l.split("\t")[1] for l in open(ff) if "\t" in l}
T={}
for l in open(tree):
    if l[0]=="#": continue
    p=l.split(); T[p[0]]=(float(p[2]),float(p[3]),float(p[5]),p[8])
fig,axs=plt.subplots(1,2,figsize=(18,9))
for ax,mode in zip(axs,("face","all")):
    for (x,y,w,h) in macros: ax.add_patch(P.Rectangle((x,y),w,h,fc="#ddd",ec="k",lw=0.5))
    ax.add_patch(P.Rectangle((0,0),W_,H_,fill=False,ec="k"))
    xs=[];ys=[];cs=[];ms=[]
    for l in open(sinks):
        if l[0]=="#": continue
        p=l.split(); inst=p[0].rsplit("/",1)[0]; f=face.get(inst)
        if mode=="face" and not f: continue
        xs.append(float(p[2]));ys.append(float(p[3]));cs.append(float(p[1]))
    sc=ax.scatter(xs,ys,c=cs,cmap="turbo",vmin=float(__import__("os").environ.get("VMIN",190)),vmax=float(__import__("os").environ.get("VMAX",320)),s=6 if mode=="all" else 10)
    for n,(x,y,a,d) in T.items():
        if d in T:
            dx,dy,_,_=T[d]; ax.plot([dx,x],[dy,y],color="k" if "leaf" not in n else "m",lw=0.4,alpha=0.6)
    lv6=[n for n in T if n.startswith("clkbuf_4_") or n=="wire3843"]
    ax.scatter([T[n][0] for n in lv6],[T[n][1] for n in lv6],marker="s",s=40,facecolors="none",edgecolors="r",label="lv6 cluster drivers (+wire3843)")
    ax.plot([ex],[ey],"k*",ms=18,label="clk entry")
    ax.set_title("%s 4_cts TT insertion (ps): %s sinks; magenta = lv6->leaf wires"%(__import__("os").environ.get("TAG","xcal_k21m5"),mode))
    ax.set_xlim(-2,W_+2); ax.set_ylim(-2,H_+2); ax.set_aspect("equal"); ax.legend(loc="lower right",fontsize=8)
    plt.colorbar(sc,ax=ax,shrink=0.7)
plt.tight_layout(); plt.savefig(out,dpi=110)
