"""DIE-S81-85 HCHAN 11-10 (form B of the S81 "M6-dominant GRT" class, DO_NOT_COUNT until a pilot signs off).

Every S81 hard-core LEF obstructs M1-M5 (some M1-M4, one col_h9 master M1-M6) and tiles route M2-M7 with M7 vertical
(METHODOLOGY 12.a: no M8/M9 in a tile), so over a macro the only horizontal layer is M6.  This rule sizes, from the
netlist's crossing demand, a macro-free horizontal channel wherever the horizontal tracks over a macro stack cannot
carry the nets that must cross it, and shifts macros in Y (outline and X fixed) to open it.

Model (per vertical cut x = c, every --cut-step um, Y bins of --bin um):
  * demand: every net whose pin X range spans c needs one horizontal track somewhere in its pin Y range (HPWL box,
    widened by --detour um each side); an end in a macro-free street at c may use the whole street (std-cell area,
    nothing to cross), so windows are bounded by macro or core edges; macro pins move with their macro.
  * supply per Y bin: sum over horizontal layers of (1 - adj) / pitch x free height (M2 0.5, M4 0.25, M6 0.30:
    39.4 tracks/um); over a macro only the layers its LEF leaves open (M6: 10.9 nominal; --mac-tpu 5.26 = measured
    GRT capacity 3 per 0.57-um gcell on S81 t15/col_h9, M6 straps included; 0 for an M6-obstructing master).
  * a cut is routable iff for every Y window W the nets whose Y range lies inside W fit in supply(W) (Hall's
    condition for intervals onto capacitated points).  Up to 4 disjoint worst windows per cut are kept; windows
    overlapping in Y on adjacent cuts form a band; deficit = max over its cuts of demand(W) - supply(W) (tracks).
  * channel width w = deficit / 39.4 tracks per um (the street grows at free capacity), rounded up to --grid
    (0.864 um, the S81 core-origin grid); the loop re-evaluates and adds width where the deficit remains.
Realisation: y* = a macro edge (or core edge) in the band's window that no macro of the band's X range straddles;
the channel R = band X range x [y*, next macro edge + w] (or mirrored downward).  Only macros that intersect R move,
in Y by the least grid multiple that clears it, and push what they then overlap; abutting macros (split-core halves)
move as one body; X never changes; everything stays inside the core box (the type outline is the partition; the
outline never grows) and off the plan's keep points (ft bit sites, internal station registers).  A band is refused,
with the reason, when no straddle-free edge exists, there is no headroom, or the channel does not lower its deficit
(nets confined inside a macro run: a channel cannot carry them).
Output: per-band demand / supply / deficit / width, the macro moves, and OT_MACRO_MOVES (plan inst:x:y in the type
frame, plan orient kept) for gen_phys.macro_move_table.
"""
import argparse
import json
import math
import sys

import numpy as np

# GRT layer adjustments of the S81 tile flow (m6wi ctl what-if and ORFS asap7 fastroute), M2-M7 signal range
H_LAYERS = {"M2": (0.039, 0.50), "M4": (0.048, 0.25), "M6": (0.064, 0.30)}


def tracks_per_um(layers, blocked=()):
    return sum((1.0 - adj) / p for name, (p, adj) in layers.items() if name not in blocked)


class Model:
    def __init__(self, dump, layers=None, cut_step=4.32, bin_um=2.16, detour=2.16, mac_tpu=None, streets=True,
                 windows=4):
        self.d = dump
        self.layers = dict(layers or H_LAYERS)
        self.core = dump["core"]
        self.cut_step, self.bin_um, self.detour, self.streets, self.windows = cut_step, bin_um, detour, streets, windows
        y0, y1 = self.core[1], self.core[3]
        self.nb = int(math.ceil((y1 - y0) / bin_um))
        self.y0 = y0
        self.free_tpu = tracks_per_um(self.layers)
        self.mac_tpu = [tracks_per_um(self.layers, set(m.get("obs", []))) for m in dump["macros"]]
        if mac_tpu is not None:
            # measured over-macro capacity (GRT congestion.rpt): scale the open-layer figure, 0 stays 0
            nom = tracks_per_um({k: v for k, v in self.layers.items() if k == "M6"})
            self.mac_tpu = [v * mac_tpu / nom for v in self.mac_tpu]
        self.cuts = np.arange(self.core[0] + cut_step / 2, self.core[2], cut_step)
        nets = dump["nets"]
        self.cell = np.array([[n[0], n[1], n[2], n[3]] if n[0] is not None else [np.nan] * 4 for n in nets], float)
        self.mpins = [n[5] for n in nets]
        # net kind: 0 cells / bterms only, 1 macro pin + cells, 2 macro pins only (core-to-core)
        self.kind = np.array([0 if not n[5] else (2 if n[4] == 0 else 1) for n in nets])

    def net_boxes(self, boxes):
        """net pin boxes with macro pins moved by their macro's displacement from the dump."""
        out = self.cell.copy()
        orig = [m["box"] for m in self.d["macros"]]
        for i, mp in enumerate(self.mpins):
            if not mp:
                continue
            xs = [p[1] + boxes[p[0]][0] - orig[p[0]][0] for p in mp]
            ys = [p[2] + boxes[p[0]][1] - orig[p[0]][1] for p in mp]
            b = out[i]
            if np.isnan(b[0]):
                b[:] = [min(xs), min(ys), max(xs), max(ys)]
            else:
                b[:] = [min(b[0], *xs), min(b[1], *ys), max(b[2], *xs), max(b[3], *ys)]
        return out

    def bin_of(self, y):
        return np.clip(((y - self.y0) / self.bin_um).astype(int), 0, self.nb - 1)

    def supply(self, c, boxes):
        """tracks per Y bin at cut x = c; macro_frac = macro-covered fraction per bin."""
        s = np.full(self.nb, self.free_tpu * self.bin_um)
        mf = np.zeros(self.nb)
        edges = self.y0 + self.bin_um * np.arange(self.nb + 1)
        for k, b in enumerate(boxes):
            if not (b[0] < c < b[2]):
                continue
            ov = np.clip(np.minimum(edges[1:], b[3]) - np.maximum(edges[:-1], b[1]), 0, None)
            s -= ov * (self.free_tpu - self.mac_tpu[k])
            mf += ov / self.bin_um
        return s, np.minimum(mf, 1.0)

    def analyse(self, boxes):
        """-> list of per-cut dicts {c, deficit, lo, hi, demand, supply, macro_um} for the worst macro window."""
        nb = self.net_boxes(boxes)
        lo_b = self.bin_of(nb[:, 1] - self.detour)
        hi_b = self.bin_of(nb[:, 3] + self.detour)
        res = []
        for c in self.cuts:
            sel = (nb[:, 0] < c) & (nb[:, 2] > c)
            s, mf = self.supply(c, boxes)
            lo, hi = lo_b[sel], hi_b[sel]
            if self.streets:
                # an end in a macro-free street at this cut may use the whole street (std-cell area, no macro to
                # cross): spans grow to the street edges, so every window is bounded by macro or core edges
                free = mf < 0.5
                idx = np.arange(self.nb)
                fs = np.maximum.accumulate(np.where(free & ~np.concatenate([[False], free[:-1]]), idx, 0))
                en = np.where(free & ~np.concatenate([free[1:], [False]]), idx, self.nb)
                fe = np.minimum.accumulate(en[::-1])[::-1]
                lo = np.where(free[lo], fs[lo], lo)
                hi = np.where(free[hi], fe[hi], hi)
            C = np.zeros((self.nb, self.nb))
            np.add.at(C, (lo, hi), 1.0)
            # D[i, j] = nets with lo >= i and hi <= j
            D = np.cumsum(np.cumsum(C[::-1, :], axis=0)[::-1, :], axis=1)
            ps = np.concatenate([[0.0], np.cumsum(s)])
            pm = np.concatenate([[0.0], np.cumsum(mf)])
            S = ps[None, 1:] - ps[:-1, None]          # S[i, j] = sum s[i..j]
            M = pm[None, 1:] - pm[:-1, None]
            X = D - S
            X[np.tril_indices(self.nb, -1)] = -np.inf
            # up to `windows` disjoint deficit windows per cut, worst first (a cut can cross two congested bands)
            for _ in range(self.windows):
                i, j = np.unravel_index(np.argmax(X), X.shape)
                if not np.isfinite(X[i, j]) or (res and res[-1]["c"] == round(float(c), 3) and X[i, j] < 1.0):
                    break
                inw = (lo >= i) & (hi <= j)
                kinds = np.bincount(self.kind[sel][inw], minlength=3)
                res.append({"c": round(float(c), 3), "deficit": float(X[i, j]), "lo": float(self.y0 + i * self.bin_um),
                            "hi": float(self.y0 + (j + 1) * self.bin_um), "demand": float(D[i, j]),
                            "supply": float(S[i, j]), "macro_um": float(M[i, j] * self.bin_um), "nets": int(sel.sum()),
                            "cell_nets": int(kinds[0]), "macro_cell_nets": int(kinds[1]),
                            "core_core_nets": int(kinds[2])})
                X[: j + 1, i:] = -np.inf          # every window overlapping [i, j]
        return res


def bands_of(cuts, step):
    """group deficit cuts into bands: X-contiguous cuts whose worst windows overlap in Y."""
    out = []
    for r in sorted(cuts, key=lambda r: (r["c"], -r["deficit"])):
        if r["deficit"] < 1.0:         # less than one track
            continue
        live = [b for b in out if 0 < r["c"] - b["x1"] <= step * 1.01 and r["lo"] < b["hi"] and b["lo"] < r["hi"]]
        if live:
            b = max(live, key=lambda b: min(b["hi"], r["hi"]) - max(b["lo"], r["lo"]))
            b["x1"] = r["c"]; b["cuts"].append(r)
            b["lo"], b["hi"] = max(b["lo"], r["lo"]), min(b["hi"], r["hi"])
        else:
            out.append({"x0": r["c"], "x1": r["c"], "lo": r["lo"], "hi": r["hi"], "cuts": [r]})
    for b in out:
        w = max(b["cuts"], key=lambda r: r["deficit"])
        b.update(deficit=w["deficit"], demand=w["demand"], supply=w["supply"], worst_c=w["c"], macro_um=w["macro_um"],
                 cell_nets=w["cell_nets"], macro_cell_nets=w["macro_cell_nets"], core_core_nets=w["core_core_nets"])
    return sorted(out, key=lambda b: -b["deficit"])


def _ov(a, b, eps=1e-6):
    return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps


def rigid_groups(boxes, tol=0.12):
    """macros that abut edge to edge (split-core halves such as col_h9 u_e11.u_w / u_e11.u_e, ROMQ-GB) move as one
    body (tol 0.12 um: the halves sit 0.036 um apart through their track offsets): -> {macro idx: group}."""
    parent = list(range(len(boxes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, p in enumerate(boxes):
        for b in range(a + 1, len(boxes)):
            q = boxes[b]
            touch_x = (abs(p[2] - q[0]) < tol or abs(q[2] - p[0]) < tol) and p[1] < q[3] - tol and q[1] < p[3] - tol
            touch_y = (abs(p[3] - q[1]) < tol or abs(q[3] - p[1]) < tol) and p[0] < q[2] - tol and q[0] < p[2] - tol
            if touch_x or touch_y:
                parent[find(a)] = find(b)
    g = {}
    for k in range(len(boxes)):
        g.setdefault(find(k), []).append(k)
    return {k: tuple(v) for v in g.values() for k in v}


def open_channel(boxes, band, width, core, keep_pts=(), eps=1e-6, grid=0.864, groups=None):
    """open a macro-free channel R = band X range x [y*, y* + width] (or [y* - width, y*]) inside the band's worst
    window, y* = a macro edge (or core edge) in the window that no macro of that X range straddles.  Only macros that
    intersect R move, by the least grid multiple that clears it, and push whatever they then overlap (minimal moves);
    the existing gap at y* counts.  -> (new boxes, y*, {macro idx: dy}, side) or (None, reason, {}, None)."""
    xa, xb = band["x0"], band["x1"]
    inx = [k for k, b in enumerate(boxes) if b[0] < xb and b[2] > xa]
    lo, hi = band["lo"] - eps, band["hi"] + eps
    ups = {v for k in inx for v in (boxes[k][3],) if lo <= v <= hi} | ({core[1]} if band["lo"] <= core[1] + 2.2 else set())
    dns = {v for k in inx for v in (boxes[k][1],) if lo <= v <= hi} | ({core[3]} if band["hi"] >= core[3] - 2.2 else set())
    mid = (band["lo"] + band["hi"]) / 2
    tried = []
    for side, ys in sorted([("up", v) for v in ups] + [("down", v) for v in dns], key=lambda t: abs(t[1] - mid)):
        if any(boxes[k][1] < ys - eps and boxes[k][3] > ys + eps for k in inx):
            tried.append(f"{side} y*={ys:.2f} straddled")
            continue
        # the window's supply already counts the free street at y*: the channel is `width` beyond it
        if side == "up":
            top = min([boxes[k][1] for k in inx if boxes[k][1] >= ys - eps], default=core[3])
            r = [xa, ys, xb, top + width]
        else:
            bot = max([boxes[k][3] for k in inx if boxes[k][3] <= ys + eps], default=core[1])
            r = [xa, bot - width, xb, ys]
        nb = [list(b) for b in boxes]
        moved = {}
        hit = [k for k in inx if _ov(nb[k], r, eps)]
        if not hit:
            tried.append(f"{side} y*={ys:.2f} already clear")
            continue
        ok = True
        for k in hit:
            dy = snap_up(r[3] - nb[k][1], grid) if side == "up" else -snap_up(nb[k][3] - r[1], grid)
            ok = ok and _push(nb, k, dy, core, moved, eps, grid, groups)
        if not ok or any(_ov(nb[a], nb[b], eps) for a in moved for b in range(len(nb)) if b != a):
            tried.append(f"{side} y*={ys:.2f} no headroom for {width:.2f} um inside the core")
            continue
        bad = [k for k in moved for p in keep_pts
               if nb[k][0] < p[0] < nb[k][2] and nb[k][1] < p[1] < nb[k][3]
               and not (boxes[k][0] < p[0] < boxes[k][2] and boxes[k][1] < p[1] < boxes[k][3])]
        if bad:
            tried.append(f"{side} y*={ys:.2f} covers a keep point")
            continue
        return nb, ys, moved, side
    return None, "; ".join(tried[:6]) or "no macro edge in the window", {}, None


def _push(nb, k, dy, core, moved, eps, grid, groups=None):
    """move macro k (with its rigid group) by dy (grid multiple) and push, in the same direction, every macro it then
    overlaps."""
    todo = [(k, dy)]
    while todo:
        k, dy = todo.pop()
        if (dy > 0 and dy <= eps) or (dy < 0 and dy >= -eps):
            continue
        grp = (groups or {}).get(k, (k,))
        for g in grp:
            nb[g][1] += dy; nb[g][3] += dy
            moved[g] = round(moved.get(g, 0.0) + dy, 6)
            if nb[g][1] < core[1] - eps or nb[g][3] > core[3] + eps:
                return False
        for j, b in enumerate(nb):
            if j in grp:
                continue
            k = next((g for g in grp if _ov(nb[g], b, eps)), None)
            if k is not None:
                if dy > 0 and b[1] >= nb[k][1] - dy - eps:
                    todo.append((j, snap_up(nb[k][3] - b[1], grid)))
                elif dy < 0 and b[3] <= nb[k][3] - dy + eps:
                    todo.append((j, -snap_up(b[3] - nb[k][1], grid)))
                else:
                    return False          # would push sideways / through: refuse
    return True


def snap_up(v, g):
    return math.ceil(v / g - 1e-9) * g


def plan_map(dump, ptype):
    """ODB macro index -> plan hard core (matched on placed lower-left = plan origin + track offset)."""
    out = {}
    for k, m in enumerate(dump["macros"]):
        for c in ptype.get("hard_cores", []):
            ox, oy = c.get("track_offset_um") or [0.0, 0.0]
            if abs(c["origin_um"][0] + ox - m["box"][0]) < 1e-3 and abs(c["origin_um"][1] + oy - m["box"][1]) < 1e-3:
                out[k] = c
                break
    # fallback: same module, nearest plan site within 5 um (a kit can place a core off its plan site: col_h9_r2
    # stations t6/t7/t8 sit 0.192 um below origin + offset); the move keeps that offset (to = plan origin + dy)
    used = {id(c) for c in out.values()}
    for k, m in enumerate(dump["macros"]):
        if k in out:
            continue
        near = sorted((math.dist(c["origin_um"], m["box"][:2]), i) for i, c in enumerate(ptype.get("hard_cores", []))
                      if c.get("module") == m["master"] and id(c) not in used)
        if near and near[0][0] < 5.0 and (len(near) == 1 or near[1][0] > near[0][0] + 1.0):
            out[k] = ptype["hard_cores"][near[0][1]]
            used.add(id(out[k]))
    return out


def keep_points(ptype):
    pts = []
    for s in ptype.get("ft_slots", []) or []:
        for grp in s.get("bit_sites_um", []) or []:
            pts.extend(tuple(p) for p in grp)
    for st in ptype.get("internal_stations", []) or []:
        pts.extend(tuple(p) for p in st.get("regs_um", []) or [])
    return pts


def run(dump, ptype=None, width_grid=0.864, max_iter=40, **kw):
    m = Model(dump, **kw)
    boxes = [list(x["box"]) for x in dump["macros"]]
    keep = keep_points(ptype or {})
    groups = rigid_groups(boxes)
    gain = m.free_tpu - min(m.mac_tpu)
    first = None
    channels, refused = [], []
    for it in range(max_iter):
        cuts = m.analyse(boxes)
        bands = bands_of(cuts, m.cut_step)
        if first is None:
            first = [dict(b, cuts=len(b["cuts"])) for b in bands]
        live = [b for b in bands if not any(abs(b["worst_c"] - r["worst_c"]) < 1e-6 and b["lo"] == r["lo"]
                                            for r in refused)]
        if not live:
            break
        b = live[0]
        w = snap_up(b["deficit"] / m.free_tpu, width_grid)    # street grows at free capacity; loop re-checks
        nb, ys, moved, side = open_channel(boxes, b, w, m.core, keep, grid=width_grid, groups=groups)
        rec = {k: b[k] for k in ("x0", "x1", "lo", "hi", "deficit", "demand", "supply", "worst_c", "macro_um",
                                 "cell_nets", "macro_cell_nets", "core_core_nets")}
        rec["width_um"] = w
        if nb is None:
            rec["refused"] = ys
            refused.append(b)
            channels.append(rec)
            continue
        after = max([r["deficit"] for r in m.analyse(nb) if abs(r["c"] - b["worst_c"]) < 1e-6
                     and r["lo"] < b["hi"] + w and b["lo"] - w < r["hi"]], default=0.0)
        if after > b["deficit"] - 1.0:
            rec["refused"] = (f"channel at y*={ys:.2f} ({side}) does not lower the window deficit "
                              f"({b['deficit']:.0f} -> {after:.0f} tracks): demand is not channel-fixable")
            refused.append(b)
            channels.append(rec)
            continue
        rec["deficit_after_at_c"] = after
        rec.update(y_split=ys, side=side, moved={dump["macros"][k]["name"]: round(dy, 4) for k, dy in moved.items()})
        channels.append(rec)
        boxes = nb
    final = bands_of(m.analyse(boxes), m.cut_step)
    pm = plan_map(dump, ptype or {})
    moves, env = [], []
    for k, (b0, b1) in enumerate(zip([x["box"] for x in dump["macros"]], boxes)):
        dy = b1[1] - b0[1]
        if abs(dy) < 1e-6:
            continue
        c = pm.get(k)
        mv = {"macro": dump["macros"][k]["name"], "dy_um": round(dy, 4), "from_ll": b0[:2], "to_ll": [b0[0], b1[1]]}
        if c:
            to = [c["origin_um"][0], round(c["origin_um"][1] + dy, 4)]
            mv.update(plan_inst=c["inst"], plan_origin=c["origin_um"], to_origin=to)
            env.append(f"{c['inst']}:{to[0]:g}:{to[1]:g}")
        moves.append(mv)
    return {"schema": "ds85-hchan/1", "params": {"layers": m.layers, "free_tracks_per_um": round(m.free_tpu, 3),
                                                  "over_macro_tracks_per_um": sorted({round(v, 3) for v in m.mac_tpu}),
                                                  "gain_tracks_per_um": round(gain, 3), "cut_step": m.cut_step,
                                                  "bin_um": m.bin_um, "detour": m.detour, "grid": width_grid},
            "bands_before": first, "channels": channels,
            "bands_after": [dict(b, cuts=len(b["cuts"])) for b in final],
            "deficit_before": round(sum(b["deficit"] for b in first), 1),
            "deficit_after": round(sum(b["deficit"] for b in final), 1),
            "moves": moves, "OT_MACRO_MOVES": ",".join(env), "unmapped": [mv["macro"] for mv in moves
                                                                          if "plan_inst" not in mv]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dump", help="hchan_dump.py JSON of the placed ODB")
    ap.add_argument("--plan", help="die_plan.json (plandir) for plan inst names, keep points")
    ap.add_argument("--type")
    ap.add_argument("--cut-step", type=float, default=4.32)
    ap.add_argument("--bin", type=float, default=2.16)
    ap.add_argument("--detour", type=float, default=2.16)
    ap.add_argument("--grid", type=float, default=0.864)
    ap.add_argument("--mac-tpu", type=float, default=None,
                    help="measured over-macro horizontal tracks/um (S81 GRT: capacity 3 per 0.57-um gcell = 5.26)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    dump = json.load(open(a.dump))
    ptype = json.load(open(a.plan))["partition_types"][a.type] if a.plan else None
    r = run(dump, ptype, width_grid=a.grid, cut_step=a.cut_step, bin_um=a.bin, detour=a.detour, mac_tpu=a.mac_tpu)
    s = json.dumps(r, indent=1)
    if a.out:
        open(a.out, "w").write(s + "\n")
    print(f"HCHAN bands_before={len(r['bands_before'])} deficit_before={r['deficit_before']} "
          f"channels={sum(1 for c in r['channels'] if 'moved' in c)} refused={sum(1 for c in r['channels'] if 'refused' in c)} "
          f"bands_after={len(r['bands_after'])} deficit_after={r['deficit_after']} moves={len(r['moves'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
