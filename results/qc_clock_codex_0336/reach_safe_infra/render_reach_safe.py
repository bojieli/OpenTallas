import sys,json
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude");R=Q/"codex-qc-clock-0336";W=Q/"wt/codex-qc-clock-0336";sys.path.insert(0,str(W/"tools/die_plan"))
import schema as S,die_trial as D
import matplotlib;matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
T=json.load(open(R/"reach_safe/out/kit/clock/tree.json"));raw=json.load(open(Q/"die-qc-46/plan/plan_qc45.json"));P=S.Plan(raw)
c,p=max(T["parent_of"].items(),key=lambda e:sum(abs(x-y)for x,y in zip(T["sites"][e[0]],T["sites"][e[1]])));a,b=T["sites"][c],T["sites"][p];cx=(a[0]+b[0])/2;cy=(a[1]+b[1])/2;lo,hi=cx-900,cx+900;bo,to=cy-900,cy+900
fig,ax=plt.subplots(figsize=(10,9),dpi=140)
for n in P.parts:
 x0,y0,x1,y1=P.rect(n)
 if x1<lo or x0>hi or y1<bo or y0>to:continue
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec="black",lw=.5))
 for x,y,xx,yy,*_ in D.core_obs(P.ptype(n)):
  pts=[P.to_die(n,q)for q in [(x,y),(x,yy),(xx,y),(xx,yy)]];xs,ys=zip(*pts)
  ax.add_patch(Rectangle((min(xs),min(ys)),max(xs)-min(xs),max(ys)-min(ys),fc="grey",ec="black",alpha=.22,lw=.5))
for cc,pp in T["parent_of"].items():
 aa,bb=T["sites"][cc],T["sites"][pp]
 if max(aa[0],bb[0])<lo or min(aa[0],bb[0])>hi or max(aa[1],bb[1])<bo or min(aa[1],bb[1])>to:continue
 d=sum(abs(x-y)for x,y in zip(aa,bb));ax.plot([aa[0],bb[0]],[aa[1],bb[1]],color="red"if d>405 else"steelblue",lw=1.8 if d>405 else.6,alpha=.75)
 ax.plot([aa[0]],[aa[1]],".",color="navy",ms=2)
ax.plot([a[0],b[0]],[a[1],b[1]],color="darkgreen",lw=3);ax.annotate("Longest physical clock cell hop",xy=((a[0]+b[0])/2,(a[1]+b[1])/2),xytext=(lo+40,to-120),arrowprops=dict(arrowstyle="->"),fontsize=10)
ax.set(xlim=(lo,hi),ylim=(bo,to),xlabel="x (um)",ylabel="y (um)",title="QC46 reach-safe candidate: longest actual cell-to-cell hop\nGrey=planned hard cores; green=longest origin span (398.142 um); INFRA coupon")
ax.set_aspect("equal");fig.tight_layout();fig.savefig(R/"review/reach_safe_longest.png")
