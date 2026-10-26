#!/usr/bin/env python3
"""Complete the missed S81 station geometry and clock-demand batch.

This source-only candidate never enables START on a released plan. It writes a
separate broadcast diagnostic and reports why physical launch remains blocked
until the parent bind and calendar carry the actual START protocol.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

TYPES = tuple(f"slice_station__t{n}" for n in (28,29,45,50,51,31,43,44,49,52))

def apply(raw, tools, controls, types=TYPES, checkpoint=None):
    sys.path.insert(0, str(tools))
    import ft_knee_sites as K
    sys.path.insert(0, str(controls))
    import delta_station_controls_1713 as D
    types=tuple(types)
    candidate=copy.deepcopy(raw)
    report={"types": list(types), "knee": [], "failures": {}}
    for name in types:
        trial=copy.deepcopy(candidate)
        try:
            rows=K.place(trial,[name])
        except (ValueError,IndexError) as exc:
            report["failures"][name]=str(exc)
            continue
        candidate=trial
        report["knee"].extend(rows)
        print("{}: {} slots, +{} slot cycles".format(name,len(rows),sum(r["added_cycles"] for r in rows)),flush=True)
        clock=candidate["partition_types"][name].setdefault("clock",{})
        clock.update(tap_mode="density",tap_target_sinks=600,
                     tap_max_sinks=1500,tap_radius_um=150.)
    names=[name for name in types if name not in report["failures"]]
    # Regenerate the inventory on final geometry, including the reset entry.
    # The current released plan has no START field; retain that contract and
    # explicitly label the separate broadcast result as diagnostic only.
    if checkpoint is not None:
        Path(checkpoint).write_text(json.dumps(candidate,indent=1)+"\n")
    reset_only=copy.deepcopy(candidate)
    report["reset_only"]=D.apply(reset_only,names,require_start=False)
    broadcast=copy.deepcopy(candidate)
    broadcast.setdefault("reset",{})["start"]="broadcast"
    report["broadcast_diagnostic"]=D.apply(broadcast,names)
    report["route_authorized"]=False
    report["route_blocker"]="START protocol must be present in generated parent RTL, bind and token calendar before this broadcast diagnostic can be adopted."
    report["added_cycles_by_slot"]={r["type"]+"/"+r["slot"]:r["added_cycles"] for r in report["knee"] if r["added_cycles"]}
    report["added_flops"]=sum(r["added_flops"] for r in report["knee"])
    import schema as S
    import gen as G
    before=G.latency_table(S.Plan(raw))
    after=G.latency_table(S.Plan(reset_only))
    report["lane_latency_delta"]={name:dict(before=before[name]["cycles"],after=val["cycles"],delta=val["cycles"]-before[name]["cycles"]) for name,val in after.items() if val["cycles"]!=before[name]["cycles"]}
    reset_only["latency"]={"lanes":after}
    broadcast["latency"]={"lanes":G.latency_table(S.Plan(broadcast))}
    return reset_only,broadcast,report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan",type=Path)
    ap.add_argument("out",type=Path)
    ap.add_argument("--tools",type=Path,default=Path(__file__).resolve().parents[3]/"tools/die_plan")
    ap.add_argument("--controls",type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument("--types",help="comma-separated types; default is the ten missing station types")
    args=ap.parse_args()
    raw=json.loads(args.plan.read_text())
    args.out.mkdir(parents=True,exist_ok=True)
    candidate,broadcast,report=apply(raw,args.tools,args.controls,args.types.split(",") if args.types else TYPES,args.out/"geometry_only.json")
    for name,payload in (("die_plan.json",candidate),("broadcast_diagnostic.json",broadcast),("station_delta_report.json",report)):
        (args.out/name).write_text(json.dumps(payload,indent=1)+"\n")
    print(json.dumps({k:report[k] for k in ("types","failures","added_cycles_by_slot","added_flops","route_authorized")}),flush=True)

if __name__=="__main__": main()
