#!/usr/bin/env python3
"""DIE-KV-15 item 4: PV bank V-word vs command offset check on a strict KV bind (bus_groups.json).

Every PV bank tile (ot_qwen_tp8_pv_slice_t) registers pv2 / pe2 / bc at its pins and takes the V word on the bc
command it receives in the SAME cycle (v_r <= pv2; c_r <= bc; u_slice.take = c_r[1]).  In the as-built design the
relation (V depth - cmd depth) per bank is what the vport schedule (DQ/RT) is built for.  On a bind every bank of one
vport must keep that relation up to ONE per-vport shift (absorbable at the vport, e.g. its DQ):
    d(bank) = (V landed - V as-built) - (bc landed - bc as-built)      must be one value per V source.
Same for the ASTK response -> pe2.  Prints per source the d histogram; PASS iff every source has a single d.
usage: v_offset_check.py BIND_DIR [--json OUT]"""
import argparse, collections, json, sys
ap = argparse.ArgumentParser(); ap.add_argument("bind"); ap.add_argument("--json"); a = ap.parse_args()
bg = json.load(open(a.bind + "/bus_groups.json"))
cmd = {}; data = collections.defaultdict(list)
for g in bg["landing"]:
    for m in g["members"]:
        p = m["sink_port"]
        if p == "bc" and m["source"].endswith("__u_ctl.cmd"):
            cmd[g["sink"]] = m["landed_stages"] - m["asbuilt_stages"]
        elif p in ("pv2", "pe2"):
            data[(p, m["source"])].append((g["sink"], m["sink_bits"][0][0], m["landed_stages"] - m["asbuilt_stages"]))
out = {}; bad = 0; worst = {}
for (p, s), rows in sorted(data.items()):
    d = collections.Counter(); miss = 0
    for sink, lo, dv in rows:
        if sink not in cmd: miss += 1; continue
        d[dv - cmd[sink]] += 1
    spread = (max(d) - min(d)) if d else None
    out[f"{p}:{s}"] = dict(members=len(rows), no_cmd=miss, d_hist=dict(sorted(d.items())), spread=spread)
    if spread or miss: bad += 1
    worst[p] = max(worst.get(p, 0), spread or 0)
summ = dict(banks_with_cmd=len(cmd), sources=len(out), sources_not_single_offset=bad, worst_spread=worst,
            verdict="PASS" if bad == 0 else "FAIL")
print("V_OFFSET", json.dumps(summ))
for k, v in out.items():
    if v["spread"] or v["no_cmd"]: print(" ", k, json.dumps(v)[:300])
if a.json: json.dump(dict(summary=summ, sources=out), open(a.json, "w"), indent=1)
sys.exit(0 if bad == 0 else 1)
