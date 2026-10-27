# per-leaf (ot_ms_<tap>_clk net) clock-arrival stats from meas_ck.tsv: col 3 = arrival_max_rise (tap-mean basis of
# OT_MSCTS_TAP), col 5 = arrival_min_rise (early).  Output one JSON line per file.  Non-leaf sinks (macro CK etc.) reported apart.
import sys, json, re, statistics as st
for fn in sys.argv[1:]:
    leaf, other, allv, alle = {}, [], [], []
    for l in open(fn):
        if l.startswith("#"): continue
        f = l.rstrip("\n").split("\t")
        try: a = float(f[2]); e = float(f[4])
        except ValueError: continue
        m = re.fullmatch(r"ot_ms_(Q\w+?)_clk", f[1])
        allv.append(a); alle.append(e)
        if m: leaf.setdefault(m.group(1), []).append((a, e))
        else: other.append((f[0], f[1], round(a, 1)))
    lm = {k: st.mean(x[0] for x in v) for k, v in leaf.items()}
    le = {k: st.mean(x[1] for x in v) for k, v in leaf.items()}
    print(json.dumps(dict(file=fn.split("/")[-1], n=len(allv), mean=round(st.mean(allv), 2), min=round(min(allv), 1), max=round(max(allv), 1),
        leaves=len(lm), leaf_mean_lo=round(min(lm.values()), 1), leaf_mean_hi=round(max(lm.values()), 1), window=round(max(lm.values()) - min(lm.values()), 1),
        early_mean=round(st.mean(alle), 2), early_window=round(max(le.values()) - min(le.values()), 1), nonleaf=len(other), nonleaf_ex=other[:3])))
