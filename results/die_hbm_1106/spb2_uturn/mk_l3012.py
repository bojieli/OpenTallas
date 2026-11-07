#!/usr/bin/env python3
"""DIE-HBM-82-SPB d44v part 54: widen the 16 pin windows of the 27-bit chain L3012 (su21 -> ... -> hub) to max(old,
3.5) um, same centre, both faces of every abutted port together.  mk_l3012.py IN_PLAN.json OUT_PLAN.json LEDGER.json"""
import json, sys
NEW_W = 3.5
pin, pout, pled = sys.argv[1:4]
raw = json.load(open(pin)); T = raw["partition_types"]; parts = {p["name"]: p for p in raw["partitions"]}
lane = next(l for l in raw["lanes"] if l["id"] == "L3012")
ports = {p["id"]: p for p in raw["ports"]}
def win(tname, bus):  # -> (holder dict, key, face)
    t = T[tname]
    for b in t.get("buses", []):
        if b["name"] == bus: return b, "window_um", b["face"]
    for s in t.get("ft_slots", []):
        if bus == s["name"] + "_i": return s, "in_window_um", s["in_face"]
        if bus == s["name"] + "_o": return s, "out_window_um", s["out_face"]
    raise KeyError((tname, bus))
def other_windows(tname, face, skip):
    t = T[tname]; out = []
    for b in t.get("buses", []):
        if b.get("face") == face and b is not skip[0]: out.append((b["name"], b["window_um"]))
    for s in t.get("ft_slots", []):
        for k, f in (("in_window_um", "in_face"), ("out_window_um", "out_face")):
            if s.get(f) == face and not (s is skip[0] and k == skip[1]): out.append((s["name"] + ":" + k[:-10], s[k]))
    return out
types_used = {}
for pid in lane["ports"]:
    pr = ports[pid]
    for end in ("src", "dst"):
        tn = parts[pr[end]["part"]]["type"]; types_used.setdefault(tn, set()).add(pr[end]["part"])
inst = {tn: sorted(p for p, v in parts.items() if v["type"] == tn) for tn in types_used}
led = {"lane": "L3012", "new_width_um": NEW_W, "windows": [], "instances_per_type": inst}
done = set()
for pid in lane["ports"]:
    pr = ports[pid]; row = {"port": pid, "width": pr["width"]}
    for end in ("src", "dst"):
        tn = parts[pr[end]["part"]]["type"]; h, k, face = win(tn, pr[end]["bus"])
        lo, hi = h[k]; c = (lo + hi) / 2
        if (tn, pr[end]["bus"]) not in done:
            w = max(NEW_W, hi - lo)
            nlo, nhi = round(c - w / 2, 3), round(c + w / 2, 3)
            # pin-window collision check against every other window on the same face of this type
            clash = [(n, w) for n, w in other_windows(tn, face, (h, k)) if w[0] < nhi and w[1] > nlo]
            assert not clash, (tn, pr[end]["bus"], clash)
            gap = min([min(abs(w[0] - nhi), abs(nlo - w[1])) for n, w in other_windows(tn, face, (h, k))] or [1e9])
            h[k] = [nlo, nhi]; done.add((tn, pr[end]["bus"]))
        row[end] = {"part": pr[end]["part"], "type": tn, "bus": pr[end]["bus"], "face": face, "old": [lo, hi],
                    "new": h[k],
                    "min_gap_um": round(gap, 3)}
    led["windows"].append(row)
open(pout, "w").write(json.dumps(raw) + "\n")
open(pled, "w").write(json.dumps(led, indent=1) + "\n")
print("L3012 windows ->", NEW_W, "um:", len(done), "type windows;", {t: len(v) for t, v in inst.items()})
for r in led["windows"]:
    print(r["port"], r["src"]["type"], r["src"]["old"], "->", r["src"]["new"], "gap", r["src"]["min_gap_um"], "|", r["dst"]["type"], r["dst"]["old"], "->", r["dst"]["new"], "gap", r["dst"]["min_gap_um"])
