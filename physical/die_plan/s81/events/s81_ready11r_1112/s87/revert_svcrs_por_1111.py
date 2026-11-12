"""DIE-S81-87 (DO_NOT_COUNT): COORD-approved ruling 11-11 (prov_1109 views never built): revert the svc_rs types hard-core
set to the pre-v5 POR b05c29bb. usage: revert_svcrs_por_1111.py IN.json OUT.json REPORT.json POR.json
Only hard_cores, contents, ft_slots and clock.taps of every type whose hard_cores reference prov_1109 are replaced from POR; outline_um,
ft_slots and everything die-level stay as in IN."""
import json, sys
inp, out, rep, por = sys.argv[1:5]
P = json.load(open(inp)); R = json.load(open(por))
done = {}
for t, v in P["partition_types"].items():
    if not any("prov_1109" in json.dumps(h) for h in v.get("hard_cores", [])):
        continue
    r = R["partition_types"][t]
    done[t] = dict(cores_before=len(v["hard_cores"]), cores_after=len(r["hard_cores"]), prov_refs_removed=sum("prov_1109" in json.dumps(h) for h in v["hard_cores"]))
    for k in ("hard_cores", "contents", "ft_slots"):
        v[k] = r[k]
    # slot pins that sit on the top edge of the POR outline follow the grown outline (outline_um stays as in IN)
    dh = v["outline_um"][1] - r["outline_um"][1]
    if dh:
        ph = r["outline_um"][1]
        def sh(pt):
            return [pt[0], round(pt[1] + dh, 4)] if pt[1] > ph - 5.0 else pt
        for fs in v["ft_slots"]:
            fs["regs_um"] = [sh(p) for p in fs["regs_um"]]
            if "bit_sites_um" in fs:
                fs["bit_sites_um"] = [[sh(p) for p in st] for st in fs["bit_sites_um"]]
    v["clock"]["taps"] = r["clock"]["taps"]   # core taps only; tap_um, edge_clocks, landing_contract stay at the grown outline
assert not any("prov_1109" in json.dumps(v.get("hard_cores", [])) for v in P["partition_types"].values())
json.dump(P, open(out, "w"), indent=1)
json.dump(dict(types=done, por=por), open(rep, "w"), indent=1)
print(len(done), "types reverted")
