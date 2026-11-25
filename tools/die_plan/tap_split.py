#!/usr/bin/env python3
"""tap_split: split overloaded clock taps of grid+explicit types by MEASURED sink clusters (KV-TAPSPLIT, 11-25).

Why: a type whose clock.sink_bins_file is absent or stale is planned on the planned face/ft sinks only, so its grid +
added taps carry no idea of where the real register inventory sits.  The kit (clock_taps.tcl: nearest tap, then a capacity
re-assignment limited by OT_TAP_REASSIGN_UM) then lands thousands of sinks on one tap (kv3_pc_v3 clk_t7 14,012, kv3_hub_C
clk_t57 5,284), or the plan carries tap_max_sinks 3000 against a 1000 policy cap.

Method (per type, deterministic):
  1. sinks = the clocked-register positions of the newest placed kit (`sink_bins_from_place.py dump` TSV: net inst master x y),
     binned at BIN_UM into a bins file {"bin_um","n","bins":[[x,y,n]],...} (the clock.sink_bins_file form), so the plan sees
     the real inventory (taps.sink_sites reads it; grid_explicit_taps validates every added tap against it).
  2. every sink -> its nearest tap (the kit's rule, Manhattan).  A tap above CAP sinks, or whose furthest sink is beyond its far
     limit (FAR_ADDED for added taps, FAR_GRID for grid taps), is split: its sinks are clustered (weighted L1 k-medians,
     k = ceil(load / TARGET), at least 2 when only the distance is wrong), the existing tap stays as one of the k centres, the
     other k-1 become NEW taps appended after the existing ones (names clk_t<N>, N continuing the grid + added order, so no
     existing tap, reset tap or landing node is renamed).  Each new tap is legalised with schema.tap_clear (outline, macro halo,
     8.64 um tap spacing) and the whole assignment is recomputed, up to ROUNDS times.
  3. the row: jsonpatch ops with OLD-VALUE CHECKS -- a `test` op on the last existing tap name and on every replaced value,
     `add` ops that append the new taps, `add`/`replace` of clock.sink_bins_file and clock.tap_max_sinks.  The sinks of a split
     tap are re-pointed by the kit's nearest-tap rule (no sink table exists to edit); the report lists, per new tap, the
     sinks it takes from each old tap.

usage:
  tap_split.py plan   PLAN --dump TYPE=TSV [...] [--alias TYPE=SRC_TYPE] --bins-dir DIR --row ROW.json --report R.json
                      [--base-sha12 S] [--lane L] [--cap 1000] [--target 800] [--far-added 200] [--far-grid 300]
                      [--row-name N] [--types a,b]   (PLAN is the base plan json; run from the tree root)
  tap_split.py apply  PLAN ROW.json OUT_PLAN          (checks every `test`/`old`, then writes the patched plan)
  tap_split.py loads  PLAN --dump TYPE=TSV [...]      (nearest-tap loads of the plan as it stands)
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

import numpy as np

BIN_UM = 10.8
CAP, TARGET, SPLIT_ABOVE, FAR_ADDED, FAR_GRID, ROUNDS = 1000, 800, 900, 200.0, 300.0, 12


# --------------------------------------------------------------------------------------------------------- sinks / bins
def read_dump(path):
    """[(x, y)] of a sink_bins_from_place.py dump TSV (net inst master x y)."""
    out = []
    with open(path) as f:
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            if len(p) >= 5:
                out.append((float(p[3]), float(p[4])))
    return out


def make_bins(sinks, bin_um=BIN_UM):
    c = {}
    for x, y in sinks:
        k = (int(x // bin_um), int(y // bin_um))
        c[k] = c.get(k, 0) + 1
    return dict(bin_um=bin_um, n=len(sinks),
                bins=[[round((i + 0.5) * bin_um, 3), round((j + 0.5) * bin_um, 3), n] for (i, j), n in sorted(c.items())])


# ----------------------------------------------------------------------------------------------------------- assignment
def nearest(taps, pts):
    """taps [(name,x,y)], pts ndarray (m,3) x y w -> (asg per pt, load per tap, far per tap) by the Manhattan nearest tap
    (ties to the lower index, as taps.assign)."""
    t = np.array([[a[1], a[2]] for a in taps])
    asg = np.empty(len(pts), dtype=np.int64)
    dist = np.empty(len(pts))
    for s in range(0, len(pts), 2048):
        q = pts[s:s + 2048, :2]
        d = np.abs(q[:, None, 0] - t[None, :, 0]) + np.abs(q[:, None, 1] - t[None, :, 1])
        a = d.argmin(axis=1)
        asg[s:s + 2048] = a
        dist[s:s + 2048] = d[np.arange(len(q)), a]
    load = np.bincount(asg, weights=pts[:, 2], minlength=len(taps))
    far = np.zeros(len(taps))
    np.maximum.at(far, asg, dist)
    return asg, load, far


def _wmedian(v, w):
    o = np.argsort(v, kind="stable")
    cw = np.cumsum(w[o])
    return float(v[o][np.searchsorted(cw, cw[-1] / 2.0)])


def kmedians(pts, k, iters=30):
    """weighted L1 k-medians of pts (m,3); farthest-point seeding from the weighted-median point; returns [(x, y)]."""
    c0 = np.array([_wmedian(pts[:, 0], pts[:, 2]), _wmedian(pts[:, 1], pts[:, 2])])
    first = int(np.argmin(np.abs(pts[:, 0] - c0[0]) + np.abs(pts[:, 1] - c0[1])))
    cen = [pts[first, :2]]
    dmin = np.abs(pts[:, 0] - cen[0][0]) + np.abs(pts[:, 1] - cen[0][1])
    while len(cen) < k:
        i = int(np.argmax(dmin))
        cen.append(pts[i, :2])
        dmin = np.minimum(dmin, np.abs(pts[:, 0] - pts[i, 0]) + np.abs(pts[:, 1] - pts[i, 1]))
    cen = np.array(cen)
    prev = None
    for _ in range(iters):
        d = np.abs(pts[:, None, 0] - cen[None, :, 0]) + np.abs(pts[:, None, 1] - cen[None, :, 1])
        a = d.argmin(axis=1)
        if prev is not None and (a == prev).all():
            break
        prev = a
        for j in range(len(cen)):
            m = a == j
            if m.any():
                cen[j] = (_wmedian(pts[m, 0], pts[m, 2]), _wmedian(pts[m, 1], pts[m, 2]))
    return [(float(x), float(y)) for x, y in cen]


# --------------------------------------------------------------------------------------------------------------- split
def split_type(taps, n_grid, pts, legalize, cap=CAP, target=TARGET, far_added=FAR_ADDED, far_grid=FAR_GRID, rounds=ROUNDS,
               split_above=SPLIT_ABOVE):
    """taps [(name,x,y)] (grid first, then the added ones), pts ndarray (m,3).  Returns (new_taps [(x,y)], info):
    the taps to ADD (in order), `legalize(x, y, taken_xy) -> (x, y)` puts a candidate on a legal site.  info: per-round
    max load / far, and the final loads (nearest rule) of every tap."""
    cur = list(taps)
    new = []
    hist = []
    stuck = set()           # taps whose split did not lower their load (every legal site is blocked: macro halos)
    tried = {}
    for rd in range(rounds):
        asg, load, far = nearest(cur, pts)
        lim = np.array([far_grid if i < n_grid else far_added for i in range(len(cur))])
        hist.append((rd, float(load.max()), float(far.max()), len(new)))
        for j, l0 in tried.items():
            if load[j] >= l0 - 1e-9:
                stuck.add(j)
        over = [j for j in np.argsort(-load, kind="stable")
                if j not in stuck and (load[j] > min(cap, split_above) or far[j] > lim[j] + 1e-9)]
        tried = {int(j): float(load[j]) for j in over}
        if not over:
            break
        for j in over:
            sel = pts[asg == j]
            k = max(int(math.ceil(load[j] / target)), 2)
            if load[j] <= split_above:               # distance only: split in two (more when still far afterwards)
                k = 2
            cen = kmedians(sel, k)
            # the existing tap stays: drop the centre nearest to it
            keep = sorted(range(len(cen)), key=lambda i: abs(cen[i][0] - cur[j][1]) + abs(cen[i][1] - cur[j][2]))[1:]
            for i in sorted(keep):
                x, y = legalize(cen[i][0], cen[i][1], [(a[1], a[2]) for a in cur])
                cur.append((f"@{len(new)}", x, y))
                new.append((x, y))
    asg, load, far = nearest(cur, pts)
    return new, dict(history=hist, load=load.tolist(), far=far.tolist(), asg=asg, stuck=sorted(int(j) for j in stuck))


# ------------------------------------------------------------------------------------------------------------- jsonpatch
def _walk(doc, path):
    cur = doc
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur, parts[-1]


def apply_ops(doc, ops):
    """RFC 6902 subset: test / add / replace / remove; `replace` and `add` of an existing key may carry "old" (checked)."""
    for n, o in enumerate(ops):
        par, key = _walk(doc, o["path"])
        if isinstance(par, list):
            idx = len(par) if key == "-" else int(key)
        if o["op"] == "test" and "len" in o:
            have = (par[idx] if isinstance(par, list) else par[key])
            if len(have) != o["len"]:
                raise ValueError(f"op {n} test {o['path']}: length {len(have)} want {o['len']}")
        elif o["op"] == "test":
            have = par[idx] if isinstance(par, list) else par[key]
            if have != o["value"]:
                raise ValueError(f"op {n} test {o['path']}: have {str(have)[:80]!r} want {str(o['value'])[:80]!r}")
        elif o["op"] in ("add", "replace"):
            if "old" in o:
                have = (par[idx] if idx < len(par) else None) if isinstance(par, list) else par.get(key)
                if have != o["old"]:
                    raise ValueError(f"op {n} {o['path']}: old-value check failed, have {str(have)[:80]!r} want {str(o['old'])[:80]!r}")
            if isinstance(par, list):
                if o["op"] == "add":
                    par.insert(idx, o["value"])
                else:
                    par[idx] = o["value"]
            else:
                par[key] = o["value"]
        elif o["op"] == "remove":
            have = par[idx] if isinstance(par, list) else par.get(key)
            if "old" in o and have != o["old"]:
                raise ValueError(f"op {n} {o['path']}: old-value check failed on remove")
            if isinstance(par, list):
                del par[idx]
            else:
                del par[key]
        else:
            raise ValueError(f"op {n}: unsupported {o['op']}")
    return doc


def type_ops(tn, ck, grid_n, new_xy, bins_path, cap):
    """the row ops of one type: guards, sink_bins_file, tap_max_sinks, appended added_taps."""
    base = f"/partition_types/{tn}/clock"
    added = ck.get("added_taps") or []
    ops = []
    if added:
        ops.append(dict(op="test", path=f"{base}/added_taps", len=len(added)))
        ops.append(dict(op="test", path=f"{base}/added_taps/{len(added) - 1}/name", value=added[-1]["name"]))
    else:
        raise ValueError(f"{tn}: no added_taps (grid-only types are not handled)")
    ops.append(dict(op="test", path=f"{base}/tap_mode", value="grid+explicit"))
    for key, val in (("sink_bins_file", bins_path), ("tap_max_sinks", cap)):
        old = ck.get(key)
        if old == val:
            continue
        ops.append(dict(op="replace" if key in ck else "add", path=f"{base}/{key}", old=old, value=val))
    for i, (x, y) in enumerate(new_xy):
        ops.append(dict(op="add", path=f"{base}/added_taps/-", value=dict(name=f"clk_t{grid_n + len(added) + i}", xy=[round(x, 3), round(y, 3)])))
    return ops


# ---------------------------------------------------------------------------------------------------------------- CLI
def _kv(items):
    return dict(i.split("=", 1) for i in items or [])


def geometry_key(t):
    ck = t.get("clock", {})
    return json.dumps([t.get("outline_um"), t.get("hard_cores"), ck.get("added_taps"), ck.get("tap_um"), ck.get("tap_pitch_um"),
                       ck.get("tap_edge_y_um")], sort_keys=True)


def auto_aliases(raw, dumps):
    """{type: dumped type} for plan types without a dump whose outline, hard cores, grid parameters and added taps are
    IDENTICAL to a dumped type's (clone forms: the kit placement of one stands for the others)."""
    pt = raw["partition_types"]
    have = {geometry_key(pt[t]): t for t in sorted(dumps) if t in pt}
    out = {}
    for tn in sorted(pt):
        if tn in dumps or not tn.startswith("kv3_"):
            continue
        k = geometry_key(pt[tn])
        if k in have and pt[tn].get("clock", {}).get("added_taps"):
            out[tn] = have[k]
    return out


def _plan_types(P, only):
    return [t for t in sorted(P.types) if (not only or t in only)]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def explicit_taps(ck):
    """the sink-carrying explicit taps of an explicit-mode type: clock.taps entries without a `kind` (core / pin taps carry one)."""
    return [(t["name"], float(t["xy"][0]), float(t["xy"][1])) for t in ck.get("taps") or []
            if isinstance(t, dict) and "kind" not in t and t.get("xy")]


def type_taps(schema, P, ck, tn):
    """-> taps [(name,x,y)] and the count of fixed (non-added) ones: grid + added (grid+explicit) or the explicit list (explicit)."""
    if ck.get("tap_mode") == "explicit":
        t = explicit_taps(ck)
        return t, len(t)
    grid = schema._grid_taps(P, tn)
    return [(g[0], g[1], g[2]) for g in grid] + [(t["name"], float(t["xy"][0]), float(t["xy"][1])) for t in ck.get("added_taps") or []], len(grid)


def explicit_type_ops(tn, ck, new_xy, cap):
    """explicit-mode row ops (S81HEAD-TAPSPLIT 11-25): guards on clock.taps length / last name and tap_mode, tap_max_sinks, new taps
    appended to clock.taps named clk_t<max existing index + 1 ...> (no tap renamed; sink_bins_file untouched: explicit taps do not
    derive from bins)."""
    base = f"/partition_types/{tn}/clock"
    taps = ck.get("taps") or []
    if not taps:
        raise ValueError(f"{tn}: explicit type without clock.taps")
    ops = [dict(op="test", path=f"{base}/taps", len=len(taps)),
           dict(op="test", path=f"{base}/taps/{len(taps) - 1}/name", value=taps[-1]["name"]),
           dict(op="test", path=f"{base}/tap_mode", value="explicit")]
    if ck.get("tap_max_sinks") != cap:
        ops.append(dict(op="replace" if "tap_max_sinks" in ck else "add", path=f"{base}/tap_max_sinks", old=ck.get("tap_max_sinks"), value=cap))
    idx = [int(m.group(1)) for t in taps for m in [re.match(r"clk_t(\d+)$", str(t.get("name")))] if m]
    nxt = max(idx, default=0) + 1
    for i, (x, y) in enumerate(new_xy):
        ops.append(dict(op="add", path=f"{base}/taps/-", value=dict(name=f"clk_t{nxt + i}", xy=[round(x, 3), round(y, 3)])))
    return ops


def cmd_plan(a):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import schema
    import taps as TP
    raw = json.load(open(a.plan))
    P = schema.Plan(raw, a.plan)
    dumps, alias = _kv(a.dump), _kv(a.alias)
    only = set(a.types.split(",")) if a.types else None
    ops, rep = [], {}
    os.makedirs(a.bins_dir, exist_ok=True)
    work = json.loads(json.dumps(raw)) if a.validate else None
    for tn, src in auto_aliases(raw, dumps).items():
        alias.setdefault(tn, src)
    skipped = {}
    for tn in sorted(set(dumps) | set(alias)):
        if only and tn not in only:
            continue
        src = alias.get(tn, tn)
        ck = raw["partition_types"][tn]["clock"]
        expl = ck.get("tap_mode") == "explicit" and bool(explicit_taps(ck))
        if not expl and (ck.get("tap_mode") != "grid+explicit" or not ck.get("added_taps")):
            skipped[tn] = f"tap_mode {ck.get('tap_mode')} (density / grid types are re-binned, not split)"
            print(f"{tn}: SKIP {skipped[tn]}", flush=True)
            continue
        taps_all, n_fixed = type_taps(schema, P, ck, tn)
        sinks = read_dump(dumps[src])
        bins = make_bins(sinks)
        bins.update(type=tn, placed_kit=src, source=f"tap_split.py dump {os.path.basename(dumps[src])}")
        bpath = os.path.join(a.bins_dir, f"{tn}__tapsplit.json")
        rel = os.path.relpath(bpath, a.root) if a.root else bpath
        typ = P.types[tn]
        # the sink set the plan validators see once the bins file is set: the bins + the plan's own sink_sites_um rows
        # (taps.sink_sites) + the reset relay registers (grid_explicit_taps), so the split holds under both
        extra = [[float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 else 1.0] for r in ck.get("sink_sites_um", [])]
        if not typ.get("hard"):
            import reset_tree as RT
            extra += [[float(r["xy"][0]), float(r["xy"][1]), 1.0] for r in RT.for_type(P, tn).get("relays", [])]
        pts = np.array(bins["bins"] + extra, dtype=float)

        def legalize(x, y, taken, typ=typ):
            return schema.tap_clear(typ, x, y, taken, strict=True)[:2]
        _, load0, far0 = nearest(taps_all, pts)
        new_xy, info = split_type(taps_all, n_fixed, pts, legalize, a.cap, a.target, a.far_added, a.far_grid,
                                  split_above=a.split_above)
        if expl:
            t_ops = explicit_type_ops(tn, ck, new_xy, a.cap)
        else:
            t_ops = type_ops(tn, ck, n_fixed, new_xy, rel, a.cap)
            json.dump(bins, open(bpath, "w"))
        ops += t_ops
        load1, far1 = np.array(info["load"]), np.array(info["far"])
        lim = np.array([a.far_grid if i < n_fixed else a.far_added for i in range(len(load1))])
        rep[tn] = dict(sinks=len(sinks), taps_before=len(taps_all), taps_after=len(taps_all) + len(new_xy), new=len(new_xy),
                       max_load_before=float(load0.max()), max_load_after=float(load1.max()),
                       max_far_before=float(far0.max()), max_far_after=float(far1.max()),
                       over_cap_after=int((load1 > a.cap).sum()), stuck_taps=[taps_all[j][0] if j < len(taps_all) else f"new{j - len(taps_all)}" for j in info["stuck"]], far_violations_after=int((far1 > lim + 1e-9).sum()),
                       history=info["history"], source_dump=src, bins=None if expl else rel, aliased=(src != tn),
                       mode=ck.get("tap_mode"))
        print(f"{tn}{'<-'+src if src != tn else ''}: sinks {len(sinks)} taps {len(taps_all)} -> {len(taps_all) + len(new_xy)}  max load {load0.max():.0f} -> "
              f"{load1.max():.0f}  max far {far0.max():.0f} -> {far1.max():.0f}  over-cap {rep[tn]['over_cap_after']} "
              f"far-viol {rep[tn]['far_violations_after']}", flush=True)
    row = dict(row=a.row_name, lane=a.lane, base_sha12=a.base_sha12 or _sha(a.plan), why=(
        "clock taps split by measured sink clusters (cap %d, target %d, far <= %g um added / %g um grid): real sink inventory as "
        "clock.sink_bins_file, tap_max_sinks %d, extra taps appended after the existing ones (no tap renamed)" %
        (a.cap, a.target, a.far_added, a.far_grid, a.cap)), ops=ops, check=dict(types=sorted(rep)))
    json.dump(row, open(a.row, "w"), indent=1)
    json.dump(dict(types=rep, skipped=skipped), open(a.report, "w"), indent=1)
    print("ROW", a.row, "ops", len(ops), "sha", hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:12])
    return 0


def cmd_apply(a):
    doc = json.load(open(a.plan))
    row = json.load(open(a.row))
    apply_ops(doc, row["ops"])
    json.dump(doc, open(a.out, "w"), separators=(",", ":"))
    print("APPLIED", len(row["ops"]), "ops ->", a.out)
    return 0


def cmd_loads(a):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import schema
    raw = json.load(open(a.plan))
    P = schema.Plan(raw, a.plan)
    for tn, d in sorted(_kv(a.dump).items()):
        ck = raw["partition_types"][tn]["clock"]
        taps_all, _ = type_taps(schema, P, ck, tn)
        pts = np.array(make_bins(read_dump(d))["bins"], dtype=float)
        _, load, far = nearest(taps_all, pts)
        j = int(load.argmax())
        print(f"{tn}: taps {len(taps_all)} max load {load.max():.0f} ({taps_all[j][0]}) max far {far.max():.0f} "
              f">1000: {(load > 1000).sum()}")
    return 0


def cmd_check(a):
    """the plan validators on the patched plan: taps.grid_explicit_taps (every added tap non-empty, <= tap_max_sinks, within
    tap_radius_um of its sinks, legal sites) and the nearest-tap loads of the plan's own sink inventory."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import schema
    import taps as TP
    raw = json.load(open(a.plan))
    P = schema.Plan(raw, a.plan)
    row = json.load(open(a.row))
    bad = 0
    for tn in row["check"]["types"]:
        try:
            out = TP.grid_explicit_taps(P, tn)
        except ValueError as e:
            print(f"{tn}: FAIL {e}")
            bad += 1
            continue
        print(f"{tn}: OK taps {len(out)} max load {max(o[3] for o in out):.0f} max far {max(o[4] for o in out):.0f}", flush=True)
    return 1 if bad else 0


def cmd_render(a):
    """before | after picture of one type: sink bins (grey), hard cores (boxes), taps (circle area ~ nearest-rule load,
    red above the cap, blue = added by the row)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import schema
    pts = np.array(make_bins(read_dump(a.dump))["bins"], dtype=float)
    fig, axs = plt.subplots(1, 2, figsize=(16, 10))
    n_before = None
    for ax, path, lab in zip(axs, (a.before, a.after), ("before", "after")):
        raw = json.load(open(path))
        P = schema.Plan(raw, path)
        ck = raw["partition_types"][a.type]["clock"]
        t, _ = type_taps(schema, P, ck, a.type)
        if n_before is None:
            n_before = len(t)
        _, load, far = nearest(t, pts)
        ax.scatter(pts[:, 0], pts[:, 1], s=np.maximum(0.3, pts[:, 2] * 0.15), c="#9ab", alpha=0.5, lw=0)
        for h in raw["partition_types"][a.type].get("hard_cores") or []:
            (x, y), (w, hh) = h["origin_um"], h["outline_um"]
            ax.add_patch(plt.Rectangle((x, y), w, hh, fill=False, ec="#c90", lw=0.6))
        col = ["r" if l > a.cap else ("b" if i >= n_before else "k") for i, l in enumerate(load)]
        ax.scatter([q[1] for q in t], [q[2] for q in t], s=load / 3, facecolors="none", edgecolors=col, lw=0.8)
        ax.set_aspect("equal")
        ax.set_title(f"{a.type} {lab}: {len(t)} taps, max load {load.max():.0f}, max far {far.max():.0f} um, "
                     f"{int((load > a.cap).sum())} over {a.cap}", fontsize=10)
    fig.savefig(a.out, dpi=70, bbox_inches="tight")
    print("RENDER", a.out)
    return 0


def diff_ops(old, new, path=""):
    """jsonpatch ops (test/add/replace/remove with old-value checks) turning old into new.  Lists that only grew are
    appended to (with a length test), other differing lists are replaced whole."""
    ops = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in old:
            if k not in new:
                ops.append(dict(op="remove", path=f"{path}/{k}", old=old[k]))
        for k in new:
            if k not in old:
                ops.append(dict(op="add", path=f"{path}/{k}", old=None, value=new[k]))
            elif old[k] != new[k]:
                ops += diff_ops(old[k], new[k], f"{path}/{k}")
    elif isinstance(old, list) and isinstance(new, list):
        if len(new) >= len(old) and new[:len(old)] == old:
            ops.append(dict(op="test", path=path, len=len(old)))
            ops += [dict(op="add", path=f"{path}/-", value=v) for v in new[len(old):]]
        elif len(new) == len(old):
            for i, (a, b) in enumerate(zip(old, new)):
                if a != b:
                    ops += diff_ops(a, b, f"{path}/{i}")
        else:
            ops.append(dict(op="replace", path=path, old=old, value=new))
    else:
        ops.append(dict(op="replace", path=path, old=old, value=new))
    return ops


def cmd_diff(a):
    old = json.load(open(a.old))
    new = json.load(open(a.new))
    ops = []
    for k in sorted(set(old) | set(new)):
        if old.get(k) != new.get(k):
            ops += diff_ops(old.get(k), new.get(k), f"/{k}") if k in old and k in new else                 [dict(op="add", path=f"/{k}", old=None, value=new[k])]
    changed = {}
    for o in ops:
        q = o["path"].split("/")
        key = q[2] if q[1] == "partition_types" and len(q) > 2 else q[1] + ("/" + q[2] + "/" + q[3] if q[1] == "clock" and len(q) > 3 else "")
        changed[key] = changed.get(key, 0) + 1
    chk = apply_ops(json.loads(json.dumps(old)), ops)
    assert chk == new, "applying the diff ops does not give the new plan"
    json.dump(dict(row=a.row_name, lane=a.lane, base_sha12=a.base_sha12, why=a.why, ops=ops, check=dict(types=sorted(changed), ops_per_type=changed)),
              open(a.out, "w"))
    print("DIFF types", len(changed), "ops", len(ops), "->", a.out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("plan")
    p.add_argument("plan")
    p.add_argument("--dump", action="append")
    p.add_argument("--alias", action="append")
    p.add_argument("--types")
    p.add_argument("--bins-dir", required=True)
    p.add_argument("--root", help="tree root: bins path in the row is relative to it")
    p.add_argument("--row", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--row-name", default="KV-TAPSPLIT")
    p.add_argument("--lane", default="KV-TAPSPLIT")
    p.add_argument("--base-sha12")
    p.add_argument("--cap", type=int, default=CAP)
    p.add_argument("--split-above", type=int, default=SPLIT_ABOVE)
    p.add_argument("--target", type=int, default=TARGET)
    p.add_argument("--far-added", type=float, default=FAR_ADDED)
    p.add_argument("--far-grid", type=float, default=FAR_GRID)
    p.add_argument("--validate", action="store_true")
    p.set_defaults(fn=cmd_plan)
    p = sp.add_parser("apply")
    p.add_argument("plan")
    p.add_argument("row")
    p.add_argument("out")
    p.set_defaults(fn=cmd_apply)
    p = sp.add_parser("diff")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("out")
    p.add_argument("--row-name", default="KV-TAPSPLIT")
    p.add_argument("--lane", default="KV-TAPSPLIT")
    p.add_argument("--base-sha12", required=True)
    p.add_argument("--why", default="clock taps split by measured sink clusters")
    p.set_defaults(fn=cmd_diff)
    p = sp.add_parser("check")
    p.add_argument("plan")
    p.add_argument("row")
    p.set_defaults(fn=cmd_check)
    p = sp.add_parser("render")
    p.add_argument("type")
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--dump", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--cap", type=int, default=CAP)
    p.set_defaults(fn=cmd_render)
    p = sp.add_parser("loads")
    p.add_argument("plan")
    p.add_argument("--dump", action="append")
    p.set_defaults(fn=cmd_loads)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
