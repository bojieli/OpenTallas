#!/usr/bin/env python3
"""DIE-HBM-6 estimate: hub station-chain crossing profile for vertical (x=c) vs horizontal (y=c) cuts.
Hops = from_um -> regs_um... -> to_um per station, bits each (original C20j geometry; banks keep hops <=reach near sites)."""
import json,sys,collections,math
p=json.load(open(sys.argv[1]));res={}
for tn in ("q_hub_nw","q_hub_ne"):
  t=p["partition_types"][tn];W,H=t["outline_um"]
  step=8.64*5
  xs=[i*step for i in range(1,int(W/step))];ys=[i*step for i in range(1,int(H/step))]
  cx=collections.Counter();cy=collections.Counter()
  # hop direction census
  dx_tot=0;dy_tot=0;bits_tot=0;regbits=0
  cellsx=collections.Counter();cellsy=collections.Counter()
  for s in t["internal_stations"]:
    pts=[s["from_um"]]+s["regs_um"]+[s["to_um"]];b=s["bits"];regbits+=b*len(s["regs_um"])
    for r in s["regs_um"]:
      cellsx[int(r[0]//step)]+=1.3*b;cellsy[int(r[1]//step)]+=1.3*b
    for a,c in zip(pts,pts[1:]):
      dx_tot+=abs(a[0]-c[0])*b;dy_tot+=abs(a[1]-c[1])*b
      lo,hi=sorted((a[0],c[0]))
      for i in range(math.ceil(lo/step),math.floor(hi/step)+1):
        if lo<i*step<=hi: cx[i]+=b
      lo,hi=sorted((a[1],c[1]))
      for i in range(math.ceil(lo/step),math.floor(hi/step)+1):
        if lo<i*step<=hi: cy[i]+=b
  hc={h["inst"] for h in t["hard_cores"]}
  for c in t["contents"]:
    if any(h==c["inst"] or h.startswith(c["inst"]+"_") or h.startswith(c["inst"]+".") for h in hc):continue
    cellsx[int((c["origin_um"][0]+c["outline_um"][0]/2)//step)]+=c["cells"];cellsy[int((c["origin_um"][1]+c["outline_um"][1]/2)//step)]+=c["cells"]
  def prof(cn,n):
    return [(round(i*step,2),cn.get(i,0)) for i in range(1,n)]
  px=prof(cx,int(W/step));py=prof(cy,int(H/step))
  res[tn]=dict(outline=[W,H],station_reg_bits=regbits,bit_um_x=dx_tot,bit_um_y=dy_tot,
    vcut_bits_min=min(v for _,v in px),vcut_bits_median=sorted(v for _,v in px)[len(px)//2],vcut_bits_max=max(v for _,v in px),
    hcut_bits_min=min(v for _,v in py),hcut_bits_median=sorted(v for _,v in py)[len(py)//2],hcut_bits_max=max(v for _,v in py),
    vcut_face_cap_6um=int(6*H),hcut_face_cap_6um=int(6*W),
    hcut_profile=py,vcut_profile=px[::4],vcut_full=[(i,cx.get(i,0)) for i in range(1,int(W/step))],cells_by_y=[(round(i*step,1),round(cellsy.get(i,0))) for i in range(int(H/step)+1)],
    cells_total_unbanked=round(sum(cellsy.values())))
  r=res[tn];print(tn,{k:v for k,v in r.items() if "profile" not in k and k!="cells_by_y"})
json.dump(res,open(sys.argv[2],"w"),indent=0)
