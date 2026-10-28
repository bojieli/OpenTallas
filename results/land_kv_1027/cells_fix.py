"""LAND-KV-1: G0C [cells] fix in the landed plan (structural: every type carries type.cells with a stated basis).
 - explicit-split types (kv3_pv_vKn, kv3_hg_v1pK; PATH-KV-BIND 10-25 splits of one parent, same contents modules):
   the parent type estimate (cells.py best source);
 - every soft type with landing rings (incl. cohort types <base>__cl*): base estimate + their landing rings, measured
   ot_dp_clk_landing count per ring = 4*(W+3)+124 flops + 612 cells per 64-bit chunk (yosys, LAND-KV-1).
usage: cells_fix.py LANDED_PLAN PLANDIR TOOLS_DIE_PLAN BASE_PLAN   (estimates come from the BASE plan, so a rerun is idempotent)"""
import json, sys, math, re
pl, pd, tools, basepl = sys.argv[1:5]
sys.path.insert(0, tools)
import cells as CE

P = json.load(open(pl))
est, _ = CE.estimate(json.load(open(basepl)), pd, ())


def ring_cells(w):
    wl = w + 1
    return 4 * (wl + 3) + 124 + 612 * math.ceil(wl / 64)


def parent(tn):
    m = re.match(r"^(kv3_pv_v\d+)n$", tn) or re.match(r"^(kv3_hg_v1)p\d+$", tn)
    return m.group(1) if m else None


fixed = []
for tn, t in P["partition_types"].items():
    bands = [c for c in t.get("clock", {}).get("landing_contract", {}).get("bands", {}).values()
             if isinstance(c, dict) and c.get("width")]
    if t.get("hard") or (est.get(tn, (None,))[0] is not None and not bands):
        continue
    if tn not in est and "__cl" not in tn and not parent(tn):
        continue  # estimated in the landed plan by its own source; not a split or cohort
    base, basis = tn, ""
    if "__cl" in base:
        base = base.split("__cl")[0]
        basis = f"landing cohort of {base}"
    src = base
    if est.get(src, (None,))[0] is None and parent(src):
        src = parent(src)
        basis = (basis + "; " if basis else "") + f"explicit split of {src} (same contents modules)"
    nc = est.get(src, (None,))[0]
    if nc is None:
        print("NO BASE", tn, base, src)
        continue
    rings = 0
    for c in bands:
        rings += ring_cells(int(c["width"]))
    t["cells"] = int(nc + rings)
    why = f"cells {t['cells']} = {basis or 'base'}: {src} {nc} ({est[src][1]}) + landing rings {rings} (LAND-KV-1 measured ring count)"
    t["note"] = (t.get("note", "").split(" | LAND-KV-1 cells")[0] + " | LAND-KV-1 " + why).lstrip(" |")
    fixed.append((tn, t["cells"], why))
json.dump(P, open(pl, "w"))
print("FIXED", len(fixed))
for x in fixed:
    print(" ", *x)
