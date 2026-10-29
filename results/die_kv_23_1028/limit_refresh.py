# DIE-KV-23 (COORD 23:3x after NUMBER-CHECK-KV-1, INFO only, not a gate input): the plan start_skew_limit_ps (planned
# sync_dist - sync aperture) is below the measured clk->Q hi on some TT start rows.  The gate's sta_sync_dist is measured
# AFTER shifting the STA interval by the clk->Q range, so the skew the row tolerates = clk->Q hi + (sta_sync_dist - sync
# aperture): refreshed limit (comparable with clk->Q hi, like the plan field).  Per start row, both corners.
import json, sys
d = json.load(open(sys.argv[1])); AP = float(sys.argv[3]) if len(sys.argv) > 3 else 26.5; out = {}
for C in ("TT", "FF"):
    ss = d["count_aligned"][C]["start_skew"]; rows = []
    for r in ss["rows"]:
        if r.get("limit_ps") is None or r.get("sta_sync_dist_ps") is None: continue
        new = round(r["skew_hi_ps"] + r["sta_sync_dist_ps"] - AP, 1)
        rows.append(dict(port=r["port"], region=r["region"], plan_limit_ps=r["limit_ps"], clkq_hi_ps=r["skew_hi_ps"],
                         stale=r["skew_hi_ps"] > r["limit_ps"], sta_sync_dist_ps=r["sta_sync_dist_ps"], refreshed_limit_ps=new,
                         refreshed_ok=r["skew_hi_ps"] <= new))
    st = [x for x in rows if x["stale"]]
    out[C] = dict(rows=len(rows), stale_plan_limit=len(st), min_refreshed_limit_ps=min(x["refreshed_limit_ps"] for x in rows),
                  refreshed_fail=sum(not x["refreshed_ok"] for x in rows), stale_rows=st)
json.dump(dict(aperture_ps=AP, basis="refreshed = clk->Q hi + gate sta_sync_dist (clk->Q-shifted) - sync aperture; plan field kept, INFO only", corners=out),
          open(sys.argv[2], "w"), indent=1)
for C in out: print(C, {k: v for k, v in out[C].items() if k != "stale_rows"})
