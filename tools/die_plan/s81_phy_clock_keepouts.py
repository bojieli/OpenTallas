#!/usr/bin/env python3
"""Apply published PHY rectangles as clock keepouts to a candidate S81 plan.

The existing grid+sinks recentrer removes empty displaced drops and retains
real sink-budget coverage. This changes clock/reset interfaces and therefore
belongs only in the combined S81 plan delta, never an isolated kit ECO.
"""
import argparse
import json
from pathlib import Path
import schema as S


def apply(raw, plan_path):
    p = S.Plan(raw, plan_path)
    changes = {}
    for domain in p.die.get("pg", {}).get("domains", []):
        name = domain.get("name", "")
        if not name.startswith("phy_lk_"):
            continue
        pn = name[len("phy_"):]
        if pn not in p.parts:
            raise ValueError(f"PHY domain {name} has no corresponding partition")
        tn = p.parts[pn]["type"]
        x0,y0,x1,y1 = domain["rect_um"]
        corners = [p.to_type(pn, xy) for xy in [(x0,y0),(x0,y1),(x1,y0),(x1,y1)]]
        box = [round(min(q[0] for q in corners),6),round(min(q[1] for q in corners),6),
               round(max(q[0] for q in corners),6),round(max(q[1] for q in corners),6)]
        if tn in changes and changes[tn]["rect_um"] != box:
            raise ValueError(f"nonuniform PHY footprint for shared type {tn}")
        ck = raw["partition_types"][tn].setdefault("clock", {})
        if ck.get("tap_mode") not in (None,"grid+sinks","sinks"):
            raise ValueError(f"{tn}: review existing {ck.get('tap_mode')} clock before replacing it")
        keep = ck.setdefault("keepouts_um", [])
        if box not in keep:
            keep.append(box)
        ck["tap_recentre"] = "sinks"
        changes[tn] = dict(part=pn,rect_um=box,clock_interface_changed=True)
    return raw, dict(status="CANDIDATE_NOT_ADOPTED",types=len(changes),changes=changes,
                     data_cycles_added=0,requires="sink census, render, reset/START regeneration, bind and combined delta")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan",type=Path)
    ap.add_argument("out",type=Path)
    ap.add_argument("--report",type=Path,required=True)
    a = ap.parse_args()
    raw, report = apply(S.load(a.plan),a.plan)
    a.out.write_text(json.dumps(raw,indent=1)+"\n")
    a.report.write_text(json.dumps(report,indent=1)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="changes"}))


if __name__ == "__main__":
    main()
