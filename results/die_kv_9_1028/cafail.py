#!/usr/bin/env python3
"""DIE-KV-9 10-28: CA-OCV-1 failing KV crossings, interval width vs ring window (COORD 07:2x ask).
window(D) = (D-1) T - 2 ap (K/PAD retune can place an interval of that width); width = L_hi - L_lo (OCV-widened).
usage: cafail.py die_sta_related.json out.json"""
import json, sys, collections
d = json.load(open(sys.argv[1])); T = d["period_ps"]
out = {}
for C in ("TT", "FF"):
    c = d["count_aligned"][C]; ap = c["aperture_ps"]
    win = lambda D: (D - 1) * T - 2 * ap
    rows = [r for r in c["rows"] if not (r["lag_ok"] and r["slot_read_ok"] and r["guard_ok"])]
    res = []
    for r in rows:
        w = r["L_hi_ps"] - r["L_lo_ps"]; D = r["depth"]
        fix = "K/PAD retune" if w <= win(D) else ("DEPTH %d" % (2 * D) if w <= win(2 * D) else "DEPTH>%d or shorter unshared clock" % (2 * D))
        res.append(dict(port=r["port"], tag=r["tag"], depth=D, L_lo=r["L_lo_ps"], L_hi=r["L_hi_ps"], width=round(w, 1),
                        window=round(win(D), 1), ocv_lo=r.get("ocv_lo_ps"), ocv_hi=r.get("ocv_hi_ps"),
                        margin_lo=r["margin_lo_ps"], margin_hi=r["margin_hi_ps"], fix=fix))
    out[C] = dict(fail=len(res), by_fix=dict(collections.Counter(x["fix"] for x in res)),
                  by_pair=dict(collections.Counter(x["tag"] for x in res).most_common()), rows=res)
    print(C, "fail", len(res), out[C]["by_fix"], "max width", max((x["width"] for x in res), default=0),
          "pairs", len(out[C]["by_pair"]))
json.dump(out, open(sys.argv[2], "w"), indent=1)
