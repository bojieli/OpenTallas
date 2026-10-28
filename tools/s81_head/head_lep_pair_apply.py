#!/usr/bin/env python3
"""DIE-HEAD-10 plan event LEP-C0: apply the LEP split plan delta (head_lep_pair_pack.py lep_pair_plan_delta.json) to the
HEAD die plan type hd_lep0N.

    python3 tools/s81_head/head_lep_pair_apply.py PLAN.json DELTA.json [--out PLAN_OUT.json]   (default: in place)

  * u_core (ot_s81hd_lep0N_noidx_core) gets params PAIR=1 (opt-in parameter of the LEP branch; PAIR=0 is the old form,
    wiring LEC PAIR0 vs PAIR1 18080/18080);
  * hard_cores[] = the 4 PAIR child placements (inst u_core.u.g_pp[k].u_pair, module ot_s81hd_lep_pair, origin /
    outline / orient from the delta).  No lef/lib yet: the child is not hardened, so kits leave it unplaced (gen_phys
    type_macros skips view-less cores) -- the plan carries the floorplan, the views follow the child kit;
  * contents[] += the 45 parent SRAM with lef / lib / origin_um / orient (status 'reuse': generated macros).
The 220 child SRAM stay in the delta's child_type (the child's own floorplan) until the child gets its core plan.
Idempotent: re-applying replaces the previous LEP-C0 entries.
"""
import argparse
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def lef_wh(lef):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", (ROOT / lef).read_text())
    return [float(m.group(1)), float(m.group(2))]

TAG = "DIE-HEAD-10 LEP-C0"
LATTICE = 8.64      # G0C hard-core origin lattice; the sub-lattice part goes in track_offset_um


def apply(plan, delta):
    t = plan["partition_types"]["hd_lep0N"]
    core = next(c for c in t["contents"] if c["inst"] == "u_core")
    if core["module"] != "ot_s81hd_lep0N_noidx_core":
        raise SystemExit(f"hd_lep0N u_core is {core['module']}, expected ot_s81hd_lep0N_noidx_core")
    core.setdefault("params", {})["PAIR"] = int(delta["parent_type"]["params"]["PAIR"])
    t["contents"] = [c for c in t["contents"] if TAG not in c.get("note", "")]
    for c in delta["parent_type"]["contents"]:
        t["contents"].append({"inst": c["inst"], "module": c["module"], "status": "reuse", "origin_um": c["origin_um"],
                              "outline_um": lef_wh(c["lef"]), "orient": c["orient"], "lef": c["lef"], "lib": c["lib"], "note": f"{TAG}: {c['note']}"})
    t["hard_cores"] = [h for h in t.get("hard_cores", []) if TAG not in h.get("note", "")]
    for h in delta["parent_type"]["hard_cores"]:
        lat = [round(math.floor(v / LATTICE + 1e-9) * LATTICE, 2) for v in h["origin_um"]]
        off = [round(v - l, 3) for v, l in zip(h["origin_um"], lat)]
        t["hard_cores"].append({"inst": h["inst"], "module": h["module"], "origin_um": lat, "track_offset_um": off,
                                "outline_um": h["outline_um"], "orient": h["orient"],
                                "note": f"{TAG}: {h['note']} (no view yet: child kit pending)"})
    return dict(pair=core["params"]["PAIR"], parent_sram=len(delta["parent_type"]["contents"]),
                hard_cores=len(delta["parent_type"]["hard_cores"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("delta")
    ap.add_argument("--out")
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    r = apply(plan, json.loads(Path(a.delta).read_text()))
    Path(a.out or a.plan).write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(r))


if __name__ == "__main__":
    main()
