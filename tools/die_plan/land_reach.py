#!/usr/bin/env python3
"""LAND-REACH generator fix (CLASS-OWNERS-B / C-LAND-REACH, 11-26; default OFF behind a plan flag).

Class: a hard clock-landing core (clock.landing_contract.bands[].hard_core) sits farther from its data port than the data-wire
allowance.  A fall-edge writer pads the cland fclk to input max + DATA_ALLOWANCE_PS (45 ps = ~66 um) + setup, so a core parked
200-300 um from its port has negative setup before CTS (QC sle_ctl x_hc1_st_b_i / cws2_i: static -162 / -154 ps, measured -55.8 /
-40.4 ps).  PRE sees it as ADV-LAND-REACH (adv_land_reach.py).  Not a clock-tap-reach problem (C-TAP-REACH): the wire is data,
port -> core pin.

Cause in the generator: hard cores are seated by plan events (band resize / re-seat) from band geometry alone; nothing ties the
seat to the port the core captures.  QC sle_ctl: the band was resized south by DIE-KV-32 (ring_ff reserve) and the core followed
(y 1291 -> 1157 against an N-face port at y 1339).

Fix (by construction from the plan inputs, no hand coordinates): for every landing the check flags, re-seat the hard core TOGETHER
with its band (same shift, in 4.32 um steps so every PG / row / site phase is kept) to the legal spot nearest its old seat whose
worst port -> pin distance is inside the allowance; when no spot reaches the allowance, the legal spot with the smallest worst
distance if that clears the flag threshold.  Legal = clear of the cland_band_fit obstacle union (macros + reset clearance, clock
keep-outs, other bands, ft station sites, die islands, tap sites, PHY supply, reset / start / status groups), inside the 17.28 um
margin, band-to-pin hop <= cland_band_fit.REACH.  Port windows and die pins are never moved (they are the die IO contract shared
with the abutting type); a landing with no legal spot is reported UNRESOLVED, never forced.

Flag (default off; with it absent the plan and every report are byte-identical):
    plan top level  "land_reach": {"enable": 1, "margin_ps": -100, "target_ps": 0, "types": "regex", "landings": ["type/band", ...],
                                 "sidecar": "tree-relative clock-landing sidecar json (collector reset sites are obstacles)"}
    row_normalize.normalize_plan runs it first (before reprice / legal / tapname / landremap / retap), so later steps see the seat.
    CLI:  land_reach.py PLAN OUT [--tree TREE] [--sidecar SIDECAR] [--types RE] [--margin-ps N] [--force] [--check] [--report R]

    apply(raw, tree=None, side=None) -> report (raw changed in place when the flag is on)
"""
import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.dirname(os.path.dirname(HERE))):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import adv_land_reach as A  # noqa: E402

FLAG = "land_reach"
STEP_UM = 4.32              # PG pitch: every shift is a multiple, so row / site / PG phases are kept
MARGIN_UM = 17.28           # cland_band_fit.MARGIN
SEARCH_UM = 520.0           # candidate window around the old seat
MIN_GAIN_PS = 10.0          # a best-effort seat must improve the worst-bit margin by this much
CHUNK = 1500


def enabled(raw):
    cfg = raw.get(FLAG) if isinstance(raw, dict) else None
    return isinstance(cfg, dict) and bool(cfg.get("enable"))


def config(raw, **over):
    cfg = dict(raw.get(FLAG) or {}) if isinstance(raw, dict) else {}
    cfg.update({k: v for k, v in over.items() if v is not None})
    cfg.setdefault("margin_ps", A.MARGIN_FLAG_PS)
    cfg.setdefault("target_ps", 0.0)
    cfg.setdefault("types", ".")
    return cfg


def _dist_max(shifts, ports, rel):
    """worst Manhattan port -> pin distance per candidate shift (rel = {k: (x, y)} absolute pin centres at the old seat; a candidate adds
    its shift).  Same pairing as adv_land_reach.rows."""
    dx, dy = shifts[:, 0], shifts[:, 1]
    ks = sorted(rel)
    out = np.zeros(len(dx))
    if len(ports) > 1:
        P = np.array(ports, float)
        Q = np.array([rel[min(k, max(ks))] for k in range(len(ports))], float)
        for i0 in range(0, len(dx), CHUNK):
            sx, sy = dx[i0:i0 + CHUNK, None], dy[i0:i0 + CHUNK, None]
            out[i0:i0 + CHUNK] = (np.abs(P[None, :, 0] - (Q[None, :, 0] + sx)) + np.abs(P[None, :, 1] - (Q[None, :, 1] + sy))).max(axis=1)
    else:
        px, py = ports[0]
        Q = np.array([rel[k] for k in ks], float)
        # max over a point set of |px - x| + |py - y| is reached on the four extreme combinations
        s, d = Q[:, 0] + Q[:, 1], Q[:, 0] - Q[:, 1]
        a, b = px + py, px - py
        out = np.maximum.reduce([a - (s.min() + dx + dy), (s.max() + dx + dy) - a, b - (d.min() + dx - dy), (d.max() + dx - dy) - b])
    return out


def _obstacles(raw, tn, t, c, bus, side, P):
    """cland_band_fit obstacle union minus the landing's own core and band"""
    import cland_band_fit as CBF
    lc = ((t.get("clock") or {}).get("landing_contract") or {})
    t2 = dict(t)
    t2["hard_cores"] = [h for h in t.get("hard_cores") or [] if h.get("inst") != c["inst"]]
    return CBF.obstacles(t2, tn, P, side, lc, bus)


def _hit(x0, y0, x1, y1, O):
    """bool per candidate: rect (x0..x1, y0..y1 arrays) overlaps any obstacle"""
    if not len(O):
        return np.zeros(len(x0), bool)
    X0, Y0, X1, Y1 = x0[:, None], y0[:, None], x1[:, None], y1[:, None]
    return ((np.minimum(X1, O[:, 2]) > np.maximum(X0, O[:, 0]) + 1e-6) & (np.minimum(Y1, O[:, 3]) > np.maximum(Y0, O[:, 1]) + 1e-6)).any(axis=1)


def seat(t, c, band, det, obs, thr, target):
    """best legal shift for core c + band: (dx, dy, dmax, status) or None.  status: 'ok' margin >= target, 'best' improved, flag cleared."""
    ox, oy = c["origin_um"]
    ow, oh = c["outline_um"]
    W, H = t["outline_um"]
    br = band.get("rect_um") or [ox, oy, ox + ow, oy + oh]
    ux0, uy0 = min(ox, br[0]), min(oy, br[1])
    ux1, uy1 = max(ox + ow, br[2]), max(oy + oh, br[3])        # core + band union, moves rigidly
    n = int(SEARCH_UM // STEP_UM)
    ii, jj = np.meshgrid(np.arange(-n, n + 1), np.arange(-n, n + 1))
    S = np.stack([ii.ravel() * STEP_UM, jj.ravel() * STEP_UM], axis=1)
    inb = ((ux0 + S[:, 0] >= MARGIN_UM - 1e-6) & (uy0 + S[:, 1] >= MARGIN_UM - 1e-6)
           & (ux1 + S[:, 0] <= W - MARGIN_UM + 1e-6) & (uy1 + S[:, 1] <= H - MARGIN_UM + 1e-6))
    S = S[inb]
    O = np.asarray(obs, float).reshape(-1, 4)
    free = ~_hit(ux0 + S[:, 0], uy0 + S[:, 1], ux1 + S[:, 0], uy1 + S[:, 1], O)
    S = S[free]
    if not len(S):
        return None
    rel = {k: (x, y) for k, (x, y) in det["pins"].items()}      # absolute pin centres at the OLD seat; a candidate adds its shift
    d = _dist_max(S, det["ports"], rel)
    allow = A.DATA_ALLOWANCE_PS if det["fall"] else None
    if allow is None:
        return None                                             # rise writers carry a full-cycle allowance: not this class
    m = allow - d * A.PS_PER_UM
    d0 = float(_dist_max(np.zeros((1, 2)), det["ports"], rel)[0])
    m0 = allow - d0 * A.PS_PER_UM
    cost = np.abs(S[:, 0]) + np.abs(S[:, 1])
    okm = m >= target - 1e-9
    if okm.any():
        j = np.flatnonzero(okm)[np.argmin(cost[okm])]
        return float(S[j, 0]), float(S[j, 1]), float(d[j]), "ok", m0
    clr = (m >= thr - 1e-9) & (m >= m0 + MIN_GAIN_PS)
    if clr.any():
        idx = np.flatnonzero(clr)
        j = idx[np.lexsort((cost[idx], -m[idx]))[0]]
        return float(S[j, 0]), float(S[j, 1]), float(d[j]), "best", m0
    return None


def _shift_rect(r, dx, dy):
    return [round(r[0] + dx, 4), round(r[1] + dy, 4), round(r[2] + dx, 4), round(r[3] + dy, 4)]


def apply(raw, tree=None, side=None, check=False, **over):
    """re-seat every flagged hard landing core (raw in place unless check); report dict.  Runs only when the flag is on or force."""
    cfg = config(raw, **{k: v for k, v in over.items() if k != "force"})
    rep = dict(enabled=True, moved=[], unresolved=[], skipped=[], cfg={k: cfg[k] for k in ("margin_ps", "target_ps", "types")})
    if side is None and cfg.get("sidecar") and tree:          # the clock-landing sidecar carries the collector reset sites (obstacles)
        sp = Path(cfg["sidecar"])
        try:
            side = json.loads((sp if sp.is_absolute() else Path(tree) / sp).read_text())
        except (OSError, ValueError) as e:
            rep["sidecar_error"] = f"{type(e).__name__}: {e}"[:200]
    thr, target = float(cfg["margin_ps"]), float(cfg["target_ps"])
    only = set(cfg.get("landings") or [])
    det = []
    rows = A.rows(raw, tree, margin_ps=thr, detail=det)
    dkey = {(d["type"], d["landing"]): d for d in det}
    P = None
    try:
        import schema as S
        if (raw.get("die") or {}).get("pg", {}).get("domains") and raw.get("partitions"):
            P = S.Plan(raw)
    except Exception:           # noqa: BLE001 - the PHY supply obstacle is an extra, never a reason to refuse
        P = None
    todo = [r for r in rows if r["verdict"] == "FAIL" and re.search(cfg["types"], r["type"])
            and (not only or f"{r['type']}/{r['landing']}" in only)]
    for r in todo:
        tn, bn = r["type"], r["landing"]
        t = raw["partition_types"][tn]
        band = t["clock"]["landing_contract"]["bands"][bn]
        c = next(h for h in t["hard_cores"] if h["inst"] == band["hard_core"])
        d = dkey.get((tn, bn))
        row = dict(type=tn, landing=bn, core=c["inst"], d50_um=round(r["d50"], 1), dmax_um=round(r["dmax"], 1),
                   margin_ps=round(r["mmax"], 1), basis=r["basis"])
        if not d or not d.get("pins"):
            rep["skipped"].append(dict(row, why="no readable LEF: pin positions unknown"))
            continue
        if band.get("rects_um") or not band.get("rect_um"):
            rep["skipped"].append(dict(row, why="multi-rect or missing band rect"))
            continue
        res = seat(t, c, band, d, _obstacles(raw, tn, t, c, bn, side, P), thr, target)
        if res is None:
            rep["unresolved"].append(dict(row, why="no legal seat within %.0f um clears the flag" % SEARCH_UM))
            continue
        dx, dy, dmax, st, _m0 = res
        new_m = A.DATA_ALLOWANCE_PS - dmax * A.PS_PER_UM
        mv = dict(row, shift_um=[round(dx, 3), round(dy, 3)], old_origin_um=list(c["origin_um"]), status=st,
                  new_dmax_um=round(dmax, 1), new_margin_ps=round(new_m, 1))
        if not check:
            old_o, old_b = list(c["origin_um"]), list(band["rect_um"])
            c["origin_um"] = [round(old_o[0] + dx, 4), round(old_o[1] + dy, 4)]
            band["land_reach_from_um"] = old_b
            band["rect_um"] = _shift_rect(old_b, dx, dy)
            band["land_reach"] = f"C-LAND-REACH: core+band re-seated ({dx:+.2f}, {dy:+.2f}) um to the port (worst {r['dmax']:.0f} -> {dmax:.0f} um)"
            c["note"] = (c.get("note") or "") + f" | C-LAND-REACH: re-seated ({dx:+.2f}, {dy:+.2f}) um within the 45 ps port allowance"
            pxy = _pin_xy(t, band, bn)
            if pxy is not None and "max_pin_to_band_hop_um" in band:
                import cland_band_fit as CBF
                band["max_pin_to_band_hop_um"] = round(CBF.hop(band["rect_um"], pxy), 3)
        rep["moved"].append(mv)
    rep["summary"] = dict(flagged=len(todo), moved=len(rep["moved"]), unresolved=len(rep["unresolved"]), skipped=len(rep["skipped"]),
                          resolved_ok=sum(1 for m in rep["moved"] if m["status"] == "ok"))
    if not check and rep["moved"]:
        after = A.rows(raw, tree, margin_ps=thr)
        rep["after"] = dict(fail=sum(1 for r in after if r["verdict"] == "FAIL"), watch=sum(1 for r in after if r["verdict"] == "WATCH"),
                            ok=sum(1 for r in after if r["verdict"] == "OK"))
    return rep


def _pin_xy(t, band, bn):
    try:
        import cland_band_fit as CBF
        lc = (t.get("clock") or {}).get("landing_contract") or {}
        return CBF.pin_xy(t, lc, bn)
    except Exception:           # noqa: BLE001
        return None


def run_flagged(raw, tree=None, side=None):
    """the normalize hook: the report when the flag is on, None (and raw untouched) otherwise"""
    if not enabled(raw):
        return None
    return apply(raw, tree, side)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--tree")
    ap.add_argument("--sidecar")
    ap.add_argument("--types")
    ap.add_argument("--margin-ps", type=float)
    ap.add_argument("--force", action="store_true", help="run although the plan flag is absent")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    if not enabled(raw) and not a.force:
        print("land_reach: plan flag absent (land_reach.enable), nothing to do; --force to run")
        return 0
    side = json.loads(Path(a.sidecar).read_text()) if a.sidecar and a.sidecar not in ("-", "none") else None
    rep = apply(raw, a.tree, side, check=a.check, types=a.types, margin_ps=a.margin_ps)
    if not a.check:
        Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    s = rep["summary"]
    print(f"land_reach: flagged {s['flagged']} moved {s['moved']} (to allowance {s['resolved_ok']}) unresolved {s['unresolved']} skipped {s['skipped']}"
          + (f" after {rep['after']}" if rep.get("after") else ""))
    for m in rep["moved"]:
        print("MOVED", m["type"], m["landing"], m["shift_um"], f"{m['dmax_um']} -> {m['new_dmax_um']} um", f"margin {m['margin_ps']} -> {m['new_margin_ps']} ps", m["status"])
    for u in rep["unresolved"] + rep["skipped"]:
        print("LEFT", u["type"], u["landing"], u["why"])
    return 1 if rep["unresolved"] and not a.check else 0


if __name__ == "__main__":
    sys.exit(main())
