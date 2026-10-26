import sys,csv,matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
rows=list(csv.DictReader(open(sys.argv[1]))); title=sys.argv[3]
fig,ax=plt.subplots(figsize=(9,8))
for r in rows:
  x,y,x2,y2=(float(r[k]) for k in ("x","y","x2","y2"))
  if r["kind"]=="die": ax.add_patch(Rectangle((0,0),x2,y2,fill=False,lw=1.5,ec="k"))
  elif r["kind"]=="macro": ax.add_patch(Rectangle((x,y),x2-x,y2-y,fc="#ccd",ec="#557",lw=.8))
  elif r["kind"]=="bufedge": ax.plot([x,x2],[y,y2],"-",c="#d22",lw=1.0)
  elif r["kind"]=="macroedge": ax.plot([x,x2],[y,y2],"-",c="#a0a",lw=1.4)
  elif r["kind"]=="sinkedge": ax.plot([x,x2],[y,y2],"-",c="#4a4",lw=.15,alpha=.4)
ax.set_aspect("equal"); ax.autoscale(); ax.set_title(title,fontsize=9); ax.set_xlabel("um")
plt.savefig(sys.argv[2],dpi=110,bbox_inches="tight")
