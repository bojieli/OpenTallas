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

CLK-STD (owner 10-23 ~23:30, industry multi-source CTS) -- the default model is now "zst", a STRUCTURED SPINE built and
balanced by construction (zst_tree), not the bisection estimate above (clock.spine.model "htree" keeps it):

  topology  die level: seam-aware recursive bisection of the partitions (each cut is the axis-aligned split, between
            partition centres, that cuts the fewest seam bits -- the plan ports between the two halves -- with a
            balance penalty), so partitions that share heavy seams hang off the same branch as deep as possible
            (fix 6); partition level: each partition's connected taps under ONE partition entry node (its clock port
            feeds its tap tree), bisected geometrically (larger extent, median split).
  geometry  bottom-up zero-skew merge (Tsay / DME on the Manhattan metric, repeated wire = delay linear in length):
            the merge point of two subtrees sits on their connecting L path where both root->leaf lengths are equal;
            when they cannot be equalised on the straight path, the shorter leg gets a snake (pad_um).  Every die-root
            -> tap path therefore has the SAME length by construction; horizontal legs ride M8, vertical legs M9
            (die layer_budget.die_layers), non-default rule 2W2S (clock.spine.ndr), repeaters every <= die.rep_um.
  outputs   spine_tree.json (gen.py assembly): nodes, legs (length, layer, pad, repeaters), per-tap path length and
            latency, per-partition entry node, per-seam shared path (length from the die root to the lowest common
            branch of the two partitions; unshared = path - shared) -- fix 6 report.
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
    """clock.spine.model "zst" (default, CLK-STD): zst_branch_table; "htree": the bisection estimate below.
    {part: {"die_origin_um", "taps": {port: dict(xy_die, length_um, branch_ps, early_ps, offset_ps)}}} and the
    model parameters.  offset_ps = branch_ps - min(branch_ps over the plan) - early_ps (the source latency the die STA
    sets on the partition tap pin).  dropped {type: {port}}: taps without sinks (kit clock_taps.tcl) are skipped."""
    if (P.clock.get("spine", {}) or {}).get("model", "zst") == "zst":
        return zst_branch_table(P, dropped)
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
    if (P.clock.get("spine", {}) or {}).get("model", "zst") == "zst":
        tr = zst_tree(P)
        if a.out:
            Path(a.out).write_text(json.dumps(tr, indent=1) + "\n")
        print(f"zst spine: root {tr['root_um']}, path {tr['path_um']} um (every tap), wire {tr['wire_um']} um, "
              f"snake {tr['snake_um']} um, {tr['repeaters']} repeaters, layers {tr['layers']}, NDR {tr['ndr']}")
        for sm in sorted(tr["seams"], key=lambda z: -z["bits"]):
            print(f"seam {sm['parts'][0]}|{sm['parts'][1]} {sm['bits']} b: shared {sm['shared_um']} um "
                  f"({100 * sm['shared_frac']:.0f}%), unshared {sm['unshared_um']} um")
        return 0
    tab = branch_table(P)
    js = json.dumps(tab, indent=1)
    if a.out:
        Path(a.out).write_text(js + "\n")
    for n, r in tab["parts"].items():
        print(f"{n} ({r['type']}): branch mean {r['branch_ps_mean']} ps, offset mean {r['offset_ps_mean']} ps over "
              f"{len(r['taps'])} taps")
    return 0



# ------------------------------------------------------------------------------------- CLK-STD structured spine (zst)
def seam_bits(P):
    """{frozenset({a, b}): bits} of the plan ports between two partitions (die IO excluded)."""
    out = {}
    for pr in P.ports.values():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if S.DIE_PART in (a, b) or a == b:
            continue
        k = frozenset((a, b))
        out[k] = out.get(k, 0) + S.port_pins_count(pr)
    return out


def _part_centre(P, name):
    x0, y0, x1, y1 = P.rect(name)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def seam_bisect(P, names, bits=None, balance_w=0.5):
    """seam-aware recursive bisection -> nested tuples of partition names (leaves = names)."""
    bits = seam_bits(P) if bits is None else bits
    names = sorted(names)
    if len(names) == 1:
        return names[0]
    tot = sum(v for k, v in bits.items() if k <= set(names)) or 1
    cen = {n: _part_centre(P, n) for n in names}
    best = None
    for ax in (0, 1):
        order = sorted(names, key=lambda n: (cen[n][ax], cen[n][1 - ax], n))
        for k in range(1, len(order)):
            if abs(cen[order[k]][ax] - cen[order[k - 1]][ax]) < 1e-6:
                continue                       # a cut runs BETWEEN partition centres
            a, b = set(order[:k]), set(order[k:])
            cut = sum(v for kk, v in bits.items() if len(kk & a) == 1 and len(kk & b) == 1)
            score = cut / tot + balance_w * abs(len(a) - len(b)) / len(names)
            key = (round(score, 9), abs(len(a) - len(b)), ax, k)
            if best is None or key < best[0]:
                best = (key, sorted(a), sorted(b))
    if best is None:                           # coincident centres: split the sorted list
        h = len(names) // 2
        best = (None, names[:h], names[h:])
    return (seam_bisect(P, best[1], bits, balance_w), seam_bisect(P, best[2], bits, balance_w))


def geo_bisect(items):
    """[(key, x, y)] -> nested tuples of keys: split at the median of the larger extent."""
    if len(items) == 1:
        return items[0][0]
    xs = [i[1] for i in items]
    ys = [i[2] for i in items]
    ax = 1 if (max(ys) - min(ys)) > (max(xs) - min(xs)) else 2
    o = sorted(items, key=lambda i: (i[ax], i[3 - ax], i[0]))
    h = len(o) // 2
    return (geo_bisect(o[:h]), geo_bisect(o[h:]))


def _toward(a, b, t):
    """point at Manhattan distance t from a along the L path a -> b (x first, then y)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if t <= abs(dx):
        return (a[0] + math.copysign(t, dx) if dx else a[0], a[1])
    t -= abs(dx)
    return (b[0], a[1] + (math.copysign(min(t, abs(dy)), dy) if dy else 0.0))


def zst_merge(a, b):
    """zero-skew merge of subtrees a, b = (xy, D) with D = root->leaf length below the subtree root.
    Returns (xy, D, la, lb, pad_a, pad_b): merge point, its depth, the two leg lengths and their snake pads."""
    (pa, Da), (pb, Db) = a, b
    d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
    x = (Db - Da + d) / 2.0
    if x < 0:          # a is already deeper than b + the whole path: merge at a, snake b's leg
        return pa, Da, 0.0, Da - Db, 0.0, Da - Db - d
    if x > d:
        return pb, Db, Db - Da, 0.0, Db - Da - d, 0.0
    return _toward(pa, pb, x), Da + x, x, d - x, 0.0, 0.0


def zst_tree(P, dropped=None, root=None):
    """CLK-STD structured spine (module doc): dict(nodes, taps, parts, seams, root_um, path_um, ...)."""
    dropped = dropped or {}
    sp = P.clock.get("spine", {}) or {}
    root = root or sp.get("die_root_um") or sp.get("root_um") or [P.W / 2.0, P.H / 2.0]
    ps_mm = float(sp.get("branch_ps_per_mm", DEFAULT_PS_PER_MM))
    origins = sp.get("part_die_origin_um") or {}
    die_l = P.layer_budget.get("die_layers", ["M8", "M9"])
    lay_h = next((L for L in die_l if P.layers.get(L, {}).get("dir") == "H"), die_l[0])
    lay_v = next((L for L in die_l if P.layers.get(L, {}).get("dir") == "V"), die_l[-1])
    rep = float(P.rep_um)
    nodes = []

    def add(kind, xy, D, children=(), **kw):
        nodes.append(dict(id=len(nodes), kind=kind, xy=[round(xy[0], 3), round(xy[1], 3)], depth_um=round(D, 3),
                          children=list(children), **kw))
        return len(nodes) - 1

    taps_of = {}
    by_type = {}
    for name, p in sorted(P.parts.items()):
        tn = p["type"]
        if tn not in by_type:
            by_type[tn] = tap_ports(P, tn)
        o = origins.get(name, p["origin_um"])
        dx, dy = o[0] - p["origin_um"][0], o[1] - p["origin_um"][1]
        tl = []
        for port, x, y, early in by_type[tn]:
            if port in dropped.get(tn, ()):
                continue
            X, Y = P.to_die(name, (x, y))
            tl.append((port, X + dx, Y + dy, early))
        taps_of[name] = tl

    def build(t, leaf_fn):
        if not isinstance(t, tuple):
            return leaf_fn(t)
        ia, ib = build(t[0], leaf_fn), build(t[1], leaf_fn)
        na, nb = nodes[ia], nodes[ib]
        xy, D, la, lb, pa_, pb_ = zst_merge((na["xy"], na["depth_um"]), (nb["xy"], nb["depth_um"]))
        na["leg_um"], na["pad_um"] = round(la, 3), round(pa_, 3)
        nb["leg_um"], nb["pad_um"] = round(lb, 3), round(pb_, 3)
        return add("branch", xy, D, (ia, ib))

    part_entry = {}

    def part_leaf(name):
        tl = taps_of[name]

        def tap_leaf(port):
            _, X, Y, early = next(t for t in tl if t[0] == port)
            return add("tap", (X, Y), 0.0, part=name, port=port, early_ps=early)
        if not tl:
            raise ValueError(f"partition {name}: no connected clock tap")
        i = build(geo_bisect([(t[0], t[1], t[2]) for t in tl]), tap_leaf)
        nodes[i]["entry_of"] = name
        part_entry[name] = i
        return i

    top = build(seam_bisect(P, list(P.parts)), part_leaf)
    D = nodes[top]["depth_um"]
    rl = abs(root[0] - nodes[top]["xy"][0]) + abs(root[1] - nodes[top]["xy"][1])
    nodes[top]["leg_um"], nodes[top]["pad_um"] = round(rl, 3), 0.0
    parent = {}
    for n in nodes:
        for c in n["children"]:
            parent[c] = n["id"]
    root_id = add("root", root, D + rl, (top,))
    parent[top] = root_id
    # legs: L route child -> parent, x first on the H layer, then y on the V layer; repeaters every rep_um
    for n in nodes:
        if n["id"] == root_id:
            continue
        pxy = nodes[parent[n["id"]]]["xy"]
        hx, vy = abs(n["xy"][0] - pxy[0]), abs(n["xy"][1] - pxy[1])
        leg = n["leg_um"]
        n["parent"] = parent[n["id"]]
        n["segments"] = [s_ for s_ in ({"layer": lay_h, "um": round(hx, 3)}, {"layer": lay_v, "um": round(vy, 3)})
                         if s_["um"] > 0]
        n["repeaters"] = int(math.ceil(leg / rep)) - 1 if leg > rep else 0

    def path(i):
        out = []
        while i in parent:
            out.append(i)
            i = parent[i]
        return out

    def path_len(i):
        return sum(nodes[j]["leg_um"] for j in path(i))
    taps = {}
    for n in nodes:
        if n["kind"] != "tap":
            continue
        L = path_len(n["id"])
        taps.setdefault(n["part"], {})[n["port"]] = dict(
            node=n["id"], xy_die=n["xy"], length_um=round(L, 2), branch_ps=round(L / 1000.0 * ps_mm, 2),
            early_ps=round(n["early_ps"], 2))
    seams = []
    bits = seam_bits(P)
    for k, v in sorted(bits.items(), key=lambda kv: sorted(kv[0])):
        a, b = sorted(k)
        pa_, pb_ = path(part_entry[a]), path(part_entry[b])
        common = [i for i in pa_ if i in set(pb_)]
        lca = common[0] if common else root_id
        shared = D + rl - nodes[lca]["depth_um"]       # die root -> lowest common branch (zero skew below)
        seams.append(dict(parts=[a, b], bits=v, lca=lca, shared_um=round(shared, 2),
                          unshared_um=round(D + rl - shared, 2),
                          shared_frac=round(shared / (D + rl), 4) if D + rl else 1.0))
    tot_len = sum(n.get("leg_um", 0.0) for n in nodes if n["id"] != root_id)
    return dict(model="zst", root_um=list(root), path_um=round(D + rl, 2), branch_ps_per_mm=ps_mm,
                layers=dict(H=lay_h, V=lay_v), ndr=sp.get("ndr", "2W2S"), rep_um=rep,
                wire_um=round(tot_len, 1), snake_um=round(sum(n.get("pad_um", 0.0) for n in nodes), 1),
                repeaters=sum(n.get("repeaters", 0) for n in nodes),
                part_entry={k: nodes[v]["xy"] for k, v in part_entry.items()},
                nodes=nodes, taps=taps, seams=seams)


def zst_branch_table(P, dropped=None):
    """branch_table() in the zst model: every tap's branch latency is the same by construction; offset_ps = - early."""
    tr = zst_tree(P, dropped)
    ps_mm = tr["branch_ps_per_mm"]
    res = {}
    allb = [t["branch_ps"] for r in tr["taps"].values() for t in r.values()]
    ref = min(allb) if allb else 0.0
    for name, p in sorted(P.parts.items()):
        tt = tr["taps"].get(name, {})
        taps = {}
        for port, v in tt.items():
            taps[port] = dict(v, offset_ps=round(v["branch_ps"] - ref - v["early_ps"], 2))
        bs = [t["branch_ps"] for t in taps.values()]
        res[name] = dict(type=p["type"], die_origin_um=list((P.clock.get("spine", {}) or {}).get(
            "part_die_origin_um", {}).get(name, p["origin_um"])), taps=taps,
            branch_ps_mean=round(sum(bs) / len(bs), 2) if bs else None,
            offset_ps_mean=round(sum(b - ref for b in bs) / len(bs), 2) if bs else None)
    return dict(model="zst", die_root_um=tr["root_um"], die_outline_um=[P.W, P.H], branch_ps_per_mm=ps_mm,
                branch_leaf_um=None, ref_branch_ps=ref, path_um=tr["path_um"], parts=res, seams=tr["seams"])


if __name__ == "__main__":
    sys.exit(main())
