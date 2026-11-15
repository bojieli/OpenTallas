#!/usr/bin/env python3
"""DIE-QC-103 (hop formula + cl_* skip: QC-CB-GEN-1115): deepen the cb landing bands (clock.landing_contract.bands.<bus>) so the ring flops reach density DENS.
usage: gen_cb_strip.py BASE_PLAN OUT_ROWS OUT_PLAN [--dens 0.45]   FLOPS_PER_RING_BIT = 5400/576 (QC-CB-GEN measured ~5.4k per ring)"""
import json, sys, math, copy
base, out_rows, out_plan = sys.argv[1:4]
DENS = float(sys.argv[sys.argv.index("--dens")+1]) if "--dens" in sys.argv else 0.45
FPB = 5400/576.0; G = 2.16
plan = json.load(open(base)); pt = plan["partition_types"]; rows = {}; rep = []
def pin_xy(face, win, W, H):
    """centre of a bus pin window on its face: S y=0, N y=H, W x=0, E x=W (the window is the span along the face)"""
    c = sum(win) / 2.0
    return {"S": (c, 0.0), "N": (c, H), "W": (0.0, c), "E": (W, c)}[face]


def ov(a, b, g):
    return min(a[2], b[2]) + g > max(a[0], b[0]) and min(a[3], b[3]) + g > max(a[1], b[1])
for tn, t in pt.items():
    if not tn.startswith("cb"): continue
    lc = (t.get("clock") or {}).get("landing_contract") or {}; bands = lc.get("bands") or {}
    W, H = t["outline_um"]
    cores = []
    for h in t.get("hard_cores", []) or []:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; cores.append([x, y, x+w, y+hh])
    for bn, old in list(bands.items()):
        if bn.startswith("monitor") or not old.get("rect_um"): continue
        # QC-CB-GEN-1115 (FABLE-PD-QC-1545 F3a): a cl_* band is a HARD-CORE ring (the band rect is the macro): a strip density key does not apply
        if bn.startswith("cl_") or any(abs(old["rect_um"][i] - c[i]) < 1.0 for c in cores for i in range(4)) and any(
                c[0] <= old["rect_um"][0] and c[1] <= old["rect_um"][1] and c[2] >= old["rect_um"][2] and c[3] >= old["rect_um"][3] for c in cores):
            rep.append((tn, bn, "hard-core ring", old["rect_um"])); continue
        n = old["ring_width"] * FPB; need = n / DENS
        have = (old["rect_um"][2]-old["rect_um"][0])*(old["rect_um"][3]-old["rect_um"][1])
        if have >= need: rep.append((tn, bn, "ok", round(n/have, 2))); continue
        x0, y0, x1, y1 = old["rect_um"]; others = [v["rect_um"] for k, v in bands.items() if k != bn and v.get("rect_um")] + cores
        best = None
        # grow in y (deeper into the block) keeping x extent; then widen x symmetric up to 8 steps
        for wx in range(0, 40):
            xa, xb = max(17.28, x0 - wx*G), min(W - 17.28, x1 + wx*G)
            d = math.ceil(need/(xb-xa)/G)*G
            for sgn in (1, -1):
                box = [xa, y0, xb, y0+d] if sgn > 0 else [xa, y1-d, xb, y1]
                if box[1] < 17.28 or box[3] > H-17.28: continue
                if not any(ov(box, o, 1.5) for o in others): best = box; break
            if best: break
        if not best: rep.append((tn, bn, "NO FIT", round(need), round(have))); continue
        wb=[b for b in t.get("buses",[]) if b.get("name")==bn]
        if wb and wb[0].get("window_um"):
            # QC-CB-GEN-1115 (FABLE-PD-QC-1545 F3b): the hop runs from the bus's own face, not only the S face
            pxy = pin_xy(wb[0].get("face", "S"), wb[0]["window_um"], W, H)
            hop=max(abs(x-pxy[0])+abs(y-pxy[1]) for x in (best[0],best[2]) for y in (best[1],best[3]))
            if hop>403: rep.append((tn,bn,"NO FIT hop",round(hop))); continue
        nb = copy.deepcopy(old); nb["rect_um"] = [round(v, 6) for v in best]
        nb["area_reserve_um2"] = round((best[2]-best[0])*(best[3]-best[1]), 3)
        nb["resized_from_um"] = list(old["rect_um"])
        nb["resize"] = f"DIE-QC-103 cb strip: band deepened for cland_strip_density {DENS} (5.4k flops per ring)"
        bands[bn] = nb; rows.setdefault(tn, {})[f"clock.landing_contract.bands.{bn}"] = nb
        rep.append((tn, bn, old["rect_um"], nb["rect_um"], round(nb["area_reserve_um2"]), round(n/nb["area_reserve_um2"], 2)))
dens = dict(plan["budgets"].get("cland_strip_density_types") or {})
for b in ("cbf_", "cbn_", "cbx_"): pass
for tn in rows: dens[tn.split("__")[0]] = DENS
plan["budgets"]["cland_strip_density_types"] = dens
json.dump({"lane": "DIE-QC-103", "rows": rows, "die_rows": {"budgets.cland_strip_density_types": dens}}, open(out_rows, "w"), indent=1)
open(out_plan, "w").write(json.dumps(plan, indent=1) + "\n")
for r in rep: print(r)
