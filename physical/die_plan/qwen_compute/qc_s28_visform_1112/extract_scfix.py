import json, sys
B = json.load(open(sys.argv[1])); A = json.load(open(sys.argv[2])); rows = json.load(open(sys.argv[3]))["rows"]
types = sys.argv[4].split(",")
def rect(h):
    (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]; dx, dy = h.get("track_offset_um", [0, 0]); return [ox + dx, oy + dy, ox + dx + w, oy + dy + hh]
def ex(P, tn):
    t = P["partition_types"][tn]; sl = []
    for s in t.get("ft_slots", []):
        bl = []
        for b in s.get("bit_sites_um") or []:
            xs = [p[0] for p in b]; ys = [p[1] for p in b]; bl.append([min(xs), min(ys), max(xs) + 1.404, max(ys) + 0.27])
        sl.append(dict(name=s["name"], in_face=s.get("in_face"), out_face=s.get("out_face"), in_window_um=s.get("in_window_um") or [0, 0],
                       out_window_um=s.get("out_window_um") or [0, 0], regs=s.get("regs_um") or [], blocks=bl))
    return dict(outline_um=t["outline_um"], cores=[rect(h) for h in t.get("hard_cores") or []], slots=sl)
mv = {}
for r in rows:
    if r["action"] == "move": mv.setdefault(r["type"], []).append(r["slot"])
json.dump(dict(before={t: ex(B, t) for t in types}, after={t: ex(A, t) for t in types}, moved=mv), open(sys.argv[5], "w"))
