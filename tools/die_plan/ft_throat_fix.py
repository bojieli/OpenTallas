#!/usr/bin/env python3
"""S81-LEAF-PLAN 11-15 (COORD r57, Fable closure lever 2; FABLE-TRIAGE-S81 sec 8): ft station throat fix.

The kit generator's ft_track_use.json gives per ft slot u_station = bits / (narrowest station column extent across the
bundle x usable tracks per um) (ft_spread.track_use).  Over 1.0 the bundle cannot leave its station column on the
signal layers it has: leaf t14 ft5 (1104 bits turning W through a 17-um gap between ve_m/ve_s and u_vs) is the GRT
overflow of that pattern, and 53 of the 62 leaf types have such a slot (t62/t72 1.99).

Form (plan geometry only; pins, windows, outlines, cores, stations, cycles and RTL unchanged):
for every station of a slot whose u_station > TARGET, the station's explicit bit sites are rebuilt as an even band
ACROSS the bundle (the axis track_use measures: y for E/W in-face slots, x for N/S) of extent >= bits / (TARGET x
tracks/um), bits kept in their old order along that axis, each snapped to a free legal row site (RowAllocator with the
macro keep-offs and clock halos of ft_seam_fix / ft_nudge).  When macros squeeze the band in place (the throat), the
band centre is re-sited along the flow and across it in 5.4-um steps up to SHIFT_MAX_UM, nearest first, and the
station centre (regs_um) moves to the band centroid.  A site is accepted only if u_station of the station is <= TARGET,
every hop of every lane crossing the slot stays <= max(LIMIT, its value before), and for station 1 the S0->S1
input-face hops stay within reach.  Slots without plan bit sites (gen spread fell back to the clump) get a band too.
What still fails is listed with the gap it found (core spacing needed = throat widening, a core move).

    ft_throat_fix.py PLAN OUT LEDGER [--type REGEX] [--target 0.95] [--dry]
"""
import argparse, json, math, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import ft_spread as FS  # noqa: E402
import ft_seam_fix as SF  # noqa: E402

TARGET = 0.95                   # build target (the gate COORD set is 1.0)
LIMIT = SF.LIMIT
SHIFT_STEP_UM = 5.4
SHIFT_MAX_UM = 64.8             # across the bundle
ALONG_MAX_UM = 129.6
HOP_TOL_UM = 2.16               # a station that follows a core move may lengthen an over-reach hop by one column pitch            # along the flow (last-station siting)


def horiz(s):
    return s.get("in_face", "W") in "EW"


def extent(sites, W, hz):
    c = sorted(p[1] if hz else p[0] for p in sites[:W])
    lo, hi = c[int(.02 * len(c))], c[max(int(.98 * len(c)) - 1, 0)]
    return hi - lo + (FS.CELL[1] if hz else FS.CELL[0])


def u_clump(s):
    """track_use's u_station of a centre-only slot when gen spread falls back to the ff_put_near clump."""
    W, k = int(s["width"]), int(s.get("stations", 1))
    if k < 2 or len(s.get("regs_um") or []) < k:
        return None
    return W / (math.sqrt(W * FS.CELL[0] * FS.CELL[1]) * 1.15 * FS._tracks(s, horiz(s)))


def u_stations(s):
    """u per explicit stage (None for slots without bit sites: gen clump/spread form)."""
    W = int(s["width"]); tpu = FS._tracks(s, horiz(s))
    if not s.get("bit_sites_um"):
        return None
    return [W / (extent(st, W, horiz(s)) * tpu) for st in s["bit_sites_um"]]


def band(al, centre, order, W1, ext, hz, cell):
    """allocate W1 sites as a band of extent ext across the bundle at centre; order[i] = rank of bit i."""
    cp, rp = 2.16, .27
    if hz:          # stacked along y (rows), columns along x
        nper = max(1, int(ext / rp)); ncol = math.ceil(W1 / nper)
        pos = [(centre[0] + (c - (ncol - 1) / 2) * cp, centre[1] - ext / 2 + r * rp)
               for r in range(nper) for c in range(ncol)]
        pos.sort(key=lambda q: (q[1], q[0]))
    else:           # stacked along x (columns), rows along y
        nper = max(1, int(ext / cp)); nrow = math.ceil(W1 / nper)
        pos = [(centre[0] - ext / 2 + c * cp, centre[1] + (r - (nrow - 1) / 2) * rp)
               for c in range(nper) for r in range(nrow)]
        pos.sort(key=lambda q: (q[0], q[1]))
    # spread the W1 ranks evenly over the band (not just the first W1 grid points)
    step = len(pos) / W1
    out = [None] * W1
    for i in range(W1):
        q = pos[min(int(order[i] * step), len(pos) - 1)]
        try:
            c = al.allocate(q, 1, max_radius_um=20.0)[0][0]
        except ValueError:
            return None
        out[i] = [round(float(c[0] - cell[0] / 2), 6), round(float(c[1] - cell[1] / 2), 6)]
    return out


def ranks(sites, hz):
    k = 1 if hz else 0
    idx = sorted(range(len(sites)), key=lambda i: (sites[i][k], sites[i][1 - k]))
    r = [0] * len(sites)
    for n, i in enumerate(idx):
        r[i] = n
    return r


def shifts(hz):
    """(along-flow, across) offsets nearest first; along = x for E/W slots."""
    n = int(SHIFT_MAX_UM / SHIFT_STEP_UM); na = int(ALONG_MAX_UM / SHIFT_STEP_UM)
    c = [(a * SHIFT_STEP_UM, b * SHIFT_STEP_UM) for a in range(-na, na + 1) for b in range(-n, n + 1)]
    c.sort(key=lambda q: (abs(q[0]) + abs(q[1]), abs(q[1])))
    return [((q[0], q[1]) if hz else (q[1], q[0])) for q in c]


GRID = 0.54                      # core origin grid (core_place G)
KEEP = 2.0                       # ft_nudge KEEPOFF: flop keep-off from a macro edge


def entry(t, name):
    """the plan record that places macro `name` (hard core, content, or a content's physical part)."""
    for c in t.get("hard_cores") or []:
        if c["inst"] == name:
            return c
    for c in t.get("contents") or []:
        if c["inst"] == name and "origin_um" in c:
            return c
        for q in c.get("physical_parts") or []:
            if q.get("physical_inst") == name:
                return q
    return None


def band_thickness(W1, ext, hz):
    return math.ceil(W1 / max(1, int(ext / (.27 if hz else 2.16)))) * (2.16 if hz else .27)


def throat(t, centre, ext, thick, hz):
    """free interval across the bundle at the station's along-flow slice: (lo, hi, low_macro, high_macro)."""
    ax = 1 if hz else 0                    # across axis
    W, H = t["outline_um"]; L = (H if hz else W)
    a0, a1 = centre[1 - ax] - thick / 2, centre[1 - ax] + thick / 2
    c = centre[ax]
    lo, hi, mlo, mhi = 4.32, L - 4.32, None, None
    for m, b in S.placed_macro_boxes(t).items():
        b0, b1 = (b[0], b[2]) if ax == 1 else (b[1], b[3])          # along extent
        if min(b1 + KEEP, a1) - max(b0 - KEEP, a0) <= 0:
            continue
        q0, q1 = (b[1], b[3]) if ax == 1 else (b[0], b[2])          # across extent
        if q1 <= c:
            if q1 + KEEP > lo:
                lo, mlo = q1 + KEEP, m
        elif q0 >= c:
            if q0 - KEEP < hi:
                hi, mhi = q0 - KEEP, m
        else:                                                        # the centre is in this macro: not a throat read
            return None
    return lo, hi, mlo, mhi


def push_ok(t, name, d, ax, max_group=6):
    """move macro `name` by d along axis ax, rigidly with every macro it would then crowd (chain, <= max_group), if the
    group stays inside the outline, 2 x keep-off clear of every other macro, of every ft bit site / station centre and
    every clock point.  Returns [(record, old origin)] or None."""
    from ft_nudge import clock_points
    d = math.copysign(math.ceil(abs(d) / GRID - 1e-9) * GRID, d)
    boxes = S.placed_macro_boxes(t)
    W, H = t["outline_um"]
    def moved(b):
        b = list(b); b[ax] += d; b[ax + 2] += d; return b
    def crowd(a, o):
        return min(a[2], o[2] + 2 * KEEP) - max(a[0], o[0] - 2 * KEEP) > 0 and \
            min(a[3], o[3] + 2 * KEEP) - max(a[1], o[1] - 2 * KEEP) > 0
    group = [name]
    while True:
        add = [m for m, o in boxes.items() if m not in group and any(crowd(moved(boxes[g]), o) for g in group)]
        if not add:
            break
        group += add
        if len(group) > max_group:
            return None
    recs = [entry(t, m) for m in group]
    if any(e is None or e.get("fixed") for e in recs):
        return None
    nb = [moved(boxes[m]) for m in group]
    hit_site = lambda bx, by: any(b[0] - KEEP < bx + 1.404 and bx < b[2] + KEEP and b[1] - KEEP < by + .27 and by < b[3] + KEEP
                                  for b in nb)
    for b in nb:
        if b[0] < 4.32 or b[1] < 4.32 or b[2] > W - 4.32 or b[3] > H - 4.32:
            return None
        for q in clock_points(t):
            if b[0] - 4 < q[0] < b[2] + 4 and b[1] - 4 < q[1] < b[3] + 4:
                return None
    # explicit / added clock taps keep TAP_CLEAR_UM off every placement box (taps.grid_explicit_sites rule): a tap the
    # moved group now crowds moves with it (by d); the type's own tap gate (taps.grid_explicit_taps) then decides
    clr = float(getattr(S, "TAP_CLEAR_UM", 10.0))
    ck = t.get("clock") or {}
    tap_moves = []
    for p in list(ck.get("added_taps") or []) + [x for x in ck.get("taps") or [] if isinstance(x, dict)]:
        if "xy" in p:
            x, y = map(float, p["xy"])
            if any(b[0] - clr < x < b[2] + clr and b[1] - clr < y < b[3] + clr for b in nb):
                tap_moves.append((p, list(p["xy"])))
    out = []; slot_keep = []
    for e in {id(e): e for e in recs}.values():
        old = list(e["origin_um"]); out.append((e, old))
        e["origin_um"] = [round(old[0] + (d if ax == 0 else 0), 4), round(old[1] + (d if ax == 1 else 0), 4)]
    # ft stations the moved cores now cover move with them (by d, onto the nearest free legal site)
    dv = np.array([d if ax == 0 else 0.0, d if ax == 1 else 0.0])
    moved_slots = []
    for x in t.get("ft_slots") or []:
        regs = x.get("regs_um") or []
        sites = x.get("bit_sites_um") or []
        aff = [(j, [i for i, (bx, by) in enumerate(st) if hit_site(bx, by)]) for j, st in enumerate(sites)]
        aff = [(j, ii) for j, ii in aff if ii]
        rhit = [j for j, r in enumerate(regs) if j and any(b[0] < r[0] < b[2] and b[1] < r[1] < b[3] for b in nb)]
        if not aff and not rhit:
            continue
        slot_keep.append((x, json.dumps(x))); moved_slots.append(x["name"])
        cw, ch = x.get("bit_site_cell_um", FS.CELL)
        for j, ii in aff:
            al = SF.allocator(t, x["name"], j)
            iset = set(ii)
            for i, (bx, by) in enumerate(x["bit_sites_um"][j]):
                if i not in iset:
                    al.reserve_rectangle((bx, by, bx + cw, by + ch))
            for i in ii:
                bx, by = x["bit_sites_um"][j][i]
                c = np.array([bx + cw / 2, by + ch / 2]) + dv
                try:
                    q = al.allocate(c, 1, max_radius_um=40.0)[0][0]
                except ValueError:
                    q = None
                if q is None or hit_site(q[0] - cw / 2, q[1] - ch / 2):
                    for e, o in out:
                        e["origin_um"] = o
                    for xx, kk in slot_keep:
                        xx.clear(); xx.update(json.loads(kk))
                    return None
                x["bit_sites_um"][j][i] = [round(float(q[0] - cw / 2), 6), round(float(q[1] - ch / 2), 6)]
            if j + 1 < len(regs):
                cen = np.array(x["bit_sites_um"][j], float).mean(0) + np.array([cw, ch]) / 2
                regs[j + 1] = [round(float(cen[0]), 4), round(float(cen[1]), 4)]
        for j in rhit:
            if not sites:
                regs[j] = [round(float(regs[j][0] + dv[0]), 4), round(float(regs[j][1] + dv[1]), 4)]
    for p, old in tap_moves:
        p["xy"] = [round(float(old[0]) + float(dv[0]), 4), round(float(old[1]) + float(dv[1]), 4)]
    o = dict(group=group, um=d, undo=out, slots=moved_slots, slot_keep=slot_keep, taps=tap_moves)
    if tap_moves or ck.get("tap_mode") in ("grid+explicit", "explicit"):
        try:
            import taps as TP
            P, tn = CTX["P"], CTX["tn"]
            if ck.get("tap_mode") == "grid+explicit":
                TP.grid_explicit_taps(P, tn)
            elif ck.get("tap_mode") == "explicit":
                TP.explicit_taps(P, tn)
        except Exception as ex:                      # noqa: BLE001  (tap/reset gate errors all reject the push)
            undo(o)
            CTX.setdefault("tap_rejects", []).append(str(ex)[:160])
            return None
    return o


def undo(o):
    for e, old in o["undo"]:
        e["origin_um"] = old
    for p, old in o.get("taps") or []:
        p["xy"] = old
    for x, k in o["slot_keep"]:
        x.clear(); x.update(json.loads(k))


def hops_worse(t, done):
    """True when a slot whose stations followed a core move now has a lane hop > max(LIMIT, its value before)."""
    P, tn = CTX["P"], CTX["tn"]
    for o in done:
        for x, k in o["slot_keep"]:
            lids = SF.slot_lanes(P, tn, x["name"])
            now = SF.max_slot_hop(P, lids, tn, x["name"])[0]
            cur = json.dumps(x); x.clear(); x.update(json.loads(k))
            before = SF.max_slot_hop(P, lids, tn, x["name"])[0]
            x.clear(); x.update(json.loads(cur))
            if now > max(LIMIT, before + HOP_TOL_UM) + 1e-6:
                return True
            us = u_stations(x)
            if x["name"] in CTX.get("pending", ()):          # rebuilt later in this run
                continue
            if us and max(us) > CTX["gate"] + 1e-6 and max(us) > max(u_stations(json.loads(k)) or [0]) + 1e-6:
                return True
    return False


CTX = {}


def widen_throat(t, s, centre, ext, W1, hz, rec):
    """open the throat at the station: push the macro(s) bounding the free interval across the bundle apart."""
    th = band_thickness(W1, ext, hz)
    g = throat(t, centre, ext, th, hz)
    if g is None:
        return False
    lo, hi, mlo, mhi = g
    deficit = ext + 2 * GRID - (hi - lo)
    if deficit <= 0:
        return False
    ax = 1 if hz else 0
    tries = []
    if mhi: tries.append([(mhi, deficit)])
    if mlo: tries.append([(mlo, -deficit)])
    if mhi and mlo: tries.append([(mhi, deficit / 2), (mlo, -deficit / 2)])
    for f in (.75, .5, .25):                         # partial pushes: the next attempt reads the throat again
        if mhi: tries.append([(mhi, deficit * f)])
        if mlo: tries.append([(mlo, -deficit * f)])
    for plan in tries:
        done = []
        for m, d in plan:
            o = push_ok(t, m, d, ax)
            if o is None:
                break
            done.append(o)
        if len(done) == len(plan) and not hops_worse(t, done):
            rec.setdefault("core_moves", []).extend(
                dict(cores=o["group"], axis="xy"[ax], um=o["um"], throat_um=round(hi - lo, 1)) for o in done)
            return True
        for o in reversed(done):
            undo(o)
    rec.setdefault("throat_fail", []).append(dict(gap_um=round(hi - lo, 1), need_um=round(ext, 1), low=mlo, high=mhi))
    return False


def _entries(t):
    out = [c for c in t.get("hard_cores") or []]
    for c in t.get("contents") or []:
        if "origin_um" in c:
            out.append(c)
        out += [q for q in c.get("physical_parts") or [] if "origin_um" in q]
    return out


def search(P, t, s, j, r0, order, W1, ext_need, hz, cell, W, tpu, target, lids, lim_touch, first_ok0):
    """nearest band site (shifts) for stage j+1 -> (done record or None, fail counts)."""
    tn = next(k for k, v in P.types.items() if v is t)
    regs = s["regs_um"]; olds = s["bit_sites_um"][j]
    al = SF.allocator(t, s["name"], j); base_used = set(al.used)
    fails = dict(no_band=0, u=0, hop=0)
    for dx, dy in shifts(hz):
        c = r0 + (dx, dy)
        al.used = set(base_used)
        g = band(al, c, order, W1, ext_need, hz, cell)
        if g is None:
            fails["no_band"] += 1; continue
        u = W / (extent(g, W, hz) * tpu)
        if u > target + 1e-6:
            fails["u"] += 1; continue
        cen = np.array(g, float).mean(0) + np.array(cell) / 2
        if not dx and not dy and float(abs(cen - r0).max()) <= 2.16:
            cen = r0                                 # band built round the station centre: the centre stays
        s["bit_sites_um"][j] = g
        regs[j + 1] = [round(float(cen[0]), 4), round(float(cen[1]), 4)]
        touch, _ = SF.max_slot_hop(P, lids, tn, s["name"])
        if touch > lim_touch + 1e-6 or (j == 0 and first_ok0 and not SF.first_hop_ok(P, tn, s)):
            regs[j + 1] = [float(r0[0]), float(r0[1])]; s["bit_sites_um"][j] = olds
            fails["hop"] += 1; continue
        return dict(stage=j + 1, shift_um=[dx, dy], u=round(u, 3), moved_um=round(float(abs(cen - r0).sum()), 1)), fails
    return None, fails


def fix_slot(P, raw, tn, s, target, rec):
    t = raw["partition_types"][tn]
    CTX.update(P=P, tn=tn, gate=1.0)
    W = int(s["width"]); W1 = W + 1; hz = horiz(s); tpu = FS._tracks(s, hz)
    # track_use measures the 2..98 % span of the bits: build the band 1/0.95 wider so the measured span meets target
    ext_need = W / (target * tpu) / 0.95 + (FS.CELL[1] if hz else FS.CELL[0])
    k = int(s.get("stations", 1)); regs = s.get("regs_um") or []
    if k < 2 or len(regs) != k:
        rec["why"] = "no station centres (route form)"; return False
    lids = SF.slot_lanes(P, tn, s["name"])
    keep = json.dumps(s)
    keep_t = {id(e): list(e["origin_um"]) for e in _entries(t)}
    keep_slots = json.dumps(t.get("ft_slots"))
    lim_touch = max(LIMIT, SF.max_slot_hop(P, lids, tn, s["name"])[0])
    first_ok0 = SF.first_hop_ok(P, tn, s)
    if not s.get("bit_sites_um"):
        s["bit_site_cell_um"] = list(FS.CELL); s["bit_sites_um"] = [[] for _ in range(k - 1)]
        olds = [None] * (k - 1)
    else:
        olds = [list(x) for x in s["bit_sites_um"]]
    cell = s["bit_site_cell_um"]
    us = u_stations(s) if olds[0] is not None else [9.9] * (k - 1)
    rec.update(width=W, stations=k, ext_need_um=round(ext_need, 1), u_before=[round(u, 3) for u in us], stages=[])
    for j in range(k - 1):
        if us[j] <= target and olds[j] is not None:
            continue
        r0 = np.array(regs[j + 1], float)
        order = ranks(olds[j], hz) if olds[j] is not None else list(range(W1))
        done = None; fails = dict(no_band=0, u=0, hop=0)
        s["bit_sites_um"][j] = olds[j] if olds[j] is not None else []
        for attempt in range(5):
            done, fails = search(P, t, s, j, r0, order, W1, ext_need, hz, cell, W, tpu, target, lids, lim_touch, first_ok0)
            if done is not None or not widen_throat(t, s, r0, ext_need, W1, hz, rec):
                break
        if done is None:
            for e in _entries(t):
                if id(e) in keep_t:
                    e["origin_um"] = keep_t[id(e)]
            rec.pop("core_moves", None)
            ks = json.loads(keep_slots)
            for x, y in zip(t["ft_slots"], ks):
                x.clear(); x.update(y)
            s.clear(); s.update(json.loads(keep))
            rec["why"] = (f"stage {j + 1}: no band of {ext_need:.1f} um across the bundle within the search keeps "
                          f"u <= {target} and the hops, and the throat could not be widened")
            rec["failed_stage"] = j + 1; rec["centre"] = list(r0); rec["fails"] = fails
            return False
        rec["stages"].append(done)
    if any(not x for x in s["bit_sites_um"]):           # clump slot: the untouched stages need a band too
        s.clear(); s.update(json.loads(keep)); rec["why"] = "clump slot partly banded"; return False
    rec["u_after"] = [round(u, 3) for u in u_stations(s)]
    s["note"] = (s.get("note", "") + " | ft_throat_fix 11-15: station band(s) %s widened to u<=%.2f" %
                 ([d["stage"] for d in rec["stages"]], target)).strip(" |")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("ledger")
    ap.add_argument("--type", default=r"^ot_s81sl_leaf__t\d+$"); ap.add_argument("--target", type=float, default=TARGET)
    ap.add_argument("--gate", type=float, default=1.0); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--clump", action="store_true", help="also centre-only slots whose gen spread falls back to the clump "
                    "(give them plan bit sites); pass the slot names with --slot")
    ap.add_argument("--slot", help="regex of slot names (default all)")
    ap.add_argument("--rows-only", action="store_true", help="OUT gets only the changed partition_types rows")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text()); P = S.Plan(raw)
    led = []
    for tn in sorted(raw["partition_types"]):
        if not re.search(a.type, tn):
            continue
        um = lambda x: max(u_stations(x)) if u_stations(x) else (u_clump(x) if a.clump else None)
        todo = [x["name"] for x in raw["partition_types"][tn].get("ft_slots") or [] if (um(x) or 0) > a.gate
                and (not a.slot or re.search(a.slot, x["name"]))]
        for s in raw["partition_types"][tn].get("ft_slots") or []:
            CTX["pending"] = set(todo[todo.index(s["name"]) + 1:]) if s["name"] in todo else set()
            if s["name"] not in todo:
                continue
            us = u_stations(s) or [u_clump(s)]
            rec = dict(type=tn, slot=s["name"])
            if not a.dry:
                rec["ok"] = fix_slot(P, raw, tn, s, a.target, rec)
            else:
                rec["u_before"] = [round(u, 3) for u in us]
            led.append(rec); print(tn, s["name"], rec.get("u_before"), "->", rec.get("u_after"), rec.get("why", ""), flush=True)
    if not a.dry:
        raw["note"] = "S81-LEAF-PLAN ft_throat_fix <- " + raw.get("note", "")[:200]
        if a.rows_only:
            ch = sorted({r["type"] for r in led if r.get("ok")})
            Path(a.out).write_text(json.dumps({tn: raw["partition_types"][tn] for tn in ch}) + "\n")
        else:
            Path(a.out).write_text(json.dumps(raw) + "\n")
    Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    print("slots over %.2f: %d, fixed %d" % (a.gate, len(led), sum(1 for r in led if r.get("ok"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
