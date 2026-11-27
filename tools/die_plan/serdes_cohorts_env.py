#!/usr/bin/env python3
"""SERDES-H-FORM (S81-SERDES-GEN 11-17): reset_cohort_model.py JSON -> Tcl env lines for clock_taps.tcl.

usage: serdes_cohorts_env.py MODEL.json OUT.tcl [EXISTING_OT_TAP_GROUP_FIXED]
Same mapping as the H17 hand stager (stage_H_clocks_1c.py): OT_SERDES_RELAY_COHORTS = groups' compiled relay ids ("a,b;c,d"),
OT_TAP_GROUP_FIXED += serdes_rst_<key>:<nearest light root tap>.  Fails closed when a group has no root candidate, a bbox over the
hop budget, or an unfit light-root group.
"""
import json
import sys
from pathlib import Path


def env_values(model, existing_fixed=""):
    if model.get("unfit_light_root_groups"):
        raise SystemExit(f"cohort model: unfit light-root groups {model['unfit_light_root_groups']}")
    groups = model["groups"]
    if not groups:
        raise SystemExit("cohort model: no groups")
    budget = float(model.get("hop_budget_um", 405.0)) + 1e-6
    max_cohort_ff = model.get("max_cohort_FF", 64)
    for g in groups:
        ff_count = g.get("FF_count")
        if type(ff_count) is not int or ff_count < 0:
            raise SystemExit(f"cohort model: group {g['key']} requires a nonnegative integer FF_count")
        if ff_count > max_cohort_ff:
            raise SystemExit(
                f"cohort model: group {g['key']} FF {ff_count} over the CTS sizing cap "
                f"{max_cohort_ff} (an atomic RRL+collector set; needs a relay split)"
            )
        if g["bbox_span_um"] > budget or not g["root_candidates"]:
            raise SystemExit(f"cohort model: group {g['key']} span {g['bbox_span_um']} roots {len(g['root_candidates'])}")
    cohorts = ";".join(",".join(str(i) for i in g["rrl_ids"]) for g in groups)
    rc = model.get("root_collector_groups", [])
    for g in rc:
        if g["bbox_span_um"] > budget or not g["root_candidates"]:
            raise SystemExit(f"cohort model: root collector {g['key']} span {g['bbox_span_um']} roots {len(g['root_candidates'])}")
    fixed = ",".join(f"serdes_rst_{g['key']}:{g['root_candidates'][0]['name']}" for g in groups + rc)
    return {"OT_SERDES_RESET_COHORT": "1", "OT_SERDES_RELAY_COHORTS": cohorts,
            "OT_TAP_GROUP_FIXED": (existing_fixed + "," if existing_fixed else "") + fixed}


def main(argv):
    model = json.loads(Path(argv[1]).read_text())
    vals = env_values(model, argv[3] if len(argv) > 3 else "")
    Path(argv[2]).write_text("".join(f'set ::env({k}) {{{v}}}\n' for k, v in vals.items()))
    print(f"OT_SERDES_COHORTS groups={len(model['groups'])} fixed_taps={len(vals['OT_TAP_GROUP_FIXED'].split(','))}")


if __name__ == "__main__":
    main(sys.argv)
