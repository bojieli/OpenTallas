"""VISLAYOUT2-QC 11-11: stm family hand arrangement (positions/orients only, EQ by construction).
4 ROMs (ot_rom_4096x266_m8, rd_out on M4 at the W/E edges, low y in R0) move from mid-type (y 587-745) to a 2x2
block under the N 2103-b b_tw_data_ctl_o window (x 4-366), all MX so rd_out faces N; m0/m2 and m1/m3 (address pairs)
stacked.  Origins on the 8.64 die lattice; MX keeps M4 pins on track with the same track_offset (h=62.952 = 0.024 mod
0.048).  usage: make_stm.py BASE.json OUT.json DELTA.json [BLOCKS.json]"""
import hashlib, json, sys
src, dst, dpath = sys.argv[1:4]
X0, X1, YT, YB = (60.48, 233.28, 1235.52, 1123.2)
G = 8.64
for v in (X0, X1, YT, YB):
    assert abs(v / G - round(v / G)) < 1e-6, v
raw = open(src, "rb").read()
p = json.loads(raw)
assert json.dumps(p, indent=1).encode() == raw
# per-type block (xl, xr, y_top, y_bot), legalised by stm_free.py against the planned straps / ft regs / taps / landing
# pins of each type (collector and reset relays are cleared at kit time by landing_place._collector_window)
BLK = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
def POSF(tn):
    xl, xr, yt, yb = BLK.get(tn, (X0, X1, YT, YB))
    return {"m0": (xl, yt, "MX"), "m1": (xr, yt, "MX"), "m2": (xl, yb, "MX"), "m3": (xr, yb, "MX")}
POS = None
delta = []; warn = []
def xys(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from xys(v, path + "." + k)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(a, (int, float)) for a in o):
            yield path, o
        else:
            for i, v in enumerate(o):
                yield from xys(v, path + "[%d]" % i)
for tn, t in sorted(p["partition_types"].items()):
    if not tn.startswith(("sle_stm", "slw_stm")):
        continue
    hcs = t.get("hard_cores") or []
    assert len(hcs) == 4 and all(h["module"] == "ot_rom_4096x266_m8" for h in hcs), tn
    boxes = []
    for h in hcs:
        k = h["inst"].rsplit(".", 1)[1]
        x, y, o = POSF(tn)[k]
        assert abs(x / G - round(x / G)) < 1e-6 and abs(y / G - round(y / G)) < 1e-6
        was = dict(origin_um=h["origin_um"], orient=h["orient"])
        h["origin_um"] = [x, y]; h["orient"] = o
        w, hh = h["outline_um"]; dx, dy = h["track_offset_um"]
        boxes.append((h["inst"], x + dx - 4.32, y + dy - 4.32, x + dx + w + 4.32, y + dy + hh + 4.32))
        delta.append(dict(type=tn, inst=h["inst"], was=was, now=dict(origin_um=[x, y], orient=o)))
    for path, (a, b) in list(xys(t.get("clock", {}), "clock")) + list(xys(t.get("ft_slots", []), "ft_slots")) + \
            list(xys(t.get("internal_stations") or [], "internal_stations")) + list(xys(t.get("count_straps") or [], "count_straps")):
        for nm, x0, y0, x1, y1 in boxes:
            if x0 < a < x1 and y0 < b < y1:
                warn.append((tn, path, (a, b), nm.rsplit(".", 1)[1]))
p["note"] = p["note"] + " | vl2qc_stm (VISLAYOUT2-QC 11-11): 11 stm types, 4 ROMs to a 2x2 MX block under the N b_tw_data_ctl_o window"
out = json.dumps(p, indent=1)
open(dst, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, blocks=BLK, edits=delta, inside_box_xy=warn),
          open(dpath, "w"), indent=1)
print("edited", len(delta), "cores in", len({d["type"] for d in delta}), "types; sha256", sha[:12])
for w in warn:
    print("XY-IN-MACRO", *w)
