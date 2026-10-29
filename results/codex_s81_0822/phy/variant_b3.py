#!/usr/bin/env python3
"""DIE-S81-24 S81-007 fix variant B (fix-only on FROZEN plan_s13r2; no type/RTL/cycle change for ES0/ES1):
 (1) lk_ES0/lk_ES1 orient MY -> R180. They sit on the SOUTH die edge but MY keeps the typed u_phy at the partition TOP
     (die y 406.08..1330.56, shoreline 406.08 > 200). R180 = MY + MX puts the same typed macro at die y 103.68..1028.16
     (shoreline 103.68), which is what the declared die.io / PG phy_macro metadata already say; die-W/E faces unchanged.
     South-edge peers lk_WS* already use MX (macro to the edge); north-edge lk_WN*/EN* keep R0/MY.
 (2) s_7S_x10 (slice_station__t23, 1 instance) mirrors its 4 FT windows on its local W face (die E, abutting lk_ES0)
     y -> H - y with per-stem order lsb_high, so the abutment with the y-flipped ES0 stays bit-aligned; N face unchanged.
 (3) PG domains phy_lk_ES0/1: rect mirrored inside the partition row; phy_macro/bumps/io rect = typed macro box.
 (4) landing bay relayout of 12 types = Codex batch02 candidates (translation/band order only; cand/SHA256SUMS).
usage: variant_b.py PLAN CROSSINGS CAND_DIR OUT_DIR"""
import copy,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,"tools/die_plan")
import schema as S,clock_landing_plan as CL,die_io as IO
sp=importlib.util.spec_from_file_location("s12","results/die_s81_19_1028/scripts/recompose_s12.py");m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
plan,cross,cdir,out=sys.argv[1:5];out=Path(out);out.mkdir(exist_ok=True)
raw,_=m.uncompose(json.load(open(plan)));log=[]
P0=S.Plan(raw)
y0s={p:P0.rect(p) for p in ("lk_ES0","lk_ES1")}
for p in raw["partitions"]:
  if p["name"] in ("lk_ES0","lk_ES1"):
    assert p["orient"]=="MY";p["orient"]="R180";log.append(f"{p['name']} orient MY->R180")
t=raw["partition_types"]["slice_station__t23"];H=t["outline_um"][1]
for s in t["ft_slots"]:
  for stem in ("in","out"):
    if s[stem+"_face"]=="W":
      a,b=s[stem+"_window_um"];s[stem+"_window_um"]=[round(H-b,6),round(H-a,6)]
      s[stem+"_order"]="lsb_high" if s.get(stem+"_order",s.get("order","lsb_low"))=="lsb_low" else "lsb_low"
      log.append(f"t23 {s['name']}.{stem} W window [{a},{b}] -> {s[stem+'_window_um']} {s[stem+'_order']}")
t["note"]=t.get("note","")+"; DIE-S81-24 S81-007: W-face (to lk_ES0) FT windows mirrored y->H-y, lsb_high, for lk_ES0/1 R180 shoreline fix"
P=S.Plan(raw)
for part in ("lk_ES0","lk_ES1"):
  ty=P.ptype(part);u=next(c for c in ty["contents"] if c["inst"]=="u_phy");x,y=u["origin_um"];w,h=u["outline_um"]
  a=P.to_die(part,(x,y));b=P.to_die(part,(x+w,y+h));box=[round(min(a[0],b[0]),6),round(min(a[1],b[1]),6),round(max(a[0],b[0]),6),round(max(a[1],b[1]),6)]
  r=y0s[part];Y=r[1]+r[3]
  d=next(d for d in raw["die"]["pg"]["domains"] if d["name"]=="phy_"+part);dr=d["rect_um"];d["rect_um"]=[dr[0],round(Y-dr[3],6),dr[2],round(Y-dr[1],6)]
  d["phy_macro_um"]=box
  if "bumps" in d: d["bumps"]["rect_um"]=box
  io=next(z for z in raw["die"]["io"] if z["part"]==part and z["iface"]=="serdes");io["rect_um"]=box;io["sites"]=IO.count_sites(box,io["pitch_um"],io.get("bump_exclude_um",()))
  log.append(f"{part} typed macro {box} edge {IO.edge_dist(P,box):.2f} domain {dr}->{d['rect_um']}")
orders={}
for f in sorted(Path(cdir).glob("*.candidate.json")):
  p=json.load(open(f));tn=p["type"];ty=raw["partition_types"][tn];dx,dy=p["translation_um"]
  for c in ty.get("hard_cores",[]):c["origin_um"]=[round(c["origin_um"][0]+dx,6),round(c["origin_um"][1]+dy,6)]
  for s in ty.get("ft_slots",[]):
    if s.get("regs_um"):s["regs_um"]=[s["regs_um"][0]]+[[round(x+dx,6),round(y+dy,6)] for x,y in s["regs_um"][1:]]
    if s.get("bit_sites_um"):s["bit_sites_um"]=[[[round(x+dx,6),round(y+dy,6)] for x,y in st] for st in s["bit_sites_um"]]
  for e in p.get("bank_relief",[]):
    s=next(s for s in ty["ft_slots"] if s["name"]==e["slot"]);j=e["internal_stage"];ex,ey=e["delta_um"]
    s["bit_sites_um"][j-1]=[[round(x+ex,6),round(y+ey,6)] for x,y in s["bit_sites_um"][j-1]]
    s["regs_um"][j]=[round(s["regs_um"][j][0]+ex,6),round(s["regs_um"][j][1]+ey,6)]
  for c in ty.get("clock",{}).get("taps",[]):
    if c.get("kind")=="core":c["xy"]=[round(c["xy"][0]+dx,6),round(c["xy"][1]+dy,6)]
  for r in ty.get("internal_stations",[]):
    for k in ("from_um","to_um"):r[k]=[round(r[k][0]+dx,6),round(r[k][1]+dy,6)]
    r["regs_um"]=[[round(x+dx,6),round(y+dy,6)] for x,y in r["regs_um"]]
  if p.get("band_order")=="largest_first":orders[tn]="largest_first"
  ty["note"]=ty.get("note","")+f"; DIE-S81-24 S81-007 landing bay relayout (Codex batch02 candidate) translation {dx},{dy}um; no RTL/pin/cycle change"
  log.append(f"landing {tn} translation {dx},{dy} order {p.get('band_order')}")
raw["note"]=raw.get("note","")+"; DIE-S81-24 S81-007 variant B fix-only event on plan_s13r2: lk_ES0/1 R180 + t23 W FT windows + 12-type landing relayout"
B=S.Plan(raw)
# (5) explicit die-port geometry of the lk_ES0/1 <-> s_7S_x10 abutment ports re-derived from the type windows; src must equal dst
for pr in raw["ports"]:
  sides=[pr[k]["part"] for k in ("src","dst")]
  if not any(x in ("lk_ES0","lk_ES1") for x in sides) or not all(k in pr for k in ("face","window_um")): continue
  gs=B.port_geom_from(pr,"src");gd=B.port_geom_from(pr,"dst")
  if gs is not None and gd is not None: assert gs==gd,(pr["id"],gs,gd)
  gs=gs or gd
  assert gs is not None,(pr["id"],"neither endpoint has geometry")
  oldg=(pr["face"],pr["window_um"],pr.get("order","lsb_low"))
  if oldg!=(gs[0],gs[1],gs[3]):
    pr["face"],pr["window_um"],pr["order"]=gs[0],gs[1],gs[3];log.append(f"port {pr['id']} {oldg} -> {(gs[0],gs[1],gs[3])}")
# B3: mirrored W windows require matching physical station banks in t23.
# Preserve every slot depth; exact paired-bit geometry is the placement input.
import numpy as np
sys.path.insert(0,str(Path.cwd()))
from tools.die_trial.legal_sites import RowAllocator
from gen_phys import type_pins
from ft_sites import bit_ordered
from schema import tap_grid
P3=S.Plan(raw);tn="slice_station__t23";tt=raw["partition_types"][tn];w,h=tt["outline_um"]
al=RowAllocator((4.32,4.32,w-4.32,h-4.32),cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
for _,x,y in tap_grid(P3,tn):al.reserve_rectangle((x-1.08,y-1.08,x+1.08,y+1.08))
pins={(b,i):(x,y) for b,i,_,x,y,_ in type_pins(P3,tn)};station_receipt=[]
for ss in tt['ft_slots']:
 k=ss['stations'];a=np.array([pins[(ss['name']+'_i',i)] for i in range(ss['width']+1)]);b=np.array([pins[(ss['name']+'_o',i)] for i in range(ss['width']+1)])
 pts=[]
 for j in range(1,k):
  ideal=a+(b-a)*j/k;p,_=al.allocate(ideal.mean(axis=0),len(a),max_radius_um=40.);pts.append(p)
 pts=bit_ordered(a,pts,b);chain=[a,*pts,b];worst=max(float(np.abs(y-x).sum(axis=1).max()) for x,y in zip(chain,chain[1:]));assert worst<=395.,(ss['name'],worst)
 ss['bit_sites_um']=[(p-np.array([.702,.135])).round(6).tolist() for p in pts];ss['bit_site_cell_um']=[1.404,.27];ss['regs_um']=[a.mean(axis=0).round(6).tolist()]+[p.mean(axis=0).round(6).tolist() for p in pts]
 station_receipt.append(dict(slot=ss['name'],stations=k,bits=len(a),worst_paired_bit_um=worst))
 log.append(f"B3 {tn}/{ss['name']} exact banks resited same {k} stages worst {worst:.3f}um")
(out/'b3_station_receipt.json').write_text(json.dumps(station_receipt,indent=1))
B=S.Plan(raw);base,_=m.uncompose(json.load(open(plan)));A=S.Plan(base)
dl={n:B.lane_natural(n)["cycles"]-A.lane_natural(n)["cycles"] for n in B.lanes};dl={n:v for n,v in dl.items() if v}
src=out/"plan_source.json";src.write_text(json.dumps(raw,indent=1))
new,sc=CL.compose(raw,json.load(open(cross)),plan_path=str(src),observer_part=m.OBS_PART,observer=dict(m.OBS),band_order_by_type=orders)
(out/"plan_composed.json").write_text(json.dumps(new,indent=1));(out/"sidecar.json").write_text(json.dumps(sc,indent=1))
N=S.Plan(new);sh={p:round(IO.edge_dist(N,next(z for z in new["die"]["io"] if z["part"]==p and z["iface"]=="serdes")["rect_um"]),3) for p in ("lk_ES0","lk_ES1")}
col=sc["collector"];res=dict(log=log,lane_natural_cycle_delta=dl,placement_failures=col["placement_failures"],max_die_hop_um=col["max_die_hop_um"],boot_ready=col["boot_budget"]["ready_at_glue_max_cycles"],shoreline_um=sh)
(out/"variant_b.json").write_text(json.dumps(res,indent=1));print(json.dumps(res,indent=1))
