#!/usr/bin/env python3
"""DIE-KV-9 12.16 estimate: per crossing joint TT+FF OCV interval (clock_variation=table) vs standard DEPTH 8/16 window,
K from planned arrival centre, no PAD: worst margin = (W(D) - width - T)/2 (K integer-cycle quantisation T/2 each side).
W(D) = (D-1)T - 2ap. usage: est1216.py die_sta_related.json out.json"""
import json, sys, collections
d = json.load(open(sys.argv[1])); T = d["period_ps"]
tt = {r["port"]: r for r in d["count_aligned"]["TT"]["rows"]}; ff = {r["port"]: r for r in d["count_aligned"]["FF"]["rows"]}
ap = d["count_aligned"]["TT"]["aperture_ps"]; need = 100.0
W = lambda D: (D - 1) * T - 2 * ap
rows = []; cnt = collections.Counter()
for p in tt:
    lo = min(tt[p]["L_lo_ps"], ff[p]["L_lo_ps"]); hi = max(tt[p]["L_hi_ps"], ff[p]["L_hi_ps"]); w = hi - lo
    ocv = max(tt[p].get("ocv_lo_ps") or 0, tt[p].get("ocv_hi_ps") or 0, ff[p].get("ocv_lo_ps") or 0, ff[p].get("ocv_hi_ps") or 0)
    pick = next((D for D in (8, 16) if (W(D) - w - T) / 2 >= need), None)
    cnt[(tt[p]["depth"], pick)] += 1
    rows.append(dict(port=p, tag=tt[p]["tag"], depth_now=tt[p]["depth"], width=round(w, 1), ocv_max=ocv,
                     depth_1216=pick, margin=round((W(pick or 16) - w - T) / 2, 1)))
ws = sorted(r["width"] for r in rows)
summ = dict(T=T, ap=ap, window={8: W(8), 16: W(16)}, crossings=len(rows), now_depth_to_1216=dict((f"D{a}->D{b}", n) for (a, b), n in cnt.items()),
            width_p50=ws[len(ws)//2], width_p99=ws[int(.99*len(ws))], width_max=ws[-1],
            min_margin_D8=min((W(8) - r["width"] - T) / 2 for r in rows), ocv_max=max(r["ocv_max"] for r in rows))
print(json.dumps(summ, indent=1)); json.dump(dict(summary=summ, rows=rows), open(sys.argv[2], "w"), indent=0)
