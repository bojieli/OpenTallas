"""Die clock spine branch model (CP2): per-partition-tap source latency offsets for the die STA.

A pair plan (pair.py) is a two-partition window of a full die.  Its own spine (clock.spine.root_um at the pair centre)
only routes the pair die, so the pair die STA saw the two partitions' taps fed from one short local net: no branch
mismatch.  On the real die each tap hangs off the die H-tree (clock.spine.topology 'htree') at the die root.  This
module estimates every tap's branch latency on that tree:

  recursive bisection of the die outline, starting at the die root (clock.spine.die_root_um): level 1 splits at the
  root x, level 2 at the root y, every later level at the region midpoint, x and y alternating; at each level the
  tree node moves along the split axis to the centre of the child region holding the tap (the classic H-tree leg).
  The recursion stops once the region is <= branch_leaf_um on the split axis (default budgets.tap_pitch_um: the
  spine reaches tap-grid granularity); the last leg is the Manhattan distance from the leaf node to the tap.
  branch latency = path length (mm) x clock.spine.branch_ps_per_mm (default 60 ps/mm: repeated M8/M9 wire, the
  ~450 um repeater pitch at ~25-30 ps per stage).

The die STA (gen_phys.sta_die_tcl, SPINE=branch) puts a generated clock on every partition tap pin with source
latency = offset_ps = branch latency - the smallest branch latency of the plan (- the early shift of a core tap),
so seam paths see the branch mismatch.  A plan without die_root_um uses its own root and outline (a full die).
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

DEFAULT_PS_PER_MM = 60.0


def htree_path(root, outline, pt, leaf_um):
    """(length_um, legs) of the H-tree branch from `root` to point `pt` in a die of `outline` (see module doc)."""
    W, H = outline
    lo, hi = [0.0, 0.0], [float(W), float(H)]
    node = [float(root[0]), float(root[1])]
    legs = []
    level = 0
    small = 0
    while small < 2 and level < 64:
        ax = level % 2
        if hi[ax] - lo[ax] <= leaf_um + 1e-9:
            small += 1
            level += 1
            continue
        small = 0
        s = root[ax] if level < 2 else (lo[ax] + hi[ax]) / 2
        if not lo[ax] < s < hi[ax]:
            s = (lo[ax] + hi[ax]) / 2
        if pt[ax] < s:
            hi[ax] = s
        else:
            lo[ax] = s
        c = (lo[ax] + hi[ax]) / 2
        legs.append(abs(c - node[ax]))
        node[ax] = c
        level += 1
    last = abs(pt[0] - node[0]) + abs(pt[1] - node[1])
    legs.append(last)
    return sum(legs), legs


def spine_geom(P):
    sp = P.clock.get("spine", {}) or {}
    root = sp.get("die_root_um") or sp.get("root_um") or [P.W / 2, P.H / 2]
    outline = sp.get("die_outline_um") or [P.W, P.H]
    origins = sp.get("part_die_origin_um") or {}
    ps_mm = float(sp.get("branch_ps_per_mm", DEFAULT_PS_PER_MM))
    leaf = float(sp.get("branch_leaf_um", P.budgets.get("tap_pitch_um", 400.0)))
    return root, outline, origins, ps_mm, leaf


def tap_ports(P, tn):
    """every clock port of a type [(port, x, y, early_ps)]: the R4 grid / sink taps (early 0) + early core taps."""
    out = [(n, x, y, 0.0) for n, x, y in S.tap_grid(P, tn)]
    out += [(n, x, y, S.core_tap_early_ps(P, tp)) for n, x, y, tp in S.core_taps(P, tn)]
    return out


def branch_table(P, dropped=None):
    """{part: {"die_origin_um", "taps": {port: dict(xy_die, length_um, branch_ps, early_ps, offset_ps)}}} and the
    model parameters.  offset_ps = branch_ps - min(branch_ps over the plan) - early_ps (the source latency the die STA
    sets on the partition tap pin).  dropped {type: {port}}: taps without sinks (kit clock_taps.tcl) are skipped."""
    root, outline, origins, ps_mm, leaf = spine_geom(P)
    res = {}
    for name, p in sorted(P.parts.items()):
        tn = p["type"]
        o = origins.get(name, p["origin_um"])
        dx, dy = o[0] - p["origin_um"][0], o[1] - p["origin_um"][1]
        taps = {}
        for port, x, y, early in tap_ports(P, tn):
            if dropped and port in dropped.get(tn, ()):
                continue
            X, Y = P.to_die(name, (x, y))
            X, Y = X + dx, Y + dy
            L, legs = htree_path(root, outline, (X, Y), leaf)
            taps[port] = dict(xy_die=[round(X, 3), round(Y, 3)], length_um=round(L, 2),
                              legs_um=[round(v, 1) for v in legs], branch_ps=round(L / 1000.0 * ps_mm, 2),
                              early_ps=round(early, 2))
        res[name] = dict(type=tn, die_origin_um=list(o), taps=taps)
    allb = [t["branch_ps"] for r in res.values() for t in r["taps"].values()]
    ref = min(allb) if allb else 0.0
    for r in res.values():
        for t in r["taps"].values():
            t["offset_ps"] = round(t["branch_ps"] - ref - t["early_ps"], 2)
        bs = [t["branch_ps"] for t in r["taps"].values()]
        r["branch_ps_mean"] = round(sum(bs) / len(bs), 2) if bs else None
        r["offset_ps_mean"] = round(sum(t["branch_ps"] - ref for t in r["taps"].values()) / len(bs), 2) if bs else None
    return dict(model="htree", die_root_um=list(root), die_outline_um=list(outline), branch_ps_per_mm=ps_mm,
                branch_leaf_um=leaf, ref_branch_ps=ref, parts=res)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan))
    tab = branch_table(P)
    js = json.dumps(tab, indent=1)
    if a.out:
        Path(a.out).write_text(js + "\n")
    for n, r in tab["parts"].items():
        print(f"{n} ({r['type']}): branch mean {r['branch_ps_mean']} ps, offset mean {r['offset_ps_mean']} ps over "
              f"{len(r['taps'])} taps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
