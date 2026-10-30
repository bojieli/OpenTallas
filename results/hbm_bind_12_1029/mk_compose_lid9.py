#!/usr/bin/env python3
"""HBM-BIND-12: re-shape the as-built SU 4-lane cuts' lane id to the plan's canon kit pin (fail-closed).

Source: ot_hbm_su_static_pgslice_s.sv drives each lane's .lane_id(11'(lid(n))), lid(n) = n<16 ? 16G+n : 64+16G+(n-16);
a 4-lane cut holds lanes n = 4j..4j+3, so the 4 ids are {B, 2'd0..3} with one 9-bit base B.  The plan canon kits
(lanes_plain__canon_663526, lanes__canon_cf1e77; mk_canon_wrappers.py) expose lane_lane_id[8:0] and wire lane k's id
as {lane_lane_id, 2'd<k>}.  The Codex native compose (native_compounds.py) exposes all 44 literal bits instead.
This script rewrites ONLY those cuts whose plan hard core declares parent_id_straps lane_lane_id width 9:
  lane_lane_id[i] (i = 0..8) = alias of the 4 lanes' lane_id[i+2] (bind_compose requires identical original values),
  lane_id[1:0] of lane k stay unexposed member terminals -> bind_compose keeps their as-built literals (= k) inside.
The bound strap value is then checked by bind.py validate_bound_id_bits against the as-built literals.
usage: mk_compose_lid9.py COMPOSE_IN MAP PLAN COMPOSE_OUT REPORT"""
import json, sys
src, mapf, planf, dst, repf = sys.argv[1:6]
C = json.load(open(src)); MP = json.load(open(mapf))["parts"]; P = json.load(open(planf))
OLD, NEW = "ot_hnx_su_plain4__7dd6a1bbbf47", "ot_hnx_su_plain4__lid9"
ptype = {p["name"]: p["type"] for p in P["partitions"]}
rep = dict(changed=[], kept=[])
for core in C["cores"]:
    if core["module"] != OLD:
        continue
    part, pinst = MP[core["inst"]]
    t = P["partition_types"][ptype[part]]
    ds = [d for d in t.get("hard_cores", []) + t.get("contents", []) if d["inst"] == pinst]
    assert len(ds) == 1, (core["inst"], pinst, len(ds))
    decl = (ds[0].get("parent_id_straps") or {}).get("lane_lane_id")
    if decl is None:
        rep["kept"].append(dict(inst=core["inst"], plan=[part, pinst, ds[0]["module"]], reason="no plan lane_lane_id strap"))
        continue
    assert decl["width"] == 9, decl
    bits = core["ports"]["lane_lane_id"]["bits"]
    assert core["ports"]["lane_lane_id"]["dir"] == "input" and len(bits) == 44, len(bits)
    assert all(len(b) == 1 and b[0]["port"] == "lane_id" for b in bits)
    lanes = []
    for k in range(4):
        grp = [b[0] for b in bits[11 * k:11 * k + 11]]
        assert len({a["member"] for a in grp}) == 1 and [a["bit"] for a in grp] == list(range(11)), core["inst"]
        lanes.append(grp[0]["member"])
    assert len(set(lanes)) == 4
    core["ports"]["lane_lane_id"]["bits"] = [[dict(member=m, port="lane_id", bit=i + 2) for m in lanes] for i in range(9)]
    core["module"] = NEW
    rep["changed"].append(dict(inst=core["inst"], plan=[part, pinst, ds[0]["module"]], declared=decl, lanes=lanes))
assert rep["changed"], "nothing to change"
json.dump(C, open(dst, "w"))
rep.update(n_changed=len(rep["changed"]), n_kept=len(rep["kept"]), old_module=OLD, new_module=NEW)
json.dump(rep, open(repf, "w"), indent=1)
print("changed", len(rep["changed"]), "kept", len(rep["kept"]), [k["inst"] for k in rep["kept"]])
