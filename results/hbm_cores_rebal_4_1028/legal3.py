#!/usr/bin/env python3
"""HBM-CORES-REBAL-4: column legaliser for a plan-fixed SRAM placement (die-local, estimate + output).
Input: an RTLMP-derived placement (gen --macro-placement json: k, origin_um, orient, macro), the kit (CORE_AREA,
macro LEF SIZE, core_infra_plan.json island rects). Output: a placement that satisfies the existing kit_contract
rules -- macro columns (x-overlap clusters) with >= MIN vertical channels incl. the core edges, >= one interior
horizontal channel >= MIN per stacked column -- and keeps every macro + halo clear of every planned island rect.
Method: keep RTLMP's column order and per-column macro order (smallest change); align each x-cluster to one x,
spread columns to the channel minimum, then stack each column bottom-up at 2*halo pitch with the widest gap
forced to MIN, skipping island y-bands that fall inside the column's x band (+halo); top-down retry if it overflows.
  legal3.py IN.json KITDIR OUT.json"""
import json, re, sys
from pathlib import Path

MIN, HALO = 10.8, 4.32
src, kd, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
cfg = {m.group(1): m.group(2).strip() for m in re.finditer(r"^export\s+(\w+)\s*=\s*(.*)$", (kd / "config.mk").read_text(), re.M)}
cx0, cy0, cx1, cy1 = map(float, cfg["CORE_AREA"].split())
sizes = {}
for lef in (kd / "macros").glob("*.lef"):
    t = lef.read_text()
    for m in re.finditer(r"^MACRO\s+(\S+).*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t, re.S | re.M):
        sizes[m.group(1)] = (float(m.group(2)), float(m.group(3)))
isl = sorted({tuple(c["rect_um"]) for c in json.load(open(kd / "core_infra_plan.json"))["cells"]})
mp = json.load(open(src))["macro_placement"]
M = []
for m in mp:
    w, h = sizes[m["macro"]]
    if m["orient"] in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    x, y = m["origin_um"]
    M.append(dict(m, w=w, h=h, x0=x, y0=y))
# columns = x-overlap clusters of the input
M.sort(key=lambda b: b["x0"])
cols = []
for b in M:
    if cols and b["x0"] < cols[-1][0]["x0"] + b["w"] / 2:              # same column: x0 within half a width
        cols[-1].append(b)
    else:
        cols.append([b])
W = [max(b["w"] for b in c) for c in cols]
X = [sum(b["x0"] for b in c) / len(c) for c in cols]                  # mean member x
lo, hi = cx0 + MIN, cx1 - MIN
for i in range(len(cols)):                                              # left-to-right spread
    X[i] = max(X[i], lo if i == 0 else X[i - 1] + W[i - 1] + MIN)
for i in reversed(range(len(cols))):                                    # right-to-left pull-back
    X[i] = min(X[i], hi - W[i] if i == len(cols) - 1 else X[i + 1] - W[i] - MIN)
fail = []
if X[0] < lo - 1e-6:
    fail.append(f"columns do not fit: need {sum(W) + MIN * (len(W) + 1):.2f} um of {cx1 - cx0:.2f}")


def bands(x, w):
    """island y-bands (expanded by halo) that intersect the column x band [x - HALO, x + w + HALO]."""
    return sorted((r[1] - HALO, r[3] + HALO) for r in isl if r[0] < x + w + HALO and r[2] > x - HALO)


def stack(col, x, w, up=True):
    bs = bands(x, w)
    col = sorted(col, key=lambda b: b["y0"])
    n = len(col)
    # forced interior channel: at the widest input gap (keeps RTLMP's grouping)
    gi = max(range(n - 1), key=lambda k: col[k + 1]["y0"] - col[k]["y0"] - col[k]["h"]) if n > 1 else -1
    ys, prev = [], None
    for k, b in enumerate(col):
        y = b["y0"] if prev is None else max(b["y0"], prev + (MIN if k - 1 == gi else 2 * HALO))
        y = max(y, cy0 + HALO)
        moved = True
        while moved:
            moved = False
            for a, z in bs:
                if y < z and y + b["h"] > a:
                    y, moved = z, True
        ys.append(y)
        prev = y + b["h"]
    return col, ys, (prev or 0) <= cy1 - HALO + 1e-6


def stack_down(col, x, w):
    bs = bands(x, w)
    col = sorted(col, key=lambda b: b["y0"])
    n = len(col)
    gi = max(range(n - 1), key=lambda k: col[k + 1]["y0"] - col[k]["y0"] - col[k]["h"]) if n > 1 else -1
    ys, nxt = [0.0] * n, None
    for k in reversed(range(n)):
        b = col[k]
        y = b["y0"] if nxt is None else min(b["y0"], nxt - (MIN if k == gi else 2 * HALO) - b["h"])
        y = min(y, cy1 - HALO - b["h"])
        moved = True
        while moved:
            moved = False
            for a, z in bs:
                if y < z and y + b["h"] > a:
                    y, moved = a - b["h"], True
        ys[k] = y
        nxt = y
    return col, ys, nxt is None or nxt >= cy0 + HALO - 1e-6


res = []
for i, c in enumerate(cols):
    col, ys, ok = stack(c, X[i], W[i])
    if not ok:
        col, ys, ok = stack_down(c, X[i], W[i])
    if not ok:
        fail.append(f"column {i} x={X[i]:.3f}: {len(c)} macros do not fit between island bands")
    for b, y in zip(col, ys):
        res.append(dict(k=b["k"], macro=b["macro"], orient=b["orient"], origin_um=[round(X[i] / 0.054) * 0.054, round(y / 0.27) * 0.27],
                        moved_um=0.0, w=b["w"], h=b["h"], src=[b["x0"], b["y0"]]))
for r in res:
    r["origin_um"] = [round(v, 3) for v in r["origin_um"]]
    # grid snap can only move by < one step; re-check spacing after snap below
    r["moved_um"] = round(abs(r["origin_um"][0] - r["src"][0]) + abs(r["origin_um"][1] - r["src"][1]), 3)


def ov(a, b, m=0.0):
    return a[0] < b[2] + m and a[2] > b[0] - m and a[1] < b[3] + m and a[3] > b[1] - m


R = [(r["origin_um"][0], r["origin_um"][1], r["origin_um"][0] + r["w"], r["origin_um"][1] + r["h"]) for r in res]
isl_hits = sum(1 for a in R for s in isl if ov(a, s, HALO - 1e-6))
mac_hits = sum(1 for i, a in enumerate(R) for b in R[i + 1:] if ov(a, b))
mv = [r["moved_um"] for r in res]
rep = dict(src=src, kit=str(kd), macros=len(res), columns=len(cols), col_x=[round(x, 3) for x in X], islands=len(isl),
           moved=sum(1 for v in mv if v > 0.01), max_move_um=max(mv), mean_move_um=round(sum(mv) / len(mv), 2),
           island_halo_hits=isl_hits, macro_overlaps=mac_hits, fail=fail)
json.dump(dict(source=f"HBM-CORES-REBAL-4 legal3.py from {src}", report=rep,
               macro_placement=[{k: r[k] for k in ("k", "macro", "orient", "origin_um", "moved_um")} for r in res]),
          open(out, "w"), indent=1)
print(json.dumps(rep))
