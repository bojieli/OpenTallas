"""KV-SLGLAND-1 vC (COORD 21:4x): split each wide slg/ectl response landing ring of kv3_pv*/kv3_hgi*/kv3_hg* over two
rects (rects_um, existing DIE-S81-47 key): rect 1 = the planned band at the pins, rect 2 = a same-size rect next to it
(inward from the pin face first, then along the face), clear of every hard core by min(CH, rect 1's own core clearance) um (fixed channel) and of every
other band.  ring_place stays ff; fill_axis is dropped (rects_um does not support it).  Rings with no clear rect 2 stay
as they are (listed).  Idempotent: bands that already carry rects_um are kept."""
import copy, collections, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))
import schema as S, gen_phys as G
TYPES = re.compile(r"^kv3_(pv|hgi|hg)(_|$)"); RING = re.compile(r"^i_(slg|ectl)_.*"); WIDE = 1024; CH = 10.8
a, b = sys.argv[1:3]; raw = json.load(open(a)); orig = copy.deepcopy(raw)
P = S.Plan(copy.deepcopy(raw), Path(a).resolve())
def ov(r, q, m=0.0): return min(r[2], q[2]) > max(r[0], q[0]) - m + 1e-6 and min(r[3], q[3]) > max(r[1], q[1]) - m + 1e-6
done, kept = [], []
for tn in sorted(raw["partition_types"]):
    if not TYPES.match(tn): continue
    t = raw["partition_types"][tn]; W, H = t["outline_um"]; bands = t["clock"]["landing_contract"]["bands"]
    faces = collections.defaultdict(set)
    for bus, _b, _l, _x, _y, f in G.type_pins(P, tn): faces[bus].add(f)
    cores = [[h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]]
             for h in t.get("hard_cores", [])]
    occ = lambda skip: [r for k, v in bands.items() if k != skip and v.get("rect_um") for r in (v.get("rects_um") or [v["rect_um"]])]
    for k in sorted(bands):
        v = bands[k]
        if not RING.match(k) or v.get("width", 0) < WIDE or not v.get("rect_um") or "rects_um" in v: continue
        if v.get("ring_place") != "ff" or any(x in v for x in ("ff_rect_um", "native_role_banks")): continue
        f = faces.get(k)
        if not f or len(f) != 1: kept.append((tn, k, "face")); continue
        f = next(iter(f)); x0, y0, x1, y1 = v["rect_um"]; w, h = x1 - x0, y1 - y0; g = 0.2
        inward = {"S": (0, h + g), "N": (0, -h - g), "W": (w + g, 0), "E": (-w - g, 0)}[f]
        along = [(w + g, 0), (-w - g, 0)] if f in "NS" else [(0, -h - g), (0, h + g)]
        gap = lambda r, c: max(c[0] - r[2], r[0] - c[2], c[1] - r[3], r[1] - c[3])
        m = min([CH] + [max(0.0, gap(v["rect_um"], c)) for c in cores])
        pick = None
        for dx, dy in [inward] + along:
            r = [round(x0 + dx, 4), round(y0 + dy, 4), round(x1 + dx, 4), round(y1 + dy, 4)]
            if not (0 <= r[0] and r[2] <= W and 0 <= r[1] and r[3] <= H): continue
            if any(ov(r, c, m) for c in cores) or any(ov(r, q) for q in occ(k)): continue
            pick = r; break
        if not pick: kept.append((tn, k, "no clear rect")); continue
        v.pop("fill_axis", None); v["rects_um"] = [list(v["rect_um"]), pick]; done.append((tn, k, f, pick))
for k in raw:
    if k != "partition_types": assert raw[k] == orig[k], k
for tn in raw["partition_types"]:
    if not TYPES.match(tn): assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
open(b, "w").write(json.dumps(raw, indent=1) + "\n")
for d in done: print("SPLIT", *d)
for d in kept: print("KEPT", *d)
print({"split": len(done), "kept": len(kept)})
