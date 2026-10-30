from pathlib import Path
import matplotlib;matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path("/tmp/qcclock0336");fig,axs=plt.subplots(1,2,figsize=(12,4.5),dpi=150)
lower_top=2320.056;h=2.16
for ax,upper_y,title in zip(axs,[2324.16,2328.264],["Baseline inner origins [0,0]: no driver channel","Review option: upper body +4.104 um; 3.888 um channel"]):
 ax.add_patch(Rectangle((730,2314),120,lower_top-2314,fc="lightgrey",ec="black"));ax.add_patch(Rectangle((730,upper_y),120,2336-upper_y,fc="lightgrey",ec="black"))
 ax.axhspan(lower_top,lower_top+h,color="crimson",alpha=.15);ax.axhspan(upper_y-h,upper_y,color="crimson",alpha=.15)
 ax.axhline(2324.16,color="black",ls="--",lw=.7,label="unchanged outer slot seam")
 low,high=lower_top+h,upper_y-h
 if high>low:
  ax.axhspan(low,high,color="green",alpha=.12)
  rows=[n*.54 for n in range(4300,4310)if low<=n*.54 and n*.54+.27<=high]
  for y in rows:ax.axhline(y,color="green",lw=.6,alpha=.6)
  ax.add_patch(Rectangle((753.3,2323.62),1.62,.27,fc="steelblue",ec="navy"))
  ax.annotate("Example R0 clock-cell home\n(not placed or PG-qualified)",xy=(754.1,2323.75),xytext=(780,2329.5),arrowprops={"arrowstyle":"->"},fontsize=8)
  ax.plot([753.288,753.3],[2319.96,2323.62],color="orange",lw=1.3)
  ax.text(734,2324.8,"7 row positions fit the halo gap",color="darkgreen",fontsize=8)
 else:
  ax.axhspan(high,low,color="red",alpha=.4);ax.text(734,2326,"halos overlap 0.216 um",color="crimson")
 x=753.018 if upper_y==2324.16 else 753.288
 ax.plot(x,2319.96,"o",color="darkorange");ax.annotate("native M5 clk entry",xy=(x,2319.96),xytext=(775,2316),arrowprops={"arrowstyle":"->"},fontsize=8)
 ax.set(xlim=(730,850),ylim=(2314,2336),title=title,xlabel="x local die (um)",ylabel="y die (um)")
 ax.legend(fontsize=7,loc="upper right")
fig.suptitle("READ-ONLY body-packing review: full native bodies +2.16 um halos; no PHY interior islands")
fig.tight_layout();fig.savefig(r/"phy_body_channel_proposal.png")

