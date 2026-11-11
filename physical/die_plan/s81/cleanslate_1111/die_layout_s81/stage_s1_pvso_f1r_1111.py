"""DIE-LAYOUT-S81 11-11 S1 pvso F1-rigid (COORD 07:30 (A) F1 accepted, 0 growth, positions only).
The 181-macro contents band and the 72-core stack (64 hcore + 8 sx_hrow) translate up by LIFT inside the same
1442.88 x 2747.52 outline, so every core/core, core/macro and macro/macro distance is unchanged (no new B34 street
pairs: the SRAM LEF pins sit on the left/right M4 edges, so a tighter repack would need >= 34.56 streets per column and
does not fit). Core clock taps move with their cores. Faces, windows, landing bands, partners: unchanged.
The S-face strip under the stack grows 34.56 -> 34.56 + LIFT, which takes the S-face cland ring off the cores."""
import json, sys
src, out, rep = sys.argv[1:4]
LIFT = float(sys.argv[4]) if len(sys.argv) > 4 else 57.24
P = json.load(open(src)); T = P["partition_types"]; R = {"lift_um": LIFT, "types": {}}
for tn in ("svc_hi_dsdv_svc_pvso_entry__t1", "svc_hi_dsdv_svc_pvso_entry__t2"):
    t = T[tn]; W, H = t["outline_um"]
    n = {"hard_cores": 0, "contents": 0, "core_taps": 0}
    for k in ("hard_cores", "contents"):
        for e in t.get(k) or []:
            if "origin_um" in e:
                e["origin_um"] = [e["origin_um"][0], round(e["origin_um"][1] + LIFT, 4)]
                assert e["origin_um"][1] + e["outline_um"][1] <= H + 1e-6, (tn, e["inst"])
                n[k] += 1
    for tp in (t.get("clock") or {}).get("taps") or []:
        if tp.get("kind") == "core":
            tp["xy"] = [tp["xy"][0], round(tp["xy"][1] + LIFT, 4)]; n["core_taps"] += 1
    t["note"] = (t.get("note") or "") + f" | DIE-LAYOUT-S81 11-11 F1-rigid: core stack + macro band +{LIFT} um Y in outline"
    top = max(e["origin_um"][1] + e["outline_um"][1] for e in t["contents"] if "origin_um" in e)
    bot = min(e["origin_um"][1] for e in t["hard_cores"])
    R["types"][tn] = dict(n, macro_top_um=round(top, 3), top_margin_um=round(H - top, 3), s_strip_um=round(bot, 3))
json.dump(P, open(out, "w"), indent=1)
json.dump(R, open(rep, "w"), indent=1)
print(json.dumps(R))
