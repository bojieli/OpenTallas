#!/usr/bin/env python3
"""Pin ALIGNMENT of die net bundles (owner 2026-10-13: "are pin placements ready for die-level routing?").

child_lint proves a pin can be REACHED, slot_fit that it is on the contract FACE and LAYER, the hop gates that the two
ends are within reach.  Nothing checked that the two ends of a bundle FACE EACH OTHER: a 512-b bus whose pins leave one
tile 60 um above the pins they enter on the next tile needs 512 perpendicular jog wires in the channel between them, and
a bus whose bit order is reversed needs every bit to cross every other.  Both are cut demand the die cut tables
(results/arch/*/cuts.py: pins projected onto the face toward the peer) do not see.

Per bundle (one driver instance port -> one load instance port, every bit pin to pin, real pin rectangles of the LEFs the
die binds, instance orientation applied):
  kind      straight  the two pin faces look at each other (E->W, N->S ...): travel axis = the face normal
            corner    perpendicular faces (an L): no jog by construction, bit order still matters
            uturn     both pins on faces looking the same way, or the load lies behind the driver's face: the bus has to
                      wrap around a tile (reported, WARN)
            area      a pin that is not on a face of its macro (area pin, PHY bump field): length only
  jog       straight: |offset perpendicular to the travel axis| per bit: max / mean / min
  order     preserved / reversed / interleaved (share of bit pairs that cross); corner bundles: nested or not
  length    pin-to-pin Manhattan per bit: max / mean
  gap       distance between the two faces along the travel axis (the channel the jog has to be made in)
  jog_cross the largest number of the bundle's jog wires crossing one line parallel to the travel axis
  jog_cut   jog_cross / (CAP_PER_UM x gap): the share of the channel's perpendicular tracks the jog alone takes.

Capacity is the die leads' cut rule (results/arch/qwen_tp8_1012/cuts.py usable(), channel case): the die layer at 75 %
(M8 or M9, pitch 80 nm), M6 / M7 at 75 % (64 nm) and M4 / M5 at 50 % (48 nm) = 31.51 tracks per um of channel for
either direction.

Verdict per bundle
  WARN  max jog > WARN_UM (20 um), or bit order not preserved, or kind uturn
  FAIL  jog_cut > CUT_LIMIT (0.60, the top of the owner's 0.55-0.60 cut rule: the jog ALONE fills the channel, before any
        through traffic), or an abutted bundle (gap < ABUT_UM) with a jog above one track.
FAIL_UM (36 um) is the same rule as one length for checks that see only one end (slot_fit: a new tile's planned pin
range against its contract slot span): the contract's minimum channel is 20 um = 630 perpendicular tracks, 0.60 of them =
378 jog wires; a bus at the relay pin pitch (2 tracks, 0.096 um a bit) shifted by J puts J / 0.096 wires across the cut,
so J = 378 x 0.096 = 36.3 um fills it.  20 um (WARN) is the same sum at one track a bit (18.1 um) and half of it at two.

Library: analyze(insts, buses, lef_texts, names=None, ...) -> record;  insts: objects with name / master / x / y /
orient (the die generators' Inst), buses: (bus id, class, bits, [(inst, port), ...]) with the driver first, names(inst,
port, bits) -> the pin name of every bit (default: `port[lo + i]` with the generators' `port[lo:hi]` slices).
range_jog(lo, hi, slot_lo, slot_hi) is the one-ended form used by slot_fit.

CLI:  pin_align.py PLAN.json[.gz] --lef A.lef [--lef B.lef ...] [--out REC.json] [--warn-um 20] [--cut-limit 0.6]
      PLAN = {"insts": [[name, master, x, y, orient], ...], "buses": [[id, class, bits, [[inst, port], ...]], ...],
              "pins": {"<master>|<port>": [pin names]} (optional explicit bit -> pin table)}
      exit 0 PASS (warnings allowed) / 1 FAIL / 2 usage.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import sys
from pathlib import Path

SCHEMA = "opentallas.pin_align.v1"
WARN_UM = 20.0
CUT_LIMIT = 0.60
ABUT_UM = 1.0
TRACK_UM = 0.048
PITCH_UM = {"M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064, "M8": 0.080, "M9": 0.080}
# cuts.py usable(), channel case: die layer 75 % + M6/M7 75 % + M4/M5 50 % (same sum for both directions)
CAP_PER_UM = 0.75 / PITCH_UM["M8"] + 0.75 / PITCH_UM["M6"] + 0.50 / PITCH_UM["M4"]
MIN_CHANNEL_UM = 20.0            # tools/hier_contract/schema.md: >= 20 um channels
RELAY_PIN_PITCH_UM = 0.096       # contract relay_masters: 2 tracks a bit
FAIL_UM = round(CUT_LIMIT * CAP_PER_UM * MIN_CHANNEL_UM * RELAY_PIN_PITCH_UM)     # 36
EXEMPT_CLS = ("clock_trunk", "reset", "reset_tree", "clock", "col_clock", "col_reset", "fclk", "top_in")
ORI = {"R0": "N", "MY": "FN", "MX": "FS", "R180": "S", "N": "N", "FN": "FN", "FS": "FS", "S": "S"}
NORMAL = {"E": (1, 0), "W": (-1, 0), "N": (0, 1), "S": (0, -1)}
FLIP_X = {"E": "W", "W": "E", "N": "N", "S": "S", None: None}
FLIP_Y = {"N": "S", "S": "N", "E": "E", "W": "W", None: None}
EPS = 0.0015
JOG_BINS = (0.048, 5.0, 20.0, 36.0, 100.0)                       # um: straight-bundle max jog histogram edges
JOG_BINS_LABEL = ("<= 1 track", "<= 5", "<= 20", "<= 36", "<= 100", "> 100")
_PSL = re.compile(r"^(.*)\[(\d+):(\d+)\]$")


# ------------------------------------------------------------------------------------------------------------ LEF
def read_pins(lef_texts, want=None):
    """{macro: (w, h, {pin: (cx, cy, face, layer)})}: per pin the rect on a macro face (else its first rect)"""
    out = {}
    for t in lef_texts:
        m = pin = None
        rects = []
        layer = None
        skip = False
        for line in t.splitlines():
            s = line.split()
            if not s:
                continue
            k = s[0]
            if k == "MACRO":
                m = s[1]
                skip = want is not None and m not in want
                if not skip:
                    out[m] = [0.0, 0.0, {}]
                pin = None
            elif m is None or skip:
                if k == "END" and len(s) > 1 and s[1] == m:
                    m = None
                continue
            elif k == "SIZE":
                out[m][0], out[m][1] = float(s[1]), float(s[3])
            elif k == "PIN":
                pin, rects, layer = s[1], [], None
            elif k == "OBS":
                pin = None
            elif pin is not None and k == "LAYER":
                layer = s[1]
            elif pin is not None and k == "RECT":
                v = [x for x in s[1:] if x not in ("MASK", ";")]
                try:
                    x0, y0, x1, y1 = map(float, v[-4:])
                except ValueError:
                    continue
                rects.append((layer, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
            elif k == "END" and len(s) > 1:
                if pin is not None and s[1] == pin:
                    if rects:
                        out[m][2][pin] = rects
                    pin = None
                elif s[1] == m:
                    m = None
    for m, rec in out.items():
        W, H, pp = rec
        for p, rects in pp.items():
            best = None
            for r in rects:
                f = _face(r, W, H)
                if f:
                    best = (r, f)
                    break
            r, f = best or (rects[0], None)
            pp[p] = ((r[1] + r[3]) / 2, (r[2] + r[4]) / 2, f, r[0])
        out[m] = (W, H, pp)
    return out


def _face(r, W, H):
    _, x0, y0, x1, y1 = r
    if y0 <= EPS:
        return "S"
    if y1 >= H - EPS:
        return "N"
    if x0 <= EPS:
        return "W"
    if x1 >= W - EPS:
        return "E"
    return None


def place(it, w, h, p):
    """pin (cx, cy, face, layer) of the master -> (X, Y, face, layer) in the die frame"""
    px, py, f, lay = p
    o = ORI.get(it.orient, "N")
    if o == "S":
        px, py, f = w - px, h - py, FLIP_X[FLIP_Y[f]]
    elif o == "FN":
        px, f = w - px, FLIP_X[f]
    elif o == "FS":
        py, f = h - py, FLIP_Y[f]
    return it.x + px, it.y + py, f, lay


def default_names(inst, port, bits):
    mm = _PSL.match(port)
    base, lo = (mm.group(1), int(mm.group(2))) if mm else (port, 0)
    return [f"{base}[{lo + i}]" for i in range(bits)]


def port_base(port):
    mm = _PSL.match(port)
    return mm.group(1) if mm else port


# -------------------------------------------------------------------------------------------------------- geometry
def inversions(seq):
    """number of pairs i < j with seq[i] > seq[j] (merge sort)"""
    n = len(seq)
    if n < 2:
        return 0
    a, tmp, inv, w = list(seq), [0] * n, 0, 1
    while w < n:
        for lo in range(0, n, 2 * w):
            mid, hi = min(lo + w, n), min(lo + 2 * w, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                if a[i] <= a[j]:
                    tmp[k] = a[i]
                    i += 1
                else:
                    tmp[k] = a[j]
                    j += 1
                    inv += mid - i
                k += 1
            while i < mid:
                tmp[k] = a[i]
                i += 1
                k += 1
            while j < hi:
                tmp[k] = a[j]
                j += 1
                k += 1
        a, tmp = tmp, a
        w *= 2
    return inv


def order_of(ka, kb):
    """bit order of a bundle from the two per-bit keys: ('preserved' | 'reversed' | 'interleaved', crossing pair share)"""
    n = len(ka)
    if n < 2:
        return "preserved", 0.0
    idx = sorted(range(n), key=lambda i: (ka[i], kb[i]))
    seq = [kb[i] for i in idx]
    pairs = n * (n - 1) // 2
    inv = inversions(seq)
    if inv == 0:
        return "preserved", 0.0
    # ties on the driver side are sorted to the preserving order above, so a full reversal is every strict pair
    if inversions([-v for v in seq]) == 0:
        return "reversed", 1.0
    return "interleaved", inv / pairs


def max_cross(lo, hi):
    """largest number of closed intervals [lo, hi] (hi - lo > one track) containing one point"""
    ev = []
    for a, b in zip(lo, hi):
        if b - a > TRACK_UM:
            ev.append((a, 1))
            ev.append((b, -1))
    ev.sort(key=lambda e: (e[0], -e[1]))
    cur = best = 0
    for _, d in ev:
        cur += d
        best = max(best, cur)
    return best


def bundle(A, B, warn_um=WARN_UM, cut_limit=CUT_LIMIT, cap_per_um=CAP_PER_UM):
    """A, B: per-bit (X, Y, face, layer) of the driver and the load pins (same length >= 1) -> the bundle record"""
    n = len(A)
    fa = collections.Counter(a[2] for a in A).most_common(1)[0][0]
    fb = collections.Counter(b[2] for b in B).most_common(1)[0][0]
    la = collections.Counter(a[3] for a in A).most_common(1)[0][0]
    lb = collections.Counter(b[3] for b in B).most_common(1)[0][0]
    L = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(A, B)]
    rec = {"bits": n, "face": [fa, fb], "layer": [la, lb], "len_max": round(max(L), 3), "len_mean": round(sum(L) / n, 3)}
    why_w, why_f = [], []
    if fa is None or fb is None:
        rec.update(kind="area", order="n/a")
        return dict(rec, verdict="OK", why=[])
    na, nb = NORMAL[fa], NORMAL[fb]
    t = 0 if na[0] else 1                       # travel axis of the driver face normal
    p = 1 - t
    ahead = sum((b[t] - a[t]) * na[t] for a, b in zip(A, B)) / n      # > 0: the load lies in front of the driver face
    if na[0] == -nb[0] and na[1] == -nb[1]:
        kind = "straight" if ahead >= -EPS else "uturn"
    elif na == nb:
        kind = "uturn"
    else:
        tb = 0 if nb[0] else 1
        behind = sum((a[tb] - b[tb]) * nb[tb] for a, b in zip(A, B)) / n
        kind = "corner" if (ahead >= -EPS and behind >= -EPS) else "uturn"
    rec["kind"] = kind
    if kind == "straight":
        jog = [abs(a[p] - b[p]) for a, b in zip(A, B)]
        gap = abs(ahead)
        order, share = order_of([a[p] for a in A], [b[p] for b in B])
        cross = max_cross([min(a[p], b[p]) for a, b in zip(A, B)], [max(a[p], b[p]) for a, b in zip(A, B)])
        cut = cross / (cap_per_um * gap) if gap >= ABUT_UM else None
        rec.update(axis="xy"[t], gap=round(gap, 3), jog_max=round(max(jog), 3), jog_mean=round(sum(jog) / n, 3),
                   jog_min=round(min(jog), 3), order=order, cross_share=round(share, 4), jog_cross=cross,
                   jog_cut=round(cut, 4) if cut is not None else None)
        if max(jog) > warn_um:
            why_w.append(f"jog {max(jog):.1f} um > {warn_um:g}")
        if order != "preserved":
            why_w.append(f"bit order {order}" + (f" ({share:.0%} of pairs cross)" if order == "interleaved" else ""))
        if cut is not None and cut > cut_limit:
            why_f.append(f"jog cut {cut:.2f} > {cut_limit:g}: {cross} jog wires in a {gap:.1f} um channel "
                         f"({cap_per_um * gap:.0f} tracks)")
        if cut is None and max(jog) > TRACK_UM + EPS:
            why_f.append(f"abutted faces (gap {gap:.3f} um) with a jog of {max(jog):.3f} um")
    elif kind == "corner":
        # an L (driver wire leaves along its normal, turns once, enters the load face) does not cross another bit of the
        # bundle when the pin nearer to the load's face plane lands on the load pin nearer to the driver's face plane
        ka = [(a[p] - sum(b[p] for b in B) / n) * nb[p] for a in A]      # distance of the driver pin from the load face
        kb = [(b[t] - sum(a[t] for a in A) / n) * na[t] for b in B]      # distance of the load pin from the driver face
        order, share = order_of(ka, kb)
        rec.update(order="preserved" if order == "preserved" else order, cross_share=round(share, 4))
        if order != "preserved":
            why_w.append(f"corner bundle not nested: {order}" + (f" ({share:.0%} of pairs cross)" if order == "interleaved" else ""))
            span = max(max(ka) - min(ka), max(kb) - min(kb))
            cut = n * share / (cap_per_um * span) if span >= ABUT_UM else None
            rec["jog_cut"] = round(cut, 4) if cut is not None else None
            if cut is not None and cut > cut_limit:
                why_f.append(f"corner crossing cut {cut:.2f} > {cut_limit:g}")
    else:
        rec.update(order="n/a")
        why_w.append(f"u-turn: driver face {fa}, load face {fb}, load {'behind' if ahead < 0 else 'beside'} the driver face")
    rec.update(verdict="FAIL" if why_f else "WARN" if why_w else "OK", why=why_f + why_w)
    return rec


def range_jog(lo, hi, slot_lo, slot_hi):
    """one-ended form (slot_fit): the largest distance a pin placed anywhere in [lo, hi] can sit outside the slot span"""
    return max(0.0, slot_lo - lo, hi - slot_hi)


# --------------------------------------------------------------------------------------------------------- analyze
def _strip(s):
    return re.sub(r"\d+", "#", s)


def analyze(insts, buses, lef_texts, names=None, exempt_cls=EXEMPT_CLS, warn_um=WARN_UM, cut_limit=CUT_LIMIT,
            cap_per_um=CAP_PER_UM, top=200, pins=None):
    """the die record from LEF texts: totals, per-class rows (driver master.port -> load master.port), the flagged
    bundles.  Later LEF texts override earlier ones (generated abstracts first, published views after)."""
    names = names or default_names
    if pins is None:
        pins = read_pins(lef_texts, {it.master for it in insts})

    def locate(it, port, bits):
        w, h, pp = pins.get(it.master, (0.0, 0.0, {}))
        nm = names(it, port, bits)
        out = []
        for i in range(bits):
            q = pp.get(nm[i]) if i < len(nm) else None
            if q is None and bits == 1:
                q = pp.get(port_base(port))
            out.append(None if q is None else place(it, w, h, q))
        return out
    return analyze_points(insts, buses, locate, exempt_cls, warn_um, cut_limit, cap_per_um, top)


def analyze_points(insts, buses, locate, exempt_cls=EXEMPT_CLS, warn_um=WARN_UM, cut_limit=CUT_LIMIT,
                   cap_per_um=CAP_PER_UM, top=200):
    """the die record from a pin locator: locate(inst, port, bits) -> per bit (X, Y, face, layer) in the die frame, or
    None for a bit without a pin (the generators' own pin tables: tools/die_top_lint.py pin_align_record)"""
    by = {it.name: it for it in insts}
    rows, missing, miss_ex = [], 0, collections.Counter()
    for bid, cls, bits, eps in buses:
        if cls.split('@')[0] in exempt_cls:
            continue
        ie = [(i, q) for i, q in eps if i in by]
        if len(ie) < 2:
            continue
        (da, dp), loads = ie[0], ie[1:]
        ia = by[da]
        pa = locate(ia, dp, bits)
        for li, lp in loads:
            if li == da:
                continue
            ib = by[li]
            pb = locate(ib, lp, bits)
            A, B = [], []
            for i in range(bits):
                qa = pa[i] if i < len(pa) else None
                qb = pb[i] if i < len(pb) else None
                if qa is None or qb is None:
                    missing += 1
                    if qa is None:
                        miss_ex[f"{ia.master}.{port_base(dp)}"] += 1
                    if qb is None:
                        miss_ex[f"{ib.master}.{port_base(lp)}"] += 1
                    continue
                A.append(qa)
                B.append(qb)
            if not A:
                continue
            r = bundle(A, B, warn_um, cut_limit, cap_per_um)
            r.update(bus=str(bid), cls=cls, drv=da, drv_master=ia.master, drv_port=port_base(dp), load=li,
                     load_master=ib.master, load_port=port_base(lp),
                     at=[round(A[0][0]), round(A[0][1]), round(B[0][0]), round(B[0][1])])
            rows.append(r)
    return summarise(rows, missing, miss_ex, warn_um, cut_limit, cap_per_um, top)


def summarise(rows, missing=0, miss_ex=None, warn_um=WARN_UM, cut_limit=CUT_LIMIT, cap_per_um=CAP_PER_UM, top=200):
    cls = {}
    for r in rows:
        key = (r["drv_master"], r["drv_port"], r["load_master"], r["load_port"], r["kind"])
        c = cls.setdefault(key, dict(drv=f"{r['drv_master']}.{r['drv_port']}", load=f"{r['load_master']}.{r['load_port']}",
                                     kind=r["kind"], cls=r["cls"], bundles=0, bits=0, face=r["face"], layer=r["layer"],
                                     jog_max=0.0, jog_sum=0.0, len_max=0.0, len_sum=0.0, gap_min=None, jog_cut_max=None,
                                     order=collections.Counter(), verdict=collections.Counter(), example=None, why=None))
        c["bundles"] += 1
        c["bits"] += r["bits"]
        c["jog_max"] = max(c["jog_max"], r.get("jog_max", 0.0))
        c["jog_sum"] += r.get("jog_mean", 0.0) * r["bits"]
        c["len_max"] = max(c["len_max"], r["len_max"])
        c["len_sum"] += r["len_mean"] * r["bits"]
        if r.get("gap") is not None:
            c["gap_min"] = r["gap"] if c["gap_min"] is None else min(c["gap_min"], r["gap"])
        if r.get("jog_cut") is not None:
            c["jog_cut_max"] = r["jog_cut"] if c["jog_cut_max"] is None else max(c["jog_cut_max"], r["jog_cut"])
        c["order"][r["order"]] += 1
        c["verdict"][r["verdict"]] += 1
        rank = {"OK": 0, "WARN": 1, "FAIL": 2}
        if c["example"] is None or (rank[r["verdict"]], r.get("jog_max", 0.0)) > (rank[c["example"]["verdict"]], c["example"].get("jog_max", 0.0)):
            c["example"] = {k: r[k] for k in ("bus", "drv", "load", "at", "verdict") if k in r}
            c["example"]["jog_max"] = r.get("jog_max", 0.0)
            c["why"] = r["why"]
    out = []
    for c in cls.values():
        c["jog_mean"] = round(c.pop("jog_sum") / c["bits"], 3)
        c["len_mean"] = round(c.pop("len_sum") / c["bits"], 3)
        c["order"] = dict(c["order"])
        c["verdict"] = dict(c["verdict"])
        c["worst"] = "FAIL" if c["verdict"].get("FAIL") else "WARN" if c["verdict"].get("WARN") else "OK"
        out.append(c)
    out.sort(key=lambda c: ({"FAIL": 0, "WARN": 1, "OK": 2}[c["worst"]], -(c["jog_cut_max"] or 0), -c["jog_max"], -c["bits"]))
    v = collections.Counter(r["verdict"] for r in rows)
    hist = collections.OrderedDict((k, dict(bundles=0, bits=0)) for k in JOG_BINS_LABEL)
    for r in rows:
        if r["kind"] == "straight":
            h = hist[JOG_BINS_LABEL[sum(r["jog_max"] > e for e in JOG_BINS)]]
            h["bundles"] += 1
            h["bits"] += r["bits"]
    kinds = collections.Counter(r["kind"] for r in rows)
    orders = collections.Counter(r["order"] for r in rows)
    jog20 = [r for r in rows if r.get("jog_max", 0.0) > warn_um]
    bad_order = [r for r in rows if r["order"] in ("reversed", "interleaved")]
    flagged = sorted((r for r in rows if r["verdict"] != "OK"),
                     key=lambda r: ({"FAIL": 0, "WARN": 1}[r["verdict"]], -(r.get("jog_cut") or 0), -r.get("jog_max", 0.0)))
    return {"schema": SCHEMA, "warn_um": warn_um, "cut_limit": cut_limit, "cap_per_um": round(cap_per_um, 3), "fail_um": FAIL_UM,
            "bundles": len(rows), "bits": sum(r["bits"] for r in rows), "bits_without_pin": missing,
            "ports_without_pin": dict((miss_ex or collections.Counter()).most_common(40)),
            "verdict": "FAIL" if v.get("FAIL") else "PASS", "by_verdict": dict(v), "by_kind": dict(kinds), "by_order": dict(orders),
            "jog_over_warn": {"bundles": len(jog20), "bits": sum(r["bits"] for r in jog20)},
            "order_not_preserved": {"bundles": len(bad_order), "bits": sum(r["bits"] for r in bad_order)},
            "jog_max": max((r.get("jog_max", 0.0) for r in rows), default=0.0),
            "jog_hist_um": hist, "len_max": max((r["len_max"] for r in rows), default=0.0),
            "len_mean": round(sum(r["len_mean"] * r["bits"] for r in rows) / max(1, sum(r["bits"] for r in rows)), 1),
            "classes": out, "classes_flagged": sum(1 for c in out if c["worst"] != "OK"), "flagged": flagged[:top],
            "flagged_total": len(flagged)}


def line(rec):
    return ("OT_PIN_ALIGN %s bundles %d bits %d: FAIL %d WARN %d (jog > %g um: %d bundles / %d bits, max %.1f um; order not "
            "preserved: %d bundles; u-turn %d); bits without pin %d" %
            (rec["verdict"], rec["bundles"], rec["bits"], rec["by_verdict"].get("FAIL", 0), rec["by_verdict"].get("WARN", 0),
             rec["warn_um"], rec["jog_over_warn"]["bundles"], rec["jog_over_warn"]["bits"], rec["jog_max"],
             rec["order_not_preserved"]["bundles"], rec["by_kind"].get("uturn", 0), rec["bits_without_pin"]))


def gate_mode():
    """OT_PIN_ALIGN_GATE: fail (default; a FAIL bundle stops the generator's check step) | warn | off"""
    import os
    g = os.environ.get("OT_PIN_ALIGN_GATE", "fail").strip().lower()
    return g if g in ("fail", "warn", "off") else "fail"


class _I:
    __slots__ = ("name", "master", "x", "y", "orient")

    def __init__(self, name, master, x, y, orient="R0", *_):
        self.name, self.master, self.x, self.y, self.orient = name, master, float(x), float(y), orient


def load_plan(path):
    p = Path(path)
    d = json.loads(gzip.open(p, "rt").read() if p.suffix == ".gz" else p.read_text())
    insts = [_I(*r[:5]) if not isinstance(r, dict) else _I(r["name"], r["master"], r["x"], r["y"], r.get("orient", "R0"))
             for r in d["insts"]]
    buses = [(b[0], b[1], b[2], [tuple(e[:2]) for e in b[3]]) for b in d["buses"]]
    table = d.get("pins") or {}

    def names(inst, port, bits):
        mm = _PSL.match(port)
        base, lo = (mm.group(1), int(mm.group(2))) if mm else (port, 0)
        t = table.get(f"{inst.master}|{base}")
        if t is not None:
            return t[lo:lo + bits]
        return [f"{base}[{lo + i}]" for i in range(bits)]
    return insts, buses, names, d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--lef", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--warn-um", type=float, default=WARN_UM)
    ap.add_argument("--cut-limit", type=float, default=CUT_LIMIT)
    ap.add_argument("--top", type=int, default=200)
    a = ap.parse_args(argv)
    if not a.lef:
        print("pin_align: at least one --lef", file=sys.stderr)
        return 2
    insts, buses, names, _ = load_plan(a.plan)
    texts = [gzip.open(f, "rt").read() if f.endswith(".gz") else Path(f).read_text(errors="replace") for f in a.lef]
    rec = analyze(insts, buses, texts, names, warn_um=a.warn_um, cut_limit=a.cut_limit, top=a.top)
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(line(rec))
    for c in rec["classes"][:30]:
        if c["worst"] == "OK":
            break
        print("  %-4s %5d bundles %8d bits  jog max %7.1f mean %6.1f  cut %s  gap >= %s  %s  %s -> %s (%s)  %s" %
              (c["worst"], c["bundles"], c["bits"], c["jog_max"], c["jog_mean"], c["jog_cut_max"], c["gap_min"],
               "/".join(f"{k} {v}" for k, v in c["order"].items()), c["drv"], c["load"], c["kind"], "; ".join(c["why"] or [])))
    return 1 if rec["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
