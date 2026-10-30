import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
t=json.load(open(sys.argv[1])); g=json.load(open(sys.argv[2])); s=t["sites"]
fig,ax=plt.subplots(1,2,figsize=(18,10))
for k,(x0,x1,y0,y1) in enumerate([(None,)*4,(0,1600,2240,2410)]):
    a=ax[k]; xs=[v[0] for v in s.values()]; ys=[v[1] for v in s.values()]
    a.scatter(xs,ys,s=1 if k==0 else 12,c="tab:blue")
    for n,(bx0,by0,bx1,by1) in g["phy_body_boxes"].items():
        kw=dict(fill=False,ec="red" if "keepout" in n else "orange",lw=1.2 if "keepout" in n else .6,ls="-" if "keepout" in n else "--")
        a.add_patch(Rectangle((bx0,by0),bx1-bx0,by1-by0,**kw))
    if x0 is not None: a.set_xlim(x0,x1); a.set_ylim(y0,y1)
    a.set_title(["plan_qc47 die clock cells (blue), PHY body keep-outs red, old slot windows orange dashed","SerDes gap row zoom"][k])
plt.tight_layout(); plt.savefig(sys.argv[3],dpi=90)
