#!/usr/bin/env python3
"""DIE-HBM-30-O: opstore_a V1 q_b113 repack (DIE-HBM-29-O estimate, 064a34ec3fb) as a die-local plan delta.

    opstore_a_v1.py SRC_PLAN_DIR OUT_PLAN_DIR K_DELTA

 - q_b113 + q_b113__physical_v1 (same type frame): u_sfucore_Q_opstore_a -> origin (1080.0, 941.76), outline
   760.32 x 483.84 (DIE-HBM-28-K 4x8 static grid, kit_contract PASS on the staged copy), orient MX kept;
   u_sfucore_Q_ctl -> origin (388.8, 924.48), orient MY + track offset kept, outline kept.
 - opstore_a pin table: the d29d table (390.528x436.32, 7,534 pins) re-spread on the SAME faces/layers/depths of
   the new outline (order kept, along-face coordinate scaled to the new face span, on the same 0.048 track residue,
   old spacing never reduced). New file cores/ot_hgi_sfu_core_split3__opstore_a__760.32x483.84__d30o.json.
 - core_macros.json: opstore_a -> K's KNOWN static grid (32 x ot_sram_1r1w_256x256_m2_r2c2).
 - clock: opstore_a entry at its new centre (380.16, 241.92) core frame (4.32 lattice, island +-4.32) and the type
   tap; ctl keeps its core-frame entry, type tap follows the move (same MY formula as d29d).
 - internal stations touching opstore_a / ctl: endpoints follow the cores (launch / named capture port = its pin
   centroid clamped to the core edge; capture = whole core -> nearest point of its boundary); register count kept. FF homes are re-solved
   afterwards by tools/die_plan/station_resite.py (same count; any added cycle is reported there).
Writes OUT/die_plan.json, OUT/core_macros.json, OUT/clock_entries.json, OUT/cores/<new table>, OUT/opstore_a_v1_report.json;
every other file is hard-linked from SRC (files that change are replaced, never written through a link).
"""
import json, os, re, subprocess, sys, hashlib
from pathlib import Path

SRC, OUT, KD = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
assert not OUT.exists(), OUT
subprocess.check_call(["cp", "-al", str(SRC), str(OUT)])

def put(rel, obj):
    p = OUT / rel; tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1)); os.replace(tmp, p)

P = json.loads((OUT / "die_plan.json").read_text())
TYPES = ["q_b113", "q_b113__physical_v1"]
OA, CT = "u_sfucore_Q_opstore_a", "u_sfucore_Q_ctl"
NEW_W, NEW_H = 760.32, 483.84
OA_ORIG, CT_ORIG = [1080.0, 941.76], [388.8, 924.48]
G, RES = 0.048, 0.024
rep = {"lane": "DIE-HBM-30-O", "src": str(SRC), "types": {}}

# ---- 1. opstore_a pin table re-spread -------------------------------------------------------------------------
h0 = next(h for h in P["partition_types"]["q_b113"]["hard_cores"] if h["inst"] == OA)
OW, OH = h0["outline_um"]
old = json.loads((OUT / h0["pins_file"]).read_text())
def face(p, W, H):
    if p["y"] < 1: return "S"
    if p["y"] > H - 1: return "N"
    if p["x"] < 1: return "W"
    if p["x"] > W - 1: return "E"
    raise ValueError(p)
new = [dict(p) for p in old]
fstat = {}
for f in "NSEW":
    idx = [i for i, p in enumerate(old) if face(p, OW, OH) == f]
    if not idx: continue
    along = "x" if f in "NS" else "y"
    span_old, span_new = (OW, NEW_W) if f in "NS" else (OH, NEW_H)
    ks = sorted(idx, key=lambda i: (old[i][along], old[i]["layer"]))
    k = [round((old[i][along] - RES) / G) for i in ks]
    assert all(abs(RES + kk * G - old[i][along]) < 1e-6 for kk, i in zip(k, ks)), f
    lo, hi = k[0], k[-1]
    hi_new = round((span_new - (span_old - old[ks[-1]][along]) - RES) / G)   # keep the old end margin
    s = (hi_new - lo) / max(1, hi - lo)
    out, prev, prevk = [], None, None
    for kk in k:
        v = lo + round((kk - lo) * s)
        if prev is not None:
            v = max(v, prev + (kk - prevk))
        out.append(v); prev, prevk = v, kk
    assert out[-1] <= hi_new + 1e-9, (f, out[-1], hi_new)
    for i, v in zip(ks, out):
        new[i][along] = round(RES + v * G, 3)
        if f == "E": new[i]["x"] = round(NEW_W - (OW - old[i]["x"]), 3)
        if f == "N": new[i]["y"] = round(NEW_H - (OH - old[i]["y"]), 3)
    fstat[f] = dict(pins=len(ks), layers=sorted({old[i]["layer"] for i in ks}), scale=round(s, 4),
                    span_new=[new[ks[0]][along], new[ks[-1]][along]])
# legality: no duplicates per (layer, x, y)
assert len({(p["layer"], p["x"], p["y"]) for p in new}) == len(new)
NEWPF = "cores/ot_hgi_sfu_core_split3__opstore_a__760.32x483.84__d30o.json"
(OUT / NEWPF).write_text(json.dumps(new, indent=1))
rep["pin_table"] = dict(old=h0["pins_file"], new=NEWPF, pins=len(new), faces=fstat,
                        sha256=hashlib.sha256((OUT / NEWPF).read_bytes()).hexdigest()[:12])

# ---- 2. geometry helpers ----------------------------------------------------------------------------------------
def xf(h, x, y):
    W, H = h["outline_um"]; o = h.get("orient", "R0"); tx, ty = h.get("track_offset_um", [0, 0])
    if o in ("MY", "R180"): x = W - x
    if o in ("MX", "R180"): y = H - y
    return [h["origin_um"][0] + tx + x, h["origin_um"][1] + ty + y]
def rect(h):
    return [h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]]
def clamp_to_boundary(r, p):
    x = min(max(p[0], r[0]), r[2]); y = min(max(p[1], r[1]), r[3])
    if r[0] < x < r[2] and r[1] < y < r[3]:   # inside -> nearest edge
        d = [(x - r[0], "W"), (r[2] - x, "E"), (y - r[1], "S"), (r[3] - y, "N")]; e = min(d)[1]
        x = r[0] if e == "W" else r[2] if e == "E" else x; y = r[1] if e == "S" else r[3] if e == "N" else y
    return [round(x, 3), round(y, 3)]
def port(n): return re.sub(r"\[\d+\]$", "", n)

# ---- 3. per type edits ------------------------------------------------------------------------------------------
CE = json.loads((OUT / "clock_entries.json").read_text())
for tn in TYPES:
    T = P["partition_types"][tn]
    hc = {h["inst"]: h for h in T["hard_cores"]}
    tr = rep["types"][tn] = {}
    a, c = hc[OA], hc[CT]
    tr["opstore_a_before"] = dict(origin=a["origin_um"], outline=a["outline_um"], orient=a.get("orient"))
    tr["ctl_before"] = dict(origin=c["origin_um"], orient=c.get("orient"), toff=c.get("track_offset_um"))
    a["origin_um"] = OA_ORIG; a["outline_um"] = [NEW_W, NEW_H]; a["pins_file"] = NEWPF
    a["note"] += " | DIE-HBM-30-O V1 q_b113 repack: K 4x8 static grid 760.32x483.84 at (1080, 941.76), pins re-spread same faces"
    c["origin_um"] = CT_ORIG
    c["note"] += " | DIE-HBM-30-O V1 q_b113 repack: moved W 267.84 (656.64 -> 388.8) onto the NS ft band (M5 lost there, M7 kept)"
    # legality: gaps >= 17.28 between all cores, inside outline
    W, H = T["outline_um"]; rs = {i: rect(h) for i, h in hc.items()}
    errs = []
    for i in rs:
        r = rs[i]
        if r[0] < 0 or r[1] < 0 or r[2] > W + 1e-6 or r[3] > H + 1e-6: errs.append(f"{i} outside")
        for j in rs:
            if i < j:
                q = rs[j]; dx = max(q[0] - r[2], r[0] - q[2]); dy = max(q[1] - r[3], r[1] - q[3])
                if max(dx, dy) < 17.28 - 1e-6: errs.append(f"{i}/{j} gap {max(dx, dy):.3f}")
    assert not errs, errs
    tr["core_rects"] = {i: [round(v, 3) for v in r] for i, r in rs.items()}
    # clock: entries (core frame) + type taps
    ce = CE[tn]
    ce[OA]["xy_um"] = [380.16, 241.92]; ce[OA]["island_um"] = [375.84, 237.6, 384.48, 246.24]
    ce[OA]["source"] += " | DIE-HBM-30-O: centre of the 760.32x483.84 outline (4.32 lattice)"
    for t in T["clock"]["taps"]:
        if t["name"] == OA + ".clk":
            t0 = list(t["xy"]); t["xy"] = [round(v, 3) for v in xf(a, *ce[OA]["xy_um"])]
            tr["tap_opstore_a"] = [t0, t["xy"]]
        if t["name"] == CT:
            t0 = list(t["xy"]); t["xy"] = [round(v, 3) for v in xf(c, *ce[CT]["xy_um"])]
            tr["tap_ctl"] = [t0, t["xy"]]
    assert "tap_opstore_a" in tr and "tap_ctl" in tr
    # internal stations
    pins = {i: json.loads((OUT / h["pins_file"]).read_text()) for i, h in hc.items() if i in (OA, CT)}
    moved = 0
    for s in T["internal_stations"]:
        li, _, lp = s["launch"].partition(".")
        ci = s["capture"].split(".")[0]
        if li not in (OA, CT) and ci not in (OA, CT): continue
        f0, t0 = list(s["from_um"]), list(s["to_um"])
        if li in (OA, CT):
            ps = [xf(hc[li], p["x"], p["y"]) for p in pins[li] if port(p["name"]) == lp]
            assert ps, s["launch"]
            cen = [sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)]
            s["from_um"] = clamp_to_boundary(rect(hc[li]), cen)
        if ci in (OA, CT):
            cp = s["capture"].partition(".")[2]
            ps = [xf(hc[ci], p["x"], p["y"]) for p in pins[ci] if cp and port(p["name"]) == cp]
            if ps:   # capture port named: its pin centroid on the core edge (the d29d convention)
                cen = [sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)]
                s["to_um"] = clamp_to_boundary(rect(hc[ci]), cen)
            else:    # capture = whole core: nearest boundary point
                s["to_um"] = clamp_to_boundary(rect(hc[ci]), s["from_um"])
        if (f0, t0) != (s["from_um"], s["to_um"]):
            moved += 1
            s["note"] += " | DIE-HBM-30-O: endpoints follow the V1 repack (count kept)"
    tr["station_endpoints_moved"] = moved
    tr["stations_total"] = len(T["internal_stations"])

# ---- 4. core_macros ----------------------------------------------------------------------------------------------
K = json.loads(KD.read_text())["core_macros"]
CM = json.loads((OUT / "core_macros.json").read_text())
mod = "ot_hgi_sfu_core_split3__opstore_a"
rep["core_macros_before"] = {k: v for k, v in CM["cores"][mod].items() if k != "macros"}
CM["cores"][mod] = K[mod]
# macro clearance of the new clock island
isl = CE["q_b113"][OA]["island_um"]
hits = [m["name"] for m in K[mod]["macros"] if not (m["rect_um"][2] <= isl[0] or m["rect_um"][0] >= isl[2] or m["rect_um"][3] <= isl[1] or m["rect_um"][1] >= isl[3])]
rep["clock_island_macro_hits"] = hits
assert not hits, hits
assert K[mod]["outline_um"] == [NEW_W, NEW_H]

P["note"] = "DIE-HBM-30-O opstore_a V1 q_b113 repack <- " + P["note"]
put("die_plan.json", P); put("clock_entries.json", CE); put("core_macros.json", CM)
rep["out_sha256"] = hashlib.sha256((OUT / "die_plan.json").read_bytes()).hexdigest()[:12]
(OUT / "opstore_a_v1_report.json").write_text(json.dumps(rep, indent=1))
print(json.dumps({k: rep[k] for k in ("pin_table", "out_sha256", "clock_island_macro_hits")}, indent=1))
for tn in TYPES: print(tn, {k: v for k, v in rep["types"][tn].items() if k != "core_rects"})
