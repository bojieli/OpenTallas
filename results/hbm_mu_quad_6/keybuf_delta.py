#!/usr/bin/env python3
"""HBM-MU-QUAD-6 keybuf delta: replace the 4 unpinned 324^2 hnx_idxn_keybuf hard cores (q_hub_nw/q_hub_ne
u_mu_keybuf_0__q0/__q1) by 8 ot_hnx_idxn_keybuf_slice hard cores each (lot 241.92x293.76, lot_model.json), ONE core
design (one pin table), MY instances where the partner (u_hb_idx__q_Q__q<seg>) lies east.  Placement: greedy nearest
free 8.64-lattice lot to the partner centre within the segment, no hard-core overlap incl 4.32 halo, and NO existing
station / ft register inside the lot (hard constraint, so nothing has to be re-stationed).  The old proxy kin/kout
internal_stations (256-bit, R9) are replaced by one kin (1127 b) + one kout (1100 b) entry per slice, regs on an L
path every <= 396 um, never inside a hard core.  Deterministic.  usage: keybuf_delta.py PLAN_IN PLAN_OUT REPORT.json"""
import json, sys, shutil, math, hashlib
from pathlib import Path
import numpy as np
src, dst, rep_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
W_, H_ = 241.92, 293.76; LAT = 8.64; HALO = 4.32; SEGX = 3957.12; HOP = 396.0
CLK = (120.984, 146.88)
PEN = 15.0      # um of distance traded per displaced existing register
MOD = "ot_hnx_idxn_keybuf_slice"; PFILE = f"cores/{MOD}__241.92x293.76__canon.json"
KIN_BITS = 1099 + 28; KOUT_BITS = 1099 + 1     # key_in + (clear, live_v, live_index8, pre_v, pre_index8, replay_v, replay_index8); key_out + fault

def pin_table():
    sig = (["clear", "live_v"] + [f"live_index[{i}]" for i in range(8)] + ["pre_v"] + [f"pre_index[{i}]" for i in range(8)]
           + ["replay_v"] + [f"replay_index[{i}]" for i in range(8)] + [f"key_in[{i}]" for i in range(1099)]
           + [f"key_out[{i}]" for i in range(1099)] + ["fault"] + [f"strap_lane_id[{i}]" for i in range(3)] + ["rst_n"])
    pins = [dict(name="clk", layer="M5", x=CLK[0], y=CLK[1])]
    # W face, M4 (H) on every 2nd track: y = 0.024 + 0.048*(2k+1), starting above 2 um
    k0 = 21
    for j, n in enumerate(sig):
        y = round(0.024 + 0.048 * (k0 + 2 * j), 3)
        assert y < H_ - 1.0, (n, y)
        pins.append(dict(name=n, layer="M4", x=0.019, y=y))
    return pins

def box(c):
    x, y = c["origin_um"]; dx, dy = c.get("track_offset_um", [0, 0]); w, h = c["outline_um"]
    return (x + dx, y + dy, x + dx + w, y + dy + h)

def inside(p, b, e=0.5): return b[0] + e < p[0] < b[2] - e and b[1] + e < p[1] < b[3] - e

G = 17.28; HC = int((HOP - G) // G)     # router raster and hop radius in cells (Manhattan, endpoint snap included)

def free_grid(TW, TH, boxes):
    nx, ny = int(TW // G), int(TH // G)
    X, Y = np.meshgrid((np.arange(nx) + 0.5) * G, (np.arange(ny) + 0.5) * G)      # [ny, nx]
    ok = np.ones(X.shape, bool)
    for x0, y0, x1, y1 in boxes:
        ok &= ~((X > x0 - 0.5) & (X < x1 + 0.5) & (Y > y0 - 0.5) & (Y < y1 + 0.5))
    return ok

def l1dt(seed):
    d = np.where(seed, 0, 10 ** 6).astype(np.int64)
    for j in range(1, d.shape[1]): d[:, j] = np.minimum(d[:, j], d[:, j - 1] + 1)
    for j in range(d.shape[1] - 2, -1, -1): d[:, j] = np.minimum(d[:, j], d[:, j + 1] + 1)
    for i in range(1, d.shape[0]): d[i] = np.minimum(d[i], d[i - 1] + 1)
    for i in range(d.shape[0] - 2, -1, -1): d[i] = np.minimum(d[i], d[i + 1] + 1)
    return d

def cell(p, ok): return (min(ok.shape[0] - 1, int(p[1] // G)), min(ok.shape[1] - 1, int(p[0] // G)))

def station(a, b, ok):
    """minimum-register chain a->b: regs only on free raster cells (outside every hard core), every hop <= HOP
    Manhattan; wires may cross cores on M6/M7 (cores are OBS M1-M5).  BFS levels by L1 distance transforms."""
    if abs(a[0] - b[0]) + abs(a[1] - b[1]) <= HOP: return [], abs(a[0] - b[0]) + abs(a[1] - b[1])
    ca, cb = cell(a, ok), cell(b, ok)
    seed = np.zeros(ok.shape, bool); seed[cb] = True
    levels = [ok & (l1dt(seed) <= HC)]
    while True:
        da = abs(np.indices(ok.shape)[0] - ca[0]) + abs(np.indices(ok.shape)[1] - ca[1])
        if (levels[-1] & (da <= HC)).any(): break
        nxt = ok & (l1dt(levels[-1]) <= HC)
        if (nxt == levels[-1]).all() or len(levels) > 60: raise SystemExit(f"no register chain {a}->{b}")
        levels.append(nxt)
    I = np.indices(ok.shape); cur = ca; regs = []
    for lv in reversed(levels):
        dc = abs(I[0] - cur[0]) + abs(I[1] - cur[1]); db = abs(I[0] - cb[0]) + abs(I[1] - cb[1])
        m = lv & (dc <= HC)
        j = np.unravel_index(int(np.argmin(np.where(m, db * 1000 + dc, 10 ** 12))), ok.shape)
        regs.append([round((j[1] + 0.5) * G, 3), round((j[0] + 0.5) * G, 3)]); cur = j
    pts = [list(a)] + regs + [list(b)]
    hops = [abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    assert max(hops) <= 405.0, hops
    return regs, sum(hops)

if dst.exists(): shutil.rmtree(dst)
shutil.copytree(src, dst, symlinks=True)
d = json.loads((dst / "die_plan.json").read_text())
(dst / PFILE).write_text(json.dumps(pin_table(), indent=0) + "\n")
report = dict(module=MOD, pins_file=PFILE, lot_um=[W_, H_], kin_bits=KIN_BITS, kout_bits=KOUT_BITS, types={})
import copy
D0 = copy.deepcopy(d)
for tn in ("q_hub_nw", "q_hub_ne"):
  forbid = []
  for attempt in range(8):
    d["partition_types"][tn] = copy.deepcopy(D0["partition_types"][tn])
    report["types"].pop(tn, None); report.pop("restation", None) if False else None
    report["restation_fail"] = [x for x in report.get("restation_fail", []) if x["type"] != tn]
    t = d["partition_types"][tn]; TW, TH = t["outline_um"]
    old = {c["inst"]: c for c in t["hard_cores"] if c["module"] == "hnx_idxn_keybuf"}
    assert sorted(old) == ["u_mu_keybuf_0__q0", "u_mu_keybuf_0__q1"], old.keys()
    t["hard_cores"] = [c for c in t["hard_cores"] if c["inst"] not in old]
    B = [box(c) for c in t["hard_cores"]]
    regs = [p for key in ("internal_stations", "ft_slots") for e in t.get(key, []) or [] for p in e.get("regs_um", []) or []]
    old_ist = [e for e in t["internal_stations"] if "u_mu_keybuf" in json.dumps(e)]
    t["internal_stations"] = [e for e in t["internal_stations"] if "u_mu_keybuf" not in json.dumps(e)]
    regs = [p for p in regs if not any(p == q for e in old_ist for q in e["regs_um"])]
    R = np.array(regs)
    tr = report["types"][tn] = []
    new_cores, new_ist, new_taps = [], [], []
    for seg in range(2):
        idx = next(c for c in t["hard_cores"] if c["inst"] == f"u_hb_idx__q_Q__q{seg}")
        ib = box(idx); tc = ((ib[0] + ib[2]) / 2, (ib[1] + ib[3]) / 2)
        okin = [e for e in old_ist if e["r9_segments"] == [seg, seg] and e["capture"].startswith("u_mu_keybuf")]
        okout = [e for e in old_ist if e["r9_segments"] == [seg, seg] and e["launch"].startswith("u_mu_keybuf")]
        a_kin = tuple(okin[0]["from_um"]); b_kout = tuple(okout[0]["to_um"])
        old_regs = (len(okin[0]["regs_um"]), len(okout[0]["regs_um"]))
        lo, hi = (0.0, SEGX) if seg == 0 else (SEGX, TW)
        X, Y = np.meshgrid(np.arange(math.ceil((lo + LAT) / LAT) * LAT, hi - W_ - LAT, LAT), np.arange(LAT, TH - H_ - LAT, LAT))
        X = X.ravel(); Y = Y.ravel(); ok = np.ones(len(X), bool)
        for x0, y0, x1, y1 in B:
            ok &= ~((X + W_ + HALO > x0) & (X - HALO < x1) & (Y + H_ + HALO > y0) & (Y - HALO < y1))
        for x0, y0, x1, y1 in forbid:
            ok &= ~((X + W_ > x0) & (X < x1) & (Y + H_ > y0) & (Y < y1))
        nreg = np.zeros(len(X))
        for px, py in R:
            nreg += ((X - 0.5 < px) & (px < X + W_ + 0.5) & (Y - 0.5 < py) & (py < Y + H_ + 0.5))
        cost = np.abs(X + W_ / 2 - tc[0]) + np.abs(Y + H_ / 2 - tc[1])
        for k in range(8):
            c2 = np.where(ok, cost + PEN * nreg, np.inf); j = int(np.argmin(c2))
            if not np.isfinite(c2[j]): raise SystemExit(f"{tn} seg {seg}: no lot for slice {k}")
            x, y = round(float(X[j]), 2), round(float(Y[j]), 2)
            ok &= ~((X + W_ + HALO > x) & (X - HALO < x + W_) & (Y + H_ + HALO > y) & (Y - HALO < y + H_))
            east = tc[0] > x + W_ / 2
            orient = "MY" if east else "R0"
            inst = f"u_mu_keybuf_0_s{k}__q{seg}"
            new_cores.append(dict(inst=inst, module=MOD, origin_um=[x, y], outline_um=[W_, H_], track_offset_um=[0.0, 0.0],
                                  orient=orient, pins_file=PFILE, obs_max="M5",
                                  note=f"HBM-MU-QUAD-6 keybuf slice {k} of segment {seg} (replaces 324^2 u_mu_keybuf_0__q{seg}); "
                                       f"5 SRAM 256x256 macros, lot_model.json; strap_lane_id = {k} (3-bit ID strap tied at the parent: "
                                       "port name not yet in parent_id_straps.ID_PORTS -> declared here only)"))
            B.append((x, y, x + W_, y + H_))
            face = (x + W_, y + H_ / 2) if east else (x, y + H_ / 2)
            cx = x + (W_ - CLK[0] if orient == "MY" else CLK[0])
            new_taps.append(dict(name=inst, kind="core", xy=[round(cx, 3), round(y + CLK[1], 3)], insertion_ps=250.0,
                                 insertion_ff_ps=202.5, budget_owner=MOD,
                                 note="HBM-MU-QUAD-6: keybuf slice centre clock entry (lot_model clock_entry_um), common latency"))
            tr.append(dict(seg=seg, slice=k, inst=inst, origin=[x, y], orient=orient, partner=idx["inst"],
                           dist_um=round(float(cost[j]), 1), face=face))
        # stations after all lots exist (so no reg lands in a slice)
        FG = free_grid(TW, TH, B)
        for s in [r for r in tr if r["seg"] == seg]:
            rk, Lk = station(a_kin, s["face"], FG); ro, Lo = station(s["face"], b_kout, FG)
            new_ist.append(dict(conn=f"u_hb_idx__q_Q.kin|{s['inst'][:-4]}", launch="u_hb_idx__q_Q.kin", capture=s["inst"][:-4],
                                bits=KIN_BITS, from_um=list(a_kin), to_um=[round(v, 3) for v in s["face"]], regs_um=rk,
                                r9_segments=[seg, seg], note=f" | HBM-MU-QUAD-6 keybuf slice link (L, {Lk:.1f} um, {len(rk)} st)"))
            new_ist.append(dict(conn=f"{s['inst'][:-4]}.kout|u_hb_idx__q_Q", launch=f"{s['inst'][:-4]}.kout", capture="u_hb_idx__q_Q",
                                bits=KOUT_BITS, from_um=[round(v, 3) for v in s["face"]], to_um=list(b_kout), regs_um=ro,
                                r9_segments=[seg, seg], note=f" | HBM-MU-QUAD-6 keybuf slice link (L, {Lo:.1f} um, {len(ro)} st)"))
            s.update(kin_regs=len(rk), kout_regs=len(ro), kin_len=round(Lk, 1), kout_len=round(Lo, 1),
                     old_kin_regs=old_regs[0], old_kout_regs=old_regs[1],
                     kin_cycle_delta=len(rk) - old_regs[0], kout_cycle_delta=len(ro) - old_regs[1])
    # re-station existing regs that now fall inside a new slice lot: move each to the nearest lot edge (2.16 um out),
    # never into another hard core; every hop to its neighbours (regs, from_um/to_um) stays <= its reach
    lots = [box(c) for c in new_cores]; allb = B
    moved = fails = 0
    for key in ("internal_stations", "ft_slots"):
        for e in t.get(key, []) or []:
            rr = e.get("regs_um") or []
            for i, p in enumerate(rr):
                lb = next((b for b in lots if inside(p, b, 0.0)), None)
                if lb is None: continue
                prev = rr[i - 1] if i > 0 else e.get("from_um")
                # next register (or the capture end) that stays outside every new lot, and the hop count to it
                h, nxt = 1, None
                for jj in range(i + 1, len(rr) + 1):
                    q = rr[jj] if jj < len(rr) else e.get("to_um")
                    if q is None: break
                    if jj == len(rr) or not any(inside(q, bb, 0.0) for bb in lots): nxt = q; h = jj - i; break
                ends = [(prev, 1)] if prev is not None else []
                if nxt is not None: ends.append((nxt, h))
                # free 4.32-grid point closest to the old site with every hop to its neighbours <= 400 um
                xs = np.arange(max(0, p[0] - 820), min(TW, p[0] + 820), 4.32); ys = np.arange(max(0, p[1] - 820), min(TH, p[1] + 820), 4.32)
                QX, QY = np.meshgrid(xs, ys); QX = QX.ravel(); QY = QY.ravel(); m = np.ones(len(QX), bool)
                for n, hh in ends: m &= (np.abs(QX - n[0]) + np.abs(QY - n[1])) <= 404.0 * hh
                for bb in allb: m &= ~((QX > bb[0] - 0.5) & (QX < bb[2] + 0.5) & (QY > bb[1] - 0.5) & (QY < bb[3] + 0.5))
                if not m.any():
                    fails += 1
                    report.setdefault("restation_fail", []).append(dict(type=tn, key=key, entry=e.get("conn", e.get("name")), reg=p)); forbid.append(lb)
                    continue
                dd = np.where(m, np.abs(QX - p[0]) + np.abs(QY - p[1]), np.inf); j = int(np.argmin(dd))
                cands = [[float(QX[j]), float(QY[j])]]
                rr[i] = [round(cands[0][0], 3), round(cands[0][1], 3)]; moved += 1
    report.setdefault("restation", {})[tn] = dict(moved=moved, hop_fail=fails)
    print(tn, "re-stationed", moved, "hop>405 fails", fails)
    if fails and attempt < 7:
        print(tn, "attempt", attempt, "forbid", len(forbid), "lots; retry")
        continue
    t["hard_cores"] += new_cores
    t["internal_stations"] += new_ist
    t["clock"]["taps"] = [tp for tp in t["clock"]["taps"] if "u_mu_keybuf" not in tp["name"]] + new_taps
    t["note"] = t.get("note", "") + " | HBM-MU-QUAD-6: keybuf = 8 x ot_hnx_idxn_keybuf_slice per segment (real 5-SRAM lots)"
    break
(dst / "die_plan.json").write_text(json.dumps(d, indent=1) + "\n")
report["sha256_die_plan"] = hashlib.sha256((dst / "die_plan.json").read_bytes()).hexdigest()
rep_path.write_text(json.dumps(report, indent=1) + "\n")
for tn, rs in report["types"].items():
    for seg in range(2):
        r = [x for x in rs if x["seg"] == seg]
        print(tn, seg, "dist max/avg", max(x["dist_um"] for x in r), round(sum(x["dist_um"] for x in r) / 8, 1),
              "kin regs", [x["kin_regs"] for x in r], "old", r[0]["old_kin_regs"], "kout regs", [x["kout_regs"] for x in r], "old", r[0]["old_kout_regs"])
print("sha256", report["sha256_die_plan"])
