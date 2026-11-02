#!/usr/bin/env python3
"""DIE-QC-58 11-01: QC landing-collector re-derive after the su_lane pin event (su_lane_repin.py, claude/die-qc-58-suw-1031).

The pin event re-pins the su_lane hard_cores of 9 types (sle_su_l0/_l1, slw_su_l0/_l1 classes), so reset_tree.for_type
of those types changes and the landing collector entries that name tree nodes go stale (strict bind: 'EMIT collector
rst_n_t3: raw reset parent rst_rl_8 absent' + 'wavefront core reset .../u_lane<k>.rst_n: expected one bound leaf,
found 0' on sle_su_l0__cl086d85ba).  Same one-block form as S81 delta_alltap_coll_1030.py (DIE-S81-45 t4/t13, COORD
22:5x 10-31 ruling 1), adapted to the QC files: plan = one-line json.dumps, sidecar = indent=1 json.  The sidecar boot
budget is recomputed only when the stored budget passes the recursion self-check (QC does not: 1256 vs 1258,
DIE-QC-58 00452027cbe); otherwise it is left unchanged and reported.
usage (repo root): TYPES_RE=... delta_su_coll_1101.py PLAN SIDECAR REPORT.json   (rewrites PLAN and SIDECAR in place)"""
import copy
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join("tools", "die_plan"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_tree as RT  # noqa: E402
import schema as S  # noqa: E402

TYPES = re.compile(os.environ["TYPES_RE"])   # DIE-S81-39 10-31: the types changed by delta_alltap_1030
REACH = 405


def norm(x):
    return json.loads(json.dumps(x))


def tapxy(tree):
    return {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}


def nearest(tree, xy):
    t = tapxy(tree)
    return min(range(RT.consumer_count(tree)), key=lambda i: abs(t[i][0] - xy[0]) + abs(t[i][1] - xy[1]))


def shift(node, c0, c1, tn):
    m = re.fullmatch(r"rst_n_t(\d+)", node)
    if not m:
        return node
    n = int(m.group(1))
    assert n >= c0, (tn, node, c0)          # only reset-out nodes may be shifted
    return f"rst_n_t{n - c0 + c1}"


def local_depth(inf):
    tree, rootnode = inf["tree"], inf["collector_root_node"]
    adj = defaultdict(list)
    for r in tree["relays"]:
        adj[r["q"]].append(r["d"])
        adj[r["d"]].append(r["q"])
    dist = {rootnode: 0}
    todo = [rootnode]
    while todo:
        n = todo.pop()
        for q in adj[n]:
            if q not in dist:
                dist[q] = dist[n] + 1
                todo.append(q)
    nodes = [f"rst_n_t{s['tap']}" for s in inf["local_sources"]] + [c["node"] for c in inf["children"]]
    return max([dist[n] + 1 for n in nodes] or [0])


def main():
    pp, sp, rp = sys.argv[1:4]
    text = open(pp).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    stext = open(sp).read()
    side = json.loads(stext)
    compact = json.dumps(side, separators=(",", ":")) + "\n" == stext
    assert compact or json.dumps(side, indent=1) + "\n" == stext, "sidecar format"
    assert json.dumps(raw) + "\n" == text, "plan text style is not one-line json.dumps"
    sorig = copy.deepcopy(side)
    P = S.Plan(S.load(pp), pp)
    W = RT.wf_plan(P)
    col = side["collector"]
    ct = col["types"]
    rep = {}
    for tn in sorted(ct):
        ent = ct[tn]
        if not TYPES.search(tn) or not ent.get("tree"):
            continue
        lc = raw["partition_types"][tn]["clock"]["landing_contract"]
        old = ent["tree"]
        assert lc["collector_tree"] == old and lc["collector_local_sources"] == ent["local_sources"] \
            and lc["collector_children"] == ent["children"] and lc.get("collector_root_node") == ent["collector_root_node"], tn
        T = norm(RT.for_type(P, tn))
        c0, c1 = RT.consumer_count(old), RT.consumer_count(T)
        srcs = []
        for s in ent["local_sources"]:
            s = copy.deepcopy(s)
            assert "node" not in s, (tn, s["name"])        # soft types only
            point = s["pin_xy_um"]
            tap = nearest(T, point)
            status = None
            band = s.get("band") or {}
            t = tapxy(T)
            if band.get("rect_um") and abs(t[tap][0] - point[0]) + abs(t[tap][1] - point[1]) > REACH:
                x0, y0, x1, y1 = band["rect_um"]
                status = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
                tap = nearest(T, status)
            s["tap"] = tap
            s["xy_um"] = status or point
            srcs.append(s)
        kids = [dict(c, node=shift(c["node"], c0, c1, tn)) for c in ent["children"]]
        rn = ent["collector_root_node"]
        m = re.fullmatch(r"rst_n_t(\d+)", rn)
        if m and int(m.group(1)) < c0:                  # collector root type: its leaf tap
            tap = RT.leaf_tap(P, tn)
            rn = f"rst_n_t{tap}"
            ent["collector_root_xy"] = next(r["xy"] for r in T["relays"] if r["q"] == rn)
        else:
            rn = shift(rn, c0, c1, tn)
        for n in [rn] + [c["node"] for c in kids] + [f"rst_n_t{s['tap']}" for s in srcs]:
            assert n == "rst_root_n" or any(r["q"] == n for r in T["relays"]), (tn, n)
        ent.update(tree=T, local_sources=srcs, children=kids, collector_root_node=rn)
        lc.update(collector_tree=T, collector_local_sources=srcs, collector_children=kids, collector_root_node=rn)
        rep[tn] = dict(taps=[c0, c1], relays=[len(old["relays"]), len(T["relays"])], depth=[old["depth"], T["depth"]],
                       source_taps=[[a["tap"], b["tap"]] for a, b in zip(sorig["collector"]["types"][tn]["local_sources"], srcs)],
                       children=[[a["node"], b["node"]] for a, b in zip(sorig["collector"]["types"][tn]["children"], kids)])
    # boot budget (compose's rule) from the actual trees
    bb = col.get("boot_budget")
    if isinstance(bb, dict) and "local_registered_depths" in bb:
        parts = col["parts"]
        for pn, d in list(bb["local_registered_depths"].items()):
            tn = parts[pn]["type"]
            if tn in rep:
                inf = ct[tn]
                bb["local_registered_depths"][pn] = len(inf["tree"]["relays"]) + 1 if inf["tree"].get("hard") else local_depth(inf)
        # deadline law of prepare_h2_2249.py (= compose): children of the part's type, seam 21 else STATUS_FACE_CYCLES
        import clock_landing_plan as CLP
        kids = defaultdict(list)
        for e in col["edges"]:
            kids[e["dst"]].append(dict(part=e["src"], seam=e["seam"]))
        dl = {}
        rel = bb["raw_reset_release_max_cycles"]

        def deadline(pn):
            if pn not in dl:
                # QC: children per PART from the collector edges (as coll_refresh_1031.py); per-type children
                # repeat over shared types and do not form a tree here
                ch = [deadline(c["part"]) + (21 if c["seam"] else CLP.STATUS_FACE_CYCLES) for c in kids[pn]]
                dl[pn] = max([rel + 21] + ch) + bb["local_registered_depths"][pn]
            return dl[pn]
        # self-check: the stored budget must be what this recursion gives on the OLD depths
        sb = sorig["collector"]["boot_budget"]
        saved = bb["local_registered_depths"]
        bb["local_registered_depths"] = sb["local_registered_depths"]
        dl.clear()
        got = deadline(col["root"])
        bb["local_registered_depths"] = saved
        dl.clear()
        if got != sb["ready_at_glue_max_cycles"]:      # QC: stored budget is not this recursion's -> leave it, report
            col["boot_budget"] = copy.deepcopy(sorig["collector"]["boot_budget"])
            rep["_boot_selfcheck"] = dict(stored=sb["ready_at_glue_max_cycles"], recursion=got,
                                          action="boot budget unchanged")
            bb = None
    if isinstance(bb, dict) and "local_registered_depths" in bb:
        # the added taps deepen the reset wavefront (one relay per tap): the raw release is re-read from the plan
        bb["raw_reset_release_max_cycles"] = rel = W["max_release"]
        bb["ready_at_glue_max_cycles"] = deadline(col["root"])
        rep["_boot"] = dict(raw_reset_release_max_cycles=[sb["raw_reset_release_max_cycles"], rel],
                            ready_at_glue_max_cycles=[sb["ready_at_glue_max_cycles"], bb["ready_at_glue_max_cycles"]],
                            depth_changes={pn: [sb["local_registered_depths"][pn], d] for pn, d in saved.items()
                                           if sb["local_registered_depths"][pn] != d})
        assert W["max_release"] == rel, (W["max_release"], rel)
    # nothing else changed
    for tn in raw["partition_types"]:
        a, b = raw["partition_types"][tn], orig["partition_types"][tn]
        if tn not in rep:
            assert a == b, tn
        else:
            a2, b2 = copy.deepcopy(a), copy.deepcopy(b)
            for k in ("collector_tree", "collector_local_sources", "collector_children", "collector_root_node"):
                a2["clock"]["landing_contract"].pop(k, None)
                b2["clock"]["landing_contract"].pop(k, None)
            assert a2 == b2, tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for k in side:
        if k != "collector":
            assert side[k] == sorig[k], k
    for k in col:
        if k not in ("types", "boot_budget"):
            assert col[k] == sorig["collector"][k], k
    for tn in ct:
        if tn not in rep:
            assert ct[tn] == sorig["collector"]["types"][tn], tn
    text = json.dumps(raw) + "\n"
    assert json.loads(text) == raw
    open(pp, "w").write(text)
    open(sp, "w").write(json.dumps(side, separators=(",", ":")) + "\n" if compact else json.dumps(side, indent=1) + "\n")
    json.dump(rep, open(rp, "w"), indent=1)
    print(len([t for t in rep if not t.startswith("_")]), "types refreshed;", json.dumps(rep.get("_boot", rep.get("_boot_selfcheck", {})))[:600])


if __name__ == "__main__":
    main()
