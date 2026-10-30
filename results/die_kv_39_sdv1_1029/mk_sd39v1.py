#!/usr/bin/env python3
"""DIE-KV-39-SD-V1 (KV-022 variant V1 = Codex 19-tap SD prep 635a21369 on the PHY-bearing plan).
Codex prepared the 19 explicit clock taps (density of 6589 actual main-clk sinks, varD 3_place; E root 1883.52,520,
cland_tstart_in at E 1898.656,520) on the bare event28b plan, whose contents.serdes has no lef/origin/outline -> the
reset planner saw no PHY obstacle (35/103 relays on the macro) and the 12 event28b reset.local_taps_um sat on it.
Fix-only delta: start from the DIE-KV-36 sd36A plans (contents.serdes = actual kit PHY w522 abstract, origin
(17.28,54) outline 1848.96x972 R0, = the kits' macro_place.tcl; reset.local_taps_um = the 10 band sites re-sited from
actual capture groups by DIE-KV-36) and apply only Codex's clock-entry change.  Then mk_sd36.py rebuilds the collector
tree from reset_tree.for_type on the result.
usage: mk_sd39v1.py TOOLS TAPS19 SINKBINS PLAN_IN PLAN_OUT [PLAN_IN PLAN_OUT ...]"""
import json, sys, hashlib
sys.path.insert(0, sys.argv[1])
TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
taps = json.load(open(sys.argv[2])); bins = sys.argv[3]
assert len(taps) == 19 and taps[0]["name"] == "clk" and taps[0]["xy"] == [1883.52, 520.0]
# Codex sited the taps without the PHY in its plan: two W-rim taps sit at x=17.28 = the macro edge, inside the
# 8.64-um tap clear (schema.TAP_CLEAR_UM).  Project such taps onto the nearest legal point (W rim x=8.64); record it.
CLR = 8.64; MB = (17.28 - CLR, 54.0 - CLR, 17.28 + 1848.96 + CLR, 54.0 + 972.0 + CLR)
moves = []
for t2 in taps:
    x, y = t2["xy"]
    if MB[0] < x < MB[2] and MB[1] < y < MB[3]:
        c = min([(MB[0], y), (MB[2], y), (x, MB[1]), (x, MB[3])], key=lambda q: abs(q[0] - x) + abs(q[1] - y))
        moves.append(dict(name=t2["name"], old=[x, y], new=[round(c[0], 4), round(c[1], 4)]))
        t2["xy"] = [round(c[0], 4), round(c[1], 4)]
rep = {"tap_legalize_moves": moves}
for pin, pout in zip(sys.argv[4::2], sys.argv[5::2]):
    raw = json.load(open(pin))
    for tn in TYPES:
        t = raw["partition_types"][tn]
        serdes = [c for c in t["contents"] if c["inst"] == "serdes"]
        # die plan (gen.py phys) carries the PHY footprint; the bind plan is logical (sd36A form)
        assert serdes and ("/b/" in pin or (serdes[0].get("lef") and serdes[0]["origin_um"] == [17.28, 54.0])), (tn, "PHY footprint missing")
        ck = t["clock"]
        ck.pop("tap_edge_y_um", None)
        ck.update(tap_mode="explicit", tap_um=[1883.52, 520.0], tap_radius_um=200.0, tap_max_sinks=1500,
                  tap_target_sinks=1100, control_sinks=True, sink_bins_file=bins,
                  taps=[dict(t2) for t2 in taps])
        n = 0
        for p in ck["landing_contract"]["pins"]:
            if p["name"] == "cland_tstart_in":
                p.update(xy_um=[1898.656, 520.0], native_entry_reference_um=[1890.0, 520.0]); n += 1
        assert n == 1
    raw["note"] = (raw.get("note", "") + " | DIE-KV-39-SD-V1: Codex 635a21369 19 explicit SD clock taps (E root 1883.52,520; tstart E) on the sd36A PHY-bearing plan").strip(" |")
    json.dump(raw, open(pout, "w"), indent=1)
    rep[pout] = hashlib.sha256(open(pout, "rb").read()).hexdigest()
print(json.dumps(rep, indent=1))
