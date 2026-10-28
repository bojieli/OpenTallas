"""probe: count-aligned TYPE_SPLIT consequences on the KV land128 plan (Landings, no RTL)"""
import json, sys
from collections import defaultdict
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import clock_landings as CL
plan = json.load(open(sys.argv[2])); tab = json.load(open(sys.argv[3]))
orig = CL.Landings._count_aligned_types
CL.Landings._count_aligned_types = lambda self, raise_split=False: orig(self, False)
L = CL.Landings(plan, tab, require_geometry=False)
rep = dict(L.ca_type_split)
# same per-type signature without the relay role (rings + origin role only): the splits K alone forces
per = defaultdict(set); per_norelay = defaultdict(set); per_mask = defaultdict(set)
for pn, r in L.ca_part_role.items():
    tn = L.parts[pn]["type"]
    rings = tuple((b, x["ring_k"], x["ring_depth"]) for b, x in sorted(L.ins[pn].items()))
    per_norelay[tn].add((rings, r["role"] if r["role"] != "relay" else "origin?"))
    per[tn].add((rings, r["role"], r["relay_tx"]))
    per_mask[tn].add((r["role"], r["relay_tx"]))
per_rings = defaultdict(set); per_k0 = defaultdict(set)
for pn, r in L.ca_part_role.items():
    tn = L.parts[pn]["type"]
    per_rings[tn].add(tuple((b, x["ring_k"], x["ring_depth"]) for b, x in sorted(L.ins[pn].items())))
    per_k0[tn].add((tuple((b, x["ring_k"], x["ring_depth"]) for b, x in sorted(L.ins[pn].items())),
                    r["role"] if r["role"] != "relay" else "child-like"))
rep["type_count_after_rings_only"] = sum(len(v) for v in per_rings.values())
rep["types_with_landed_parts"] = len(per)
rep["types_split_by_relay_role_alone"] = sum(1 for tn in per_mask if len(per_mask[tn]) > 1)
rep["types_needing_split_without_relay_role"] = sum(1 for tn in per_norelay if len(per_norelay[tn]) > 1)
rep["type_count_after_without_relay_role"] = sum(len(v) for v in per_norelay.values())
roles = defaultdict(int)
for r in L.ca_part_role.values():
    roles[r["role"] + ("+tx" if r["relay_tx"] else "")] += 1
rep["partition_roles"] = dict(roles)
rep["partition_types_in_plan"] = len(L.types)
print(json.dumps(rep, indent=1))
