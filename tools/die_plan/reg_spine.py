#!/usr/bin/env python3
"""Register clock SPINE + LOCAL TREES planner for one partition kit (METHODOLOGY 12.13b / 12.16e local form; DIE-HEAD-16/17).

Opt-in per partition type (`partition_types.<t>.reg_spine`, gen_phys writes reg_spine.json + this file + reg_spine.tcl into
the kit).  reg_spine.tcl runs it in PRE_CTS on the placed register clock sinks:

    python3 reg_spine.py reg_spine.json sinks.txt OUTDIR   ->  OUTDIR/reg_spine_plan.tcl, reg_spine_assign.txt, reg_spine_plan.json

Plan (all from the spec + placed sink coordinates, deterministic, no timing measurement inside):
  * trunk: spec `trunk` = [[name, x, y, parent], ...]; parent "CLK" = the clock entry net, "-" = the root marker (no cell).
    Every node is one `trunk_cell` at its plan coordinate fed from its parent's output net.  Nodes named in `express`
    carry no taps (express chains to far hubs).
  * taps: k-means of the sinks seeded from fixed `bin_um` bins with >= `min_bin_sinks` sinks; while a cluster's
    farthest sink (Manhattan) is beyond `radius_um`, that sink seeds a new cluster; clusters below `min_tap_sinks`
    merge into their neighbours.  Ties break by index/coordinate.  The tap driver sits at the sink centroid, moved just
    outside a `keepouts_um` rectangle (hard core) if it falls inside; it hangs off the nearest non-express trunk node.
  * pads: spec `pads` {tap_id: n} = n x `pad_cell` abutted before the tap driver (driver end, slew by construction).
    They are PLAN DATA (12.8 d1: computed from the plan model / a recorded routed pass of the same plan, frozen with
    it); tap ids are stable for a given placement because the clustering is deterministic.
"""
import collections
import json
import sys


def load_sinks(path, net="clk"):
    out = []
    for line in open(path):
        f = line.split()
        if len(f) >= 6 and f[0] == net and f[3] in ("CLK", "clk", "CK"):
            out.append((f[1], float(f[4]), float(f[5])))
    out.sort()
    return out


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _kmeans(sinks, cent):
    groups = [[] for _ in cent]
    for _ in range(40):
        groups = [[] for _ in cent]
        for _, x, y in sinks:
            j = min(range(len(cent)), key=lambda i: (abs(cent[i][0] - x) + abs(cent[i][1] - y), i))
            groups[j].append((x, y))
        new = [(sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)) if g else c for g, c in zip(groups, cent)]
        if new == cent:
            break
        cent = new
    keep = [i for i, g in enumerate(groups) if g]
    return [cent[i] for i in keep], [groups[i] for i in keep]


def cluster(sinks, spec):
    bx, by = spec.get("bin_um", [118.0, 115.2])
    bins = collections.defaultdict(list)
    for _, x, y in sinks:
        bins[(int(x // bx), int(y // by))].append((x, y))
    seeds = [(sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
             for _, v in sorted(bins.items()) if len(v) >= spec.get("min_bin_sinks", 250)]
    if not seeds:
        seeds = [(sum(s[1] for s in sinks) / len(sinks), sum(s[2] for s in sinks) / len(sinks))]
    cent, groups = _kmeans(sinks, seeds)
    radius = float(spec.get("radius_um", 100.0))
    for _ in range(int(spec.get("max_split_rounds", 40))):
        worst = None
        for c, g in zip(cent, groups):
            far = max(g, key=lambda p: (_d(p, c), p))
            r = _d(far, c)
            if r > radius and (worst is None or r > worst[0]):
                worst = (r, far)
        if worst is None:
            break
        cent, groups = _kmeans(sinks, cent + [worst[1]])
    while True:
        small = [i for i, g in enumerate(groups) if len(g) < spec.get("min_tap_sinks", 20)]
        if not small or len(cent) == 1:
            break
        i = small[0]
        cent, groups = _kmeans(sinks, cent[:i] + cent[i + 1:])
    return cent


def snap_out(x, y, keepouts):
    for a, b, c, d in keepouts:
        if a <= x <= c and b <= y <= d:
            _, x, y = min([(x - a + 2, a - 2, y), (c - x + 2, c + 2, y), (y - b + 2, x, b - 2), (d - y + 2, x, d + 2)])
    return x, y


def close_projected_radius(taps, sinks, trunk, spec):
    """Opt-in radius closure AFTER keepout projection and small-cluster merging.

    Add a legal tap at the actual farthest sink, then reassign. This preserves
    all existing physical taps; sparse outliers may own a singleton tap.
    """
    radius = float(spec["projected_radius_um"])
    pads = {str(k): int(v) for k, v in spec.get("pads", {}).items()}
    attach = [t for t in trunk if t[3] != "-" and t[0] not in set(spec.get("express", []))]
    def assign():
        return {n: min(range(len(taps)), key=lambda i: (_d((taps[i]["x"], taps[i]["y"]), (x, y)), i))
                for n, x, y in sinks}
    for _ in range(int(spec.get("max_projected_splits", 1000))):
        asg = assign()
        far = max((_d((taps[asg[n]]["x"], taps[asg[n]]["y"]), (x, y)), n, x, y) for n, x, y in sinks)
        if far[0] <= radius:
            break
        _, _, x, y = far
        x, y = snap_out(x, y, spec.get("keepouts_um", []))
        node = min(attach, key=lambda t: (_d((t[1], t[2]), (x, y)), t[0]))
        # pads are keyed by the id a tap is CREATED with (k-means ids, then appended ids), read here once
        taps.append(dict(id=len(taps), x=round(x, 2), y=round(y, 2), node=node[0], pad=pads.get(str(len(taps)), 0)))
    else:
        raise ValueError("reg_spine projected-radius closure did not converge")
    occupied = set(asg.values())
    taps = [t for i, t in enumerate(taps) if i in occupied]
    # renumber after pruning; every surviving tap keeps the pad it was created with (never re-read by the new id)
    for i, t in enumerate(taps):
        t["id"] = i
    return taps


def legalize_tap_footprints(taps, spec):
    """Opt-in (`tap_footprint`): move each tap driver to the nearest point where its WHOLE built footprint is legal.

    reg_spine.tcl abuts `pad` x pad_cell to the LEFT of the tap driver (x - (pad - s) * pitch - 0.3) and places the
    tap_cell driver at x, one row high.  snap_out only clears the driver point, so long pad chains next to a hard core
    or the core edge land inside the core or outside the rows.  The footprint [x - cols*pitch - 0.3, x + tap_width] x
    rows (plus site/row snapping slack and `margin_um`) must lie inside `core_um` and clear every `keepouts_um`
    rectangle grown by `keepout_halo_um` (row cut-back) and every `extra_keepouts_um` rectangle (e.g. die islands).
    A chain that fits no single row within `max_move_um` (narrow core-edge channels) is FOLDED: the same pads, same
    order, `cols` per row on consecutive rows stacked away from the driver row; their coordinates are written as the
    optional 6th tap field (`pad_xy`), which reg_spine.tcl uses instead of the single-row formula.  Candidates are
    ranked by (Manhattan move, fewest rows, down before up); search on a `step_um` grid is deterministic.  No tap id,
    pad count, cell or topology changes.  Fails closed if no legal footprint exists.
    """
    fp = spec["tap_footprint"]
    pitch = float(spec.get("pad_pitch_um", CFG_DEFAULTS["pad_pitch_um"]))
    sw, sh = spec.get("site_um", CFG_DEFAULTS["site_um"])
    tw = float(fp.get("tap_width_um", 1.62))
    m = float(fp.get("margin_um", 0.054)) + sw / 2
    step = float(fp.get("step_um", sh))
    cx0, cy0, cx1, cy1 = fp["core_um"]
    halo = float(fp.get("keepout_halo_um", 0.0))  # hard-core row cut-back (rows stop this far from a macro)
    keep = [(a - halo, b - halo, c + halo, d + halo) for a, b, c, d in spec.get("keepouts_um", [])]
    keep += [tuple(k) for k in fp.get("extra_keepouts_um", [])]
    reach = int(round(float(fp.get("max_move_um", 30.0)) / step))
    ring = sorted((abs(i) + abs(j), j, i) for i in range(-reach, reach + 1) for j in range(-reach, reach + 1))

    def rect(x, y, cols, rows, sgn):
        y0, y1 = (y - (rows - 1) * sh, y) if sgn < 0 else (y, y + (rows - 1) * sh)
        return (x - cols * pitch - 0.3 - m, y0 - sh / 2 - m, x + tw + m, y1 + 1.5 * sh + m)

    for t in taps:
        n = int(t["pad"])
        forms = [(n, 1, -1)] + [(-(-n // r), r, s) for r in range(2, n + 1) for s in (-1, 1)
                                if -(-n // r) < -(-n // (r - 1))]
        best = None
        for cols, rows, sgn in forms:
            r0 = rect(t["x"], t["y"], cols, rows, sgn)
            span = reach * step
            near = [k for k in keep if k[0] < r0[2] + span and r0[0] - span < k[2]
                    and k[1] < r0[3] + span and r0[1] - span < k[3]]
            for dist, j, i in ring:
                if best is not None and dist > best[0]:
                    break
                x, y = t["x"] + i * step, t["y"] + j * step
                a = rect(x, y, cols, rows, sgn)
                if a[0] < cx0 or a[1] < cy0 or a[2] > cx1 or a[3] > cy1:
                    continue
                if any(a[0] < k[2] and k[0] < a[2] and a[1] < k[3] and k[1] < a[3] for k in near):
                    continue
                if best is None or (dist, rows, sgn) < best[0:3]:
                    best = (dist, rows, sgn, x, y, cols, sgn)
                break
        if best is None:
            raise ValueError(f"reg_spine tap {t['id']}: no legal pad+driver footprint within "
                             f"{fp.get('max_move_um', 30.0)} um")
        _, rows, _, x, y, cols, sgn = best
        if (round(x - t["x"], 3), round(y - t["y"], 3)) != (0.0, 0.0):
            t["footprint_move_um"] = [round(x - t["x"], 3), round(y - t["y"], 3)]
        t["x"], t["y"] = round(x, 2), round(y, 2)
        if rows > 1:
            # pad s feeds pad s+1 feeds the driver: last pad sits next to the driver on its row, like the 1-row form
            xy = []
            for s in range(n):
                k = n - 1 - s                      # 0 = the pad abutting the driver
                r, c = divmod(k, cols)
                xy.append([round(t["x"] - (c + 1) * pitch - 0.3, 3), round(t["y"] + sgn * r * sh, 3)])
            t["pad_xy"] = xy
    return taps


def plan(spec, sinks):
    sinks = sorted(sinks)
    trunk = [tuple(t) for t in spec["trunk"]]
    names = {t[0] for t in trunk}
    for n, _, _, p in trunk:
        if p not in ("-", "CLK") and p not in names:
            raise ValueError(f"reg_spine trunk node {n}: unknown parent {p}")
    express = set(spec.get("express", []))
    attach = [t for t in trunk if t[3] != "-" and t[0] not in express]
    if not attach:
        raise ValueError("reg_spine: no trunk node to attach taps to")
    cent = cluster(sinks, spec)
    keep = [tuple(k) for k in spec.get("keepouts_um", [])]
    pads = {str(k): int(v) for k, v in spec.get("pads", {}).items()}
    taps = []
    for i, (cx, cy) in enumerate(cent):
        tx, ty = snap_out(cx, cy, keep)
        node = min(attach, key=lambda t: (abs(t[1] - tx) + abs(t[2] - ty), t[0]))
        taps.append(dict(id=i, x=round(tx, 2), y=round(ty, 2), node=node[0], pad=pads.get(str(i), 0)))
    if "projected_radius_um" in spec:
        taps = close_projected_radius(taps, sinks, trunk, spec)
    if "tap_footprint" in spec:
        taps = legalize_tap_footprints(taps, spec)
        for t in taps:
            t["node"] = min(attach, key=lambda n: (abs(n[1] - t["x"]) + abs(n[2] - t["y"]), n[0]))[0]
    assign = {}
    for n, x, y in sinks:
        assign[n] = min(range(len(taps)), key=lambda i: (abs(taps[i]["x"] - x) + abs(taps[i]["y"] - y), i))
    cnt = collections.Counter(assign.values())
    for t in taps:
        t["sinks"] = cnt[t["id"]]
        t["radius_um"] = round(max((abs(x - t["x"]) + abs(y - t["y"]) for n, x, y in sinks if assign[n] == t["id"]),
                                   default=0.0), 1)
    if "tap_footprint" in spec and "projected_radius_um" in spec:
        worst = max(t["radius_um"] for t in taps)
        if worst > float(spec["projected_radius_um"]):
            raise ValueError(f"reg_spine footprint legalization broke projected radius: {worst} um")
    return trunk, taps, assign


CFG_DEFAULTS = dict(entry_port="clk", root_cell="BUFx24_ASAP7_75t_R", trunk_cell="BUFx24_ASAP7_75t_R",
                    tap_cell="BUFx24_ASAP7_75t_R", pad_cell="BUFx4_ASAP7_75t_R", pad_pitch_um=0.81,
                    site_um=[0.054, 0.27], core_origin_um=[4.32, 4.32])


def _tcl(v):
    return "{" + " ".join(_tcl(x) for x in v) + "}" if isinstance(v, (list, tuple)) else str(v)


def write(out, trunk, taps, assign, spec=None):
    spec = spec or {}
    status = spec.get("placement_status", "PLACED")
    if status not in ("PLACED", "FIRM"):
        raise ValueError("reg_spine placement_status must be PLACED or FIRM")
    with open(f"{out}/reg_spine_plan.tcl", "w") as f:
        f.write("# GENERATED by reg_spine.py. cfg: tcl dict; cores: inst pin x y stages {repeaters}; "
                "trunk: name x y parent; taps: id x y node pad\n")
        cfg = dict(CFG_DEFAULTS, **{k: spec[k] for k in CFG_DEFAULTS if k in spec})
        cfg["root_split_xy"] = spec.get("root_split_xy", [trunk[0][1], trunk[0][2]])
        cfg["cts_extra_nets"] = spec.get("cts_extra_nets", [])
        # Default output stays unchanged; only a fully legalized prebuild plan
        # may retain its declared homes through CTS legalization.
        if "placement_status" in spec:
            cfg["placement_status"] = status
        f.write("set rsp_cfg {\n" + "".join(f"  {k} {_tcl(cfg[k])}\n" for k in sorted(cfg)) + "}\n")
        f.write("set rsp_cores {\n" + "".join(
            f"  {{{c['inst']} {c['pin']} {c['xy'][0]} {c['xy'][1]} {int(c['stages'])} {_tcl(c.get('repeaters', []))}}}\n"
            for c in spec.get("core_taps", [])) + "}\n")
        f.write("set rsp_trunk {\n" + "".join(f"  {{{n} {x} {y} {p}}}\n" for n, x, y, p in trunk) + "}\n")
        f.write("set rsp_taps {\n" + "".join(f"  {{{t['id']} {t['x']} {t['y']} {t['node']} {t['pad']}" + (f" {_tcl(t['pad_xy'])}" if t.get('pad_xy') else '') + "}\n" for t in taps)
                + "}\n")
    with open(f"{out}/reg_spine_assign.txt", "w") as f:
        for n in sorted(assign):
            f.write(f"{n} {assign[n]}\n")
    json.dump(dict(trunk=trunk, taps=taps, sinks=len(assign)), open(f"{out}/reg_spine_plan.json", "w"), indent=1)


def main(argv):
    spec = json.load(open(argv[1]))
    sinks = load_sinks(argv[2], spec.get("sink_net", "clk"))
    if not sinks:
        raise SystemExit("reg_spine: no register clock sinks in " + argv[2])
    trunk, taps, assign = plan(spec, sinks)
    write(argv[3], trunk, taps, assign, spec)
    print(f"REG_SPINE sinks {len(sinks)} taps {len(taps)} pads {sum(t['pad'] for t in taps)} "
          f"max_radius {max(t['radius_um'] for t in taps)}")


if __name__ == "__main__":
    main(sys.argv)
