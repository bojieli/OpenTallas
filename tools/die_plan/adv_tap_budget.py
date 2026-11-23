#!/usr/bin/env python3
"""adv_tap_budget.py -- PRECHECK-R2 static estimator ADV-TAP-BUDGET (advisory, never a gate).

Per clock tap of every placed soft type: estimate the post-balance CTS insertion at the tap's pin registers (face /
boundary registers, ft slot stations, internal_stations, explicit bit sites) from the Manhattan reach of the tap, and
flag the taps whose estimate is over the type's insertion target (clock.insertion_ps, the S81 col / leaf 450 ps; else
the die clock.insertion_ps, 250).

Model (calibrated 2026-11-22, PRECHECK-R2 TAP-BUDGET):
  natural latest-sink insertion (pre tap_balance, placement RC, OT_STB "max")
        = 40.8 + 0.6845 ps/um x dmax + 6.23 x log2(n)
    dmax = Manhattan distance tap -> farthest register on its nearest-tap cell, n = registers on the tap.
    Fit: 937 taps (>= 20 sinks) of 21 routed kits (S81 col / leaf / slice / serdes / dsdv / iqf / glue, QC sle / slw),
    registers from kit_scan placed_raw (3_place.odb), nearest kit tap (budget.json taps_snapped); R2 0.40, rms 69 ps.
    Distance alone: 90.6 + 0.724 x dmax (R2 0.39).
  post-balance pin-register arrival = max(target + 41, natural + 29)
    tap_balance raises every fast tap to ~target + 17 ps (median over 2,512 taps, p90 +42) and leaves a slow tap at its
    latest sink + 29 ps (median of 345 taps with natural max > target - 10, p10 -5, p90 +41), from 66 kits'
    4_1_cts.log OT_STB before / OT_TAP_INSERTION lines.  The pin-register mean the OT_POSTCTS_GATE TT line reads
    (postcts_gate_tt.json) sits at bound + 41 ps (median of 23 kits, p25 +28, p75 +51; 22 of 23 over the 20 ps tol:
    col_h10_r1 478, col_h9_r0_p2 485, t5 538 at 450) -- the balance floor, reported once in the summary.  A type
    line is written only when the DISTANCE term alone (natural + 29) is over target.
  So a tap (and every pin register on it) is estimated over target when natural + 29 > target, i.e. at n = 1000
  when dmax > (target - 132) / 0.6845 = 465 um for 450 ps (172 um for 250 ps).

Static inputs (plan only): tap sites (explicit clock.taps / grid pitch centres + clock.added_taps / density table),
pin-register sites (bus windows on their face, ft in windows + regs_um / bit_sites_um stations, internal_stations
regs_um / bit_sites_um, clock.sink_sites_um) and the type's register inventory clock.sink_bins_file when present.  The
free area is NOT used as a logic proxy: on explicit-table types (taps only where sinks are) it flagged 95 / 395 S81 J7
types with 700-2,100 um empty-area reaches (false positives).
n = assigned plan sinks or bins weight, at least min(tap_max_sinks, 1000).  The die-wide balance floor (target + 17)
is reported once as a summary line, not per type: it is the col-family 478-513 ps class (pin-register mean on balanced
taps), while per-tap lines are the distance class.  Not modelled: the kit's cap / tap_pair_affinity re-split of the
real netlist (S81 kv_leaf t5: 60,394 registers over 38 taps at cap 1,500, as-built tap spans 700-1,116 um vs 270-610
um nearest-tap cells), which this check cannot see from the plan.
"""
import json
import math
import os
import sys
import time

CHECK = "ADV-TAP-BUDGET"
A_PS, B_PS_PER_UM, C_PS_PER_LOG2 = 40.8, 0.6845, 6.23
SLOW_OVER_PS = 29.0       # post-balance arrival over the natural latest sink (slow taps)
FLOOR_OVER_PS = 41.0      # measured pin-register mean over the bound on balanced kits (median of 23; p25 28, p75 51)
FLOOR_STATS = "median +41 ps (p25 +28, p75 +51), 22 of 23 kits over the 20 ps tol"
N_MIN = 1000
MAX_LINES = 20
DEADLINE_S = 50.0
PIN_KINDS = ("face", "ft", "ist", "site")


def est_natural(dmax, n):
    return A_PS + B_PS_PER_UM * dmax + C_PS_PER_LOG2 * math.log2(max(2.0, n))


def est_arrival(dmax, n, target):
    return max(target + FLOOR_OVER_PS, est_natural(dmax, n) + SLOW_OVER_PS)   # noqa: E501 (pin-register mean)


def reach_limit(target, n=N_MIN):
    return (target - SLOW_OVER_PS - A_PS - C_PS_PER_LOG2 * math.log2(max(2.0, n))) / B_PS_PER_UM


def _f(v):
    return float(v)


def _face_points(face, lo, hi, w, h, k):
    """k points along a face window (type frame)"""
    pts = []
    for i in range(k):
        s = lo + (hi - lo) * (i + 0.5) / k if k > 1 else (lo + hi) / 2
        pts.append({"N": (s, h), "S": (s, 0.0), "E": (w, s), "W": (0.0, s)}.get(face, (s, 0.0)))
    return pts


def pin_sinks(t, samples=12):
    """[(x, y, weight, kind, label)] pin registers of a type (plan geometry, bits sampled along their windows)"""
    w, h = map(_f, t["outline_um"])
    out = []
    for b in t.get("buses") or []:
        win, face, wd = b.get("window_um"), b.get("face"), int(b.get("width", 1) or 1)
        if not win or not face:
            continue
        k = max(1, min(samples, wd))
        for x, y in _face_points(face, _f(win[0]), _f(win[1]), w, h, k):
            out.append((x, y, wd / k, "face", b.get("name", "?")))
    for s in t.get("ft_slots") or []:
        wd, name = int(s.get("width", 1) or 1), s.get("name", "?")
        win = s.get("in_window_um")
        if win and s.get("in_face"):
            k = max(1, min(samples, wd))
            for x, y in _face_points(s["in_face"], _f(win[0]), _f(win[1]), w, h, k):
                out.append((x, y, wd / k, "ft", name + ".s0"))
        st = int(s.get("stations", 1) or 1)
        bits = s.get("bit_sites_um")
        if bits:
            cw, ch = (s.get("bit_site_cell_um") or [0.0, 0.0])[:2]
            for j, row in enumerate(bits, 1):
                k = max(1, min(samples, len(row)))
                for i in range(k):
                    bx, by = row[int(i * (len(row) - 1) / max(1, k - 1))] if len(row) > 1 else row[0]
                    out.append((_f(bx) + cw / 2, _f(by) + ch / 2, len(row) / k, "ft", f"{name}.s{j}"))
        else:
            regs = s.get("regs_um") or []
            for j in range(1, st):
                if len(regs) >= st:
                    out.append((_f(regs[j][0]), _f(regs[j][1]), wd, "ft", f"{name}.s{j}"))
    for e in t.get("internal_stations") or []:
        nb = int(e.get("bits", 1) or 1)
        lab = (e.get("conn") or "?")[:48]
        if e.get("bit_sites_um"):
            cw, ch = (e.get("bit_site_cell_um") or [0.0, 0.0])[:2]
            for bank in e["bit_sites_um"]:
                k = max(1, min(samples, len(bank)))
                for i in range(k):
                    bx, by = bank[int(i * (len(bank) - 1) / max(1, k - 1))] if len(bank) > 1 else bank[0]
                    out.append((_f(bx) + cw / 2, _f(by) + ch / 2, len(bank) / k, "ist", lab))
            continue
        if e.get("face_bit_sites_um"):
            continue
        for r in e.get("regs_um") or []:
            out.append((_f(r[0]), _f(r[1]), nb, "ist", lab))
    for r in (t.get("clock") or {}).get("sink_sites_um") or []:
        out.append((_f(r[0]), _f(r[1]), _f(r[2]) if len(r) > 2 else 1.0, "site", "clock.sink_sites_um"))
    return out


def tap_sites(P, raw, tn, t, S=None):
    """[(name, x, y)] non-core tap sites; fast plan read (no legaliser), schema grid when available"""
    ck = t.get("clock") or {}
    mode = ck.get("tap_mode", "grid")
    if ck.get("child_root_taps") is not None:
        return None, "child_root_taps (no parent registers)"
    if t.get("hard"):
        return None, "hard type (registers inside its hard cores)"
    tab = [p for p in ck.get("taps") or [] if not p.get("kind") and p.get("xy")]   # kind core / glue: not type taps
    added = [p for p in ck.get("added_taps") or [] if p.get("xy")]
    if mode == "explicit":
        return [(p["name"], _f(p["xy"][0]), _f(p["xy"][1])) for p in tab], mode
    if mode == "density":
        if P is not None:
            try:
                import taps as TP
                import contextlib
                import io
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    base = TP._density_base(P, tn)
                return [(n, x, y) for n, x, y, *_ in base] + [(p["name"], _f(p["xy"][0]), _f(p["xy"][1])) for p in added], mode
            except Exception as e:  # noqa: BLE001
                err = type(e).__name__
        else:
            err = "no schema"
        if tab:
            return [(p["name"], _f(p["xy"][0]), _f(p["xy"][1])) for p in tab + added], mode + " (clock.taps table)"
        return None, f"density taps unavailable ({err})"
    w, h = map(_f, t["outline_um"])
    pitch = None
    if S is not None and P is not None:
        try:
            pitch = float(S.tap_pitch(P, tn))
        except Exception:  # noqa: BLE001
            pitch = None
    if pitch is None:
        pitch = float(ck.get("tap_pitch_um", (raw.get("budgets") or {}).get("tap_pitch_um", 400.0)))
    nx, ny = max(1, math.ceil(w / pitch - 1e-9)), max(1, math.ceil(h / pitch - 1e-9))
    if nx == 1 and ny == 1:
        x, y = ck.get("tap_um", [w / 2, h / 2])
        grid = [("clk", _f(x), _f(y))]
    else:
        grid = [("clk" if j * nx + i == 0 else f"clk_t{j * nx + i}", (i + 0.5) * w / nx, (j + 0.5) * h / ny)
                for j in range(ny) for i in range(nx)]
    return grid + [(p["name"], _f(p["xy"][0]), _f(p["xy"][1])) for p in added], mode


class _Near:
    """nearest tap (Manhattan) with a coarse bucket grid"""

    def __init__(self, sites, w, h):
        self.sites = sites
        self.cell = max(50.0, math.sqrt(max(1.0, w * h) / max(1, len(sites))))
        self.b = {}
        for k, (_, x, y) in enumerate(sites):
            self.b.setdefault((int(x // self.cell), int(y // self.cell)), []).append(k)

    def __call__(self, x, y):
        cx, cy = int(x // self.cell), int(y // self.cell)
        best, r = None, 0
        while True:
            for i in range(cx - r, cx + r + 1):
                for j in range(cy - r, cy + r + 1):
                    if max(abs(i - cx), abs(j - cy)) != r:
                        continue
                    for k in self.b.get((i, j), ()):
                        _, a, b = self.sites[k]
                        d = abs(a - x) + abs(b - y)
                        if best is None or d < best[0]:
                            best = (d, k)
            # any tap in ring r+1 is at least r * cell away (Chebyshev ring -> Manhattan >= r*cell)
            if best is not None and best[0] <= r * self.cell:
                return best
            r += 1
            if r > 400:
                return best


def _bins(P, raw, plan_path, t, tree):
    ck = t.get("clock") or {}
    f = ck.get("sink_bins_file")
    if not f:
        return None
    try:
        import taps as TP
        p = TP.input_path(f, os.path.dirname(os.path.abspath(plan_path)), tree)
    except Exception:  # noqa: BLE001
        p = f if os.path.isabs(f) else os.path.join(tree or os.path.dirname(os.path.abspath(plan_path)), f)
    try:
        with open(p) as fh:
            return [(_f(r[0]), _f(r[1]), _f(r[2]) if len(r) > 2 else 1.0) for r in json.load(fh)["bins"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def type_estimate(P, raw, plan_path, tn, t, die_target, S=None, tree=None):
    """-> dict or None (skipped): per tap dmax / n / est / pin cluster, plus the type target"""
    ck = t.get("clock") or {}
    target = _f(ck["insertion_ps"]) if ck.get("insertion_ps") is not None else die_target
    sites, mode = tap_sites(P, raw, tn, t, S)
    if not sites:
        return None
    w, h = map(_f, t["outline_um"])
    near = _Near(sites, w, h)
    cap = int(ck.get("tap_max_sinks", 1500) or 1500)
    nt = len(sites)
    dmax = [0.0] * nt
    src = [""] * nt
    load = [0.0] * nt
    pins = {}
    for x, y, wt, kind, lab in pin_sinks(t):
        d, k = near(x, y)
        load[k] += wt
        if d > dmax[k]:
            dmax[k], src[k] = d, f"{kind} {lab}"
        c = pins.setdefault((k, kind, lab), [0.0, 0.0, 0.0, 0.0])
        c[0] += wt
        c[1] = max(c[1], d)
        c[2] += wt * x
        c[3] += wt * y
    bins = _bins(P, raw, plan_path, t, tree)
    logic = "sink_bins" if bins else "pins only"
    for x, y, wt in bins or ():
        d, k = near(x, y)
        load[k] += wt
        if d > dmax[k]:
            dmax[k], src[k] = d, "sink_bins register"
    taps = []
    nmin = min(cap, N_MIN)
    for k, (name, x, y) in enumerate(sites):
        n = max(load[k], nmin)
        nat = est_natural(dmax[k], n)
        taps.append(dict(name=name, xy=(round(x, 1), round(y, 1)), dmax=round(dmax[k], 1), n=round(load[k]),
                         src=src[k], est=round(max(target + FLOOR_OVER_PS, nat + SLOW_OVER_PS), 1),
                         slow=nat + SLOW_OVER_PS > target))
    clusters = []
    for (k, kind, lab), (wt, d, sx, sy) in pins.items():
        clusters.append(dict(tap=k, kind=kind, label=lab, regs=round(wt), dmax=round(d, 1),
                             xy=(round(sx / wt, 1), round(sy / wt, 1)) if wt else None))
    return dict(type=tn, mode=mode, target=target, taps=taps, clusters=clusters, logic=logic, cap=cap)


def _placed_types(raw):
    parts = raw.get("partitions") or []
    s = {p.get("type") for p in parts if isinstance(p, dict) and p.get("type")}
    return s or set((raw.get("partition_types") or {}).keys())


TAP_TARGET_FLOOR_PS = float(os.environ.get("OT_ADV_TAP_TARGET_PS", "450"))


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:160]}"]


def _findings(raw, plan_path, tree=None, max_lines=MAX_LINES, deadline_s=DEADLINE_S, **kw):
    t0 = time.time()
    pt = raw.get("partition_types") or {}
    if not pt:
        return [f"WARN {CHECK} not checked: plan has no partition_types"]
    die_target = _f((raw.get("clock") or {}).get("insertion_ps", 250.0))
    P = S = None
    for d in ([os.path.join(tree, "tools", "die_plan")] if tree else []) + [os.path.dirname(os.path.abspath(__file__))]:
        if os.path.isfile(os.path.join(d, "schema.py")) and d not in sys.path:
            sys.path.insert(0, d)
    try:
        import schema as S  # noqa: N812
        P = S.Plan(raw, plan_path)
    except Exception:  # noqa: BLE001
        P = S = None
    placed = sorted(t for t in _placed_types(raw) if t in pt)
    flagged, skipped, checked, late = [], 0, 0, 0
    pin_taps_total = pin_taps_floor = 0
    for tn in placed:
        if time.time() - t0 > deadline_s:
            late += 1
            continue
        t = pt[tn]
        if not t.get("outline_um"):
            skipped += 1
            continue
        try:
            r = type_estimate(P, raw, plan_path, tn, t, die_target, S, tree)
        except Exception:  # noqa: BLE001
            r = None
        if r is None:
            skipped += 1
            continue
        checked += 1
        pin_tap_ids = {c["tap"] for c in r["clusters"]}
        pin_taps_total += len(pin_tap_ids)
        r["target"] = max(r["target"], TAP_TARGET_FLOOR_PS)      # PRECHECK-R2 brief: judged at the 450 ps tap target (250-ps types were noise)
        slow = [(k, tp) for k, tp in enumerate(r["taps"]) if tp["slow"] and tp["est"] > r["target"] and k in pin_tap_ids]
        pin_taps_floor += len(pin_tap_ids) - len(slow)
        if not slow:
            continue
        k, worst = max(slow, key=lambda kv: kv[1]["est"])
        cl = [c for c in r["clusters"] if c["tap"] == k]
        far = max(cl, key=lambda c: c["dmax"])
        regs_on_slow = sum(c["regs"] for c in r["clusters"] if c["tap"] in {i for i, _ in slow})
        lim = reach_limit(r["target"], max(worst["n"], min(r["cap"], N_MIN)))
        flagged.append((worst["est"] - r["target"], (
            f"WARN {CHECK} {tn}: tap {worst['name']} at {list(worst['xy'])} est pin-register insertion "
            f"{worst['est']:.0f} ps > target {r['target']:.0f} ps (reach {worst['dmax']:.0f} um to {worst['src']}, "
            f"est load {max(worst['n'], min(r['cap'], N_MIN))}; {len(slow)} slow tap(s) carry {regs_on_slow} pin regs; "
            f"farthest pin cluster {far['kind']} {far['label']} {far['regs']} regs at {far['dmax']:.0f} um, centroid "
            f"{list(far['xy']) if far['xy'] else '?'}); fix: add clock.added_taps so every register is within "
            f"{max(0.0, lim):.0f} um Manhattan of a tap (sinks: {r['logic']}, mode {r['mode']})")))
    flagged.sort(key=lambda f: -f[0])
    out = [line for _, line in flagged[:max_lines]]
    floor = (f"; balance floor (all {checked} types, whatever the reach): pin-register mean est target + "
             f"{FLOOR_OVER_PS:.0f} ps, measured {FLOOR_STATS} (col 478-513 / t5 538 at 450 class); lever = "
             f"tap_balance target ~45 ps under the gate bound, or bound = target + 45") if checked else ""
    tail = f"; {late} types not checked (deadline {deadline_s:.0f} s)" if late else ""
    out.append(f"WARN {CHECK} summary: {len(flagged)} of {checked} types have pin registers on taps est over their "
               f"insertion target ({skipped} skipped: hard / child-root / no taps){tail}{floor}; model 40.8 + 0.6845 ps/um x "
               f"reach + 6.23 x log2(load) + 29 (937 kit taps, R2 0.40, rms 69 ps); {time.time() - t0:.1f} s")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--tree", default=None)
    ap.add_argument("--max-lines", type=int, default=MAX_LINES)
    a = ap.parse_args()
    t0 = time.time()
    with open(a.plan) as fh:
        raw_ = json.load(fh)
    t1 = time.time()
    for line in findings(raw_, a.plan, a.tree, max_lines=a.max_lines):
        print(line)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.1f} s", file=sys.stderr)
