#!/usr/bin/env python3
"""CLKSITE-RESERVE-1115 stamp mode, per type: pick ONE template region (an R0 instance whose entry point is the one wanted),
stamp its die clock cell sites and start-stage rows onto every instance of the type by the instance transform (cell box
mirrored, M7-PG-pair slide <= 1.3 um applied ONCE in the type frame), and emit
  STAMPED_TREE.json  {schema, meta, sites: {name: [x, y]}}  sites outside the type kept as in the source tree; the type's
                     sites replaced by <inst>__s<k> (SITES-ONLY: names are not kit tree nodes; the kit region-tree step must
                     build this tree natively -- see handoff). Consumed by head_island_template_delta_nf8.py --stamped.
  EXTRA.json         {type: [rect]}  entry feed / parity site + start-stage rows (<= 7), type frame
  REPORT.json        template choice, per-instance old/new site counts, entry legs, 405 um check of intra-region edges
usage: clksite_stamp_tree.py PLAN TREE.json START_STAGES.json TYPE OUTDIR [--entry X,Y]
"""
import argparse, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_stamp as K


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("tree"); ap.add_argument("stages"); ap.add_argument("type"); ap.add_argument("out")
    ap.add_argument("--entry", default="367.6,688.5")
    ap.add_argument("--max-slide", type=float, default=1.3)
    a = ap.parse_args(argv)
    import schema as S
    P = S.Plan(S.load(a.plan), Path(a.plan))
    T = json.load(open(a.tree))
    sites, parent = T["sites"], T.get("parent_of", {})
    size = tuple(P.types[a.type]["outline_um"])
    inst = [n for n, p in P.parts.items() if p["type"] == a.type]
    inside = {n: [] for n in inst}
    rects = {n: P.rect(n) for n in inst}
    for name, (x, y) in sites.items():
        for n in inst:
            r = rects[n]
            if r[0] <= x < r[2] and r[1] <= y < r[3]:
                inside[n].append(name); break
    ent = tuple(float(v) for v in a.entry.split(","))

    def entry_of(n):
        mem = set(inside[n])
        out = [m for m in mem if parent.get(m) not in mem]
        return [P.to_type(n, sites[m]) for m in out]
    cand = []
    for n in inst:
        if P.orient(n) != "R0" or not inside[n]:
            continue
        es = entry_of(n)
        d = min((math.dist(e, ent) for e in es), default=1e9)
        cand.append((d, -len(inside[n]), n))
    cand.sort()

    def _ctr(ll):      # tree.json site = body lower-left (R0 template): box centre
        return (ll[0] + 0.81, ll[1] + 0.135)

    def conflicts(n):
        """sites of instance n (type frame) whose box cannot clear an M7 PG pair within 1.3 um"""
        return [(m, [round(v, 3) for v in P.to_type(n, sites[m])]) for m in inside[n]
                if K.slide_off_pg(K.cell_box(_ctr(P.to_type(n, sites[m]))), a.max_slide)[0] is None]
    scan = {n: len(conflicts(n)) for _, _, n in cand}
    if not cand:
        raise SystemExit("no R0 template instance")
    tpl = cand[0][2]
    tsites = {m: _ctr(P.to_type(tpl, sites[m])) for m in inside[tpl]}
    boxes, slid, bad = {}, 0, []
    for m, xy in tsites.items():
        b, d = K.slide_off_pg(K.cell_box(xy), a.max_slide)
        if b is None:
            bad.append(m); b = K.cell_box(xy)
        else:
            slid += d > 0
        boxes[m] = b
    names = sorted(boxes)
    tmpl = [boxes[m] for m in names]
    # start-stage rows of the template instance (type frame, <= 7)
    st = []
    for s in json.load(open(a.stages))["stages"]:
        x0, y0, x1, y1 = s["rect_um"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        r = rects[tpl]
        if r[0] <= cx < r[2] and r[1] <= cy < r[3]:
            st.append(P.to_type(tpl, (cx, cy)))
    rows = K.start_stage_rows(st, 7, size=size)
    out_sites = {k: v for k, v in sites.items() if not any(k in inside[n] for n in inst)}
    for n in inst:
        o = P.orient(n)
        for i, bx in enumerate(tmpl):
            ox, oy = P.origin(n) if hasattr(P, "origin") else P.parts[n]["origin_um"]
            r = K.orient_rect(bx, size, o)
            lx, ly = K.site_ll((ox + r[0], oy + r[1], ox + r[2], oy + r[3]))     # body lower-left (builder convention)
            out_sites[f"{n}__s{i}"] = [round(lx, 4), round(ly, 4)]
    # intra-region edge lengths of the template (preserved exactly by the isometry)
    mem = set(inside[tpl])
    legs = [math.dist(sites[m], sites[parent[m]]) for m in mem if parent.get(m) in mem]
    entries = [round(min(math.dist(e, ent) for e in entry_of(n)), 1) for n in inst if inside[n] and entry_of(n)]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    meta = dict(schema="ot_clksite_stamped_tree/1", sites_only=True, type=a.type, template=tpl, entry=list(ent))
    json.dump(dict(meta=meta, sites=out_sites), open(Path(a.out) / "STAMPED_TREE.json", "w"))
    extra = {a.type: [list(r) for r in rows]}
    json.dump(extra, open(Path(a.out) / "EXTRA.json", "w"), indent=1)
    rep = dict(type=a.type, template=tpl, template_sites=len(tmpl), template_entry_offset_um=round(min((math.dist(e, ent) for e in entry_of(tpl)), default=-1), 1), max_slide_um=a.max_slide, instances=len(inst), slid=slid, no_slide_fit=len(bad), no_slide_fit_list=[[m, [round(v, 3) for v in tsites[m]]] for m in bad],
               pg_conflicts_per_candidate=dict(sorted(scan.items(), key=lambda kv: kv[1])[:15]), pg_conflicts_median=sorted(scan.values())[len(scan) // 2],
               stamped_sites=len(inst) * len(tmpl), old_site_counts=sorted({len(v) for v in inside.values()}),
               template_leg_max_um=round(max(legs, default=0), 1), template_legs_over_405=sum(l > 405 for l in legs),
               entry_offset_from_wanted_um=dict(min=min(entries), p50=sorted(entries)[len(entries)//2], max=max(entries)), start_stage_rows=len(rows),
               orients=sorted({P.orient(n) for n in inst}))
    json.dump(rep, open(Path(a.out) / "REPORT.json", "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
