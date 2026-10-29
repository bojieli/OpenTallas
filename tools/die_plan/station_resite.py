#!/usr/bin/env python3
"""DIE-HBM-14: opt-in plan delta -- re-site internal-station FF homes that sit inside a hard-core body + halo.

Root cause (DIE-HBM-14, plan c25c_d14): hub_repack / hbm_r9_delta place station registers only on free lattice
points, but LATER plan events (HBM-STREETS-3 C19 re-outlines, DIE-HBM C20 C17g growth re-pack, C20f height growth,
HBM-MU-QUAD-5/6, OUTL outline growths) moved or grew hard cores and never re-sited the station chains they cover:
about 2.7k plan registers per hub (90% under a THIRD core, not the leg's own endpoints).  This pass is the generator
fix: run it after any event that moves/grows a core (it is a no-op on a legal plan).

For every station chain with a register inside any core body + 4.32 halo (hub_repack.Raster legality; signal wires
may pass over M5 cores on M6/M7, FF homes may not), or with a hop > reach, re-solve the FF homes with the SAME
register count by the exact-count Manhattan reachability solver (codex ring_fixed_count.route, here numpy-only).
If no same-count solution exists, +1..+3 registers are tried and every added cycle is REPORTED (never silent).
Chains that need a different count are listed for TOK pricing; the static schedule is otherwise unchanged.

usage: station_resite.py PLAN_DIR OUT_DIR [--types q_hub_nw,q_hub_ne] [--reach 405] [--jobs N]
Writes OUT_DIR/die_plan.json + station_resite_report.json; every other PLAN_DIR entry is symlinked.
All numbers are plan arithmetic (UNCHECKED until NUMBER-CHECK).
"""
import argparse
import hashlib
import json
import math
import os
import sys
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_repack as HR  # noqa: E402

G = HR.G
HALO = HR.HALO


def core_rects(t):
    out = []
    for h in t.get("hard_cores", []):
        ox, oy = h.get("track_offset_um", [0.0, 0.0])
        x, y = h["origin_um"][0] + ox, h["origin_um"][1] + oy
        w, hh = h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out.append((h["inst"], x, y, x + w, y + hh))
    return out


def blocked(rects, p, halo=HALO):
    """name of the core whose body + halo strictly contains p (None if legal)."""
    for nm, x0, y0, x1, y1 in rects:
        if x0 - halo < p[0] < x1 + halo and y0 - halo < p[1] < y1 + halo:
            return nm
    return None


def _dilate(m, r):
    """Manhattan (taxicab) dilation of bool mask m by r lattice steps (obstacles ignored: wires may fly over)."""
    out = m.copy()
    cur = m
    for _ in range(r):
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]
        nxt[:-1, :] |= cur[1:, :]
        nxt[:, 1:] |= cur[:, :-1]
        nxt[:, :-1] |= cur[:, 1:]
        if (nxt == cur).all():
            break
        cur = nxt
    out |= cur
    return out


def route(free, a, b, n, reach=405.0):
    """n FF homes on free lattice points, every hop (a, regs..., b) <= reach (Manhattan); None if impossible.
    Same algorithm as codex ring_fixed_count.route (layered reachability, back-trace to the straight-line ideal)."""
    nx, ny = free.shape
    rs = int(reach // G)
    for slack in (reach, 2 * reach):
        i0 = max(0, int((min(a[0], b[0]) - slack) // G)); j0 = max(0, int((min(a[1], b[1]) - slack) // G))
        i1 = min(nx, int(math.ceil((max(a[0], b[0]) + slack) / G)) + 1)
        j1 = min(ny, int(math.ceil((max(a[1], b[1]) + slack) / G)) + 1)
        f = free[i0:i1, j0:j1]
        xx = np.arange(i0, i1)[:, None] * G; yy = np.arange(j0, j1)[None, :] * G
        da = abs(xx - a[0]) + abs(yy - a[1]); db = abs(xx - b[0]) + abs(yy - b[1])
        reached = f & (da <= reach + 1e-6); layers = [reached]
        if not reached.any():
            continue
        end = None
        for k in range(1, n + 1):
            if k == n:
                cand = reached & (db <= reach + 1e-6)
                if cand.any():
                    qi, qj = np.unravel_index(np.where(cand, db, 1e20).argmin(), f.shape); end = (int(qi), int(qj))
                break
            reached = f & _dilate(reached, rs); layers.append(reached)
        if end is None:
            continue
        rev = [end]; cur = end
        for k in range(n - 2, -1, -1):
            cx, cy = (cur[0] + i0) * G, (cur[1] + j0) * G
            good = layers[k] & (abs(xx - cx) + abs(yy - cy) <= reach + 1e-6)
            tx = a[0] + (b[0] - a[0]) * (k + 1) / (n + 1); ty = a[1] + (b[1] - a[1]) * (k + 1) / (n + 1)
            cost = abs(xx - tx) + abs(yy - ty)
            for q in rev:
                good[q] = False
            if not good.any():
                break
            qi, qj = np.unravel_index(np.where(good, cost, 1e20).argmin(), f.shape); cur = (int(qi), int(qj)); rev.append(cur)
        if len(rev) != n:
            continue
        regs = [[round((i + i0) * G, 3), round((j + j0) * G, 3)] for i, j in rev[::-1]]
        pts = [list(a)] + regs + [list(b)]
        assert max(abs(x[0] - y[0]) + abs(x[1] - y[1]) for x, y in zip(pts, pts[1:])) <= reach + 1e-5
        return regs
    return None


def max_hop(s):
    pts = [s["from_um"]] + s.get("regs_um", []) + [s["to_um"]]
    return max(abs(x[0] - y[0]) + abs(x[1] - y[1]) for x, y in zip(pts, pts[1:]))


_FREE = {}


def _solve(args):
    tn, i, a, b, n, reach = args
    free = _FREE[tn]
    for k in range(n, n + 4):
        r = route(free, a, b, k, reach)
        if r is not None:
            return i, k, r
    return i, None, None


def run(plan_dir, out_dir, types=None, reach=405.0, jobs=1, log=print):
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    p = json.loads((plan_dir / "die_plan.json").read_text())
    rep = {"schema": "opentallas.station_resite.v1", "reach_um": reach, "halo_um": HALO, "types": {}}
    tt = types or [tn for tn, t in p["partition_types"].items() if t.get("hard_cores") and t.get("internal_stations")]
    for tn in tt:
        t = p["partition_types"][tn]
        rects = core_rects(t)
        R = HR.Raster(*t["outline_um"], [r[1:] for r in rects])
        _FREE[tn] = R.f
        todo, before_regs, by_core = [], 0, {}
        for i, s in enumerate(t["internal_stations"]):
            regs = s.get("regs_um", [])
            bad = [r for r in regs if blocked(rects, r)]
            before_regs += len(bad)
            for r in bad:
                c = blocked(rects, r); by_core[c] = by_core.get(c, 0) + 1
            if bad or (regs and max_hop(s) > reach + 1e-5):
                todo.append((tn, i, tuple(s["from_um"]), tuple(s["to_um"]), len(regs), reach))
        if jobs > 1:
            with ProcessPoolExecutor(jobs, mp_context=mp.get_context("fork")) as ex:  # workers inherit _FREE
                res = list(ex.map(_solve, todo, chunksize=4))
        else:
            res = [_solve(x) for x in todo]
        rows, added, failed = [], 0, []
        for (tn_, i, a, b, n, _), (_, k, r) in zip(todo, res):
            s = t["internal_stations"][i]
            if k is None:
                failed.append(dict(index=i, conn=s["conn"], regs=n)); continue
            s["regs_um"] = r
            s["note"] = s.get("note", "") + f" | DIE-HBM-14 station_resite FF homes out of core bodies (count {n}->{k})"
            rows.append(dict(index=i, conn=s["conn"], bits=s.get("bits"), old=n, final=k, added=k - n))
            added += k - n
        after = sum(1 for s in t["internal_stations"] for r in s.get("regs_um", []) if blocked(rects, r))
        rep["types"][tn] = dict(regs_total=sum(len(s.get("regs_um", [])) for s in t["internal_stations"]),
                                regs_in_body_halo_before=before_regs, regs_in_body_halo_after=after,
                                chains_resited=len(rows), chains_added_cycles=[x for x in rows if x["added"]],
                                cycles_added_total=added, failed=failed,
                                worst_cores_before=sorted(by_core.items(), key=lambda kv: -kv[1])[:12], rows=rows)
        log(f"{tn}: regs in body+halo {before_regs} -> {after}; chains re-sited {len(rows)}, "
            f"+cycles {added} on {len(rep['types'][tn]['chains_added_cycles'])} chains, failed {len(failed)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in os.listdir(plan_dir):
        if f in ("die_plan.json", "station_resite_report.json") or (out_dir / f).exists():
            continue
        os.symlink(os.path.realpath(plan_dir / f), out_dir / f)
    (out_dir / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
    rep["plan_sha256"] = hashlib.sha256((out_dir / "die_plan.json").read_bytes()).hexdigest()
    (out_dir / "station_resite_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir"); ap.add_argument("out_dir")
    ap.add_argument("--types", default=None); ap.add_argument("--reach", type=float, default=405.0)
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    rep = run(a.plan_dir, a.out_dir, a.types.split(",") if a.types else None, a.reach, a.jobs)
    bad = sum(len(v["failed"]) + v["regs_in_body_halo_after"] for v in rep["types"].values())
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
