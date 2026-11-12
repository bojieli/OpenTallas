"""SC-REFLOOR-1 paper estimate: insert a DX-wide strip at the W face of every sc type (outline +DX, every type-frame
x coordinate +DX, W-face windows unchanged in y).  usage: widen.py IN.json OUT.json DX"""
import json, sys
P = json.load(open(sys.argv[1])); DX = float(sys.argv[3])
def sh(o, k=None):
    if isinstance(o, dict):
        for kk, v in o.items():
            if kk in ("outline_um", "window_um", "out_window_um", "in_window_um", "width", "bit_site_cell_um"):
                continue
            if kk in ("rect_um", "origin_rect_um", "resized_from_um") and isinstance(v, list) and len(v) == 4:
                v[0] += DX; v[2] += DX; continue
            sh(v, kk)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(x, (int, float)) for x in o):
            if o[0] > 1e-6:          # keep points ON the W face on the face
                o[0] += DX
        else:
            for v in o: sh(v)
for n, t in P["partition_types"].items():
    if "_sc_" not in n: continue
    t["outline_um"][0] += DX
    sh({k: v for k, v in t.items() if k != "outline_um"})
    for b in t.get("buses", []):
        if b.get("face") in ("N", "S") and b.get("window_um"):
            b["window_um"] = [b["window_um"][0] + DX, b["window_um"][1] + DX]
    for s in t["ft_slots"]:
        if s["out_face"] in "NS" and s.get("out_window_um"):
            s["out_window_um"] = [s["out_window_um"][0] + DX, s["out_window_um"][1] + DX]
json.dump(P, open(sys.argv[2], "w"))
