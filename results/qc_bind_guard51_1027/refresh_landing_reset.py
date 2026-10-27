"""Refresh a composed landing collector against its current physical reset plan.
Keeps the carrier graph and data-cycle ages; reports all changed control contracts.
"""
import copy,json,sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools/die_plan"))
import schema as S,reset_tree as RT,clock_landing_plan as CLP
src=ROOT/"physical/die_plan/qwen_compute/candidate_guard51_native100_io.json"
raw=json.load(open(src));P=S.Plan(raw,src);W=RT.wf_plan(P)
oldfile=ROOT/"physical/die_plan/qwen_compute/bind/land_r8_1026/clock_landing_vertical4_phase.json"
side=json.load(open(oldfile));C=side["collector"];infos=C["types"]
changed=[]
def hardxy(pn):return infos[P.parts[pn]["type"]]["tree"]["root"]
for tn,info in infos.items():
 old=info.get("tree")
 if not old or old.get("hard"):continue
 tree=RT.for_type(P,tn)
 if tree!=old:changed.append(tn)
 info["tree"]=tree
 taps={int(r["q"].split("rst_n_t")[1]):r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
 for s in info["local_sources"]:
  point=s.get("pin_xy_um",s["xy_um"])
  tap=min(range(tree["n_clock_taps"]),key=lambda i:sum(abs(a-b) for a,b in zip(taps[i],point)))
  if sum(abs(a-b) for a,b in zip(taps[tap],point))>405:
   b=s["band"]["rect_um"];point=[(b[0]+b[2])/2,(b[1]+b[3])/2]
   tap=min(range(tree["n_clock_taps"]),key=lambda i:sum(abs(a-b) for a,b in zip(taps[i],point)))
  s["tap"]=tap;s["xy_um"]=point
 pn=next(p for p,q in P.parts.items() if q["type"]==tn)
 if info.get("up_parent"):
  e=CLP._monitor_endpoints(P,W,pn,info["up_parent"],hardxy)
  info["collector_root_node"]=e["src_node"];info["collector_root_xy"]=e["src_xy"]
 else:
  node="rst_n_t"+str(RT.leaf_tap(P,tn))
  info["collector_root_node"]=node
  info["collector_root_xy"]=next(r["xy"] for r in tree["relays"] if r["q"]==node)
 for c in info["children"]:
  e=CLP._monitor_endpoints(P,W,c["part"],pn,hardxy)
  c["node"]=e["dst_node"];c["xy_um"]=e["dst_xy"]
# Check that all collector source/edge routes remain within the physical reach.
import landing_collector as LC
depths={};fail=[]
for pn,row in C["parts"].items():
 if not row["active"]:continue
 info=infos[row["type"]];tree=info["tree"]
 if tree.get("hard"):depths[pn]=len(tree["relays"])+1;continue
 sources=copy.deepcopy(info["local_sources"])+[dict(name=c["part"],ready=c["ready"],fault=c["fault"],node=c["node"],xy_um=c["xy_um"]) for c in info["children"]]
 try:
  # Declare raw terminal copies only for this geometry/depth calculation.
  body="\n".join("wire "+LC.raw(r["q"])+";" for r in tree["relays"])
  result=LC.build_local(tree,sources,body,root_node=info["collector_root_node"])
  depths[pn]=result["depth"]
 except ValueError as e:fail.append(dict(part=pn,error=str(e)))
actual_children=defaultdict(list)
for e in C["edges"]:actual_children[e["dst"]].append(e)
deadlines={}
def deadline(pn):
 if pn in deadlines:return deadlines[pn]
 inf=infos[P.parts[pn]["type"]]
 child=[deadline(c["src"])+(21 if c["seam"] else 0) for c in actual_children[pn]]
 deadlines[pn]=max([W["max_release"]+21]+child)+depths[pn]
 return deadlines[pn]
if not fail:
 C["boot_budget"].update(raw_reset_release_max_cycles=W["max_release"],local_registered_depths=depths,ready_at_glue_max_cycles=deadline(C["root"]))
C["reset_max_release"]=W["max_release"]
receipt=dict(changed_types=changed,geometry_errors=fail,old_boot_budget=json.load(open(oldfile))["collector"]["boot_budget"],new_boot_budget=C["boot_budget"],data_cycles_added=0)
out=ROOT/"results/qc_bind_guard51_1027"
(out/"landing_reset_refresh.json").write_text(json.dumps(receipt,indent=1)+"\n")
if fail:
 print(json.dumps(receipt));raise SystemExit(1)
target=ROOT/"physical/die_plan/qwen_compute/bind/land_r8_1026/clock_landing_current_guard51.json"
target.write_text(json.dumps(side,indent=1)+"\n")
print(json.dumps(dict(changed_types=len(changed),geometry_errors=0,ready_at_glue=deadline(C["root"]))))
