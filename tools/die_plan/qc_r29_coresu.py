"""Owned R29 SU exact interfaces and collective face-memory declarations.

Apply only these owned fields to the coordinator's combined main-68 event.
No partition type, outline, station count or data cycle is added.
"""
import copy,json,re
from pathlib import Path
FACE_BINDINGS={
 "coll_core":{"u_coll_face_p":"u_io_collective_u_io_g_face_0_u_face","u_coll_face_r":"u_io_collective_u_io_g_face_1_u_face"},
 "coll_s":{"u_coll_face_s1":"u_g_face_3_u_face","u_coll_face_s2":"u_g_face_4_u_face"},
 "coll_n":{"u_coll_face_s0":"u_core"},
}
MEMORY_LAYOUT=[
 ("g_codec.u_codec.g_bank[0].u_store.u_sram","ot_sram_1r1w_64x512_m1_r2c2",[7.776,25.92],[171.288,77.784]),
 ("g_codec.u_codec.g_bank[1].u_store.u_sram","ot_sram_1r1w_64x512_m1_r2c2",[285.12,25.92],[171.288,77.784]),
 ("g_codec.u_codec.g_bank[2].u_store.u_sram","ot_sram_1r1w_64x512_m1_r2c2",[7.776,146.88],[171.288,77.784]),
 ("g_codec.u_codec.g_bank[3].u_store.u_sram","ot_sram_1r1w_64x512_m1_r2c2",[285.12,146.88],[171.288,77.784]),
 ("u_rx.u_mem","ot_sram_1r1w2c_64x546_m1",[7.776,267.84],[178.632,81]),
 ("u_tx.u_mem","ot_sram_1r1w2c_64x546_m1",[285.12,267.84],[178.632,81]),
]
def apply(plan):
 p=copy.deepcopy(plan);report={"su":[],"face_memories":[],"added_cycles":0}
 for side in ["w","e"]:
  for block in [0,1]:
   tn=f"sl{side}_su_l{block}";t=p["partition_types"][tn]
   for hc in t["hard_cores"]:
    m=re.fullmatch(r"u_lane([0-7])",hc["inst"])
    if not m:raise ValueError(f"{tn}: unexpected SU core {hc['inst']}")
    lane=int(m[1]);name=f"qfd_qc_su_lane_{side}_l{lane}"
    hc["module"]=name
    hc["pins_file"]=f"cores/su_exact_narrow/{tn}_{hc['inst']}_pins.json"
    hc["note"]="Exact five-source SU group; lane0 output constants removed with parent reconstruction; unchanged source state and cycles."
    contracts=json.loads((Path(__file__).resolve().parents[2]/"physical/die_plan/qwen_compute/cores/su_exact_narrow/group_contracts.json").read_text())
    hc["bound_group"]=copy.deepcopy(contracts[name])
    if lane==0:
     hc["bound_group"]["constant_outputs"]="su_lane0_zero24"
    report["su"].append(dict(type=tn,inst=hc["inst"],module=name,narrowed=lane==0))
 for tn,mapping in FACE_BINDINGS.items():
  t=p["partition_types"][tn]
  # Existing declarations are never silently replaced or duplicated.
  for face,bound in mapping.items():
   matches=[c for c in t["contents"] if c["inst"]==face and c["module"]=="qfd_coll_static_face"]
   if len(matches)!=1:raise ValueError(f"{tn}: missing exact face {face}")
   origin=matches[0]["origin_um"]
   for suffix,master,rel,size in MEMORY_LAYOUT:
    inst=f"u_bound.{bound}.{suffix}"
    if any(c["inst"]==inst for c in t["contents"]):raise ValueError(f"duplicate face SRAM {inst}")
    xy=[round(origin[i]+rel[i],6) for i in range(2)]
    if any(xy[i]<5.4 or xy[i]+size[i]+5.4>t["outline_um"][i] for i in range(2)):
     raise ValueError(f"{tn}: memory halo outside outline {inst}")
    d=f"physical/asap7_memory_macros_v2/{master}"
    t["contents"].append(dict(inst=inst,module=master,status="reuse",origin_um=xy,outline_um=size,
       orient="R0",lef=f"{d}/{master}.lef",lib=f"{d}/{master}_tt.lib",
       note="Actual static-face memory (FW514 pads to the same546-bit CDC SRAM); 5.4um halo. Placement template from native10058cc, bound instance from exact QC kit-RTL. No timing qualification."))
    report["face_memories"].append(dict(type=tn,face=face,inst=inst,master=master,xy=xy))
 return p,report
if __name__=="__main__":
 import argparse
 a=argparse.ArgumentParser();a.add_argument("plan",type=Path);a.add_argument("out",type=Path);a.add_argument("--report",type=Path,required=True)
 o=a.parse_args();p,r=apply(json.loads(o.plan.read_text()));o.out.write_text(json.dumps(p,indent=1)+"\n");o.report.write_text(json.dumps(r,indent=1)+"\n")
