import json,sys,argparse
from pathlib import Path
import matplotlib;matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
a=argparse.ArgumentParser();a.add_argument("--tree",required=True);a.add_argument("--out",required=True);args=a.parse_args()
t=json.load(open(args.tree));out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
windows={"io_serdes_2":[0,0,1563.84,2324.16],"io_serdes_1":[0,2324.16,1563.84,4648.32],"io_serdes":[0,14005.44,1563.84,16329.6],"ucie_kv":[0,9244.8,777.6,10022.4],"coll_ucie":[0,7603.2,777.6,8380.8]}
sites=t["sites"];receipt={"source":args.tree,"scope":"Actual cells inside published die_io.json PHY body windows; metadata contract pending. INFRA coupon only, no physical freeze.","windows":{}}
fig,axes=plt.subplots(1,5,figsize=(16,7),dpi=140)
for ax,(name,(x0,y0,x1,y1))in zip(axes,windows.items()):
 bad={n:xy for n,xy in sites.items()if x0<xy[0]<x1 and y0<xy[1]<y1}
 receipt["windows"][name]={"rect_um":[x0,y0,x1,y1],"inside_cells":len(bad),"cells":bad}
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc="lightgrey",ec="black",alpha=.5))
 for c,p in t["parent_of"].items():
  b,e=sites[c],sites[p]
  if max(b[0],e[0])<x0-100 or min(b[0],e[0])>x1+150 or max(b[1],e[1])<y0-100 or min(b[1],e[1])>y1+100:continue
  ax.plot([b[0],e[0]],[b[1],e[1]],color="steelblue",lw=.5,alpha=.5)
 for n,xy in bad.items():ax.plot(*xy,".",color="red",ms=3)
 ax.set(xlim=(x0-100,x1+150),ylim=(y0-100,y1+100),title=f"{name}\n{len(bad)} clock cells inside body",xlabel="x (um)",ylabel="y (um)");ax.set_aspect("equal")
receipt["inside_total"]=sum(x["inside_cells"]for x in receipt["windows"].values());receipt["verdict"]="FAIL"if receipt["inside_total"]else"NO_INTERIOR_CELLS_COUPON_ONLY"
(out/"phy_window_census.json").write_text(json.dumps(receipt,indent=1)+"\n")
fig.suptitle("QC clock / declared PHY body overlap: red cells need a physical contract before routing");fig.tight_layout();fig.savefig(out/"phy_window_census.png")
print(receipt["verdict"],receipt["inside_total"])
