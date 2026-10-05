#!/usr/bin/env python3
"""W12: the inter-tile wire budget behind the tile routes' --false-path-io.

Every tile port is registered on the tile side, and every wire between tiles, upper tree nodes and the spine is
a chain of corridor register stages (ot_qwen_me_array BD, NWS, TWS, ORD) whose count the floorplan sets from the
SS reach.  This record lists each connection's routed-distance estimate, its stages and the length per stage
against the reach (504 um a stage at 0.833 ns SS: W15's segment sweep), and names what the tile route leaves
untimed: the in-tile pin-to-register segments, reported by jobs/tile_corners.sh (corner_ss_in2reg.rpt) once a
route lands.

    python3 tools/qwen_rom_wire_budget_w12.py --floorplan F.json --out R.json
"""
import argparse, hashlib, json
from pathlib import Path

REACH_UM = 504.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floorplan", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    fp = json.loads(a.floorplan.read_text())
    rows = []
    for c in fp["connections"]:
        per = c["distance_um"] / max(1, c["stages"])
        rows.append(dict(name=c["name"], distance_um=c["distance_um"], stages=c["stages"], bits=c.get("bits"),
                         um_per_stage=round(per, 1), within_reach=per <= REACH_UM + 1e-6,
                         rtl_param=c.get("rtl_param")))
    rec = dict(schema="opentallas.qwen-rom-w12.wire-budget.v1", reach_um_per_stage=REACH_UM,
               reach_basis="W15 SS segment sweep at 0.833 ns (results/rtl/w15_collectives.json physical.wire_reach)",
               floorplan=str(a.floorplan), floorplan_sha256=hashlib.sha256(a.floorplan.read_bytes()).hexdigest(),
               tile_um=fp.get("tile_um"), connections=rows, all_within_reach=all(r["within_reach"] for r in rows),
               not_covered=[
                   "the in-tile pin-to-first-register and last-register-to-pin segments of each tile port (untimed "
                   "by the tile route's --false-path-io): jobs/tile_corners.sh reports them unconstrained at SS "
                   "(corner_ss_in2reg.rpt, corner_ss_reg2out.rpt); each must fit the budget a corridor stage leaves "
                   "for its last / first hop",
                   "the KV fill network (service bands -> tiles, kvw_*): not yet a floorplan connection",
                   "corridor stage distances are Manhattan estimates from macro placement, not a routed die"],
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("all_within_reach",)} | {"rows": [(r["name"][:40], r["um_per_stage"]) for r in rows]}, indent=1))


if __name__ == "__main__":
    main()
