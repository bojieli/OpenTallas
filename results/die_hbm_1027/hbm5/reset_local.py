#!/usr/bin/env python3
"""DIE-HBM-5 (COORD 02:5x (b)): hub reset local taps. The R4 grid-tap model is HBM-RISK-2 r6fast.py (tap_clear re-impl,
UNCHECKED vs the kit). Greedy farthest-sink cover: while a station reg is > TARGET um (Manhattan) from every tap, add
reset.local_taps_um at the free 2.16-site (clear 8.64) nearest that reg. Legality is then re-checked with the real tool
(reset_tree.consumer_taps).  usage: reset_local.py TOOLS_DIE_PLAN PLAN_IN [PLAN_OUT] [TARGET]"""
import json, sys, math, hashlib, pathlib
import numpy as np
tools, pin = sys.argv[1], pathlib.Path(sys.argv[2]); pout = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
TARGET = float(sys.argv[4]) if len(sys.argv) > 4 else 380.0
p = json.loads(pin.read_text()); pitch = float(p["budgets"].get("tap_pitch_um", 400.0)); lim = float(p["reset"].get("relay_um", 405.0))
rep = {}
for tn in ("q_hub_nw", "q_hub_ne"):
    t = p["partition_types"][tn]; w, h = t["outline_um"]; clear = 8.64; st = 2.16
    nx, ny = max(1, math.ceil(w / pitch - 1e-9)), max(1, math.ceil(h / pitch - 1e-9))
    xs = np.arange(0, w + 1e-9, st); ys = np.arange(0, h + 1e-9, st)
    free = np.ones((len(ys), len(xs)), bool)
    free[:, (xs < clear) | (xs > w - clear)] = False; free[(ys < clear) | (ys > h - clear), :] = False
    CB = []
    for c in t.get("hard_cores", []):
        x, y = c["origin_um"]; cw, ch = c["outline_um"]; dx, dy = c.get("track_offset_um", [0, 0])
        x0, y0, x1, y1 = x + dx - clear, y + dy - clear, x + dx + cw + clear, y + dy + ch + clear
        CB.append((x + dx, y + dy, x + dx + cw, y + dy + ch))
        free[np.ix_((ys > y0) & (ys < y1), (xs > x0) & (xs < x1))] = False
    fy, fx = np.nonzero(free); FX = xs[fx]; FY = ys[fy]
    taps = []
    for j in range(ny):
        for i in range(nx):
            cx, cy = (i + .5) * w / nx, (j + .5) * h / ny
            ix = int(round(cx / st)); iy = int(round(cy / st))
            if 0 <= iy < len(ys) and 0 <= ix < len(xs) and free[iy, ix]: taps.append((cx, cy)); continue
            d = np.maximum(abs(FX - cx), abs(FY - cy)); m = d.min()
            sel = np.nonzero(d <= m + 1e-6)[0]; k = sel[np.argmin((FX[sel] - cx) ** 2 + (FY[sel] - cy) ** 2)]
            taps.append((FX[k], FY[k]))
    old = list(t.get("reset", {}).get("local_taps_um", []))
    taps += [tuple(q) for q in old]
    S0 = np.array([(r[0], r[1]) for s in t.get("internal_stations", []) for r in s.get("regs_um", [])])
    inc = np.zeros(len(S0), bool)
    for a, b, c, d in CB: inc |= (S0[:, 0] > a) & (S0[:, 0] < c) & (S0[:, 1] > b) & (S0[:, 1] < d)
    S = S0[~inc]; print(tn, "station regs", len(S0), "inside core boxes (pushdown, reset from the core)", int(inc.sum()), flush=True)
    T = np.array(taps); dn = (np.abs(S[:, None, 0] - T[None, :, 0]) + np.abs(S[:, None, 1] - T[None, :, 1])).min(1)
    print(tn, 'grid done', flush=True)
    before = (round(float(dn.max()), 1), int((dn > lim).sum()))
    add = []
    while dn.max() > TARGET:
        a, b = S[int(np.argmax(dn))]
        k = int(np.argmin(abs(FX - a) + abs(FY - b))); q = (round(float(FX[k]), 3), round(float(FY[k]), 3))
        if list(q) in add: print(' stuck at', q, 'sink', (round(float(a), 1), round(float(b), 1)), round(float(dn.max()), 1), flush=True); break
        add.append(list(q)); dn = np.minimum(dn, abs(S[:, 0] - q[0]) + abs(S[:, 1] - q[1]))
    rep[tn] = {"pushdown_regs_excluded": int(inc.sum()), "grid_taps": len(T) - len(old), "before_max_hop_um": before[0], "before_over_405": before[1],
               "added_local_taps": len(add), "after_max_hop_um": round(float(dn.max()), 1), "after_over_405": int((dn > lim).sum()),
               "target_um": TARGET, "local_taps_um": add}
    t.setdefault("reset", {})["local_taps_um"] = old + add
    print(tn, {k: v for k, v in rep[tn].items() if k != "local_taps_um"})
sys.path.insert(0, tools)
import schema as Sch, reset_tree as RT
P = Sch.Plan(p, pin)
for tn in rep:
    print('tool check', tn, flush=True)
    try: RT.consumer_taps(P, tn); rep[tn]["tool_legal"] = True
    except Exception as e: rep[tn]["tool_legal"] = repr(e)[:300]
    print(tn, "reset_tree.consumer_taps:", rep[tn]["tool_legal"])
if pout:
    p["note"] = p.get("note", "") + " | C20i-r (DIE-HBM-5): hub reset.local_taps_um (greedy cover, target %g um)" % TARGET
    txt = json.dumps(p, indent=1); pout.write_text(txt)
    sha = hashlib.sha256(txt.encode()).hexdigest(); (pout.parent / "die_plan.sha256").write_text(sha + "  die_plan.json\n")
    (pout.parent / "reset_local_report.json").write_text(json.dumps(dict(rep, sha=sha), indent=1)); print(sha[:12])
