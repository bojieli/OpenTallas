import json, sys
sys.path.insert(0, sys.argv[4] + "/tools/die_plan")
import landing_place as LP
A = json.load(open(sys.argv[1])); B = json.load(open(sys.argv[2]))
def frame(t):
    f = dict(outline=t["outline_um"], cores=[], buses=[], slots=[], taps=[], groups={}, collectors={})
    for h in t.get("hard_cores") or []:
        (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"): w, hh = hh, w
        f["cores"].append([h["inst"], ox, oy, w, hh])
    for b in t["buses"]: f["buses"].append([b["name"], b["face"], b["window_um"], b["width"], b["dir"]])
    for s in t.get("ft_slots") or []:
        f["slots"].append(dict(name=s["name"], regs=s.get("regs_um") or [], bits=s.get("bit_sites_um") or [], out_face=s["out_face"], win=s["out_window_um"]))
    ck = t.get("clock") or {}
    f["taps"] = [[tp["name"], tp["xy"], tp.get("kind")] for tp in ck.get("taps") or []]
    lc = ck.get("landing_contract") or {}
    f["groups"] = lc.get("group_rects_um") or {}
    try:
        act, xy = LP.collector_nodes(LP.collector_event(lc)); f["collectors"] = {n: xy[n] for n in act if n in xy}
    except Exception: pass
    f["bands"] = {n: b.get("rect_um") for n, b in (lc.get("bands") or {}).items()}
    return f
out = {}
for tn in sys.argv[3].split(","):
    out[tn] = dict(before=frame(A["partition_types"][tn]), after=frame(B["partition_types"][tn]))
json.dump(out, open(sys.argv[5], "w"))
