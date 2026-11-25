#!/usr/bin/env python3
"""tree_eco.py -- incremental die clock re-site (CLK-ECO-1, HEAD-ALLFIX C3 11-25): keep a die clock tree of record, re-route
only what the CURRENT plan changed, against the CURRENT floors.  Die-agnostic: no die, type or region name in this file.

Why: a fresh one-shot tree does not converge on the arrivals of the taps that did not move (HEAD W7: fresh tree 9b8fe44bc4aa
drifts sd 44 ps on 143 unmoved hd_lep0N taps against r13), so every tap-offset table written against the clock of record
goes stale at once.  Industry ECO-CTS keeps the tree of record and only re-attaches the changed sinks.

Steps (all on the kit's own geometry: die_trial.clock_taps(P) and die_trial.clock_site(P) of the CURRENT plan):
  1 MATCH   every current tap against the base tree's taps BY SITE (same part, |dx|+|dy| <= --match-um), one to one, name
            agnostic (a density/sink-bin re-solve renumbers clk_t<i>; a name match would pair unrelated places); then any
            part at the same die site (a part split after the base tree inherits the leaves at its sites).  A matched
            tap keeps its leaf node (its port name is refreshed); its arrival is unchanged by construction.
  2 GONE    a base tap with no current tap at its site frees its leaf node (the leaf is reused by step 3 or pruned; empty
            internal nodes are pruned upward).
  3 ATTACH  every unmatched current tap (moved or new) gets a leaf, cheapest first by the arrival error against its target
            (model arrival of the same-name base tap when it was a core tap, else the median model arrival of the part's
            matched glue taps): (a) a freed leaf of the same part moves to the new site under its old parent (no load
            change for any other tap), or (b) a new leaf hangs on an internal node of the tap's region (that node's subtree
            pays one fanout term, charged in the cost).  Model = the config's stage calibration (leg [d0,k1,k2,kf], tap
            [k1,k2]), the same model die_trial's DME prices with; base legs keep their recorded physical_leg delay.
  4 RESITE  (a) every leaf farther than --max-leaf-leg-um from its tap moves to the nearest legal site to the tap when that
            site is closer (a tree legalised against an older, larger keep-out leaves its leaf drivers stranded at the old
            edge); (b) inside the outlines of --resite-types, each internal node lifts to the point of the intersection of
            the [parent, kid] boxes nearest its kids' centroid: every root->kid Manhattan length is preserved exactly, the
            pile-up at an old keep-out edge spreads; a lift whose model delay change on any kid exceeds --lift-tol-ps is
            not taken.
  Moved nodes lose their physical_leg chain; die_trial kit --tree-json re-lays those legs on its own legal-site map and
  fixes inverter parity exactly (load_stamped_tree -> legalize_stamped_nodes + clksite_stamp_native.fix_parity).

usage: tree_eco.py BASE_TREE.json PLAN.json --plan-root DIR --out TREE.json [--stage-cal CAL.json] [--regions REG.json]
                   [--match-um 0.05] [--max-leaf-leg-um 2.0] [--resite-types T,T] [--lift-tol-ps 1.0]
Writes TREE.json (die_trial kit --tree-json input) and TREE.json.report.json.
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIE_PLAN = HERE.parent / "die_plan"

DEFAULT_CAL = dict(leg=[8.8, 0.24, 0.0, 10.0], tap=[0.1466, 0.000484])


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Model:
    """die_trial DME stage model: leg of L um = n stages (n = ceil(L / rep)) n*d0 + k1*L + k2*L^2/n; tap wire k1*d + k2*d^2;
    kf per extra fanout at the driving node."""
    def __init__(self, cal=None, rep_um=150.0):
        c = cal or DEFAULT_CAL
        self.d0, self.k1, self.k2, self.kf = (float(x) for x in c["leg"])
        self.t1, self.t2 = (float(x) for x in c["tap"])
        self.rep = float(rep_um)

    def leg(self, L):
        n = max(1, int(math.ceil(L / self.rep - 1e-9)))
        return n * self.d0 + self.k1 * L + self.k2 * L * L / n

    def tap(self, d):
        return self.t1 * d + self.t2 * d * d


def subtree_taps(nodes, tap_of):
    """{node id: number of taps under it}"""
    cnt = defaultdict(int)
    for i in tap_of.values():
        j = i
        while j is not None:
            cnt[j] += 1
            j = nodes[j]["parent"]
    return cnt


def arrivals(nodes, model):
    """model arrival (ps) at every node: recorded physical_leg delay where the leg is kept, else the stage model"""
    arr = {}
    order = sorted(nodes, key=lambda i: nodes[i].get("level", 0))
    for i in order:
        v = nodes[i]
        p = v.get("parent")
        if p is None or p not in nodes:
            arr[i] = 0.0
            continue
        if p not in arr:          # level not monotone: resolve the parent chain first
            stack = [i]
            while stack[-1] is not None and nodes[stack[-1]].get("parent") in nodes and nodes[stack[-1]]["parent"] not in arr:
                stack.append(nodes[stack[-1]]["parent"])
            for j in reversed(stack):
                q = nodes[j].get("parent")
                arr[j] = (arr.get(q, 0.0) if q in nodes else 0.0) + leg_delay(nodes, j, model)
            continue
        arr[i] = arr[p] + leg_delay(nodes, i, model)
    return arr


def leg_delay(nodes, i, model):
    v = nodes[i]
    pl = v.get("physical_leg")
    if pl and pl.get("delay_ps") is not None:
        return float(pl["delay_ps"])
    p = nodes[v["parent"]]
    return model.leg(man((p["x"], p["y"]), (v["x"], v["y"]))) + model.kf * max(0, len(p.get("kids", [])) - 1)


def region_of_nodes(nodes):
    """{node id: region name}: the node's own dme / region_root tag, else its nearest tagged ancestor"""
    out = {}
    for i in nodes:
        chain, j, lab = [], i, None
        while j is not None and j in nodes:
            if j in out:
                lab = out[j]
                break
            v = nodes[j]
            lab = v.get("dme") or v.get("region_root")
            if lab:
                break
            chain.append(j)
            j = v.get("parent")
        out[i] = lab
        for c in chain:
            out[c] = lab
    return out


def match_taps(base_taps, cur_taps, tol=0.05):
    """one-to-one BY SITE within a part.  base_taps [{part, tap, xy, node}], cur_taps [(part, port, x, y)] ->
    (matched {cur index: base index}, unmatched cur indices, gone base indices)"""
    by_part = defaultdict(list)
    for k, t in enumerate(base_taps):
        by_part[t["part"]].append(k)
    used, matched, unm = set(), {}, []
    for ci, (part, port, x, y) in enumerate(cur_taps):
        best = None
        for k in by_part.get(part, ()):
            if k in used:
                continue
            d = man(base_taps[k]["xy"], (x, y))
            if d <= tol and (best is None or d < best[0] or (d == best[0] and base_taps[k]["tap"] == port)):
                best = (d, k)
        if best is None:
            unm.append(ci)
        else:
            used.add(best[1])
            matched[ci] = best[1]
    # second pass, any part: a part split after the base tree inherits the leaves at its sites (renamed port)
    grid = defaultdict(list)
    for k in range(len(base_taps)):
        if k not in used:
            x, y = base_taps[k]["xy"]
            grid[(round(x), round(y))].append(k)
    still = []
    for ci in unm:
        part, port, x, y = cur_taps[ci]
        best = None
        for gx in (round(x) - 1, round(x), round(x) + 1):
            for gy in (round(y) - 1, round(y), round(y) + 1):
                for k in grid.get((gx, gy), ()):
                    if k in used:
                        continue
                    d = man(base_taps[k]["xy"], (x, y))
                    if d <= tol and (best is None or d < best[0]):
                        best = (d, k)
        if best is None:
            still.append(ci)
        else:
            used.add(best[1])
            matched[ci] = best[1]
    gone = [k for k in range(len(base_taps)) if k not in used]
    return matched, still, gone


def prune(nodes, i, keep_ids=()):
    """remove node i if it has no kids and no taps; walk up"""
    removed = []
    while i is not None and i in nodes and i not in keep_ids:
        v = nodes[i]
        if v.get("kids") or v.get("_ntap", 0) or v.get("parent") is None:
            break
        p = v["parent"]
        del nodes[i]
        removed.append(i)
        if p in nodes:
            nodes[p]["kids"] = [k for k in nodes[p]["kids"] if k != i]
        i = p
    return removed


def drop_chain(v):
    for k in ("physical_leg", "detour", "detour_um", "stamp_leg"):
        v.pop(k, None)
    v["_relaid"] = True


def natural_nrep(a, b, rep_um=150.0):
    return max(0, math.ceil(man((a["x"], a["y"]), (b["x"], b["y"])) / rep_um) - 1)


def repair_parity(nodes, base_parity, nrep_fn):
    """top-down: a re-laid leg (no chain) takes the parity the kit's own layout gives (parent ^ (stages & 1)), so the kit's
    fix_parity inserts no parity node; a kept chain keeps its parity RELATIVE to its parent.  -> number of nodes flipped"""
    order = sorted(nodes, key=lambda i: nodes[i].get("level", 0))
    flipped = 0
    done = set()
    def visit(i):
        nonlocal flipped
        stack = [i]
        while stack:
            j = stack.pop()
            v = nodes[j]
            p = nodes.get(v.get("parent"))
            if p is not None:
                if v.get("_relaid"):
                    want = (p.get("inv_parity", 0) ^ ((nrep_fn(p, v) + 1) & 1)) & 1
                else:
                    rel = (base_parity.get(j, v.get("inv_parity", 0)) ^ base_parity.get(v["parent"], p.get("inv_parity", 0))) & 1
                    want = (p.get("inv_parity", 0) ^ rel) & 1
                if want != v.get("inv_parity", 0):
                    v["inv_parity"] = want
                    flipped += 1
            done.add(j)
            stack.extend(k for k in v.get("kids", []) if k in nodes)
    for i in order:
        if nodes[i].get("parent") is None and i not in done:
            visit(i)
    return flipped


def keep_interval(v0, p, ks):
    """one axis of a Manhattan-length-preserving move of a node at v0 between parent p and kids ks: |p - v| + |v - k| stays
    equal for every kid iff v stays in [min(p, k), max(p, k)] for each kid whose interval holds v0 (else v = v0)."""
    lo, hi = v0, v0
    first = True
    for k in ks:
        a, b = min(p, k), max(p, k)
        if not (a - 1e-9 <= v0 <= b + 1e-9):
            return [v0, v0]
        lo, hi = (a, b) if first else (max(lo, a), min(hi, b))
        first = False
    return [lo, hi]


def eco(base, cur_taps, site, model, part_region, part_type=None, part_box=None, match_um=0.05, max_leaf_leg_um=2.0,
        resite_types=(), lift_tol_ps=1.0, nrep_fn=None):
    """base: tree.json dict; cur_taps [(part, port, x, y)]; site: object with legal(q) / nearest(q); part_region {part: region}.
    -> (tree.json dict, report dict).  Pure: base is not modified."""
    nodes = {int(k): json.loads(json.dumps(v)) for k, v in base["nodes"].items()}
    btaps = base["taps"]
    base_parity = {i: v.get("inv_parity", 0) for i, v in nodes.items()}
    arr0 = arrivals(nodes, model)
    reg = region_of_nodes(nodes)
    matched, unm, gone = match_taps(btaps, cur_taps, match_um)
    base_arr = {k: arr0[t["node"]] + model.tap(man(t["xy"], (nodes[t["node"]]["x"], nodes[t["node"]]["y"])))
                for k, t in enumerate(btaps)}
    # targets: part median of matched glue taps
    glue = defaultdict(list)
    for ci, k in matched.items():
        if not cur_taps[ci][1].startswith("clk_c"):
            glue[cur_taps[ci][0]].append(base_arr[k])
    med = {p: statistics.median(v) for p, v in glue.items()}
    region_med = defaultdict(list)
    for p, v in med.items():
        region_med[part_region.get(p)].append(v)
    rmed = {r: statistics.median(v) for r, v in region_med.items()}
    base_by_name = {(t["part"], t["tap"]): k for k, t in enumerate(btaps)}
    new_taps = []                 # [(part, port, x, y, node)]
    for ci, k in matched.items():
        p, port, x, y = cur_taps[ci]
        new_taps.append([p, port, x, y, btaps[k]["node"]])
        nodes[btaps[k]["node"]]["_ntap"] = 1
    free = defaultdict(list)      # part -> freed leaf ids
    for k in gone:
        t = btaps[k]
        free[t["part"]].append(t["node"])
    # candidate internal nodes per region
    internal = defaultdict(list)
    for i, v in nodes.items():
        if v.get("kids"):
            internal[reg.get(i)].append(i)
    ntap_under = subtree_taps(nodes, {k: t["node"] for k, t in enumerate(btaps)})
    work = []
    for ci in unm:
        p, port, x, y = cur_taps[ci]
        kb = base_by_name.get((p, port))
        if port.startswith("clk_c") and kb is not None:
            tgt = base_arr[kb]
        else:
            tgt = med.get(p, rmed.get(part_region.get(p)))
        kind = "moved" if kb is not None else "new"
        work.append(dict(ci=ci, part=p, port=port, xy=(x, y), target=tgt, kind=kind,
                         region=part_region.get(p)))
    att = []
    used_free = set()
    pending = list(work)
    while pending:
        best = None
        for w in pending:
            q = site.nearest(w["xy"]) if not site.legal(w["xy"]) else w["xy"]
            dtap = man(q, w["xy"])
            opts = []
            for lf in free.get(w["part"], ()):
                if lf in used_free:
                    continue
                pa = nodes[lf]["parent"]
                a = arr0[pa] + model.leg(man((nodes[pa]["x"], nodes[pa]["y"]), q)) + model.tap(dtap)
                opts.append((abs(a - w["target"]) if w["target"] is not None else 0.0, "reuse", lf, pa, a))
            for c in internal.get(w["region"], ()):
                cv = nodes[c]
                L = man((cv["x"], cv["y"]), q)
                if L > 4 * model.rep:
                    continue
                a = arr0[c] + model.leg(L) + model.kf + model.tap(dtap)
                pen = model.kf + 0.05 * model.kf * ntap_under.get(c, 0)
                opts.append(((abs(a - w["target"]) if w["target"] is not None else 0.0) + pen, "hang", None, c, a))
            if not opts:
                continue
            o = min(opts, key=lambda z: (z[0], z[3]))
            if best is None or o[0] < best[1][0]:
                best = (w, o, q)
        if best is None:
            break
        w, o, q = best
        pending.remove(w)
        cost, how, lf, pa, a = o
        if how == "reuse":
            used_free.add(lf)
            v = nodes[lf]
            v["x"], v["y"] = round(q[0], 3), round(q[1], 3)
            v["req_xy"] = [v["x"], v["y"]]
            drop_chain(v)
            v["_ntap"] = 1
            nid = lf
        else:
            nid = max(nodes) + 1
            cv = nodes[pa]
            nodes[nid] = dict(id=nid, x=round(q[0], 3), y=round(q[1], 3), parent=pa, level=cv.get("level", 0) + 1, kids=[],
                              region=cv.get("region"), req_xy=[round(q[0], 3), round(q[1], 3)],
                              inv_parity=cv.get("inv_parity", 0), ntaps=1, _ntap=1, eco="hang", _relaid=True,
                              **({"dme": cv["dme"]} if cv.get("dme") else {}))
            cv["kids"] = list(cv["kids"]) + [nid]
        p, port, x, y = cur_taps[w["ci"]]
        new_taps.append([p, port, x, y, nid])
        att.append(dict(part=p, port=port, kind=w["kind"], how=how, node=nid, parent=pa, target_ps=None if w["target"] is None else round(w["target"], 1),
                        model_ps=round(a, 1), err_ps=None if w["target"] is None else round(a - w["target"], 1)))
    unplaced = [dict(part=w["part"], port=w["port"]) for w in pending]
    removed = []
    for lst in free.values():
        for lf in lst:
            if lf not in used_free and lf in nodes:
                nodes[lf]["_ntap"] = 0
                removed += prune(nodes, lf)
    # 4a leaf resite
    tap_of_node = {t[4]: t for t in new_taps}
    resite = []
    for t in new_taps:
        v = nodes[t[4]]
        d = man((v["x"], v["y"]), (t[2], t[3]))
        if d <= max_leaf_leg_um:
            continue
        q = (t[2], t[3]) if site.legal((t[2], t[3])) else site.nearest((t[2], t[3]))
        if man(q, (t[2], t[3])) + 1e-6 >= d:
            continue
        pa = nodes[v["parent"]]
        before = leg_delay(nodes, t[4], model) + model.tap(d)
        old = (v["x"], v["y"])
        v["x"], v["y"] = round(q[0], 3), round(q[1], 3)
        v["req_xy"] = [v["x"], v["y"]]
        drop_chain(v)
        after = model.leg(man((pa["x"], pa["y"]), (v["x"], v["y"]))) + model.tap(man(q, (t[2], t[3])))
        resite.append(dict(part=t[0], port=t[1], node=t[4], old=list(old), new=[v["x"], v["y"]], leg_was_um=round(d, 2),
                           model_delta_ps=round(after - before, 1)))
    # 4b monotone lift inside resite-type outlines
    lifted = []
    if resite_types and part_box:
        boxes = [b for p, b in part_box.items() if (part_type or {}).get(p) in set(resite_types)]
        def inside(q):
            return any(b[0] <= q[0] <= b[2] and b[1] <= q[1] <= b[3] for b in boxes)
        for _ in range(3):
            arr1 = arrivals(nodes, model)
            for i in sorted(nodes, key=lambda i: -nodes[i].get("level", 0)):
                v = nodes[i]
                if not v.get("kids") or v.get("parent") is None or not inside((v["x"], v["y"])):
                    continue
                p = nodes[v["parent"]]
                ks = [nodes[k] for k in v["kids"]]
                xs = keep_interval(v["x"], p["x"], [k["x"] for k in ks])
                ys = keep_interval(v["y"], p["y"], [k["y"] for k in ks])
                cx = statistics.mean(k["x"] for k in ks)
                cy = statistics.mean(k["y"] for k in ks)
                q = (min(max(cx, xs[0]), xs[1]), min(max(cy, ys[0]), ys[1]))
                if not site.legal(q):
                    q = site.nearest(q)
                if man(q, (v["x"], v["y"])) < 0.5 or not inside(q):
                    continue
                old = (v["x"], v["y"])
                def kid_ps(at):
                    return [model.leg(man((p["x"], p["y"]), at)) + model.leg(man(at, (k["x"], k["y"]))) for k in ks]
                d0, d1 = kid_ps(old), kid_ps(q)
                worst = max(abs(b - a) for a, b in zip(d0, d1))
                if worst > lift_tol_ps:
                    continue
                v["x"], v["y"] = round(q[0], 3), round(q[1], 3)
                v["req_xy"] = [v["x"], v["y"]]
                drop_chain(v)
                for k in ks:
                    drop_chain(k)
                lifted.append(dict(node=i, old=list(old), new=[v["x"], v["y"]], worst_kid_model_ps=round(worst, 2)))
    flipped = repair_parity(nodes, base_parity, nrep_fn or (lambda a, b: natural_nrep(a, b, model.rep)))
    relaid = 0
    for v in nodes.values():
        v["ntaps"] = v.pop("_ntap", 0)
        relaid += bool(v.pop("_relaid", False))
    taps_out = [dict(port=f"t_{p}__{port}", part=p, tap=port, xy=[x, y], node=n) for p, port, x, y, n in new_taps]
    tree = dict(meta=dict(base.get("meta", {})), nodes={str(i): v for i, v in sorted(nodes.items())}, taps=taps_out)
    tree["meta"]["eco"] = dict(tool="tools/clk/tree_eco.py (CLK-ECO-1)", matched=len(matched), attached=len(att),
                               unplaced=len(unplaced), gone=len(gone), pruned=len(removed), resited_leaves=len(resite),
                               lifted=len(lifted), relaid_legs=relaid, parity_set=flipped)
    kinds = defaultdict(lambda: defaultdict(int))
    for a in att:
        kinds[a["kind"]][a["how"]] += 1
    errs = [abs(a["err_ps"]) for a in att if a["err_ps"] is not None]
    rep = dict(counts=dict(current=len(cur_taps), base=len(btaps), matched=len(matched), unmatched=len(unm), gone=len(gone),
                           attached={k: dict(v) for k, v in kinds.items()}, unplaced=len(unplaced), pruned=len(removed),
                           resited_leaves=len(resite), lifted=len(lifted), relaid_legs=relaid, parity_set=flipped),
               attach_err_ps=dict(n=len(errs), max=round(max(errs), 1) if errs else None,
                                  p95=round(sorted(errs)[int(0.95 * (len(errs) - 1))], 1) if errs else None),
               attached=att, unplaced=unplaced, resite=resite, lifted=lifted)
    return tree, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("base_tree")
    ap.add_argument("plan")
    ap.add_argument("--plan-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage-cal", help="ot_clk_stage_cal.json ({leg, tap}); default the HEAD inv/ndr fit values")
    ap.add_argument("--rep-um", type=float, default=150.0)
    ap.add_argument("--regions", help="region map {part_region: {part: region}} (the kit's --region-trees file)")
    ap.add_argument("--match-um", type=float, default=0.05)
    ap.add_argument("--max-leaf-leg-um", type=float, default=2.0)
    ap.add_argument("--resite-types", default="")
    ap.add_argument("--lift-tol-ps", type=float, default=1.0)
    ap.add_argument("--tools", default=str(DIE_PLAN), help="die_plan tool dir whose die_trial/schema read the plan (a launch "
                    "tree's tools/die_plan when the plan's inputs live in that tree); default the sibling tools/die_plan")
    a = ap.parse_args(argv)
    sys.path[:0] = [str(a.tools)]
    import plan_inputs
    plan_inputs.set_roots(a.plan_root)
    import die_trial as D
    import schema as S
    P = S.Plan(S.load(a.plan), a.plan)
    cur = D.clock_taps(P)
    site = D.clock_site(P)
    base = json.loads(Path(a.base_tree).read_text())
    cal = json.loads(Path(a.stage_cal).read_text()) if a.stage_cal else None
    model = Model(cal, a.rep_um)
    pr = json.loads(Path(a.regions).read_text())["part_region"] if a.regions else {}
    if not pr:
        reg = region_of_nodes({int(k): v for k, v in base["nodes"].items()})
        for t in base["taps"]:
            pr.setdefault(t["part"], reg.get(t["node"]))
    ptype = {n: p["type"] for n, p in P.parts.items()}
    pbox = {}
    for n, p in P.parts.items():
        w, h = P.types[p["type"]]["outline_um"]
        c0, c1 = P.to_die(n, (0, 0)), P.to_die(n, (w, h))
        pbox[n] = (min(c0[0], c1[0]), min(c0[1], c1[1]), max(c0[0], c1[0]), max(c0[1], c1[1]))
    def nrep_fn(p, v):            # the kit's own leg layout (die_trial._leg_layout), as clksite_stamp_native.fix_parity
        return D._leg_layout(0, dict(v, physical_leg=None), p, site, a.rep_um, False)[1]
    tree, rep = eco(base, cur, site, model, pr, ptype, pbox, a.match_um, a.max_leaf_leg_um,
                    [t for t in a.resite_types.split(",") if t], a.lift_tol_ps, nrep_fn)
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    tree["meta"]["eco"].update(base_tree=str(a.base_tree), base_tree_sha256=sha(a.base_tree), plan=str(a.plan),
                               plan_sha256=sha(a.plan))
    rep["inputs"] = tree["meta"]["eco"]
    Path(a.out).write_text(json.dumps(tree) + "\n")
    Path(a.out + ".report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print("TREE-ECO", json.dumps(dict(rep["counts"], attach_err_ps=rep["attach_err_ps"])))
    return 0 if not rep["unplaced"] else 1


if __name__ == "__main__":
    sys.exit(main())
