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
    assign = {}
    for n, x, y in sinks:
        assign[n] = min(range(len(taps)), key=lambda i: (abs(taps[i]["x"] - x) + abs(taps[i]["y"] - y), i))
    cnt = collections.Counter(assign.values())
    for t in taps:
        t["sinks"] = cnt[t["id"]]
        t["radius_um"] = round(max((abs(x - t["x"]) + abs(y - t["y"]) for n, x, y in sinks if assign[n] == t["id"]),
                                   default=0.0), 1)
    return trunk, taps, assign


CFG_DEFAULTS = dict(entry_port="clk", root_cell="BUFx24_ASAP7_75t_R", trunk_cell="BUFx24_ASAP7_75t_R",
                    tap_cell="BUFx24_ASAP7_75t_R", pad_cell="BUFx4_ASAP7_75t_R", pad_pitch_um=0.81,
                    site_um=[0.054, 0.27], core_origin_um=[4.32, 4.32])


def _tcl(v):
    return "{" + " ".join(_tcl(x) for x in v) + "}" if isinstance(v, (list, tuple)) else str(v)


def write(out, trunk, taps, assign, spec=None):
    spec = spec or {}
    with open(f"{out}/reg_spine_plan.tcl", "w") as f:
        f.write("# GENERATED by reg_spine.py. cfg: tcl dict; cores: inst pin x y stages {repeaters}; "
                "trunk: name x y parent; taps: id x y node pad\n")
        cfg = dict(CFG_DEFAULTS, **{k: spec[k] for k in CFG_DEFAULTS if k in spec})
        cfg["root_split_xy"] = spec.get("root_split_xy", [trunk[0][1], trunk[0][2]])
        cfg["cts_extra_nets"] = spec.get("cts_extra_nets", [])
        f.write("set rsp_cfg {\n" + "".join(f"  {k} {_tcl(cfg[k])}\n" for k in sorted(cfg)) + "}\n")
        f.write("set rsp_cores {\n" + "".join(
            f"  {{{c['inst']} {c['pin']} {c['xy'][0]} {c['xy'][1]} {int(c['stages'])} {_tcl(c.get('repeaters', []))}}}\n"
            for c in spec.get("core_taps", [])) + "}\n")
        f.write("set rsp_trunk {\n" + "".join(f"  {{{n} {x} {y} {p}}}\n" for n, x, y, p in trunk) + "}\n")
        f.write("set rsp_taps {\n" + "".join(f"  {{{t['id']} {t['x']} {t['y']} {t['node']} {t['pad']}}}\n" for t in taps)
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
