# HBM-RISK-2 R6 reset final-hop reach ESTIMATE: R4 grid taps (budgets.tap_pitch_um default 400) moved off hard cores
# like schema.tap_clear (clear 8.64, 2.16 lattice; nearest by Chebyshev then Euclid; taken-tap spacing ignored), then
# each glue sink (internal station regs) -> nearest tap Manhattan vs reset relay_um 405.
import json, sys, math
import numpy as np
p = json.load(open(sys.argv[1])); lim = float(p["reset"].get("relay_um", 405.0))
pitch = float(p["budgets"].get("tap_pitch_um", 400.0))
for tn in sys.argv[2].split(","):
    t = p["partition_types"][tn]; w, h = t["outline_um"]; clear = 8.64; st = 2.16
    nx, ny = max(1, math.ceil(w / pitch - 1e-9)), max(1, math.ceil(h / pitch - 1e-9))
    xs = np.arange(0, w + 1e-9, st); ys = np.arange(0, h + 1e-9, st)
    free = np.ones((len(ys), len(xs)), bool)
    free[:, (xs < clear) | (xs > w - clear)] = False; free[(ys < clear) | (ys > h - clear), :] = False
    boxes = []
    for c in t.get("hard_cores", []):
        x, y = c["origin_um"]; cw, ch = c["outline_um"]; dx, dy = c.get("track_offset_um", [0, 0])
        x0, y0, x1, y1 = x + dx - clear, y + dy - clear, x + dx + cw + clear, y + dy + ch + clear
        boxes.append((x0, y0, x1, y1))
        free[np.ix_((ys > y0) & (ys < y1), (xs > x0) & (xs < x1))] = False
    fy, fx = np.nonzero(free); FX = xs[fx]; FY = ys[fy]
    taps = []; moved = []
    for j in range(ny):
        for i in range(nx):
            cx, cy = (i + .5) * w / nx, (j + .5) * h / ny
            ix = int(round(cx / st)); iy = int(round(cy / st))
            if 0 <= iy < len(ys) and 0 <= ix < len(xs) and free[iy, ix]:
                taps.append((cx, cy)); continue
            d = np.maximum(abs(FX - cx), abs(FY - cy)); m = d.min()
            sel = np.nonzero(d <= m + 1e-6)[0]; k = sel[np.argmin((FX[sel] - cx) ** 2 + (FY[sel] - cy) ** 2)]
            taps.append((FX[k], FY[k])); moved.append(m)
    T = np.array(taps)
    sinks = [(r[0], r[1], s.get("conn", "")) for s in t.get("internal_stations", []) for r in s.get("regs_um", [])]
    S = np.array([(a, b) for a, b, _ in sinks]) if sinks else np.zeros((0, 2))
    if len(S):
        D = np.abs(S[:, None, 0] - T[None, :, 0]) + np.abs(S[:, None, 1] - T[None, :, 1]); dn = D.min(1)
    else: dn = np.zeros(0)
    # sinks on a hard core box (should not exist) are flagged
    oncore = sum(1 for a, b, _ in sinks if any(x0 + clear < a < x1 - clear and y0 + clear < b < y1 - clear for x0, y0, x1, y1 in boxes))
    # outline-sample bound over free (channel) points
    sub = slice(None, None, 7)
    if len(FX):
        FS = np.stack([FX[sub], FY[sub]], 1)
        best = np.full(len(FS), np.inf)
        for a, b in T: best = np.minimum(best, abs(FS[:, 0] - a) + abs(FS[:, 1] - b))
        chb = best.max()
    else: chb = 0
    order = np.argsort(-dn)[:5]
    print(f"{tn}: {w}x{h} grid {nx}x{ny}={len(T)} taps, moved {len(moved)} (max shift {max(moved) if moved else 0:.1f} um); "
          f"station regs {len(S)}: max hop {dn.max() if len(dn) else 0:.1f} um, >{lim:g} {int((dn > lim).sum())}, on-core {oncore}; "
          f"channel-point bound {chb:.1f} um; free frac {free.mean():.3f}")
    for k in order: print("    ", round(float(dn[k]), 1), sinks[k][2][:60], round(sinks[k][0], 1), round(sinks[k][1], 1))
    bad = [(sinks[k][0], sinks[k][1]) for k in np.nonzero(dn > lim)[0]]
    from collections import Counter
    print("    >lim clusters (500-um bins):", Counter((int(a // 500) * 500, int(b // 500) * 500) for a, b in bad).most_common(8))
    print("    oncore sample:", [(round(a), round(b), c[:30]) for a, b, c in sinks if any(x0 + clear < a < x1 - clear and y0 + clear < b < y1 - clear for x0, y0, x1, y1 in boxes)][:3])
