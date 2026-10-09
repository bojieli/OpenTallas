#!/usr/bin/env python3
"""Floorplan margin lint (OWNER 2026-10-08, stream fp-lint): catch the floorplan failure classes BEFORE a route is spent.

Run by the closure loop right after floorplan / IO placement and before global placement (ORFS PRE GLOBAL_PLACE, on
3_2_place_iop.odb: macros, PDN, rows, blockages and pins are final, std cells are not placed yet).  tools/fp_margin_lint.tcl
dumps the geometry; this file judges it.  A FAIL stops the flow with "FLOORPLAN_MARGIN: <reasons>" and the loop finishes
the job with verdict FLOORPLAN_MARGIN (spec "fp_lint": false opts out; "fp_lint": {"set": {"util_max": 0.62}} overrides).

Checks (each calibrated on 2026-10-08's failing vs closed blocks, see THRESHOLDS and docs in REDESIGN_RULES.md):
  util          (std-cell + macro area) / core area > 0.60, or > 0.65 with a hold-buffer allowance (1 BUFx2 per flop:
                qfd_link_rx128 77.5% -> 146k HM-50 hold buffers -> DPL-0033; s81b pq-rootcam 85.8%; hbm_coll_port 67%)
  pin_density   signal pins per um per (edge, layer) in a sliding window > pin_density_max (hbm_vm8 seam: 20.8 failed,
                2.6-7.8 closed)
  pin_pdn       (WARNING by default) a signal pin within 1 track of a PDN strap / via stack on the same or an adjacent
                layer.  Recalibrated 2026-10-08 21:00: the s81 hend hx_W pinreg and hl_E1 blocks carry the SAME strap
                geometry as the failed hx_E pinreg (M5 strap 0.048 um off the full M4 column, identical PDN via stacks)
                and closed DRC 0, so it does not separate failure from closure (hx_E is still flagged by util 80.5%).
                pin_pdn_fail=1 restores the FAIL.
  pin_width     a pin shape whose width is not on its layer's WIDTHTABLE AND whose via-down access is blocked: a PDN
                strap on the adjacent layer overlaps / sits within one pitch of the pin footprint, so the router must
                enter on the pin layer with a min-width stub (RECTONLY DRC).  hbm_vm8 M7 ck pin 0.064 over the M6
                strap -> DRC 3 (FAIL); hbm_svc_SE_s0 r18b, same 0.064 ck pin with M6 1.43 um away -> DRC 0 (warning).
  channel       nets that must cross a cut line (fixed terminals: macro pins + block pins) exceed the cut's routing
                tracks (layers >= M4 not blocked by a macro, channel_usable of the pitch) (hbm_attn_tile r23 middle channel)
  macro_edge    a macro within macro_edge_um of a die edge that has signal pins behind it which the macro does not
                serve (hbm_coll_port: SRAMs ringed the edge, 2,736 edge pins had to cross them)
  sliver        a gap 0 < g < sliver_um between macros (pin banks) with placement rows in it and no hard placement
                blockage over them (hbm_attn_tile r23h/r23hq: 3.2 um bank gaps -> DPL-0033)
  bank_distance a macro wired straight to block pins sits more than bank_dist_um from their centroid
                (hbm_attn_tile r23h: k / ci / cf pin banks 215-260 um off their pins -> 503k repair buffers)
  capture (warn) macro outputs captured by a single flop that is not pinned beside the macro (qfd_tile rp1 class:
                ROM caps placed 400-600 um from their pins; fix rom_cap_at_pins.tcl)
Die generators (die_top_lint.py, dsrom_s81_fulldie.py, hbm_accel_die_fp.py) use relay_lint / pin_density /
sliver_gaps from here: a relay segment beyond the per-corner reach (504 um SS) or a relay on the far side of its driver.

    fp_margin_lint.py check DUMP.json [--out REPORT.json] [--set key=value ...] [--warn-only]
    fp_margin_lint.py metrics DUMP.json ...            # calibration table (no verdict)
Exit: 0 PASS (warnings allowed), 3 FAIL (prints FLOORPLAN_MARGIN: ...), 2 tool error.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

THRESHOLDS = {
    "util_max": 0.60,             # (std + macro) / core
    "util_hold_max": 0.65,        # ... + hold-buffer allowance
    "hold_buf_per_flop": 1.0,     # BUFx2 per flop (HM-50 mm repair on back-to-back flop arrays: 1-2.2 per flop)
    # signal pins / um / (edge, layer) over a 100 um window.  Calibrated 2026-10-08: hbm_vm8 seam 20.8 (3,166 bits on
    # one M5 track each over 152 um) FAILED GRT; closed blocks reach 10.4 sustained (hfd_svc SE/SW E-face M4, every
    # other track over 200 um) and 20.8 only in short columns (s81 hend hx/hl 567 pins, capt_ctl: <= 10.4 at 100 um).
    # The owner's DESIGN target is <= 6 (warning above it); the fail line sits between 10.4 (closed) and 20.8 (failed).
    "pin_density_max": 12.0,
    "pin_density_target": 6.0,
    "pin_density_window_um": 100.0,
    "pin_density_min_pins": 1,
    # pin <-> PDN strap / via stack on the same or an adjacent layer within 1 track of the pin layer, on a FULL-DENSITY
    # pin column (>= 90% of the tracks within +-1 um hold a pin: no free track to jog around the strap's via stack).
    # s81 hend hx_E: M5 strap 0.048 um from the full M4 i[] column -> DRC 4 for 60 iterations.  Half-density columns
    # beside the same strap (hfd_svc_SW 10.4 b/um, idxq / attn 5.2) closed: those are warnings.
    "pin_pdn_tracks": 1.0,
    "pin_pdn_fail": 0.0,          # 0 = warning only (geometry closed DRC 0 in hx_W pinreg / hl_E1); 1 = FAIL
    "pin_width_access_pitches": 1.0,  # off-table pin FAILS only with adjacent-layer PDN within this many pitches
    "pin_pdn_full_frac": 0.9,
    "channel_usable": 0.5,        # usable share of a cut's tracks (PDN, std-cell local routing)
    "channel_min_layer": 4,       # long-haul layers (M4+) carry the crossing nets
    "macro_edge_um": 10.0,        # a macro this close to a die edge shadows the pins behind it
    "macro_edge_pins": 32,        # shadowed signal pins (not served by that macro) that fail the check
    "sliver_um": 12.0,
    "sliver_min_row_area_um2": 2.0,
    "sliver_blocked_frac": 0.9,
    "bank_dist_um": 100.0,        # relay rule: last segment to a die pin <= ~100 um
    "bank_min_pins": 8,
    "capture_warn_um": 50.0,
    "capture_warn_count": 256,
}

# ASAP7 LEF58_WIDTHTABLE (asap7_tech_1x_201209.lef), used when the tech LEF is not readable
ASAP7_WIDTHS = {
    "M2": [0.018, 0.09, 0.162, 0.234, 0.306, 0.378], "M3": [0.018, 0.09, 0.162, 0.234, 0.306, 0.378],
    "M4": [0.024, 0.12, 0.216, 0.312, 0.408],
    "M5": [0.024, 0.12, 0.216, 0.312, 0.408, 0.504, 0.6, 0.696, 0.792, 0.888, 0.984],
    "M6": [0.032, 0.16, 0.288, 0.416, 0.544], "M7": [0.032, 0.16, 0.288, 0.416, 0.544],
}
FLOP_RE = re.compile(r"^(ASYNC_)?(S?DFF|SDF[HL]|DHL|DLL)", re.I)
PHYS_RE = re.compile(r"TAPCELL|FILL|DECAP|ENDCAP|WELLTAP|ANTENNA", re.I)
PHYS_TYPES = ("CORE_WELLTAP", "CORE_SPACER", "CORE_ANTENNACELL", "ENDCAP", "CORE_FEEDTHRU")
EDGES = ("W", "E", "S", "N")


# ------------------------------------------------------------------------------------------------ geometry helpers
def rect_gap(a, b):
    """edge-to-edge distance between two rects [x0,y0,x1,y1] (0 when they touch or overlap)"""
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


def pt_rect_dist(x, y, r):
    dx = max(r[0] - x, 0.0, x - r[2])
    dy = max(r[1] - y, 0.0, y - r[3])
    return math.hypot(dx, dy)


def inter_area(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def union_len(ivs):
    tot, cur0, cur1 = 0.0, None, None
    for a, b in sorted(ivs):
        if cur1 is None or a > cur1:
            if cur1 is not None:
                tot += cur1 - cur0
            cur0, cur1 = a, b
        else:
            cur1 = max(cur1, b)
    if cur1 is not None:
        tot += cur1 - cur0
    return tot


def edge_of(die, r):
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    d = {"W": cx - die[0], "E": die[2] - cx, "S": cy - die[1], "N": die[3] - cy}
    e = min(d, key=d.get)
    return e, (cy if e in "WE" else cx)


# ------------------------------------------------------------------------------------- reusable checks (die tools)
def pin_density(pins, window_um=20.0, min_pins=64):
    """pins: iterable of (edge, layer, pos_um).  -> {(edge, layer): (bits_per_um, n_in_window, pos_lo, n_total)}.
    Density = max pins in any window_um span / window_um; a group with fewer than min_pins pins in total is a local
    column the router escapes (reported with density 0)."""
    by = defaultdict(list)
    for e, layer, p in pins:
        by[(e, layer)].append(p)
    out = {}
    for k, ps in by.items():
        ps.sort()
        best, lo, j = 0, ps[0], 0
        for i in range(len(ps)):
            while ps[i] - ps[j] > window_um:
                j += 1
            if i - j + 1 > best:
                best, lo = i - j + 1, ps[j]
        dens = best / window_um if len(ps) >= min_pins else 0.0
        out[k] = (dens, best, lo, len(ps))
    return out


def relay_lint(chains, reach_um=504.0, back_slack_um=20.0, metric="manhattan"):
    """Die relay chains: chains = {name: [(x, y), ...]} driver -> relays... -> load (um).
    Violations: a segment longer than reach_um (per-corner wire reach, SS 504 um at 1.2 GHz), or a relay farther from
    the load than its own driver (+ back_slack_um): the relay sits on the far side of its driver (s81 r3 hop relays,
    776-906 um backwards)."""
    def d(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) if metric == "manhattan" else math.hypot(a[0] - b[0], a[1] - b[1])
    bad = []
    for name, pts in chains.items():
        if len(pts) < 2:
            continue
        tgt = pts[-1]
        for i in range(1, len(pts)):
            seg = d(pts[i - 1], pts[i])
            if seg > reach_um:
                bad.append({"chain": name, "kind": "reach", "seg": i, "um": round(seg, 1), "limit": reach_um})
            if i < len(pts) - 1 and d(pts[i], tgt) > d(pts[i - 1], tgt) + back_slack_um:
                bad.append({"chain": name, "kind": "far_side", "seg": i, "um": round(d(pts[i], tgt) - d(pts[i - 1], tgt), 1)})
    return bad


def die_margin(insts, buses, relay_kinds, reach_um=504.0, back_slack_um=20.0, stages=None, sliver_um=0.0, limit=20):
    """Die generator lint (dsrom_s81_fulldie / hbm_accel_die_fp / die_top_lint).  insts: objects with name, kind, x, y,
    w, h; buses: (bid, cls, bits, [(inst, port), ...]) with eps[0] the driver.  Every driver -> relay ... -> load chain
    through instances of relay_kinds is checked:
      reach     a register-to-register segment (nearest points, Manhattan) longer than reach_um after the segment's
                priced intermediate wire stages (stages(bid, L) -> register hops, None = 1 hop per bus)
      far_side  a relay farther from the next chain point than its own driver (+ back_slack_um)
    and (sliver_um > 0) gaps 0 < g < sliver_um between die instances (reported, die tops place no std-cell rows)."""
    by = {it.name: it for it in insts}

    def c(it):
        return (it.x + it.w / 2, it.y + it.h / 2)

    def near(it, q):
        return (min(max(q[0], it.x), it.x + it.w), min(max(q[1], it.y), it.y + it.h))

    def seg(a_, b_):
        a, b = near(a_, c(b_)), near(b_, c(a_))
        a, b = near(a_, b), near(b_, a)
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def mh(p, q):
        return abs(p[0] - q[0]) + abs(p[1] - q[1])
    succ = defaultdict(list)           # inst -> [(bid, load inst)]
    pred = defaultdict(set)            # inst -> driver insts
    for bid, cls, bits, eps in buses:
        if len(eps) < 2 or eps[0][0] not in by:
            continue
        for e in eps[1:]:
            if e[0] in by and e[0] != eps[0][0]:
                succ[eps[0][0]].append((bid, e[0]))
                pred[e[0]].add(eps[0][0])
    reach_bad, far_bad, n_chains, done = [], [], 0, set()
    for d0 in list(succ):
        if by[d0].kind in relay_kinds:
            continue
        stack = [([d0, r0], [bid0]) for bid0, r0 in succ[d0] if by[r0].kind in relay_kinds]
        while stack and n_chains < 500000:
            path, bids = stack.pop()
            cur = path[-1]
            if by[cur].kind in relay_kinds:          # extend through the relay (every branch of a relay tree)
                for b_, nx in succ.get(cur, ()):
                    if nx not in path:
                        stack.append((path + [nx], bids + [b_]))
                continue
            if tuple(path) in done:                  # a data bus and its forwarded clock follow the same relays
                continue
            done.add(tuple(path))
            n_chains += 1
            for i in range(1, len(path)):
                a_, b_ = by[path[i - 1]], by[path[i]]
                L = seg(a_, b_)
                hops = max(1, stages(bids[i - 1], L)) if stages else 1
                if L / hops > reach_um:
                    reach_bad.append(dict(chain=f'{path[0]}->{path[-1]}', seg=f'{path[i - 1]}->{path[i]}', um=round(L, 1),
                                          hops=hops))
                if i < len(path) - 1 and len({x for _, x in succ.get(path[i], ())}) == 1 and len(pred[path[i]]) == 1:
                    # far side (point-to-point relays only: a multicast / gather tree node serves several branches): the relay is farther from the NEXT chain point than its own driver (a ring / detour
                    # route still advances point to point; the s81 r3 hop relays did not)
                    nx = c(by[path[i + 1]])
                    if mh(c(b_), nx) > mh(c(a_), nx) + back_slack_um:
                        far_bad.append(dict(chain=f'{path[0]}->{path[-1]}', relay=path[i],
                                            back_um=round(mh(c(b_), nx) - mh(c(a_), nx), 1)))
    out = dict(chains=n_chains, reach_um=reach_um, reach_violations=len(reach_bad), far_side_relays=len(far_bad),
               reach_examples=sorted(reach_bad, key=lambda r: -r['um'])[:limit],
               far_side_examples=sorted(far_bad, key=lambda r: -r['back_um'])[:limit])
    if sliver_um > 0:
        sl = sliver_gaps([(it.name, [it.x, it.y, it.x + it.w, it.y + it.h]) for it in insts], sliver_um)
        out.update(slivers=len(sl), sliver_examples=[(a, b, round(g, 2)) for a, b, _, g in sl[:limit]])
    out['verdict'] = 'FAIL' if reach_bad or far_bad else 'PASS'
    return out


def sliver_gaps(rects, max_gap_um=12.0, min_overlap_um=1.0):
    """rects: list of (name, [x0,y0,x1,y1]).  -> list of (name_a, name_b, gap_rect, gap_um) for facing pairs whose
    gap is 0 < g < max_gap_um (the strip between them).  Grid-bucketed (scales to thousands of macros)."""
    cell = max(50.0, 4 * max_gap_um)
    grid = defaultdict(list)
    for i, (_, r) in enumerate(rects):
        for gx in range(int((r[0] - max_gap_um) // cell), int((r[2] + max_gap_um) // cell) + 1):
            for gy in range(int((r[1] - max_gap_um) // cell), int((r[3] + max_gap_um) // cell) + 1):
                grid[(gx, gy)].append(i)
    seen, out = set(), []
    for members in grid.values():
        for ai in range(len(members)):
            for bi in range(ai + 1, len(members)):
                i, j = members[ai], members[bi]
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                a, b = rects[i][1], rects[j][1]
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox >= min_overlap_um and oy < 0 and -oy < max_gap_um:          # stacked: vertical gap
                    lo, hi = (a, b) if a[3] <= b[1] else (b, a)
                    g = [max(a[0], b[0]), lo[3], min(a[2], b[2]), hi[1]]
                    out.append((rects[i][0], rects[j][0], g, -oy))
                elif oy >= min_overlap_um and ox < 0 and -ox < max_gap_um:        # side by side: horizontal gap
                    lf, rt = (a, b) if a[2] <= b[0] else (b, a)
                    g = [lf[2], max(a[1], b[1]), rt[0], min(a[3], b[3])]
                    out.append((rects[i][0], rects[j][0], g, -ox))
    return out


# --------------------------------------------------------------------------------------------- tech information
def width_tables(dump):
    lef = dump.get("env_TECH_LEF")
    tabs = {}
    if lef and Path(lef).is_file():
        cur = None
        for line in Path(lef).read_text(errors="replace").splitlines():
            m = re.match(r"\s*LAYER\s+(\S+)", line)
            if m:
                cur = m.group(1)
            m = re.search(r"WIDTHTABLE\s+([0-9.\s]+?)\s*(WRONGDIRECTION)?\s*;", line)
            if m and cur and not m.group(2):
                tabs[cur] = [float(v) for v in m.group(1).split()]
    return tabs or dict(ASAP7_WIDTHS)


def routing_range(dump, layers):
    lv = {l["name"]: l["level"] for l in layers}
    lo = lv.get(dump.get("env_MIN_ROUTING_LAYER", "M2"), 2)
    hi = lv.get(dump.get("env_MAX_ROUTING_LAYER", "M7"), 7)
    return lo, hi


# ------------------------------------------------------------------------------------------------------ the lint
def lint(dump, th=None):
    T = dict(THRESHOLDS, **(th or {}))
    die, core = dump["die"], dump["core"]
    layers = [l for l in dump["layers"] if re.match(r"^M\d+$", l["name"])]
    L = {l["name"]: l for l in layers}
    lvl = {l["name"]: l["level"] for l in layers}
    rmin, rmax = routing_range(dump, layers)
    fails, warns, met = [], [], {}

    # ---- util
    core_area = (core[2] - core[0]) * (core[3] - core[1])
    std = flops = 0.0
    buf_area = None
    for name, m in dump["masters"].items():
        if m["block"]:
            continue
        if m["type"] in PHYS_TYPES or m["type"].startswith("ENDCAP") or PHYS_RE.search(name):
            continue
        std += m["n"] * m["w"] * m["h"]
        if FLOP_RE.match(name):
            flops += m["n"]
        if re.match(r"^BUFx2_", name):
            buf_area = m["w"] * m["h"]
    if buf_area is None:
        buf_area = 0.27 * 0.27            # ASAP7 BUFx2 (0.27 x 0.27 um)
    macros = dump["macros"]
    macro_area = sum(inter_area(m["bbox"], core) for m in macros)
    hold = flops * T["hold_buf_per_flop"] * buf_area
    util = (std + macro_area) / core_area if core_area > 0 else 0.0
    util_h = (std + macro_area + hold) / core_area if core_area > 0 else 0.0
    met.update(core_um2=round(core_area, 1), std_um2=round(std, 1), macro_um2=round(macro_area, 1), flops=int(flops),
               hold_allow_um2=round(hold, 1), util=round(util, 4), util_hold=round(util_h, 4), n_macros=len(macros))
    if util > T["util_max"]:
        fails.append(("util", f"utilisation {util:.1%} > {T['util_max']:.0%} (std {std:.0f} + macro {macro_area:.0f} um2 "
                              f"in {core_area:.0f} um2): grow the outline to <= 55-60%"))
    elif util_h > T["util_hold_max"]:
        fails.append(("util", f"utilisation {util_h:.1%} with the hold-buffer allowance ({int(flops)} flops x "
                              f"{T['hold_buf_per_flop']} BUFx2) > {T['util_hold_max']:.0%}: grow the outline"))

    # ---- pins
    pins = []          # (bterm name, net, edge, layer, pos, rect)
    for name, net, sig, io, boxes in dump["bterms"]:
        if sig not in ("SIGNAL", "CLOCK"):
            continue
        for layer, r in boxes:
            e, p = edge_of(die, r)
            pins.append((name, net, e, layer, p, r))
    met["n_pins"] = len(pins)

    # density
    dens = pin_density([(e, l, p) for _, _, e, l, p, _ in pins], T["pin_density_window_um"], T["pin_density_min_pins"])
    worst = max(dens.items(), key=lambda kv: kv[1][0], default=None)
    if worst:
        (e, l), (d, n, lo, tot) = worst
        met["pin_density_max"] = round(d, 2)
        met["pin_density_at"] = f"{e} {l} @{lo:.1f} um ({n} pins / {T['pin_density_window_um']:.0f} um, {tot} on the face)"
    over = sorted(((k, v) for k, v in dens.items() if v[0] > T["pin_density_max"]), key=lambda kv: -kv[1][0])
    if over:
        txt = ", ".join(f"{e}/{l} {v[0]:.1f} b/um @{v[2]:.0f}" for (e, l), v in over[:4])
        fails.append(("pin_density", f"pin density > {T['pin_density_max']} bits/um/layer over "
                                     f"{T['pin_density_window_um']:.0f} um: {txt}: spread over the face (target <= "
                                     f"{T['pin_density_target']}) / more layers / a longer edge"))
    else:
        tgt = sorted(((k, v) for k, v in dens.items() if v[0] > T["pin_density_target"]), key=lambda kv: -kv[1][0])
        if tgt:
            txt = ", ".join(f"{e}/{l} {v[0]:.1f} b/um" for (e, l), v in tgt[:3])
            warns.append(("pin_density", f"pin density above the {T['pin_density_target']} bits/um/layer target: {txt}"))

    # widths
    tabs = width_tables(dump)
    badw, softw = [], []
    pdn_by_layer = defaultdict(list)
    for kind, l1, l2, r in dump.get("pdn_edge", []):
        if kind == "wire" and l1 in lvl:
            pdn_by_layer[lvl[l1]].append(r)
    for name, net, e, layer, p, r in pins:
        if layer not in L:
            continue
        w = (r[2] - r[0]) if L[layer]["dir"] == "VERTICAL" else (r[3] - r[1])
        tab = tabs.get(layer)
        ok = any(abs(w - t) < 5e-4 for t in tab) if tab else w >= L[layer]["width"] - 5e-4
        if w < L[layer]["width"] - 5e-4:
            ok = False
        if ok:
            continue
        # via-down / via-up access: an adjacent-layer PDN strap over (or within a pitch of) the pin footprint
        v0 = lvl[layer]
        blocked = False
        for v in (v0 - 1, v0 + 1):
            pitch = next((l["pitch"] for l in layers if l["level"] == v), L[layer]["pitch"])
            lim = T["pin_width_access_pitches"] * pitch + 1e-4
            if any(rect_gap(r, s_) <= lim for s_ in pdn_by_layer.get(v, ())):
                blocked = True
                break
        (badw if blocked else softw).append((name, layer, round(w, 4)))
    met["pin_width_illegal"] = len(badw)
    met["pin_width_offtable_accessible"] = len(softw)
    if badw:
        ex = "; ".join(f"{n} {l} w={w}" for n, l, w in badw[:4])
        fails.append(("pin_width", f"{len(badw)} pin shape(s) off the layer WIDTHTABLE with an adjacent-layer PDN strap "
                                   f"over the pin (no via access -> RECTONLY stub): {ex}"))
    if softw:
        ex = "; ".join(f"{n} {l} w={w}" for n, l, w in softw[:4])
        warns.append(("pin_width", f"{len(softw)} pin shape(s) off the WIDTHTABLE with free via access "
                                   f"(closed DRC 0 in hbm_svc_SE_s0 r18b): {ex}"))

    # pin <-> PDN clearance (same / adjacent layer)
    shapes = defaultdict(list)       # level -> rects
    for kind, l1, l2, r in dump.get("pdn_edge", []):
        if kind == "wire":
            if l1 in lvl:
                shapes[lvl[l1]].append(r)
        else:
            a, b = lvl.get(l1, 1), lvl.get(l2, 1)
            for v in range(min(a, b), max(a, b) + 1):
                shapes[v].append(r)
    cell = 2.0
    grid = defaultdict(list)
    for v, rs in shapes.items():
        for r in rs:
            for gx in range(int(r[0] // cell), int(r[2] // cell) + 1):
                for gy in range(int(r[1] // cell), int(r[3] // cell) + 1):
                    grid[(gx, gy)].append((v, r))
    pos = defaultdict(list)
    for name, net, e, layer, p, r in pins:
        pos[(e, layer)].append(p)
    for k in pos:
        pos[k].sort()
    near, soft, mind = [], [], {}
    for name, net, e, layer, p, r in pins:
        if layer not in lvl:
            continue
        v0, clear = lvl[layer], T["pin_pdn_tracks"] * L[layer]["pitch"] + 1e-4
        best = None
        for gx in range(int((r[0] - clear) // cell), int((r[2] + clear) // cell) + 1):
            for gy in range(int((r[1] - clear) // cell), int((r[3] + clear) // cell) + 1):
                for v, s in grid.get((gx, gy), ()):
                    if abs(v - v0) <= 1:
                        g = rect_gap(r, s)
                        best = g if best is None else min(best, g)
        if best is not None:
            mind[layer] = min(mind.get(layer, 9e9), best)
        if best is not None and best <= clear:
            ps = pos[(e, layer)]
            n = bisect.bisect_right(ps, p + 1.0) - bisect.bisect_left(ps, p - 1.0)
            full = n >= T["pin_pdn_full_frac"] * (2.0 / L[layer]["pitch"])
            (near if full else soft).append((name, layer, round(best, 3)))
    met["pin_pdn_near"] = len(near)
    met["pin_pdn_near_sparse"] = len(soft)
    met["pin_pdn_min_um"] = {k: round(v, 3) for k, v in mind.items()}
    if near:
        ex = "; ".join(f"{n} {l} {g} um" for n, l, g in near[:4])
        (fails if T["pin_pdn_fail"] else warns).append(("pin_pdn", f"{len(near)} pin(s) of a full-density column within {T['pin_pdn_tracks']:g} track of a "
                                 f"PDN strap / via stack on the same or an adjacent layer ({ex}): offset the strap half a "
                                 f"pitch off the pin column (pdn_view_m5w.tcl) or inset the core"))
    elif soft:
        warns.append(("pin_pdn", f"{len(soft)} pin(s) within {T['pin_pdn_tracks']:g} track of a PDN strap / via stack "
                                 f"(column not full: escape tracks remain)"))

    # ---- macros: nets with fixed terminals
    net_terms = defaultdict(list)           # net -> [(kind, idx, x, y)]
    for i, m in enumerate(macros):
        for net, x, y, io, cap in m["pins"]:
            net_terms[net].append(("M", i, x, y))
    for name, net, e, layer, p, r in pins:
        if net:
            net_terms[net].append(("P", name, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2))

    # macro shadowing a pin edge
    shadow = []
    if macros:
        served = defaultdict(set)            # macro idx -> bterm names wired straight to it
        for net, ts in net_terms.items():
            ms = {t[1] for t in ts if t[0] == "M"}
            ps = {t[1] for t in ts if t[0] == "P"}
            for mi in ms:
                served[mi] |= ps
        by_edge = defaultdict(list)
        for name, net, e, layer, p, r in pins:
            by_edge[e].append((p, name))
        for e in by_edge:
            by_edge[e].sort()
        for i, m in enumerate(macros):
            b = m["bbox"]
            gaps = {"W": b[0] - die[0], "E": die[2] - b[2], "S": b[1] - die[1], "N": die[3] - b[3]}
            for e, g in gaps.items():
                if g > T["macro_edge_um"]:
                    continue
                lo, hi = (b[1], b[3]) if e in "WE" else (b[0], b[2])
                lst = by_edge.get(e, [])
                k0 = bisect.bisect_left(lst, (lo, ""))
                k1 = bisect.bisect_right(lst, (hi, "￿"))
                n = sum(1 for _, nm in lst[k0:k1] if nm not in served[i])
                if n >= T["macro_edge_pins"]:
                    shadow.append((m["name"], e, round(g, 1), n))
    met["macro_edge_shadow"] = len(shadow)
    if shadow:
        ex = "; ".join(f"{n} {e} face {g} um, {k} pins behind" for n, e, g, k in shadow[:4])
        fails.append(("macro_edge", f"{len(shadow)} macro(s) abut a pin edge with signal pins behind them ({ex}): keep "
                                    f"macros off pin edges (rows/columns inside, channels to the pins)"))

    # pin bank distance
    far = []
    for i, m in enumerate(macros):
        pts = []
        for net, x, y, io, cap in m["pins"]:
            pts += [(t[2], t[3]) for t in net_terms.get(net, ()) if t[0] == "P"]
        if len(pts) < T["bank_min_pins"]:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        d = pt_rect_dist(cx, cy, m["bbox"])
        if d > T["bank_dist_um"]:
            far.append((m["name"], len(pts), round(d, 1)))
    met["bank_far"] = len(far)
    if far:
        far.sort(key=lambda t: -t[2])
        ex = "; ".join(f"{n} ({k} pins) {d} um" for n, k, d in far[:4])
        fails.append(("bank_distance", f"{len(far)} macro(s) wired to block pins sit > {T['bank_dist_um']:.0f} um from "
                                       f"their pins' centroid ({ex}): place each pin bank at its pins"))

    # slivers between macros
    rows = dump.get("rows", [])
    rgrid = defaultdict(list)
    for r in rows:
        for gy in range(int(r[1] // 20), int(r[3] // 20) + 1):
            rgrid[gy].append(r)
    hard = [b["bbox"] for b in dump.get("blockages", []) if not b["soft"]]
    sl = []
    for a, b, g, gap in sliver_gaps([(m["name"], m["bbox"]) for m in macros], T["sliver_um"]):
        cand = {tuple(r) for gy in range(int(g[1] // 20), int(g[3] // 20) + 1) for r in rgrid.get(gy, ())}
        row_area = sum(inter_area(r, g) for r in cand)
        if row_area < T["sliver_min_row_area_um2"]:
            continue
        blk = sum(inter_area(inter_rect(r, g), h) for r in cand if inter_area(r, g) > 0 for h in hard)
        if blk >= T["sliver_blocked_frac"] * row_area:
            continue
        sl.append((a, b, round(gap, 2), round(row_area, 1), [round(v, 2) for v in g]))
    met["slivers"] = len(sl)
    if sl:
        ex = "; ".join(f"{a}|{b} gap {g} um rows {ra} um2" for a, b, g, ra, _ in sl[:3])
        fails.append(("sliver", f"{len(sl)} macro gap(s) < {T['sliver_um']:.0f} um hold placement rows without a hard "
                                f"placement blockage ({ex}): block them (sliver_block.tcl) or widen to >= "
                                f"{T['sliver_um']:.0f} um"))

    # channels: cut-line demand (nets with fixed terminals on both sides) vs tracks
    ch = channel_cuts(core, macros, dump["masters"], net_terms, layers, rmin, rmax, T)
    met["channel_worst"] = ch["worst"]
    if ch["over"]:
        ex = "; ".join(f"{c['axis']}={c['at']:.1f} demand {c['demand']} > tracks {c['cap']:.0f}" for c in ch["over"][:3])
        fails.append(("channel", f"{len(ch['over'])} cut line(s) need more tracks than the free channels give ({ex}): "
                                 f"widen the channels or route the bus over the top"))

    # capture flops (warn)
    loose = 0
    for m in macros:
        for net, x, y, io, cap in m["pins"]:
            if cap and FLOP_RE.match(cap[0]):
                if cap[1] not in ("PLACED", "FIRM", "LOCKED", "FIXED", "COVER") or math.hypot(cap[2] - x, cap[3] - y) > T["capture_warn_um"]:
                    loose += 1
    met["capture_unanchored"] = loose
    if loose >= T["capture_warn_count"]:
        warns.append(("capture", f"{loose} macro outputs are captured by a single flop the placer may put far from the "
                                 f"pin (qfd_tile rp1 class): anchor them at the pins (rom_cap_at_pins.tcl)"))
    return {"verdict": "FAIL" if fails else "PASS", "fails": [{"check": c, "msg": m} for c, m in fails],
            "warns": [{"check": c, "msg": m} for c, m in warns], "metrics": met, "thresholds": T}


def inter_rect(a, b):
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def channel_cuts(core, macros, masters, net_terms, layers, rmin, rmax, T):
    """Cut lines at every macro edge: demand = nets whose fixed terminals lie on both sides; capacity = free length
    (not under a macro that blocks the layer) / pitch x channel_usable, summed over the long-haul layers routing
    across the cut."""
    if not macros:
        return {"worst": None, "over": []}
    ivx, ivy = [], []
    for net, ts in net_terms.items():
        if len(ts) < 2:
            continue
        xs = [t[2] for t in ts]
        ys = [t[3] for t in ts]
        ivx.append((min(xs), max(xs)))
        ivy.append((min(ys), max(ys)))
    lo_x = sorted(a for a, _ in ivx); hi_x = sorted(b for _, b in ivx)
    lo_y = sorted(a for a, _ in ivy); hi_y = sorted(b for _, b in ivy)

    def demand(c, lo, hi):
        return bisect.bisect_left(lo, c) - bisect.bisect_right(hi, c)    # starts before c minus ends at/before c

    top = {}
    for m in macros:
        top[m["name"]] = masters.get(m["master"], {}).get("top_layer", 99) or 99
    worst, over = None, []
    for axis in ("x", "y"):
        # a vertical cut (x = c) is crossed by horizontal wires, and vice versa
        want = "HORIZONTAL" if axis == "x" else "VERTICAL"
        lys = [l for l in layers if l["dir"] == want and max(rmin, T["channel_min_layer"]) <= l["level"] <= rmax]
        cuts = set()
        for m in macros:
            b = m["bbox"]
            k0, k1 = (0, 2) if axis == "x" else (1, 3)
            cuts.update((b[k0] - 0.05, b[k1] + 0.05, (b[k0] + b[k1]) / 2))
        span = (core[1], core[3]) if axis == "x" else (core[0], core[2])
        for c in sorted(cuts):
            if not (core[0 if axis == "x" else 1] < c < core[2 if axis == "x" else 3]):
                continue
            d = demand(c, lo_x, hi_x) if axis == "x" else demand(c, lo_y, hi_y)
            if d <= 0:
                continue
            cap = 0.0
            for l in lys:
                blocked = []
                for m in macros:
                    b = m["bbox"]
                    if top[m["name"]] < l["level"]:
                        continue
                    if axis == "x" and b[0] < c < b[2]:
                        blocked.append((max(b[1], span[0]), min(b[3], span[1])))
                    elif axis == "y" and b[1] < c < b[3]:
                        blocked.append((max(b[0], span[0]), min(b[2], span[1])))
                free = (span[1] - span[0]) - union_len([iv for iv in blocked if iv[1] > iv[0]])
                cap += free / l["pitch"] * T["channel_usable"]
            ratio = d / cap if cap > 0 else float("inf")
            rec = {"axis": axis, "at": round(c, 2), "demand": d, "cap": round(cap, 1), "ratio": round(ratio, 3)}
            if worst is None or ratio > worst["ratio"]:
                worst = rec
            if d > cap:
                over.append(rec)
    over.sort(key=lambda r: -r["ratio"])
    return {"worst": worst, "over": over}


def parse_set(items):
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        if k not in THRESHOLDS:
            raise SystemExit(f"fp_margin_lint: unknown threshold {k!r} (known: {', '.join(THRESHOLDS)})")
        out[k] = type(THRESHOLDS[k])(float(v)) if isinstance(THRESHOLDS[k], (int, float)) else v
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["check", "metrics"])
    ap.add_argument("dumps", nargs="+")
    ap.add_argument("--out")
    ap.add_argument("--set", action="append", default=[], help="threshold override key=value")
    ap.add_argument("--warn-only", action="store_true", help="report, never fail")
    a = ap.parse_args(argv)
    th = parse_set(a.set)
    if a.mode == "metrics":
        for p in a.dumps:
            r = lint(json.loads(Path(p).read_text()), th)
            print(Path(p).stem, r["verdict"], json.dumps(r["metrics"]), "|", " / ".join(f["check"] for f in r["fails"]))
        return 0
    try:
        rep = lint(json.loads(Path(a.dumps[0]).read_text()), th)
    except Exception as ex:                                     # a checker fault is not a verdict
        print(f"fp_margin_lint: ERROR {type(ex).__name__}: {ex}")
        return 2
    rep["dump"] = a.dumps[0]
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1))
    m = rep["metrics"]
    print(f"fp_margin_lint: {rep['verdict']}  util {m['util']:.1%} (+hold {m['util_hold']:.1%}), pins {m['n_pins']}, "
          f"max pin density {m.get('pin_density_max', 0)} b/um, macros {m['n_macros']}, slivers {m['slivers']}, "
          f"channel worst {(m['channel_worst'] or {}).get('ratio')}")
    for w in rep["warns"]:
        print(f"fp_margin_lint: WARN {w['check']}: {w['msg']}")
    for f in rep["fails"]:
        print(f"fp_margin_lint: FAIL {f['check']}: {f['msg']}")
    if rep["fails"] and not a.warn_only:
        print("FLOORPLAN_MARGIN: " + " | ".join(f"{f['check']}: {f['msg']}" for f in rep["fails"])[:1500])
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
