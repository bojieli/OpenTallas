"""VL2QC-STA (VISLAYOUT2-QC sub-lane) 11-12: sl_st_a family r0 SRAM group + btab[0] out of the S-face escape zone.
Positions only (core-shape freeze, orients unchanged R0, all pins on the W edge as r1..r3).  The r0 group (h9, hb,
scale_wait, skn, sks: ot_sram_1r1w_32x64_m1) sat at y 112-155 and btab g_btb[0] (128x256 r2c2) at y 121-162, 45-54 um
above the S-face landing bands x_fw_ctl_i / x_fw_i (and, on slw_st_a_v2__clf4365a62, on top of b_hw_ctl_hc0_i y 60-106
with x_fw_ctl_i y 168-218 above): every ring escape and S-face bus going N had to pass between them (VIS-TRIAGE P:
GRT ov 5967, 2344 in band + 1123 over macro + 1232 street in the 100x100 um zoom).  New sites: the r0 group in the
same 3+2 pattern as r1..r3 (pitch 43.2 x 25.92) at x 250.56, y 285.12 (clear of the b_hw_ctl_hc0 E->N bit legs at y <= ~281); btab[0] at (406.08, 371.52) under btab[1].
Both sites were searched over the 8.64 lattice to touch none of the 9 types' clock/reset/collector relays, landing
stages, ft sites, count straps (4.32 margin) or landing/collector bands (8.64 margin).
usage: make_sta.py BASE.json OUT.json DELTA.json"""
import hashlib, json, sys
src, dst, dpath = sys.argv[1:4]
G = 8.64
X, Y = 250.56, 285.12
POS = {"u_u_r0.u_h9.u_m.g_bank[0].u_m": (X, Y), "u_u_r0.u_hb.u_m.g_bank[0].u_m": (X + 43.2, Y),
       "u_u_r0.u_scale_wait.u_m.g_bank[0].u_m": (X + 86.4, Y), "u_u_r0.u_skn.u_m.g_bank[0].u_m": (X, Y + 25.92),
       "u_u_r0.u_sks.u_m.g_bank[0].u_m": (X + 43.2, Y + 25.92), "u_u_btab.u_bt.u_core.g_btb[0].u_m": (406.08, 371.52)}
for x, y in POS.values():
    assert abs(x / G - round(x / G)) < 1e-6 and abs(y / G - round(y / G)) < 1e-6, (x, y)
raw = open(src, "rb").read()
p = json.loads(raw)
assert json.dumps(p, indent=1).encode() == raw
delta, warn, over = [], [], []
def xys(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from xys(v, path + "." + k)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(a, (int, float)) for a in o):
            yield path, o
        elif len(o) == 4 and all(isinstance(a, (int, float)) for a in o) and path.endswith("rect_um"):
            yield path + "#rect", o
        else:
            for i, v in enumerate(o):
                yield from xys(v, path + "[%d]" % i)
for tn, t in sorted(p["partition_types"].items()):
    if not tn.startswith(("sle_st_a", "slw_st_a")):
        continue
    hcs = {h["inst"].split("u_bound.", 1)[-1]: h for h in t["hard_cores"]}
    assert set(POS) <= set(hcs), tn
    for k, (x, y) in POS.items():
        h = hcs[k]
        was = dict(origin_um=h["origin_um"], orient=h["orient"])
        h["origin_um"] = [x, y]
        delta.append(dict(type=tn, inst=h["inst"], was=was, now=dict(origin_um=[x, y], orient=h["orient"])))
    boxes = []
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; dx, dy = h.get("track_offset_um", (0, 0))
        boxes.append((h["inst"].rsplit(".", 2)[-2], x + dx, y + dy, x + dx + w, y + dy + hh))
    for i, a in enumerate(boxes):           # overlap / channel check among hard cores (R3: abut or >= 40 um)
        for b in boxes[i + 1:]:
            gx = max(b[1] - a[3], a[1] - b[3]); gy = max(b[2] - a[4], a[2] - b[4])
            if gx < 0 and gy < 0:
                over.append((tn, a[0], b[0]))
    for path, v in list(xys(t.get("clock", {}), "clock")) + list(xys(t.get("ft_slots", []), "ft_slots")) + \
            list(xys(t.get("internal_stations") or [], "internal_stations")) + list(xys(t.get("count_straps") or [], "count_straps")):
        for nm, x0, y0, x1, y1 in boxes:
            if path.endswith("#rect"):
                if v[0] < x1 and x0 < v[2] and v[1] < y1 and y0 < v[3]:
                    warn.append((tn, path, tuple(v), nm))
            elif x0 - 4.32 < v[0] < x1 + 4.32 and y0 - 4.32 < v[1] < y1 + 4.32:
                warn.append((tn, path, tuple(v), nm))
p["note"] = p["note"] + " | vl2qc_sta (VL2QC-STA 11-12): 9 st_a types, r0 SRAM group to (250.56, 285.12) + btab[0] to (406.08, 371.52), out of the S-face escape zone"
out = json.dumps(p, indent=1)
open(dst, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, pos=POS, edits=delta, overlaps=over,
               inside_box_xy=warn), open(dpath, "w"), indent=1)
print("edited", len(delta), "cores in", len({d["type"] for d in delta}), "types; sha256", sha[:12], "overlaps", len(over))
for w in warn:
    print("XY-IN-MACRO", *w)
for o in over:
    print("OVERLAP", *o)
