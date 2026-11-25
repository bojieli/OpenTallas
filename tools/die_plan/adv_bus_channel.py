#!/usr/bin/env python3
"""adv_bus_channel.py -- report-only advisory ADV-BUS-CHANNEL-FIT (FP-CONVERGE-QC, COORD 11-25; WARN only, never a gate).

Why: QC-FEFW-FAM (VISQC-FEFW-1 form) gives every per-bit E/W-face bus station a vertical channel band of
max(4, 0.1 * bits) um in x between the face pin and the core-centre leaf; buses whose pin..leaf y spans overlap need disjoint
bands, buses with disjoint spans may share one.  sle_fe_v2 has 4 E-face buses that no band fits inside the 311 um strip
(needs 388); that is a die-level strip growth that no row can do, and the census found no PRECHECK that saw it.

Per type and face side (E, W) this places the side's bus stations with the packer's greedy rule (widest first, 4 um gap,
x-hull = pin x .. leaf x, existing leg_order=channel bands are fixed obstacles) and, when any bus does not fit, finds the
least strip growth d (um on the pin side) that fits them all.  Needed width = strip width + d.
The packer's spine-column avoidance is a preference only (it falls back to gap 4/1/0 without it), so it is not modelled.

    findings(raw, plan_path=None, tree=None, types=None, **kw) -> ["WARN ADV-BUS-CHANNEL-FIT ..."]
    side_fit(T, face) -> dict(strip, need, unfit) or None
"""
import math
import re

CHECK = "BUS-CHANNEL-FIT"
GAPS = (4.0, 1.0, 0.0)
EDGE = 2.0
MAX_GROW_UM = 2000.0
MAX_LINES = 40


def width(bits):
    return round(max(4.0, 0.1 * bits), 3)


def _items(T, face):
    B = {b.get("name"): b for b in T.get("buses") or []}
    fixed, todo = [], []
    for e in T.get("internal_stations") or []:
        c = str(e.get("conn", ""))
        b = B.get(c[4:]) if c.startswith("bus:") else None
        if b is None or b.get("face") != face or e.get("bit_route") != "per_bit" or "leaf_um" not in e:
            continue
        pin = e["from_um"] if b.get("dir") == "in" else e["to_um"]
        lx, ly = e["leaf_um"]
        it = dict(conn=c, w=width(float(e.get("bits") or 0)), px=float(pin[0]), lx=float(lx),
                  ylo=min(float(pin[1]), float(ly)), yhi=max(float(pin[1]), float(ly)))
        if e.get("leg_order") == "channel" and e.get("channel_um"):
            it["lo"], it["hi"] = map(float, e["channel_um"])
            fixed.append(it)
        else:
            todo.append(it)
    return fixed, todo


def _ov(a, b):
    return a["yhi"] > b["ylo"] and b["yhi"] > a["ylo"]


def _place(it, placed, W, grow, face):
    # growth moves the pin side outward: E hull top, W hull bottom (x measured from the same origin, bands shift with it)
    lo_x, hi_x = min(it["px"], it["lx"]), max(it["px"], it["lx"])
    if face == "E":
        hl, hh = max(EDGE, lo_x), min(W + grow - EDGE, hi_x + grow)
    else:
        hl, hh = max(EDGE, lo_x) - grow, min(W - EDGE, hi_x)
    for gap in GAPS:
        best = None
        for x0 in range(int(math.ceil(hl)), int(math.floor(hh - it["w"])) + 1):
            lo, hi = float(x0), round(x0 + it["w"], 3)
            if any(_ov(it, p) and lo < p["hi"] + gap and p["lo"] < hi + gap for p in placed):
                continue
            sc = abs((lo + hi) / 2 - (it["px"] + it["lx"]) / 2)
            if best is None or sc < best[0]:
                best = (sc, lo, hi)
        if best:
            return best[1], best[2]
    return None


def _pack(fixed, todo, W, grow, face):
    placed = list(fixed)
    unfit = []
    for it in sorted(todo, key=lambda x: (-x["w"], -(x["yhi"] - x["ylo"]), x["conn"])):
        r = _place(dict(it), placed, W, grow, face)
        if r is None:
            unfit.append(it["conn"])
            continue
        placed.append(dict(it, lo=r[0], hi=r[1]))
    return unfit


def side_fit(T, face):
    fixed, todo = _items(T, face)
    if not todo:
        return None
    W = float(T["outline_um"][0])
    strip = max(abs(i["px"] - i["lx"]) for i in fixed + todo)
    unfit = _pack(fixed, todo, W, 0.0, face)
    if not unfit:
        return dict(strip=strip, need=strip, unfit=[])
    d = 0.0
    while d < MAX_GROW_UM:
        d += 1.0
        if not _pack(fixed, todo, W, d, face):
            return dict(strip=strip, need=strip + d, unfit=unfit)
    return dict(strip=strip, need=float("inf"), unfit=unfit)


def type_lines(tn, T):
    out = []
    for face in ("E", "W"):
        s = side_fit(T, face)
        if s and s["unfit"]:
            out.append("WARN ADV-%s %s: %s side strip %.0f um, the %d bus(es) need %.0f um (%s unplaced in the packer's band rule "
                       "max(4, 0.1*bits) um, y-overlapping buses disjoint): fix: grow the strip to the needed width at die level "
                       "(moves pins/leaves; pre-approved growth) or split the bus across faces" % (
                           CHECK, tn, face, s["strip"], len(s["unfit"]), s["need"],
                           ", ".join(u.replace("bus:", "") for u in s["unfit"][:5])))
    return out


def findings(raw, plan_path=None, tree=None, types=None, **_kw):
    P = raw.get("partition_types") or {}
    if not P:
        return [f"WARN ADV-{CHECK} not checked: plan has no partition_types"]
    out = []
    for tn in sorted(P):
        T = P[tn]
        if types and not re.search(types, tn):
            continue
        if not isinstance(T, dict) or not T.get("outline_um") or not T.get("internal_stations") or not T.get("buses"):
            continue
        try:
            out += type_lines(tn, T)
        except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
            out.append(f"WARN ADV-{CHECK} {tn}: not checked: {type(e).__name__}: {str(e)[:120]}")
    return out[:MAX_LINES]
