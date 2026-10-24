"""Cross-die G0C checks (PLAN-TOOL5, COORD DIE-PLAN VISUAL REVIEW 10-23 items (b)-(e)); called by check.run.

  cut_lines   (b) bits per cut at EVERY partition face line (vertical: distinct partition x0/x1, horizontal: y0/y1),
              not only the 250-um sweep. The sweep lines almost never fall on a face, and an abutted neighbour link
              crosses only its face line, so the sweep never counted abutted traffic: on S81 / KV / HBM most lane
              bits are 1-port neighbour lanes (S81 553 of 820 lanes, KV 1970 of 2416, HBM 3632 of 5483). A face line
              counts the abutted port bits on it plus the ft routes strictly crossing it. Capacity at a face line:
              the partition pin layers in the wire direction (<= partition_signal_max) x pin_track_max plus the die
              layers x cut_avail. ERROR when bits / tracks > cut_ratio_max.
  reach       (c) every register-to-register hop <= budgets.reach_margin (0.9) x the per-layer measured reach of the
              layers the hop routes on (reach.py, one table for all dies; die.reach_um is no longer used here).
  face_tracks (d) per partition face, sliding face_window_um window: pins / usable tracks (PG-band-free) of the
              ALLOWED pin layers of that face (type face_layers incl. the M8 / M9 third layer, else the partition
              pin layers M4..partition_signal_max in the face direction) <= pin_track_max (0.6); also per layer.
              One pin per layer of quantisation allowance.
  ft_budget   (e) per partition type: over-the-top die ft bits (ft slots: E-W bits on M8, N-S bits on M9, a turning
              slot on both) + the type's non-ft M8 / M9 face pins vs its reserved M8 / M9 tracks (usable tracks
              across the type x type.ft_budget[L], default die.layer_budget.cut_avail[L]).
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
    smax = int(P.layer_budget["partition_signal_max"][1:])
    return [ln for ln, L in P.layers.items() if L["dir"] == wire_dir and 4 <= int(ln[1:]) <= smax]


# ------------------------------------------------------------------------------------------------- (b)
def check_cut_lines(P, R, geo, max_msgs=20):
    B = P.budgets
    lim = B["cut_ratio_max"]
    avail = P.layer_budget.get("cut_avail", {})
    die_l = [n for n in P.layer_budget["die_layers"] if n in P.layers]
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
        dden = sum(avail.get(n, 0.0) / P.layers[n]["pitch_um"] for n in die_l if P.layers[n]["dir"] == wd)
        cap = along * (pden + dden)
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
                   "pin_track_max + die layers x cut_avail"
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
    if fl:
        return sorted(set(base) | {ln for ln in fl if ln in P.layers and P.layers[ln]["dir"] == wd})
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
    avail = P.layer_budget.get("cut_avail", {})
    die_l = [n for n in P.layer_budget["die_layers"] if n in P.layers]
    hl = [n for n in die_l if P.layers[n]["dir"] == "H"]
    vl = [n for n in die_l if P.layers[n]["dir"] == "V"]
    T = _tracks(P)
    # non-ft pins on die layers, per type (one instance)
    pins_die = defaultdict(lambda: defaultdict(int))
    inst_of = {}
    for (part, df), pins in face_pins.items():
        tn = P.parts[part]["type"]
        if inst_of.setdefault(tn, part) != part:
            continue
        for c, ln, pid in pins:
            if ln not in die_l:
                continue
            pr = P.ports[pid]
            end = pr["src"] if pr["src"]["part"] == part else pr["dst"]
            if P.buses(part).get(end["bus"], {}).get("slot"):
                continue
            pins_die[tn][ln] += 1
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
        rec = dict(type=tn, instances=sum(1 for p in P.parts.values() if p["type"] == tn))
        for dirn, layers, bits, ext in (("H", hl, hb, h), ("V", vl, vb, w)):
            used = bits + sum(pins_die[tn].get(n, 0) for n in layers)
            res = sum(T[n].count(0.0, ext) * fb.get(n, avail.get(n, 0.0)) for n in layers)
            rec[dirn] = dict(layers=layers, ft_bits=bits, die_layer_pins=used - bits, used=used,
                             reserved=int(res), ratio=round(used / res, 4) if res else (math.inf if used else 0.0))
            if used > res + EPS:
                nerr += 1
                R.err("ft_budget", f"type {tn}: {used} over-the-top {'/'.join(layers)} tracks needed ({bits} ft bits + "
                      f"{used - bits} {'/'.join(layers)} face pins) > {int(res)} reserved ({ext:.0f} um x "
                      f"{'/'.join(f'{fb.get(n, avail.get(n, 0.0)):g}' for n in layers)} of the usable tracks)", type=tn)
        rows.append(rec)
    rows.sort(key=lambda r: -max(r["H"]["ratio"], r["V"]["ratio"]))
    return dict(over=nerr, worst=rows[:10], total_types=len(rows))
