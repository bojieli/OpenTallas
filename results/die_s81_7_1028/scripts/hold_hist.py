#!/usr/bin/env python3
"""DIE-S81-7: FF hold structure + in-region spread from a DIE-QC-5 dump_hb.py pickle (main die_sta_related unchanged,
per endpoint-path (setup, hold) records handed to hold_buffer_model) and the proof taps.
hold = base (stand-in clkq_min - lib hold - 25 ps unc) - nominal CPPR'd damage - clock OCV (QC-5 hold_decomp method).
Per region: in-region spread = max damage+OCV over its pairs is NOT used; spread here = max nominal CPPR'd damage
(the die STA 'skew' diagnostic, per region), TT and FF.   usage: hold_hist.py TOOLS PKL_TT_FF PROOF OUT.json BASE_FF"""
import sys, pickle, json, collections, math
sys.path.insert(0, sys.argv[1])
import die_sta_related as R
from pathlib import Path
R.CPPR_LCA = True
S = pickle.load(open(sys.argv[2], "rb")); PR = Path(sys.argv[3]); base = float(sys.argv[5])
M = {C: R.load_taps(PR, C) for C in ("TT", "FF")}
call = S["calls"][0]; fe = call["hb"]["ff_early_ps"]
def dmg(C, a, b):
    meta, taps = M[C]; A, B = taps[a], taps[b]; node = R.pair_node(A, B)
    la, ea, lc, ec = R.arr4(A, B, node)
    return lc - ea - R.credit(meta["cppr_node_range_ps"], node, la, ea, lc, ec)
bins = collections.Counter(); cause = collections.Counter(); capk = {}; reg = collections.defaultdict(lambda: [0.0, 0.0])
ocvs = []; dms = []
for key, v in call["ff"].items():
    a, b, tag = key[:3]; h = v[1]
    d = dmg("FF", a, b); o = base - d - h
    reg[tag][1] = max(reg[tag][1], d)
    if h >= 0: bins[">=0"] += 1
    else:
        bins[next(l for lo, l in ((-25, "-25..0"), (-50, "-50..-25"), (-100, "-100..-50"), (-150, "-150..-100"), (-1e9, "<-150")) if h >= lo)] += 1
        cause["damage>ocv" if d > o else "ocv>=damage"] += 1
        ocvs.append(o); dms.append(d)
    k = max(0, math.ceil(-h / fe - 1e-9)) if h < 0 else 0
    capk[b] = max(capk.get(b, 0), k)
for key in call["tt"]:
    a, b, tag = key[:3]
    reg[tag][0] = max(reg[tag][0], dmg("TT", a, b))
srt = lambda L: sorted(L)[len(L) // 2] if L else None
rows = sorted(((round(t, 1), round(f, 1), p) for p, (t, f) in reg.items()), reverse=True)
seam = S["calls"][1]["ff"] if len(S["calls"]) > 1 else {}
out = dict(base_ps=base, ff_early_hb4_ps=fe, intra_paths=len(call["ff"]), seam_paths=len(seam),
           hold_bins=dict(bins), neg_paths=sum(v for k, v in bins.items() if k != ">=0"), cause=dict(cause),
           neg_median_damage_ps=round(srt(dms), 1) if dms else None, neg_median_ocv_ps=round(srt(ocvs), 1) if ocvs else None,
           neg_paths_damage_lt20=sum(1 for x in dms if x < 20),
           hb4_capture_taps=sum(1 for k in capk.values() if k), hb4_cells_per_tap_worst_k=sum(capk.values()),
           k_hist=dict(sorted(collections.Counter(capk.values()).items())), part_bits=call.get("part_bits"),
           regions=len(rows), regions_over150=[r for r in rows if r[0] > 150 or r[1] > 150], top_regions=rows[:6],
           p50_tt=sorted(r[0] for r in rows)[len(rows) // 2])
json.dump(out, open(sys.argv[4], "w"), indent=1)
print("HOLDHIST", json.dumps(out))
