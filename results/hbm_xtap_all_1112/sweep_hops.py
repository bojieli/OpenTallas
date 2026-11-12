#!/usr/bin/env python3
"""HBM-VSN-XTAP-2 11-12 all-type cross-tap station-hop sweep (paper, read-only).
sweep_hops.py TOOLS_DIR PLAN_JSON OUT_TSV
For every type with >= 2 clock taps (schema.tap_grid) and every ft slot with >= 2 stations, every hop k -> k+1:
the kit nearest-tap assignment of each bit's two stations (ft_xtap.station_sites / _nearest, as the kit's
clock_taps.tcl nearest pass), the tap pair(s), the number of bits whose two stations land on different taps, the
max/median Manhattan hop length, the type's modeled tap source latency per port (gen_phys: window W charged as
early -W / late 0 on EVERY tap port, so a cross-port pair carries W and a same-port pair gets it back by CRPR)."""
import json, statistics, sys
from collections import Counter
from pathlib import Path

tools, planp, outp = sys.argv[1:4]
sys.path.insert(0, tools)
import schema as S  # noqa: E402
import ft_xtap as X  # noqa: E402
import gen_phys as GP  # noqa: E402
import gen_rtl  # noqa: E402

raw = json.loads(Path(planp).read_text())
P = S.Plan(raw)
rows = []
summ = []
cost = {}
for tn in sorted(P.types):
    try:
        taps = S.tap_grid(P, tn)
    except Exception as e:  # noqa: BLE001
        summ.append(f"# {tn} tap_grid error {e!r}")
        continue
    slots = [s for s in P.types[tn].get("ft_slots", []) if int(s.get("stations", 1)) >= 2]
    if len(taps) < 2 or not slots:
        continue
    W = GP.tap_window_ps(P, tn)
    tab = GP.tap_window_port_table(P, tn)
    lk = gen_rtl.ft_hop_lockup(raw, tn)
    cost[tn] = (sum(int(s.get("stations", 1)) - 1 for s in slots),
                sum((int(s.get("stations", 1)) - 1) * (int(s.get("width", 1)) + 1) for s in slots), int(lk))
    for s in slots:
        st, nb = X.station_sites(P, tn, s)
        for k in range(len(st) - 1):
            a, b = st[k], st[k + 1]
            if not a or not b:
                rows.append((tn, s["name"], k, "?", "?", -1, -1, -1, 0, 0, W, W, int(lk), "unknown_sites"))
                continue
            m = max(len(a), len(b))
            pa = [a[min(i, len(a) - 1)] for i in range(m)]
            pb = [b[min(i, len(b) - 1)] for i in range(m)]
            ta = [X._nearest(taps, *p) for p in pa]
            tb = [X._nearest(taps, *p) for p in pb]
            L = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pa, pb)]
            pairs = Counter((x, y) for x, y in zip(ta, tb) if x != y)
            nx = sum(pairs.values())
            if not nx:
                continue
            la = Counter(ta).most_common(1)[0][0]
            lb = Counter(tb).most_common(1)[0][0]
            # modeled latency delta between the two ports (per-port table when present, else flat W)
            dlat = max(abs((tab.get(x, W)) - 0) for x, y in pairs) if tab else W
            rows.append((tn, s["name"], k, la, lb, round(max(L), 1), round(statistics.median(L), 1), round(min(L), 1), nx, m,
                         W, round(dlat, 1), int(lk),
                         ";".join(f"{x}>{y}:{c}" for (x, y), c in pairs.most_common(4))))
hdr = "type slot k tap_launch tap_capture Lmax_um Lmed_um Lmin_um xbits bits W_ps dlat_ps lockup pairs".split()
with open(outp, "w") as f:
    f.write("\t".join(hdr) + "\n")
    for r in rows:
        f.write("\t".join(map(str, r)) + "\n")
c = Counter(r[0] for r in rows)
print("hops", len(rows), "types", len(c))
for t, n in sorted(c.items()):
    print(f"  {t}\t{n}")
json.dump({t: {"hops_all": v[0], "latch_bits_all": v[1], "lockup": v[2], "xhops": c.get(t, 0)} for t, v in cost.items()},
          open(outp + ".cost.json", "w"), indent=1)
for t in sorted(c):
    print(f"  COST {t} hops_all {cost[t][0]} latch_bits_all {cost[t][1]} lockup {cost[t][2]}")
for l in summ:
    print(l)
