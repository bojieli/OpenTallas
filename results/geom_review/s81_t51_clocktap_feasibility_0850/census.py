#!/usr/bin/env python3
"""Read-only fixed-membership L1 feasibility; no tap target or source event."""
import json,gzip,hashlib,collections
from pathlib import Path
R=Path(__file__).parent;P=R/"inputs"
assign=json.load(gzip.open(P/"assignment.json.gz","rt"));byname={x["name"]:x["tap"] for x in assign}
contact=json.loads((P/"one_contact_target.json").read_text());assert len(contact)==1
for name,record in contact.items():
 assert byname[name]==record["old_proposed_tap"]=="clk_t17";byname[name]=record["explicit_proposed_tap"]
F=json.loads((P/"FF_targets.json").read_text());F.update(contact)
points=collections.defaultdict(list);seen=set()
for line in gzip.open(P/"cells.jsonl.gz","rt"):
 c=json.loads(line);name=c[0]
 if name not in byname:continue
 seen.add(name);bb=F[name]["bbox_dbu"] if name in F else c[2]
 centre=[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2]
 location=[bb[0]+c[3][0]-c[2][0],bb[1]+c[3][1]-c[2][1]]
 for kind,xy in [("centre",centre),("native_location",location)]:points[byname[name]].append(dict(name=name,kind=kind,xy_dbu=xy,u=xy[0]+xy[1],v=xy[0]-xy[1]))
assert len(seen)==len(byname)==39655
plan=json.loads((P/"current_plan.json").read_text());ck=plan["partition_types"]["slice_station__t51"]["clock"];assert ck["tap_radius_um"]==150 and ck["tap_max_sinks"]==1500
radius=150000.;records=[];badFF=set()
for t in ck["taps"]:
 if t.get("kind")=="core":continue
 ps=points[t["name"]];assert ps
 ex={key:fn(ps,key=lambda q:q[axis])for key,fn,axis in [("umin",min,"u"),("umax",max,"u"),("vmin",min,"v"),("vmax",max,"v")]}
 umin=ex["umax"]["u"]-radius;umax=ex["umin"]["u"]+radius;vmin=ex["vmax"]["v"]-radius;vmax=ex["vmin"]["v"]+radius
 tx,ty=[q*1000 for q in t["xy"]];u0,v0=tx+ty,tx-ty
 distances=[abs(q["xy_dbu"][0]-tx)+abs(q["xy_dbu"][1]-ty)for q in ps]
 for q,d in zip(ps,distances):
  if d>radius+1e-6:badFF.add(q["name"])
 feasible=umin<=umax and vmin<=vmax
 needed=max(0.,umin-u0,u0-umax,vmin-v0,v0-vmax)/1000 if feasible else None
 minradius=max(ex["umax"]["u"]-ex["umin"]["u"],ex["vmax"]["v"]-ex["vmin"]["v"])/2000
 records.append(dict(tap=t["name"],members=len(ps)//2,current_xy_um=t["xy"],current_max_radius_um=max(distances)/1000,fixed_membership_minimum_radius_um=minradius,feasible_at150=feasible,feasible_uv_bounds_dbu=[umin,umax,vmin,vmax],minimum_L1_node_jog_um=needed,extreme_witnesses=ex))
assert len(records)==73
out=dict(scope="READ ONLY fixed-membership clock-node feasibility on actual missionFFs, centres AND native locations, combined149342075+173repairs+explicitq496t32. No targets/site/PG/track/clock/reset/source event or native qualification.",members=39655,taps=73,radius_um=150,cap=1500,maximum_fixed_member_load=max(q["members"]for q in records),current_either_centre_or_location_bad_FFs=len(badFF),empty_fixed_membership_intersections=sum(not q["feasible_at150"]for q in records),node_movement_only_geometrically_feasible=sum(q["feasible_at150"]and q["current_max_radius_um"]>150+1e-9 for q in records),records=records,holds=["Some groups may need allowed reassignment or existing FF geometry changes; no150widening.","NonemptyUV is only a mathematical intersection, not a legal node site or activatedclockevent.","Nativeclockdomain remainsclk; actual Tcl binding/sourcephase and all other model/PG/NW holds remain."])
(R/"census.json").write_text(json.dumps(out,indent=1)+"\n")
print({k:v for k,v in out.items()if k not in ["records","holds"]})
