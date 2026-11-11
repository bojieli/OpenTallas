#!/usr/bin/env python3
"""CPL-HBM-2: per-family positions/orients-only deltas {type:{inst:[x,y,orient]}} from core_place event rows.
usage: mkdelta.py OUTDIR ARM_DIR:FAMILY:type,type ..."""
import hashlib, json, sys, os
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
def mingap(cs, dims):
    ks = list(cs); g = 1e9
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            (x, y), (w, h) = cs[ks[i]], dims[ks[i]]; (X, Y), (W, H) = cs[ks[j]], dims[ks[j]]
            d = max(X - (x + w), x - (X + W), Y - (y + h), y - (Y + H))
            if d > 1e-6: g = min(g, d)
    return round(g, 2)
plans = {}
for spec in sys.argv[2:]:
    arm, fam, ts = spec.split(":")
    D, rows = {}, []
    for t in ts.split(","):
        ev = json.load(open("%s/ev_%s.json" % (arm, t))); r = ev["rows"][0]
        bp = ev["base_plan"]
        if bp not in plans: plans[bp] = json.load(open(bp))["partition_types"]
        hc = {h["inst"]: h for h in plans[bp][t]["hard_cores"]}
        dims = {k: h["outline_um"] for k, h in hc.items()}
        bef = {k: tuple(h["origin_um"]) for k, h in hc.items()}
        ok = r["applied"] and r["moved_cores"] > 0 and not r["schema_new_errors"] and not r["eq_violations"]
        aft = {k: tuple(v["origin_um"]) for k, v in r["cores_after"].items()}
        if ok:
            D[t] = {k: [round(v["origin_um"][0], 4), round(v["origin_um"][1], 4), v["orient"]] for k, v in sorted(r["cores_after"].items())}
        rows.append(dict(type=t, base_plan=bp, base_sha=ev["base_plan_sha256"][:12], in_delta=ok, applied=r["applied"],
                         moved=r["moved_cores"], bit_mm=r["bit_mm"], ovfH=r["rudy_ovf_H"], ovfV=r["rudy_ovf_V"],
                         cutH=[c["worst_ratio"] for c in r["cut_H"]], cutV=[c["worst_ratio"] for c in r["cut_V"]],
                         rs_p99=[x.get("p99") for x in (r.get("route_supply_full") or [{}, {}])],
                         mingap=[mingap(bef, dims), mingap({**bef, **aft}, dims)], g0_new=len(r["schema_new_errors"]),
                         tv=r["timing_violations_end"], st_more=r["stations_report"]["need_more_regs"]))
    p = "%s/delta_%s.json" % (out, fam)
    if D:
        s = json.dumps(D, indent=1, sort_keys=True) + "\n"; open(p, "w").write(s)
        sha = hashlib.sha256(s.encode()).hexdigest()
    else:
        sha = None
    json.dump(dict(family=fam, delta=p if D else None, sha256=sha, rows=rows), open("%s/summary_%s.json" % (out, fam), "w"), indent=1)
    print(fam, "delta types", sorted(D), sha)
    for r in rows:
        print("  %-22s delta=%-5s mv=%2d bitmm %.0f>%.0f ovfH %d>%d ovfV %d>%d mingap %s g0new %d" % (r["type"], r["in_delta"], r["moved"], r["bit_mm"][0], r["bit_mm"][1], r["ovfH"][0], r["ovfH"][1], r["ovfV"][0], r["ovfV"][1], r["mingap"], r["g0_new"]))
