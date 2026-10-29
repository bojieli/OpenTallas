#!/usr/bin/env python3
"""HEAD-KITS-1: kit land_slots.json (face_guard --land) from the kit landing_contract.json.

Every landing band <b> of the contract is a declared landing-ring input bus with D = forwarded_write_flops / ring_width
slots (hold_mux slot form, as DIE-HEAD-9 face/land_slots_hd_tile.json), and so are its in-band monitor inputs
cland_dn_ready_<b> / cland_dn_fault_<b> when the contract declares them.  face_guard still proves every slot flop
(D loads per bit, own-Q hold, write condition) on the netlist; this only declares which buses are landing buses."""
import json, sys
from pathlib import Path


def land_slots(contract):
    pins = {p["name"] for p in contract.get("pins", []) if p.get("dir") == "in"}
    buses = {}
    for b, v in sorted(contract.get("bands", {}).items()):
        w, fw = int(v["ring_width"]), int(v["clock_roles"]["forwarded_write_flops"])
        if fw % w or fw // w < 2:
            raise SystemExit(f"band {b}: forwarded_write_flops {fw} / ring_width {w} is not a slot count >= 2")
        spec = {"D": fw // w, "form": "hold_mux"}
        buses[b] = spec
        for m in ("ready", "fault"):
            if f"cland_dn_{m}_{b}" in pins:
                buses[f"cland_dn_{m}_{b}"] = dict(spec)
    return {"schema": "opentallas.land_slots.v1", "buses": buses}


if __name__ == "__main__":
    for kd in map(Path, sys.argv[1:]):
        c = json.loads((kd / "landing_contract.json").read_text())
        (kd / "land_slots.json").write_text(json.dumps(land_slots(c), indent=1, sort_keys=True) + "\n")
        print(kd / "land_slots.json", len(land_slots(c)["buses"]))
