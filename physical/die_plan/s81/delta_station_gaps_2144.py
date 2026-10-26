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
import traceback

TYPES = tuple(f"slice_station__t{n}" for n in (28,29,45,50,51,31,43,44,49,52))

def apply(raw, tools, controls, types=TYPES, checkpoint=None, include_st3=False, whole_die_ledger=False, plan_path=None):
    sys.path.insert(0, str(tools))
    import ft_knee_sites as K
    sys.path.insert(0, str(controls))
    import delta_station_controls_1713 as D
    plan_path=plan_path or Path(__file__).resolve().parent/"die_plan.json"
    types=tuple(types)
    candidate=copy.deepcopy(raw)
    report={"types": list(types), "knee": [], "failures": {}}
    census_types=types
    if include_st3:
        import delta_kitsspare3_1025 as ST3
        legacy={}
        legacy_types=tuple(ST3.STATION_TYPES)+("slice_station__t46",)
        ST3.stations(candidate,legacy,legacy_types)
        report["legacy_st3"]=legacy
        report["knee"].extend(legacy["knee"])
        report["failures"].update(legacy["skipped"])
        census_types=tuple(dict.fromkeys(types+legacy_types))
        report["types"]=list(census_types)
    def progress():
        if checkpoint is not None:
            Path(checkpoint).with_name("geometry_progress.json").write_text(json.dumps(report,indent=1)+"\n")
    for name in types:
        trial=copy.deepcopy(candidate)
        try:
            rows=K.place(trial,[name])
        except (ValueError,IndexError) as exc:
            report["failures"][name]=str(exc)
            print("FAIL {}: {}".format(name,exc),flush=True)
            traceback.print_exc()
            progress()
            continue
        candidate=trial
        report["knee"].extend(rows)
        print("{}: {} slots, +{} slot cycles".format(name,len(rows),sum(r["added_cycles"] for r in rows)),flush=True)
        clock=candidate["partition_types"][name].setdefault("clock",{})
        clock.update(tap_mode="density",tap_target_sinks=600,
                     tap_max_sinks=1500,tap_radius_um=150.)
        progress()
    names=[name for name in census_types if name not in report["failures"]]
    # Regenerate the inventory on final geometry, including the reset entry.
    # The current released plan has no START field; retain that contract and
    # explicitly label the separate broadcast result as diagnostic only.
    if checkpoint is not None:
        Path(checkpoint).write_text(json.dumps(candidate,indent=1)+"\n")
    reset_only=copy.deepcopy(candidate)
    initial_wave=None
    reset_wave={} if whole_die_ledger else None
    start_wave={} if whole_die_ledger else None
    if whole_die_ledger:
        print("Computing original whole-die wavefront contract",flush=True)
        initial_wave=D.RT.wf_plan(D.S.Plan(raw,path=plan_path))
    print("Computing joint RESET control-demand fixed point",flush=True)
    report["reset_only"]=D.apply(reset_only,names,require_start=False,waveform=reset_wave,plan_path=plan_path)
    broadcast=copy.deepcopy(candidate)
    broadcast.setdefault("reset",{})["start"]="broadcast"
    print("Computing joint RESET+START diagnostic fixed point",flush=True)
    report["broadcast_diagnostic"]=D.apply(broadcast,names,waveform=start_wave,plan_path=plan_path)
    if whole_die_ledger:
        def delta(wave):
            rows={}
            for name,after in wave["parts"].items():
                before=initial_wave["parts"][name]
                core={key:dict(before=before.get("core_release",{}).get(key),after=value)
                      for key,value in after.get("core_release",{}).items()
                      if before.get("core_release",{}).get(key)!=value}
                if before["release"]!=after["release"] or before["parent"]!=after["parent"] or core:
                    rows[name]=dict(type=after["type"],before=before["release"],after=after["release"],
                                   delta=after["release"]-before["release"],parent_before=before["parent"],
                                   parent_after=after["parent"],core_release_changes=core)
            pins={name:dict(before=initial_wave["types"][name]["in_um"],after=ty["in_um"])
                  for name,ty in wave["types"].items()
                  if initial_wave["types"][name]["in_um"]!=ty["in_um"]}
            return dict(parts_compared=len(wave["parts"]),unchanged_parts=len(wave["parts"])-len(rows),
                        max_release_before=initial_wave["max_release"],max_release_after=wave["max_release"],
                        partition_changes=rows,reset_entry_pin_changes=pins,
                        unreachable=wave["unreachable"],long_hops=wave["long_hops"])
        report["whole_die_reset_delta"]=delta(reset_wave)
        report["whole_die_start_delta"]=delta(start_wave)
        report["whole_die_start_delta"]["offset_rule"]="START at die edge S reaches each soft partition at S+its final release offset; hard partitions retain raw reset, and bootstrap roles use explicit mission admission."
        report["whole_die_start_delta"]["scope"]="START-enabled geometry diagnostic; generated parent RTL/bind/token admission remain unqualified."

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
    ap.add_argument("--include-st3",action="store_true",help="also apply the original thirteen ST3 station treatments, preserving their five accepted clock-only geometries")
    ap.add_argument("--whole-die-ledger",action="store_true",help="compare every partition/core release and reset entry pin against the original plan; implied by --include-st3")
    ap.add_argument("--plan-context",type=Path,help="reference plan path whose directory contains the declared relative core pin tables (default: this script directory/die_plan.json)")
    args=ap.parse_args()
    raw=json.loads(args.plan.read_text())
    args.out.mkdir(parents=True,exist_ok=True)
    candidate,broadcast,report=apply(raw,args.tools,args.controls,args.types.split(",") if args.types else TYPES,args.out/"geometry_only.json",args.include_st3,args.whole_die_ledger or args.include_st3,args.plan_context)
    for name,payload in (("die_plan.json",candidate),("broadcast_diagnostic.json",broadcast),("station_delta_report.json",report)):
        (args.out/name).write_text(json.dumps(payload,indent=1)+"\n")
    print(json.dumps({k:report[k] for k in ("types","failures","added_cycles_by_slot","added_flops","route_authorized")}),flush=True)
    if report["failures"]:
        raise SystemExit(1)

if __name__=="__main__": main()
