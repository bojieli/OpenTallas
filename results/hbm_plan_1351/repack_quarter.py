import json,math,pathlib,copy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
BASE=pathlib.Path(__file__).parent
p=json.load(open(BASE/"c15_ref/die_plan.json"))
box=[3974.4,829.44,1816.992,2347.488]
G=8.64
def halo(c):
 h=c.get("halo_um",4.32)
 return max(h) if isinstance(h,list) else h
def rect(c):
 x,y=c["origin_um"];w,h=c["outline_um"];d=halo(c)
 return [x-d,y-d,x+w+d,y+h+d]
def hit(a,b):return a[0]<b[2]-1e-6 and a[2]>b[0]+1e-6 and a[1]<b[3]-1e-6 and a[3]>b[1]+1e-6
report={"basis":"C15 3a73d67be12d; native quarter71648; geometry capacity candidate only; no native/station rebinding or route qualification","quarter_box_um":box,"hubs":{}}
fig,axs=plt.subplots(2,1,figsize=(18,12))
for ax,tn in zip(axs,["q_hub_nw","q_hub_ne"]):
 t=p["partition_types"][tn];W,H=t["outline_um"]
 # Old sliced key buffers are invalid physical ABI: omit them only from this capacity probe.
 proxies=[c for c in t["hard_cores"] if c["inst"].startswith("u_mu_keybuf_")]
 remain=[c for c in t["hard_cores"] if c not in proxies]
 reserve=[box[0]-4.32,box[1]-4.32,box[0]+box[2]+4.32,box[1]+box[3]+4.32]
 movers=[c for c in remain if hit(rect(c),reserve)];fixed=[c for c in remain if c not in movers]
 obstacles=[rect(c) for c in fixed]+[reserve]
 moves=[];failed=[]
 for c in sorted(movers,key=lambda c:-math.prod(c["outline_um"])):
  w,h=c["outline_um"];d=halo(c);ox,oy=c["origin_um"]
  xs={d,ox};ys={d,oy}
  for r in obstacles:
   xs.update([r[2]+d,r[0]-w-d]);ys.update([r[3]+d,r[1]-h-d])
  xs={round(math.ceil(x/G)*G,6) for x in xs if x>=d-1e-5 and x+w+d<=W+1e-5}
  ys={round(math.ceil(y/G)*G,6) for y in ys if y>=d-1e-5 and y+h+d<=H+1e-5}
  candidates=sorted(((abs(x-ox)+abs(y-oy),x,y) for x in xs for y in ys))
  chosen=None
  for dist,x,y in candidates:
   r=[x-d,y-d,x+w+d,y+h+d]
   if all(not hit(r,q) for q in obstacles):chosen=(dist,x,y,r);break
  if chosen is None:failed.append(c["inst"]);continue
  dist,x,y,r=chosen;moves.append({"inst":c["inst"],"old_origin_um":[ox,oy],"origin_um":[x,y],"outline_um":[w,h],"halo_um":d,"displacement_l1_um":dist});c["origin_um"]=[x,y];obstacles.append(r)
 t["hard_cores"]=remain
 for c in fixed:
  x,y=c["origin_um"];w,h=c["outline_um"];ax.add_patch(plt.Rectangle((x,y),w,h,facecolor="#cbd5e1",edgecolor="#475569",lw=.3))
 for m in moves:
  x,y=m["origin_um"];w,h=m["outline_um"];ax.add_patch(plt.Rectangle((x,y),w,h,facecolor="#fbbf24",edgecolor="#92400e",lw=.5));ax.text(x+w/2,y+h/2,m["inst"].replace("u_",""),fontsize=4,ha="center",clip_on=True)
 ax.add_patch(plt.Rectangle(box[:2],box[2],box[3],facecolor="#dbeafe",edgecolor="#2563eb",lw=2));ax.text(box[0]+box[2]/2,box[1]+box[3]/2,"Native quarter reservation\n64 HCOL + 2 tails + 17 SRAM\nexisting stages; full graph still pending",ha="center",fontsize=12)
 ax.set(xlim=(0,W),ylim=(0,H),aspect="equal",title=f"{tn}: {len(moves)}/{len(movers)} colliders relocated; {len(proxies)} invalid proxies omitted for capacity only")
 report["hubs"][tn]={"removed_proxy_geometry":[c["inst"] for c in proxies],"moves":moves,"unplaced":failed,"fixed":len(fixed),"remaining_station_clock_rebind":"REQUIRED; moved origins not propagated"}
BASE.joinpath("quarter_repack_report.json").write_text(json.dumps(report,indent=2)+"\n")
BASE.joinpath("quarter_repack_geometry.json").write_text(json.dumps(p,indent=2)+"\n")
fig.tight_layout();fig.savefig(BASE/"quarter_repack.png",dpi=140)
print({tn:{"moves":len(v["moves"]),"failed":v["unplaced"],"proxies":len(v["removed_proxy_geometry"])} for tn,v in report["hubs"].items()})
