#!/usr/bin/env python3
"""DIE-QC-6: split the FF hold clock OCV on intra pairs into (i) the die tree below the pair LCA and (ii) the declared
in-core latency (class B, core_lat on BOTH branches), with main clock_ocv_fn unchanged.  usage: TOOLS PKL PROOF"""
import sys, pickle, json, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import die_sta_related as R
R.CPPR_LCA = True
S = pickle.load(open(sys.argv[2], "rb"))
P = Path(sys.argv[3])
meta, taps = R.load_taps(P, "FF")
meta, taps = R.scale_clock(meta, taps, R.SPICE_CLOCK_CAL["FF"])
dreg = R.droop_regions(P, taps, "mesh", str(P / "droop_regions.json"))
f250 = R.clock_ocv_fn("table", "shared", dict(meta, corner="FF"), taps, 250.0, region=dreg)
f0 = R.clock_ocv_fn("table", "shared", dict(meta, corner="FF"), taps, 0.0, region=dreg)
def cls(p): return "c_*" if p.startswith("c_") else ("sl_*_su_c" if p.endswith("su_c") else ("sl_*" if p.startswith("sl_") else "other"))
agg = collections.defaultdict(list)
seen = set()
for key, v in S["calls"][0]["ff"].items():
    a, b, tag = key[:3]
    if (a, b) in seen: continue
    seen.add((a, b))
    A, B_ = taps[a], taps[b]
    node = R.pair_node(A, B_)
    la, ea, lc, ec = R.arr4(A, B_, node)
    br = lc - float(meta["node_late_ps"][node]) if node != "h" else None
    o250, o0 = f250(a, b, "hold"), f0(a, b, "hold")
    agg[cls(tag)].append((v[1], o250, o0, br, len(node), int(B_["stages_from_root"]) - int(meta["node_stages"][node])))
for c, L in sorted(agg.items()):
    n = len(L)
    def q(i, p): s = sorted(x[i] for x in L if x[i] is not None); return round(s[min(len(s) - 1, int(p * len(s)))], 1)
    L.sort()
    w = L[0]
    print(f"{c:10s} n {n:6d} | ocv total med {q(1,.5)} p99 {q(1,.99)} | tree-below-LCA part (core_lat 0) med {q(2,.5)} p99 {q(2,.99)} | in-core class-B part med {round(q(1,.5)-q(2,.5),1)} | capture branch below LCA ps med {q(3,.5)} p99 {q(3,.99)} | LCA depth med {q(4,.5)} | stages below LCA med {q(5,.5)} | worst hold {w[0]:.1f} ocv {w[1]:.1f} tree-part {w[2]:.1f} branch {w[3]}")
