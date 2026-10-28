import json,sys,collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
spec,errf,x0,x1,y0,y1,out=sys.argv[1],sys.argv[2],*map(float,sys.argv[3:7]),sys.argv[7]
s=json.load(open(spec)); cs=s["cell_sites"]
e=json.load(open(errf))["rows"]
bad=collections.Counter(r["name"][6:] for r in e)
g2=collections.defaultdict(list)
for k,v in cs.items(): g2[v["group"]].append(v)
def gxy(g):
    v=g2[g][0]; return (v["origin_um"][0]+v["w"]/2, v["origin_um"][1])
col={"top_node":"red","top_rep":"orange","col_node":"purple","col_rep":"violet","col_tap":"black","band_node":"blue","band_rep":"cyan","fine_driver":"green","band_driver":"lime","chan_node":"brown","chan_rep":"brown"}
fig,ax=plt.subplots(figsize=(14,14))
for n in s["nets"]:
    a=gxy(int(n["drv"][1:])); b=gxy(int(n["load"][1:])) if n["load"].startswith("g") else None
    if b is None: continue
    if not (min(a[0],b[0])<x1 and max(a[0],b[0])>x0 and min(a[1],b[1])<y1 and max(a[1],b[1])>y0): continue
    lw={"16w":3,"8w":2,"4w":1}.get(n["ndr"],1); ls="-" if n["layer"]=="M8" else "--"
    ax.plot([a[0],b[0]],[a[1],b[1]],ls,lw=lw,color={"t":"red","c":"purple","b":"blue"}.get(n["namespace"],"gray"),alpha=.6)
for k,v in cs.items():
    x,y=v["origin_um"]
    if x0<=x<=x1 and y0<=y<=y1:
        ax.plot(x+v["w"]/2,y,"s",color=col.get(v["kind"],"gray"),ms=5)
        if bad.get(k): ax.plot(x+v["w"]/2,y,"x",color="k",ms=14,mew=2); ax.annotate(f'{v["kind"]}:{bad[k]}',(x,y),fontsize=7)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.grid(True,alpha=.3)
from matplotlib.lines import Line2D
ax.legend([Line2D([],[],marker="s",ls="",color=c) for c in col.values()],list(col.keys()),fontsize=8)
plt.savefig(out,dpi=80)
