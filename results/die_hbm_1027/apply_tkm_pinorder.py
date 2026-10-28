#!/usr/bin/env python3
"""C20i plan delta (DIE-HBM-5, COORD 02:0x step (b)): tkm tile ins_b/ovf_b pin order to the datapath columns.
Measured (d25/d30 placements): the tile's capture columns follow slot s(k)=4*(k%86)+k//86 (Spearman 0.975/0.973),
not the bit order (0.256/0.267). The delta permutes the EXISTING x slots (no new sites: track/spacing legality kept):
bit k takes the s(k)-th smallest of the current x values, on tile ins_b (S), tile ovf_b (N, keeps ovf_b x == ins_b x
for the abutted chain), terminal-tile ins_b and the root's tile0 ins_b (N face), so every abutted pair stays aligned.
No RTL change. usage: apply_tkm_pinorder.py SRC_PLANDIR DST_PLANDIR"""
import json, sys, shutil, hashlib, pathlib
src, dst = map(pathlib.Path, sys.argv[1:3])
if not dst.exists(): shutil.copytree(src, dst, symlinks=True)
N, G = 344, 86
slot = lambda k: 4 * (k % G) + k // G
assert sorted(slot(k) for k in range(N)) == list(range(N))
P = json.loads((dst / "die_plan.json").read_text())
rep = {"rule": "bit k -> slot 4*(k%86)+k//86 of the current sorted x", "files": {}}
def permute(pins, prefix):
    sel = {int(q["name"][len(prefix) + 1:-1]): q for q in pins if q["name"].startswith(prefix + "[")}
    assert sorted(sel) == list(range(N)), (prefix, len(sel))
    xs = sorted(q["x"] for q in sel.values())
    old = {k: q["x"] for k, q in sel.items()}
    for k, q in sel.items(): q["x"] = xs[slot(k)]
    return {"bits": N, "moved": sum(1 for k in sel if sel[k]["x"] != old[k]),
            "max_dx_um": round(max(abs(sel[k]["x"] - old[k]) for k in sel), 3)}
want = {"tile_core__idpin__chain": ["tile_ins_b", "tile_ovf_b"], "tile_core__terminal_idpin__chain": ["tile_ins_b"],
        "tkm_m_tp192__root__chain": ["x_u_u_g_tiles_0_e86_u_tile_ins_b"]}
done = {}
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        pf = hc.get("pins_file") or ""
        key = next((k for k in want if k in pf), None)
        if not key: continue
        if pf not in done:
            pins = json.loads((dst / pf).read_text()); lst = pins.get("pins", pins) if isinstance(pins, dict) else pins
            r = {pre: permute(lst, pre) for pre in want[key]}
            if key == "tile_core__idpin__chain":      # chain alignment: ovf_b[k].x == ins_b[k].x after the delta
                xi = {q["name"][10:]: q["x"] for q in lst if q["name"].startswith("tile_ins_b[")}
                assert all(q["x"] == xi[q["name"][10:]] for q in lst if q["name"].startswith("tile_ovf_b["))
            npf = pathlib.Path(pf); npf = str(npf.parent / (npf.stem + "__po.json"))
            (dst / npf).write_text(json.dumps(pins, indent=1) + "\n"); done[pf] = npf; rep["files"][npf] = r
        hc["pins_file"] = done[pf]
assert len(done) == 3, done
P["note"] = P.get("note", "") + " | C20i-po (DIE-HBM-5): tkm ins_b/ovf_b pin order to datapath columns (slot permutation)"
txt = json.dumps(P, indent=1); (dst / "die_plan.json").write_text(txt)
sha = hashlib.sha256(txt.encode()).hexdigest(); (dst / "die_plan.sha256").write_text(sha + "  die_plan.json\n")
rep["sha"] = sha; (dst / "tkm_pinorder_report.json").write_text(json.dumps(rep, indent=1))
print(sha[:12], json.dumps(rep["files"]))
