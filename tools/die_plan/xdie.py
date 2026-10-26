"""Cross-die G0C checks (PLAN-TOOL5, COORD DIE-PLAN VISUAL REVIEW 10-23 items (b)-(e)); called by check.run.

  cut_lines   (b) bits per cut at EVERY partition face line (vertical: distinct partition x0/x1, horizontal: y0/y1),
              not only the 250-um sweep. The sweep lines almost never fall on a face, and an abutted neighbour link
              crosses only its face line, so the sweep never counted abutted traffic: on S81 / KV / HBM most lane
              bits are 1-port neighbour lanes (S81 553 of 820 lanes, KV 1970 of 2416, HBM 3632 of 5483). A face line
              counts the abutted port bits on it plus the ft routes strictly crossing it. Capacity at a face line:
              the signal pin layers in the wire direction (M4..M7) x pin_track_max; the die layers M8/M9 carry no
              signals (ruling 9.3), so cut_avail adds nothing. ERROR when bits / tracks > cut_ratio_max.
  reach       (c) every register-to-register hop <= budgets.reach_margin (0.9) x the per-layer measured reach of the
              layers the hop routes on (reach.py, one table for all dies; die.reach_um is no longer used here).
  face_tracks (d) per partition face, sliding face_window_um window: pins / usable tracks (PG-band-free) of the
              ALLOWED signal pin layers of that face (type face_layers <= M7, else the partition pin layers
              M4..M7 in the face direction) <= pin_track_max (0.6); also per layer.
              One pin per layer of quantisation allowance.
  ft_budget   (e) per partition type: ft bits THROUGH the partition on its own signal layers (ruling 9.3: no
              over-the-top M8/M9 ft): E-W slot bits on M4/M6, N-S slot bits on M5/M7, a turning slot on both, vs the
              usable tracks across the type x type.ft_budget[L] (default the type's ft_track_frac, 0.25).
All four are G0C checks: ERROR under check.py --completeness, WARN '[G0C]' in plain G0.
"""
import bisect
import math
from collections import defaultdict

import numpy as np

import reach as RT
import schema as S
from schema import DIE_PART, OPP

EPS = 1e-6
PERIOD = 8.64          # die lattice: every pin-layer pitch and every PG band pitch divides it


# ----------------------------------------------------------------------------------------- track counting
class Tracks:
    """usable (PG-band-free) track counts of one layer over [lo, hi], O(log n) via the 8.64-um periodic pattern."""

    def __init__(self, L, ln):
        p, off = L["pitch_um"], L["offset_um"] % L["pitch_um"]
        self.p, self.off = p, off
        n = int(round(PERIOD / p))
        self.periodic = abs(n * p - PERIOD) < 1e-6
        self.L, self.ln = L, ln
        if self.periodic:
            self.pat = [off + k * p for k in range(n) if not S.pg_blocked(ln, off + k * p)]
            self.n = len(self.pat)

    def _upto(self, x):           # usable tracks with coordinate < x (x >= 0)
        q, r = divmod(x, PERIOD)
        return int(q) * self.n + bisect.bisect_left(self.pat, r)

    def count(self, lo, hi):
        if not self.periodic or lo < 0:
            return S.usable_tracks(self.L, self.ln, lo, hi)
        return self._upto(hi + 1e-9) - self._upto(lo - 1e-9)


def _tracks(P):
    return {ln: Tracks(L, ln) for ln, L in P.layers.items()}


def pin_layers(P, wire_dir):
    smax = min(int(P.layer_budget["partition_signal_max"][1:]), int(S.SIGNAL_LAYER_MAX[1:]))
    return [ln for ln, L in P.layers.items() if L["dir"] == wire_dir and 4 <= int(ln[1:]) <= smax]


# ------------------------------------------------------------------------------------------------- (b)
def check_cut_lines(P, R, geo, max_msgs=20):
    B = P.budgets
    lim = B["cut_ratio_max"]
    # ruling 9.3: the die layers carry no signals, so they add no face-line capacity (cut_avail ignored)
    # ft / die route segments
    sx0, sy0, sx1, sy1, sw = [], [], [], [], []
    for lid, (pts, _, _) in geo.items():
        w = P.ports[P.lanes[lid]["ports"][0]]["width"]
        for p, q in zip(pts, pts[1:]):
            sx0.append(p[0]); sy0.append(p[1]); sx1.append(q[0]); sy1.append(q[1]); sw.append(w)
    sx0, sy0, sx1, sy1, sw = map(np.asarray, (sx0, sy0, sx1, sy1, sw))
    if sw.size == 0:
        sx0 = sy0 = sx1 = sy1 = sw = np.zeros(0)
    # abutted port bits per face line
    on_line = {"vertical": defaultdict(int), "horizontal": defaultdict(int)}
    for pid, pr in P.ports.items():
        if DIE_PART in (pr["src"]["part"], pr["dst"]["part"]) or P.channel_of(pid):
            continue
        x0, y0, x1, y1 = P.rect(pr["src"]["part"])
        f = pr["face"]
        c = {"E": x1, "W": x0, "N": y1, "S": y0}[f]
        on_line["vertical" if f in "EW" else "horizontal"][round(c, 3)] += S.port_pins_count(pr)
    out = dict(vertical=[], horizontal=[])
    nerr = 0
    worst = (0.0, None)
    tot_abut = 0
    for orient, D, along in (("vertical", P.W, P.H), ("horizontal", P.H, P.W)):
        wd = "H" if orient == "vertical" else "V"
        pden = sum(B["pin_track_max"] / P.layers[n]["pitch_um"] for n in pin_layers(P, wd))
        cap = along * pden
        lines = sorted({round(c, 3) for n in P.parts for c in ((P.rect(n)[0], P.rect(n)[2]) if orient == "vertical"
                                                                 else (P.rect(n)[1], P.rect(n)[3]))
                        if EPS < c < D - EPS})
        a0, a1 = (sx0, sx1) if orient == "vertical" else (sy0, sy1)
        lo, hi = np.minimum(a0, a1), np.maximum(a0, a1)
        for c in lines:
            rb = int(sw[(lo < c - EPS) & (hi > c + EPS)].sum()) if sw.size else 0
            ab = on_line[orient].get(c, 0)
            tot_abut += ab
            bits = rb + ab
            ratio = bits / cap if cap else 0.0
            out[orient].append(dict(at_um=c, bits=bits, abutted_bits=ab, route_bits=rb, tracks=round(cap),
                                    ratio=round(ratio, 4)))
            if ratio > worst[0]:
                worst = (ratio, f"{orient}@{c:g}")
            if ratio > lim + EPS:
                nerr += 1
                if nerr <= max_msgs:
                    R.err("cut_lines", f"{orient} face line {c:g}: {bits} bits ({ab} abutted + {rb} ft/die routes) on "
                          f"{cap:.0f} tracks = {ratio:.2f} > {lim}")
    if nerr > max_msgs:
        R.err("cut_lines", f"... {nerr - max_msgs} more face lines over {lim}")
    for o in ("vertical", "horizontal"):
        top = sorted(out[o], key=lambda r: -r["bits"])[:5]
        out[f"top_{o}"] = top
    out["worst"] = dict(ratio=round(worst[0], 4), at=worst[1])
    out["lines"] = len(out["vertical"]) + len(out["horizontal"])
    out["model"] = "face line: abutted port bits + ft/die routes strictly crossing; tracks = partition pin layers x " \
                   "pin_track_max (M4-M7; M8/M9 carry no signals, ruling 9.3)"
    return out


# ------------------------------------------------------------------------------------------------- (c)
def _part_at(P, pt):
    for n in P.parts:
        x0, y0, x1, y1 = P.rect(n)
        if x0 - EPS <= pt[0] <= x1 + EPS and y0 - EPS <= pt[1] <= y1 + EPS:
            return n
    return None


def check_reach(P, R, geo, max_msgs=200):
    margin = float(P.budgets.get("reach_margin", RT.MARGIN))
    bad, worst, by_cls = 0, [], defaultdict(int)
    loc = margin * min(RT.layer_reach(n) for n in RT.PARTITION_LAYERS)
    over_local = 0
    for lid, (pts, regs, xs) in geo.items():
        ln = P.lanes[lid]
        r, ls = RT.hop_reach(P, ln)
        lim = margin * r
        hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(regs, regs[1:])]
        if not hops:
            continue
        h = max(hops)
        worst.append((h / r, lid, h, r))
        over_local += h > loc + EPS
        if h > lim + EPS:
            bad += 1
            i = hops.index(h)
            mid = ((regs[i][0] + regs[i + 1][0]) / 2, (regs[i][1] + regs[i + 1][1]) / 2)
            pn = _part_at(P, mid)
            by_cls["+".join(ls)] += 1
            if bad <= max_msgs:
                R.err("reach", f"lane {ln['id']}: hop {i} is {h:.0f} um > {margin:g} x reach {r:.0f} ({'/'.join(ls)}, "
                      f"reach.py) = {lim:.0f}; need {math.ceil(h / lim)} hop(s) there" + (f" (in {pn})" if pn else ""),
                      lane=lid, type=P.parts[pn]["type"] if pn else None, part=pn)
    if bad > max_msgs:
        R.err("reach", f"... {bad - max_msgs} more lanes with a hop over {margin:g} x reach")
    worst.sort(reverse=True)
    dr = float(P.die.get("reach_um", 0) or 0)
    tab = min(RT.hop_reach(P)[0], 1e9)
    if dr and abs(dr - tab) > 0.05 * tab:
        R.warn("reach", f"die.reach_um {dr:g} is not the measured layer reach {tab:.0f} ({'/'.join(RT.hop_layers(P))}, "
               "reach.py); G0C judges hops on the table")
    return dict(margin=margin, table={k: v["reach_um"] for k, v in RT.TABLE.items()}, source=RT.SOURCE,
                die_reach_um=dr or None, layers=RT.hop_layers(P), over=bad, by_layers=dict(by_cls),
                over_if_partition_layers=dict(limit_um=round(loc, 1), lanes=over_local),
                worst=[dict(lane=l, hop_um=round(h, 1), reach_um=round(r, 1), frac=round(f, 3))
                       for f, l, h, r in worst[:10]])


# ------------------------------------------------------------------------------------------------- (d)
def face_allowed_layers(P, part, df):
    wd = "H" if df in "EW" else "V"
    fl = P.ptype(part).get("face_layers", {}).get(P.type_face(part, df))
    base = pin_layers(P, wd)
    if fl:      # an M8/M9 face layer adds no signal track (ruling 9.3; check.py m89_signals ERRORs it)
        return sorted(set(base) | {ln for ln in fl if ln in P.layers and P.layers[ln]["dir"] == wd
                                   and ln not in S.RESERVED_DIE_LAYERS})
    return base


def check_face_tracks(P, R, face_pins, max_msgs=100):
    B = P.budgets
    win, lim = B["face_window_um"], B["pin_track_max"]
    T = _tracks(P)
    worst, nerr = [], 0
    seen_types = set()
    for (part, df), pins in face_pins.items():
        key = (P.parts[part]["type"], P.type_face(part, df))
        allowed = face_allowed_layers(P, part, df)
        cs = sorted(c for c, _, _ in pins)
        byl = defaultdict(list)
        for c, ln, _ in pins:
            byl[ln].append(c)
        for v in byl.values():
            v.sort()
        best = (0.0, None, None)
        for i, c in enumerate(cs):
            j = bisect.bisect_right(cs, c + win - EPS)
            tr = sum(T[ln].count(c, c + win) for ln in allowed)
            r = (j - i - len(allowed)) / tr if tr else math.inf
            if r > best[0]:
                best = (r, c, "all")
        for ln, v in byl.items():
            if ln not in T:
                continue
            for i, c in enumerate(v):
                j = bisect.bisect_right(v, c + win - EPS)
                tr = T[ln].count(c, c + win)
                r = (j - i - 1) / tr if tr else math.inf
                if r > best[0]:
                    best = (r, c, ln)
        worst.append((best[0], part, df, best[2], allowed))
        if best[0] > lim + EPS and key not in seen_types:
            seen_types.add(key)
            nerr += 1
            if nerr <= max_msgs:
                R.err("face_tracks", f"{part}.{df} (type {key[0]} face {key[1]}): {best[0]:.2f} pins per usable track "
                      f"({best[2]}) in the {win:g}-um window at {best[1]:.2f} > {lim} on allowed layers "
                      f"{'/'.join(allowed)}", type=key[0], part=part)
        for ln in byl:
            if ln not in allowed:
                pass                         # layer legality is the plain G0 'layers' check
    if nerr > max_msgs:
        R.err("face_tracks", f"... {nerr - max_msgs} more type faces over {lim}")
    worst.sort(key=lambda x: -x[0])
    return dict(over=nerr, worst=[dict(part=p, face=f, ratio=round(r, 3), on=l, allowed=a)
                                  for r, p, f, l, a in worst[:10]])


# ------------------------------------------------------------------------------------------------- (e)
def check_ft_budget(P, R, face_pins):
    """ruling 9.3: ft bits cross a partition on its own signal layers (H slots on the H layers M4/M6, V slots on M5/M7)
    inside the ft share of the tracks (type.ft_budget[L], default type.ft_track_frac / 0.25).  face_pins is unused
    (kept for the call signature): signal pins on M8/M9 are check.py m89_signals ERRORs."""
    T = _tracks(P)
    hl, vl = pin_layers(P, "H"), pin_layers(P, "V")
    rows, nerr = [], 0
    for tn, t in P.types.items():
        w, h = t["outline_um"]
        hb = vb = 0
        for s in t.get("ft_slots", []):
            fs = {s["in_face"], s["out_face"]}
            if fs & {"E", "W"}:
                hb += s["width"]
            if fs & {"N", "S"}:
                vb += s["width"]
        fb = t.get("ft_budget", {})
        frac = t.get("ft_track_frac", 0.25)
        rec = dict(type=tn, instances=sum(1 for p in P.parts.values() if p["type"] == tn))
        for dirn, layers, bits, ext in (("H", hl, hb, h), ("V", vl, vb, w)):
            res = sum(T[n].count(0.0, ext) * fb.get(n, frac) for n in layers)
            rec[dirn] = dict(layers=layers, ft_bits=bits, reserved=int(res),
                             ratio=round(bits / res, 4) if res else (math.inf if bits else 0.0))
            if bits > res + EPS:
                nerr += 1
                R.err("ft_budget", f"type {tn}: {bits} ft bits through it on {'/'.join(layers)} > {int(res)} ft tracks "
                      f"({ext:.0f} um x {'/'.join(f'{fb.get(n, frac):g}' for n in layers)} of the usable tracks; "
                      "ruling 9.3: no over-the-top M8/M9 ft)", type=tn)
        rows.append(rec)
    rows.sort(key=lambda r: -max(r["H"]["ratio"], r["V"]["ratio"]))
    return dict(over=nerr, worst=rows[:10], total_types=len(rows))
