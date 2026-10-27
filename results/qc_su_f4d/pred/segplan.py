"""QC-SU-F4D: per-node planned leg length (um) from an f4_g4d plan JSON (G4 legs_um = shortest legal maze legs between
consecutive placed cells a -> r0 -> ... -> b).  Node names follow the f4_g4d spec: <edge>_r<j> for repeaters, <edge> for
the child node.  Falls back to Manhattan for nodes not in G4 (none expected)."""
import json
def seg_from_plan(plan_json, P0, man):
    g4 = json.load(open(plan_json))["gates"]["G4_strict"]["edges"]
    seg = {}
    for e in g4:
        legs = e["legs_um"]; nm = e["edge"]; nr = len(e.get("cells", []))
        assert len(legs) == nr + 1, (nm, legs, nr)
        for j in range(nr):
            seg[f"{nm}_r{j}"] = legs[j]
        seg[nm] = legs[-1]
    out, miss = {}, []
    for n, v in P0.nodes.items():
        if not v["par"]:
            continue
        m = man(v["xy"], P0.nodes[v["par"]]["xy"])
        if n in seg:
            out[n] = max(seg[n], m)
        else:
            out[n] = m; miss.append(n)
    return out, miss
