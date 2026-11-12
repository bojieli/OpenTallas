"""VL2QC-SC step 2 (positions only): in the five *_sc_v1 types the x_stm_fe_p1_i landing band sits 136 um inside the
NW corner (hop 233 um) and cws2_i lies across the W-face corner, so the N-W corner holds two 2880-flop rings plus the
x_ctl/core ctl buses (route_supply ring H M2 1.05-1.09 at x 210-221, y 1204-1215).  Adopt the sibling sl*_sc_v2/v3
arrangement (same cohort, same band sizes): x_stm_fe_p1_i on the W face at its in-pins, cws2_i in the NW corner
column under its N window.  Only rect_um (and the band's informational hop) change; flops, widths, rings untouched.
usage: make_sc3.py BASE.json OUT.json DELTA.json"""
import hashlib, json, sys
src, dst, dpath = sys.argv[1:4]
raw = open(src, "rb").read(); p = json.loads(raw)
T = p["partition_types"]
ref = T["slw_sc_v2"]["clock"]["landing_contract"]["bands"]
edits = []
for tn in sorted(T):
    if "_sc_v1" not in tn:
        continue
    B = T[tn]["clock"]["landing_contract"]["bands"]
    for bn in ("cws2_i", "x_stm_fe_p1_i"):
        was = B[bn]["rect_um"]
        B[bn]["rect_um"] = list(ref[bn]["rect_um"])
        B[bn]["max_pin_to_band_hop_um"] = ref[bn]["max_pin_to_band_hop_um"]
        edits.append(dict(type=tn, band=bn, was=was, now=B[bn]["rect_um"]))
out = json.dumps(p, indent=1)
open(dst, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, edits=edits), open(dpath, "w"), indent=1)
print(len(edits), "band edits; sha256", sha[:12])
