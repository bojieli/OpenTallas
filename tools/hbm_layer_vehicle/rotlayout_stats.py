#!/usr/bin/env python3
"""HBM-ROTLAYOUT census statistics over tb_hbm_bw_pc4 +EXPOSE results (hbm_bw_unit.py run --expose).

  rotlayout_stats.py summary DIR         per run: B/edge/SM, exposed HBM cycles per ACT (closed+conflict+trcd), refresh
  rotlayout_stats.py classes LOG         ds_rot per-class B/edge/SM from the per-block return times (39-block L14 layer:
                                         blocks 26-31 + 33-38 routed, the rest non-expert weights)
  rotlayout_stats.py fit DIR             R2 calibration: stall rate vs words since the nearest earlier block whose set
                                         this block is 4/5 ahead of (blocks with an R1 conflict < 60 words excluded)
"""
import collections, glob, json, re, sys

BLK = r"^BLK (\d+) row (\d+) slot (\d+) words (\d+) ret (\d+) (\d+) (\d+) (\d+)"
K = 0.8138 * 128          # B/edge/SM per column word per HBM cycle (4 PCs x 32 B x 0.9766 GHz / 1.2 GHz)


def blocks(log):
    return [tuple(map(int, m)) for m in re.findall(BLK, open(log).read(), re.M)]


def summary(d):
    for f in sorted(glob.glob(d + "/*_s?.json")):
        r = json.load(open(f)); e = r["expose"][0] if r["expose"] else {}
        ex = e.get("closed", 0) + e.get("conflict", 0) + e.get("trcd", 0)
        print("%-12s s%d B/edge %6.2f steady %6.2f acts %4d exp/ACT %5.2f refresh %3d rc %d %s" % (
            r["pattern"], r["seed"], r.get("B_per_edge") or 0, r.get("steady_B_per_edge") or 0, e.get("acts", 0),
            ex / max(1, e.get("acts", 1)), e.get("refresh", 0), r["rc"], r["fault"]))


def classes(log):
    acc, prev = {}, None
    for b in blocks(log):
        r = max(b[4:8])
        if prev is not None and b[0] >= 8:
            k = b[0] % 39
            c = acc.setdefault("experts" if 26 <= k <= 31 or 33 <= k <= 38 else "weights", [0, 0])
            c[0] += b[3]; c[1] += r - prev
        prev = r
    for c, (w, cy) in acc.items():
        print(f"{c:8s} words {w:6d} cycles {cy:6d} B/edge/SM {w * K / cy:6.2f}")


def fit(d):
    bins = collections.defaultdict(lambda: [0, 0, 0])
    for f in glob.glob(d + "/*_s?.log"):
        if "asbuilt" in f or "rand_" in f:
            continue
        b = blocks(f)
        prev = None
        for i, x in enumerate(b):
            r = max(x[4:]); dur = None if prev is None else r - prev; prev = r
            if i < 8 or dur is None:
                continue
            s, acc, dmin = x[2], 0, None
            for j in range(i - 1, -1, -1):
                acc += b[j][3]
                if (s - b[j][2]) % 8 in (4, 5):
                    dmin = acc; break
                if acc > 600:
                    break
            acc1, r1 = 0, None
            for j in range(i - 1, -1, -1):
                if b[j][2] == s and b[j][1] != x[1]:
                    r1 = acc1; break
                acc1 += b[j][3]
                if acc1 > 200:
                    break
            if r1 is not None and r1 < 60:
                continue
            k = "none" if dmin is None else (dmin // 40) * 40
            ex = dur - x[3]
            bins[k][0] += 1; bins[k][1] += ex > 25; bins[k][2] += max(0, ex)
    for k in sorted(bins, key=lambda x: (x == "none", x if x != "none" else 0)):
        n, st, ex = bins[k]
        print(f"d45-dist {k!s:>5}: blocks {n:5d} stalls>25 {st:4d} ({100 * st / n:5.1f}%) mean excess {ex / n:6.1f}")


if __name__ == "__main__":
    {"summary": summary, "classes": classes, "fit": fit}[sys.argv[1]](sys.argv[2])
