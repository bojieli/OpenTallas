"""CPL-QC-NK-R0 11-11 (S2 follow-up, DIE-QC-99 request): plan_qc99_s23_nkl = plan_qc99_s22_nkr0 (main) + LEFT-column
NK tiles R0 -> MY in the q01 quads, so their data pins (core W edge in R0) face the middle channel and their tap edge
faces the W-side bc column (bc_i02 / bc_o03 windows x 4-94).

Same rule as s22: a tile flips only when no type face bus (buses[].leaf) and no internal station (internal_stations
capture) lands on it and the RTL NK-link macro-crossing score strictly improves (xscore.py).  Per flipped tile only
hard_cores[].orient and the core ck tap (clock.taps[<inst>.ck] xy = the new-orient ck pin, orient).  NK pins are all
M4 and an x mirror keeps the pin y: on-track exactly as before.
--trial-t22 builds the DIE-QC-99 t22 -> MY question plan (cbn_q11 x2, cbf_q11; t22 carries y_o22 / na_i22 / nb_i22 and
two R3-INTERNAL station chains) for measurement only, never for adoption.
usage: make_s23.py S22.json OUT.json DELTA.json [--trial-t22]"""
import hashlib, json, sys
src, dst, dpath = sys.argv[1:4]
trial = "--trial-t22" in sys.argv
raw = open(src, "rb").read()
assert hashlib.sha256(raw).hexdigest().startswith("587e484eda91"), "base must be plan_qc99_s22_nkr0"
p = json.loads(raw)
assert json.dumps(p, indent=1).encode() == raw
CK = (457.824, 668.076); W = 457.92
SEL = {"cbn_q01__clab6e67f2": {"u_t02": "MY", "u_t03": "MY"}, "cbn_q01__cld9ff4c40": {"u_t02": "MY", "u_t03": "MY"},
       "cbn_q01__cldd6ea846": {"u_t02": "MY", "u_t03": "MY"}, "cbf_q01": {"u_t02": "MY"}}
if trial:
    SEL = {t: {"u_t22": "MY"} for t in ("cbn_q11__cl49ae4555", "cbn_q11__cl5cc92dfe", "cbf_q11")}
delta = []
for tn, sel in sorted(SEL.items()):
    t = p["partition_types"][tn]
    busleaf = {b["leaf"].split(".")[0] for b in t["buses"]}
    stn = {s["capture"].split(".")[0] for s in t.get("internal_stations", []) if "." in s.get("capture", "")}
    for h in t["hard_cores"]:
        if h["inst"] not in sel:
            continue
        new = sel[h["inst"]]
        assert h["module"] == "qfd_tile_nk_a0c" and h["orient"] != new and h["orient"] in ("R0", "MY"), (tn, h["inst"])
        if not trial:
            assert h["inst"] not in busleaf and h["inst"] not in stn, (tn, h["inst"])
        ox, oy = h["origin_um"]; dx, dy = h["track_offset_um"]
        old = h["orient"]; h["orient"] = new
        tp = [x for x in t["clock"]["taps"] if x["name"] == h["inst"] + ".ck"]
        assert len(tp) == 1
        tp = tp[0]; was = dict(xy=tp["xy"], orient=tp.get("orient"))
        cx = CK[0] if new == "R0" else W - CK[0]
        tp["xy"] = [round(ox + dx + cx, 4), round(oy + dy + CK[1], 4)]; tp["orient"] = new
        delta.append(dict(type=tn, inst=h["inst"], orient=[old, new], face_bus=h["inst"] in busleaf,
                          internal_station=h["inst"] in stn, ck_tap=dict(was=was, now=dict(xy=tp["xy"], orient=new))))
p["note"] = p["note"] + (" | s23 TRIAL t22 MY (CPL-QC-NK-R0, measurement only)" if trial else
                         " | s23_nkl (CPL-QC-NK-R0 11-11, S2): s22_nkr0 + q01 left-column NK tiles R0 -> MY (%d tiles)" % len(delta))
out = json.dumps(p, indent=1)
open(dst, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base="plan_qc99_s22_nkr0.json", base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, trial=trial,
               edits=delta), open(dpath, "w"), indent=1)
print("flipped", len(delta), "sha256", sha)
for d in delta:
    print(" ", d["type"], d["inst"], d["orient"], "face_bus", d["face_bus"], "istn", d["internal_station"], d["ck_tap"]["was"]["xy"], "->", d["ck_tap"]["now"]["xy"])
