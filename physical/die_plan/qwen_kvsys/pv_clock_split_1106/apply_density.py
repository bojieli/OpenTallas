#!/usr/bin/env python3
"""Emit a fresh private PV density/affinity plan and its explicit clock ABI map."""
import argparse
import copy
import json
from pathlib import Path
import apply as entries


def produce(plan, event, sites, core_mode):
    name = event["type"]
    before = plan["partition_types"][name]
    if entries.digest(before) != event["base_type_sha256"]:
        raise ValueError("PV type differs from measured source")
    result = entries.apply(plan, event, "A") if core_mode == "early" else copy.deepcopy(plan)
    clock = result["partition_types"][name]["clock"]
    core_rows = [x for x in clock["taps"] if x.get("kind") == "core"]
    if len(core_rows) != 20 or clock.get("tap_max_sinks") != 1200 or clock.get("tap_radius_um") != 340:
        raise ValueError("source core inventory/capacity/radius differs")
    clock["tap_mode"] = "explicit"
    clock["taps"] = core_rows + [dict(name=row[0],xy=[row[1],row[2]],kind="glue") for row in sites]
    clock["sink_bins_file"] = "physical/die_plan/qwen_kvsys/pv_clock_split_1106/actual_main_clock_bins.json"
    clock["tap_chain_affinity"] = dict(radius_um=200,max_group=128)
    allowed = {"core_taps", "tap_mode", "taps", "sink_bins_file", "tap_chain_affinity"}
    if {k:v for k,v in before["clock"].items() if k not in allowed} != {k:v for k,v in clock.items() if k not in allowed}:
        raise ValueError("independent clock fields changed")
    restored = copy.deepcopy(result)
    restored["partition_types"][name]["clock"] = before["clock"]
    if restored != plan:
        raise ValueError("data/reset/START/global or unrelated type fields changed")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("--core-mode",choices=["internal","early"],default="internal")
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    source,output=Path(args.plan),Path(args.out)
    abi=output.with_name(output.stem+".clock_abi.json")
    if output.exists() or abi.exists() or source.resolve()==output.resolve():
        raise ValueError("all outputs must be fresh and distinct")
    root=Path(__file__).parent
    event=json.loads((root/"candidate.json").read_text())
    repaired=json.loads((root/"actual_density_repaired.json").read_text())
    result=produce(json.loads(source.read_text()),event,repaired["sites"],args.core_mode)
    output.write_text(json.dumps(result,indent=1)+"\n")
    mapping=json.loads((root/"clock_port_mapping.json").read_text())
    mapping["core_mode"]=args.core_mode
    mapping["extra_core_ports"]=event["core_entries"] if args.core_mode=="early" else []
    mapping["total_new_clock_ports"]=6+(20 if args.core_mode=="early" else 0)
    mapping["captured_reset_START_must_be_preserved"]=True
    abi.write_text(json.dumps(mapping,indent=1)+"\n")
    print(json.dumps(dict(plan=str(output),abi=str(abi),main_ports=166,core_mode=args.core_mode,
                          added_clock_ports=mapping["total_new_clock_ports"],added_data_cycles=0,
                          production_activation=False,timing_qualified=False)))


if __name__=="__main__":
    main()
