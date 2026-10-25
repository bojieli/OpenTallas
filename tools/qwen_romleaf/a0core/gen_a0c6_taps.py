#!/usr/bin/env python3
"""QC-P6-A0 10-23: A0 v6 sink-anchored clock taps from the PLACED flop columns (GEOM-REVIEW7 18:34 FIX list).

v4/v5 sited 20/24 taps at capacity-constrained centroids of the v2 sinks: the ROM-spine columns (15-35 um wide) put
2-4k sinks in ~300-um 1-D strips per tap and 17/24 measured trees were > 290 ps.  v6 uses the KV-P6-TAP tool's
Manhattan k-medians (tools/die_plan/taps.py, claude/kv-p6-tap-1023 @c1bae2221, clock.tap_mode 'sinks'): k grows from
ceil(N / cap) until every cluster fits the cap (default 1500 sinks) and the reach: p99 <= --radius (default 150 um) and
max <= --radius-max (default 180 um).  A strict 120-um max needs k = 65 (NK) / 49 (NL): lone E-face / corner flops set
the max, so the bulk criterion is the p99 (measured 10-23: k 33-36 per core).  Taps left with < --min-sinks (64) sinks
are dropped (their sinks go to the next tap, as a0_clock_taps.tcl re-assigns them).  The sinks are
the flops + hard-child clock pins of the v5 placed 3_5_place_dp.odb (same RTL body, regions, outline and pins as v6).

Snap (as v5): x on an M7 track in a PG-free band, y on an M6 track, >= 6 um off every hard child.

Per-tap reset (no single landing copy far from its tap): the last reset landing stage is already split into copies
(rst_n__ot_rl1 + ot_rrs__rst_n__ot_rlv__c<k>, ot_rst_copies + reset_relay_split; deterministic names, the RTL body is
unchanged); each copy is assigned to the tap nearest its v5 placed site and a0_reset_taps6.tcl puts it FIRM at that tap
before GPL (released to DPL), so every copy sits on its own tap's tree.

    gen_a0c6_taps.py TV_TSV FLOORPLAN_JSON PINS_IN PINS_OUT RESET_OUT JSON_OUT [--radius 150] [--radius-max 180] [--cap 1500] [--min-sinks 64]
"""
import argparse
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "die_plan"))
import taps as T  # noqa: E402

CLEAR_UM = 6.0


def cap_kmedians(pts, k, cap, iters=30):
    """taps.py _kmedians (farthest-point seeding from the sink nearest the centre, L1 medians) with the assignment made
    capacity-constrained as a0_clock_taps6.tcl applies it before CTS: nearest tap, then each over-full tap sheds the
    sinks of least extra distance to their best tap with room.  numpy; deterministic."""
    import numpy as np
    P = np.asarray(pts, dtype=float)
    c = P.mean(0)
    s0 = int(np.argmin(np.abs(P - c).sum(1)))
    cen = [P[s0]]
    dmin = np.abs(P - P[s0]).sum(1)
    while len(cen) < k:
        i = int(np.argmax(dmin))
        cen.append(P[i])
        dmin = np.minimum(dmin, np.abs(P - P[i]).sum(1))
    C = np.array(cen)
    prev = None
    for _ in range(iters):
        D = np.abs(P[:, None, 0] - C[None, :, 0]) + np.abs(P[:, None, 1] - C[None, :, 1])
        A = D.argmin(1)
        for _p in range(4 * k):
            cnt = np.bincount(A, minlength=k)
            over = np.where(cnt > cap)[0]
            if not len(over):
                break
            o = over[np.argmax(cnt[over])]
            mem = np.where(A == o)[0]
            room = cnt < cap
            room[o] = False
            if not room.any():
                break
            Dm = D[mem][:, room]
            alt = np.where(room)[0][Dm.argmin(1)]
            extra = Dm.min(1) - D[mem, o]
            order = np.argsort(extra, kind="stable")
            # move toward ONE target per pass (keeps the targets under cap)
            tgt = alt[order[0]]
            take = [mem[i] for i in order if alt[i] == tgt][: min(cnt[o] - cap, cap - cnt[tgt])]
            A[take] = tgt
        if prev is not None and np.array_equal(A, prev):
            break
        prev = A.copy()
        C = np.array([np.median(P[A == j], 0) if (A == j).any() else C[j] for j in range(k)])
    groups = [[tuple(p) for p in P[A == j]] for j in range(k)]
    return [tuple(x) for x in C], groups


def load_tv(fn):
    sinks, rst = [], {}
    for line in open(fn):
        f = line.rstrip("\n").split("\t")
        if f[0] == "C" and "DFF" in f[1]:
            x, y = (float(f[2]) + float(f[4])) / 2, (float(f[3]) + float(f[5])) / 2
            sinks.append((x, y))
            n = f[6]
            if re.match(r"^(rst_n__ot_rl1|ot_rrs__rst_n__ot_rlv__c\d+)\$", n) or re.match(r"^rst_n__ot_rlc", n):
                rst[n] = (x, y)
        elif f[0] == "B":
            sinks.append(((float(f[2]) + float(f[4])) / 2, (float(f[3]) + float(f[5])) / 2))
    return sinks, rst


def free_x(x):
    best = None
    for n in range(int((x - 12) / 0.064), int((x + 12) / 0.064)):
        xx = round(0.016 + 0.064 * n, 3)
        m = (xx - 1.0) % 10.8
        if (0.288 + 0.25 <= m <= 5.4 - 0.25) or (5.688 + 0.25 <= m <= 10.8 - 0.25):
            if best is None or abs(xx - x) < abs(best - x):
                best = xx
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tv")
    ap.add_argument("floorplan")
    ap.add_argument("pins_in")
    ap.add_argument("pins_out")
    ap.add_argument("reset_out")
    ap.add_argument("json_out")
    ap.add_argument("--radius", type=float, default=150.0)
    ap.add_argument("--radius-max", type=float, default=180.0)
    ap.add_argument("--min-sinks", type=int, default=64)
    ap.add_argument("--cap", type=int, default=1500)
    a = ap.parse_args()
    fp = json.load(open(a.floorplan))
    W, H = fp["die"][2], fp["die"][3]
    boxes = [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]) for b in fp["blocks"] if b.get("kind") == "child"]
    pts, rst = load_tv(a.tv)
    N = len(pts)
    k = max(1, math.ceil(N / a.cap))
    while True:
        cen, groups = cap_kmedians(pts, k, a.cap)
        cl = [(c, g) for c, g in zip(cen, groups) if len(g) >= a.min_sinks]
        import numpy as np
        rr = [np.array([abs(p[0] - c[0]) + abs(p[1] - c[1]) for p in g]) for c, g in cl]
        ok = all(len(g) <= a.cap for _, g in cl) and all(np.percentile(d, 99) <= a.radius and d.max() <= a.radius_max
                                                          for d in rr)
        print(f"k={k}: taps {len(cl)}, max sinks {max(len(g) for _, g in cl)}, reach p99 max "
              f"{max(np.percentile(d, 99) for d in rr):.0f}, max {max(d.max() for d in rr):.0f}", flush=True)
        if ok or k >= 96:
            break
        k += 1

    def inbox(x, y):
        return any(x0 - CLEAR_UM <= x <= x1 + CLEAR_UM and y0 - CLEAR_UM <= y <= y1 + CLEAR_UM for x0, y0, x1, y1 in boxes)

    taps = []
    for (x, y), g in cl:
        if inbox(x, y):  # median on a hard child: nearest own sink off the children
            off = [(p[0], p[1]) for p in g if not inbox(p[0], p[1])]
            if not off:  # only child pins: nearest free point on a 2-um spiral
                off = [(x + dx, y + dy) for r in range(2, 200, 2) for dx in range(-r, r + 1, 2) for dy in (-r, r)
                       if not inbox(x + dx, y + dy) and 2 < x + dx < W - 2 and 2 < y + dy < H - 2][:50]
            x, y = min(off, key=lambda q: abs(q[0] - x) + abs(q[1] - y))
        x = min(max(x, T.TAP_MARGIN_UM), W - T.TAP_MARGIN_UM)
        y = min(max(y, T.TAP_MARGIN_UM), H - T.TAP_MARGIN_UM)
        taps.append([free_x(x), round(0.016 + 0.064 * round((y - 0.016) / 0.064), 3)])
    # tap 0 'ck' = the v4/v5 ck site's nearest; the rest (y, x) order
    taps.sort(key=lambda q: (q[1], q[0]))
    i0 = min(range(len(taps)), key=lambda i: abs(taps[i][0] - 80.848) + abs(taps[i][1] - 1024.272))
    taps = [taps[i0]] + [q for i, q in enumerate(taps) if i != i0]
    names = ["ck" if i == 0 else f"ck_t{i}" for i in range(len(taps))]
    # nearest-tap statistics on the placed sinks (= a0_clock_taps.tcl's first assignment)
    asg = [min(range(len(taps)), key=lambda j: (abs(p[0] - taps[j][0]) + abs(p[1] - taps[j][1]), j)) for p in pts]
    st = []
    for j, (n, (x, y)) in enumerate(zip(names, taps)):
        m = [p for p, q in zip(pts, asg) if q == j]
        st.append(dict(name=n, xy=[x, y], sinks=len(m),
                       reach_um=round(max((abs(p[0] - x) + abs(p[1] - y) for p in m), default=0), 1)))
    # reset copies -> nearest tap
    rs = []
    for n, (x, y) in sorted(rst.items()):
        j = min(range(len(taps)), key=lambda q: abs(x - taps[q][0]) + abs(y - taps[q][1]))
        rs.append((n, names[j], taps[j][0], taps[j][1], round(abs(x - taps[j][0]) + abs(y - taps[j][1]), 1)))
    with open(a.reset_out, "w") as f:
        f.write("# inst\ttap\tx_um\ty_um\tmove_um (gen_a0c6_taps.py: reset landing copy -> tap nearest its v5 placed site)\n")
        for r in rs:
            f.write("\t".join(str(v) for v in r) + "\n")
    lines = [l for l in open(a.pins_in) if not re.match(r"place_pin -pin_name \{ck(_t\d+)?\}", l)
             and not l.startswith("# QC-P5 v5") and not l.startswith("# moved >=") and not l.startswith("# sinks/reach")
             and not l.startswith("# QC-P5 10-23 A0 v4 clock taps")]
    with open(a.pins_out, "w") as f:
        f.writelines(lines)
        f.write(f"# QC-P6-A0 10-23 A0 v6: {len(taps)} interior M7 clock taps (die spine M8 -> M7 drop each) = KV-P6-TAP sink-anchored\n"
                f"# k-medians (tools/die_plan/taps.py, reach p99 <= {a.radius:.0f} / max <= {a.radius_max:.0f} um, cap {a.cap}) of the v5 PLACED flops + child clock pins\n"
                f"# ({N} sinks); x on an M7 track between the PG stripes, y on an M6 track, >= {CLEAR_UM:.0f} um off hard children.\n")
        for s in st:
            f.write(f"place_pin -pin_name {{{s['name']}}} -layer M7 -location {{{s['xy'][0]} {s['xy'][1]}}} "
                    f"-pin_size {{0.032 0.768}}   ;# {s['sinks']} v5 placed sinks, reach {s['reach_um']:.0f} um\n")
    json.dump(dict(tool="tools/die_plan/taps.py@c1bae2221 _kmedians", reach_p99_um=a.radius, reach_max_um=a.radius_max, cap=a.cap, sinks=N, k=k,
                   n_taps=len(taps), empty=sum(1 for s in st if s["sinks"] == 0), taps=st,
                   reset_copies=[dict(inst=r[0], tap=r[1], move_um=r[4]) for r in rs]),
              open(a.json_out, "w"), indent=1)
    print(f"{len(taps)} taps, sinks {min(s['sinks'] for s in st)}..{max(s['sinks'] for s in st)}, "
          f"reach max {max(s['reach_um'] for s in st):.0f} um, empty {sum(1 for s in st if s['sinks'] == 0)}; "
          f"{len(rs)} reset copies -> {len(set(r[1] for r in rs))} taps, move max {max((r[4] for r in rs), default=0):.0f} um")


if __name__ == "__main__":
    main()
