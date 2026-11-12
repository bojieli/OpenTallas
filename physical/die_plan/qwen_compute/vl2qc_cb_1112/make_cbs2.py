"""VL2QC-CB cbf_q01_s2 REDESIGN (positions only): shift the 4 NK tiles N by D um (8.64 lattice) so the S street
(ft a00 514b + serdes tx/rx 2x597b + S landing rings, all at the S window cluster x 94-395) grows from 77.76 to
77.76+D; the N street shrinks 86.4 -> 86.4-D.  Every plan xy inside an old tile box (tile-owned: core taps, tile pins)
moves with its tile; everything else stays.  usage: make_cbs2.py BASE OUT DELTA D"""
import json, sys, hashlib
src, dst, dout, D = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
assert abs(D / 8.64 - round(D / 8.64)) < 1e-6
raw = open(src, "rb").read(); p = json.loads(raw)
TN = "cbf_q01_s2"; t = p["partition_types"][TN]
old = []; ed = []
for h in t["hard_cores"]:
    x, y = h["origin_um"]; w, hh = h["outline_um"]
    old.append((x, y, x + w, y + hh))
    h["origin_um"] = [x, round(y + D, 4)]
    ed.append(dict(type=TN, inst=h["inst"], was=[x, y], now=h["origin_um"], orient=h["orient"]))
new = [(a, b + D, c, d + D) for a, b, c, d in old]
# mid H street between the tile rows moves with the rows (its relays / stations / ft sites serve both rows)
MID = (min(o[3] for o in old if o[1] < 600), max(o[1] for o in old if o[1] > 600)); XS = (min(o[0] for o in old), max(o[2] for o in old))
moved = []; hit = []
def walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, path + "." + k)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(a, (int, float)) for a in o):
            if "window" in path.rsplit(".", 1)[-1]:
                return
            a, b = o
            if any(x0 < a < x1 and y0 < b < y1 for x0, y0, x1, y1 in old) or (MID[0] < b < MID[1] and XS[0] < a < XS[1]):
                o[1] = round(b + D, 4); moved.append(path)
            elif any(x0 < a < x1 and y0 < b < y1 for x0, y0, x1, y1 in new):
                hit.append((path, (a, b)))
        else:
            for i, v in enumerate(o): walk(v, path + "[%d]" % i)
for k in t:
    if k not in ("hard_cores", "outline_um", "contents"):
        walk(t[k], k)
p["note"] = p.get("note", "") + f" | vl2qc_cbs2 (VL2QC-CB 11-12): cbf_q01_s2 tiles N +{D} (S street widened)"
out = json.dumps(p, indent=1); open(dst, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, D=D, edits=ed, moved_with_tile=moved, xy_in_new_tile=hit), open(dout, "w"), indent=1)
print("D", D, "sha", sha[:12], "moved_with_tile", len(moved), "xy_in_new_tile", len(hit))
import collections
print(" moved:", collections.Counter(m.split("[")[0] for m in moved).most_common(8))
for h_ in hit[:12]: print(" HIT", h_)
