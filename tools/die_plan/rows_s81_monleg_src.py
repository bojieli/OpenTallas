#!/usr/bin/env python3
"""ROWS_S81-MONLEG-SRC = ROWS_KV-RCOLL-REBASE-RINS (4627b2f8dc04) with the band-flop centre added to the status points (S81-MONLEG 11-25, COORD ruling:
no re-point, add pipeline stations so every hop <= 405 um, status-path latency same or longer).  Applies after MONLEG-KV-A5t8 on the sources that
had no same-depth relay in reach.  Original header follows.

(KV-RCOLL-REBASE 11-23; FABLE-RC-KV 21:31 via COORD): reset-collector RELAY INSERTION.

Class: collector sources whose status pins sit > 405 um from their collector/reset node (A3g b258e3e34f22: the
collector_reach WARN, bind COLLECTOR-REACH-INFO).  Re-attachment cannot fix it (RCOLL2 4192328d3b62 = measured no-op:
no same-depth + same-predecessor + same-kind relay in reach of any of them; RCOLL v1 changed predecessor on 215/215).

Rule here: the source keeps its node N.  Below N we insert a chain of NEW collector relays X1..Xk
(X1.d = N, Xi+1.d = Xi, depth = depth(N)+i, kind = "cland_copy"), sited on an L path from N toward the source's pins,
every hop planned <= PLAN_UM (360, legalisation slack) and checked <= 405, sites pushed off placement obstacles
(reset_tree.blockages / push_off, the reset solve's own site test).  The source re-attaches to Xk.  Sources of the same
node share inserted relays when one is within reach of all their pins (one relay per source group).
So the predecessor chain to the root and the reset phase of N are unchanged; the source's reset/collector branch gets
+k cycles (boot only, 0 data cycles; START waits for root ready, so it releases at or after every reset).
The bind realises Xk as landing_collector.raw_reset copies u_cland_reset_<X> (d = parent's reset at its own site) plus
u_cland_collect_<X> (no bound-relay change, bound reset tree untouched).

Written to: plan partition_types[t].clock.landing_contract.{collector_tree.relays (+X), collector_local_sources /
collector_children node/tap} and the SAME into a NEW asbuilt clock_landing_table sidecar copy (collector.types[st]:
tree.relays, local_sources / children; R8 clones -> base_type entry, refused if the clones disagree).
Active collector EDGES over 405 (between existing relays) are reported, not changed (a bound reset edge).

usage: ROWS_KV-RCOLL-REBASE-RINS.py PLAN_IN PLAN_OUT [--json REPORT]
env: RC_TOOLS (tools/die_plan dir), RC_DRY=1 (no sidecar), else RC_ROOT, RC_AB_IN, RC_AB_OUT, RC_SC_OUT (tree-relative)
"""
import copy, json, math, os, re, sys
from pathlib import Path

sys.path.insert(0, os.environ.get("RC_TOOLS") or os.path.dirname(os.path.abspath(__file__)))
import reset_tree as RT  # noqa: E402
import collector_reach as CR  # noqa: E402

REACH, PLAN_UM, TOL = 405.0, 360.0, 1e-6
FROM_BAND = set()      # id() of sources whose xy_um was set to the band centre (no extra key is written into the plan)
argv = [a for a in sys.argv[1:]]
rep_path = None
if "--json" in argv:
    i = argv.index("--json"); rep_path = argv[i + 1]; del argv[i:i + 2]
plan_in, plan_out = argv
raw = json.loads(Path(plan_in).read_text())
DRY = os.environ.get("RC_DRY") == "1"

man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def pins_of(s, nxy, commit=True):
    """status points the leg must reach: the bind rule's (status_pins_xy_um, else xy_um) PLUS the ring-flop band centre
    (clock_landing_plan: the ready/fault flops sit in the band, not at the pin)  [MONLEG-SRC 11-25]."""
    pts = [tuple(p) for p in (s.get("status_pins_xy_um") or [s.get("xy_um", nxy)])]
    b = s.get("band") if isinstance(s.get("band"), dict) else None
    if b and b.get("rect_um"):
        r = b["rect_um"]
        bc = (round((r[0] + r[2]) / 2.0, 3), round((r[1] + r[3]) / 2.0, 3))
        if not s.get("status_pins_xy_um") and min(man(p, bc) for p in pts) > REACH:
            # the ring (band) was moved/resized away from its pin (KV-PVRING-1115 hard ring core): the ready/fault flops are in
            # the band, so the status point IS the band centre, as clock_landing_plan sets it when the pin is out of reach
            # (xy_um = status or point); pin_xy_um keeps the pin.  The bind rule then judges the same point the chain reaches.
            if commit:
                s["xy_um"] = list(bc)
                FROM_BAND.add(id(s))
            return [bc]
        pts.append(bc)
    return pts


def lpath_points(a, b, dists, xfirst):
    """points at path distances `dists` along the L route a->b (x first or y first)."""
    m = (b[0], a[1]) if xfirst else (a[0], b[1])
    l1 = man(a, m)
    out = []
    for d in dists:
        if d <= l1:
            f = d / l1 if l1 else 0
            out.append((a[0] + (m[0] - a[0]) * f, a[1] + (m[1] - a[1]) * f))
        else:
            l2 = man(m, b); f = (d - l1) / l2 if l2 else 0
            out.append((m[0] + (b[0] - m[0]) * f, m[1] + (b[1] - m[1]) * f))
    return out


def chain_sites(start, pins, boxes, box_out):
    """sites X1..Xk from `start` so start->X1, Xi->Xi+1 <= REACH and Xk -> every pin <= REACH (planned at PLAN_UM)."""
    c = (sum(p[0] for p in pins) / len(pins), sum(p[1] for p in pins) / len(pins))
    spread = max(man(c, p) for p in pins)
    last = PLAN_UM - spread
    if last < 20:
        return None, f"pin spread {spread:.1f}"
    best, why = None, "no legal chain"
    for xfirst in (True, False):
        for plan in (PLAN_UM, 330.0, 300.0, 250.0):
            L = man(start, c)
            lt = min(last, plan) * 0.5          # the last relay sits within lt of the centroid
            k = max(1, math.ceil((L - lt) / plan))
            step = (L - lt) / k                  # <= plan
            dists = [step * (i + 1) for i in range(k)]
            pts = lpath_points(start, c, dists, xfirst)
            pts = [tuple(RT.push_off(p, boxes, box_out)) for p in pts]
            seq = [start] + pts
            hops = [man(seq[i], seq[i + 1]) for i in range(len(seq) - 1)]
            tail = max(man(pts[-1], p) for p in pins)
            if max(hops) <= REACH + TOL and tail <= REACH + TOL:
                if best is None or len(pts) < len(best):
                    best = pts
                break
            why = f"hops {max(hops):.1f} tail {tail:.1f}"
    return best, why


types = raw["partition_types"]
sc = sct = None
if not DRY:
    root = Path(os.environ["RC_ROOT"])
    ab_in, ab_out, sc_out = os.environ["RC_AB_IN"], os.environ["RC_AB_OUT"], os.environ["RC_SC_OUT"]
    ab = json.loads((root / ab_in).read_text())
    sc = json.loads((root / ab["clock_landing_table"]).read_text()); sct = sc["collector"]["types"]

before = CR.find_all(raw)
report = dict(rule="relay insertion below the source node (same predecessor chain, +k collector/reset-copy depth)",
              before=dict(rows=len(before), sources=sum(r["kind"] == "source" for r in before),
                          edges=sum(r["kind"] == "edge" for r in before), types=len({r["type"] for r in before})),
              types={}, left=[], edges_left=[r for r in before if r["kind"] == "edge"])
st_result = {}
for tn in sorted(types):
    t = types[tn]
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    tr = lc.get("collector_tree")
    if not isinstance(tr, dict) or tr.get("hard") or not tr.get("relays"):
        continue
    nodes = {"rst_root_n": dict(xy=tr["root"], depth=0), **{r["q"]: r for r in tr["relays"]}}
    over = []
    for grp, key in (("collector_local_sources", "local_sources"), ("collector_children", "children")):
        for i, s in enumerate(lc.get(grp) or []):
            n = s.get("node", f"rst_n_t{s.get('tap', 0)}")
            if n not in nodes:
                continue
            pins = pins_of(s, nodes[n]["xy"], commit=False)
            hop = max(man(p, nodes[n]["xy"]) for p in pins)
            if hop > REACH + TOL:
                over.append((hop, grp, key, i, s, n, pins))
    if not over:
        continue
    W, H = t["outline_um"]
    box_out = (0.0, 0.0, float(W), float(H))
    boxes = RT.blockages(t)
    added, moves = [], []
    under = {}            # node N -> inserted relays below N (q list)
    for hop, grp, key, i, s, n, pins in sorted(over, key=lambda x: -x[0]):
        pins = pins_of(s, nodes[n]["xy"])      # commit: status point := band centre when the ring was moved away from its pin
        # 1) an inserted relay below N already reaches every pin -> share it
        cand = sorted((max(man(p, nodes[q]["xy"]) for p in pins), q) for q in under.get(n, []))
        if cand and cand[0][0] <= REACH + TOL:
            tgt = cand[0][1]
        else:
            # 2) grow a chain from the nearest of N / its inserted relays
            starts = sorted((man(nodes[q]["xy"], pins[0]), q) for q in [n] + under.get(n, []))
            tgt, why = None, ""
            for _, sq in starts[:3]:
                pts, why = chain_sites(tuple(nodes[sq]["xy"]), pins, boxes, box_out)
                if pts:
                    par = sq
                    for p in pts:
                        q = "rst_cx_%d" % (1 + max([int(x[7:]) for x in nodes if re.fullmatch(r"rst_cx_[0-9]+", x)] or [-1]))
                        r = dict(name=f"u_{q}", xy=[round(p[0], 3), round(p[1], 3)], d=par, q=q,
                                 depth=nodes[par]["depth"] + 1, kind="cland_copy", base_node=n)
                        nodes[q] = r; added.append(r); under.setdefault(n, []).append(q); par = q
                    tgt = par
                    break
            if tgt is None:
                report["left"].append(dict(type=tn, src=s.get("name", f"child{i}"), node=n, hop_um=round(hop, 1), why=why))
                continue
        s["node"] = tgt
        s.pop("tap", None)
        moves.append(dict(grp=key, src=s.get("name") if key == "local_sources" else s.get("index", i), node=n, xy=(list(s['xy_um']) if id(s) in FROM_BAND else None),
                          new=tgt, old_hop=round(hop, 1), new_hop=round(max(man(p, nodes[tgt]["xy"]) for p in pins), 1),
                          added_depth=nodes[tgt]["depth"] - nodes[n]["depth"], node_depth=nodes[n]["depth"]))
    tr["relays"].extend(added)
    report["types"][tn] = dict(added=len(added), moved=len(moves), max_added_depth=max((m["added_depth"] for m in moves), default=0),
                               max_node_depth_after=max((nodes[m["new"]]["depth"] for m in moves), default=0), moves=moves,
                               relays=added)
    st = tn if (sct is None or tn in sct) else (t.get("base_type") or re.sub(r"__r8[0-9a-f]{8}$", "", tn))
    key_res = json.dumps(dict(relays=added, moves=[(m["grp"], m["src"], m["new"]) for m in moves]), sort_keys=True)
    if st in st_result and st_result[st][0] != key_res:
        sys.exit(f"RINS REFUSED: plan types {st_result[st][1]} and {tn} share sidecar entry {st} but disagree")
    st_result[st] = (key_res, tn, added, moves)

if not DRY:
    for st, (_, tn, added, moves) in st_result.items():
        if st not in sct:
            sys.exit(f"RINS REFUSED: sidecar has no collector type {st}")
        e = sct[st]
        have = {r["q"] for r in e["tree"]["relays"]}
        e["tree"]["relays"].extend(copy.deepcopy([r for r in added if r["q"] not in have]))
        for m in moves:
            lst = e[m["grp"]]
            hit = [x for j, x in enumerate(lst) if (x.get("name") == m["src"] if m["grp"] == "local_sources" else x.get("index", j) == m["src"])]
            if len(hit) != 1:
                sys.exit(f"RINS REFUSED: sidecar {st}.{m['grp']} {m['src']}: {len(hit)} matches")
            hit[0]["node"] = m["new"]; hit[0].pop("tap", None)
            if m.get("xy"):
                hit[0]["xy_um"] = list(m["xy"])      # the bind reads the status point from the sidecar

def ready_bound(coll):
    """reach_relay_plan.ready_bound on the sidecar collector (root ready deadline, cycles after external reset release)."""
    b = coll["boot_budget"]; depths = b["local_registered_depths"]; train = b["ring_train_max_cycles"]
    initial = b["raw_reset_release_max_cycles"] + train
    kids = {}
    for e in coll.get("edges") or []:
        kids.setdefault(e["dst"], []).append(e)
    memo = {}
    def dl(part):
        if part not in memo:
            arr = [initial]
            for e in kids.get(part, ()):
                tr = train + e.get("monitor_relay_cycles", 0) if e.get("seam") else e.get("boot_transport_extra_cycles", 0)
                arr.append(dl(e["src"]) + tr)
            memo[part] = max(arr) + depths.get(part, 0)
        return memo[part]
    return dl(coll["root"])


if not DRY:
    coll = sc["collector"]; b = coll.get("boot_budget") or {}
    rel = dict(raw_reset_release_max_cycles=b.get("raw_reset_release_max_cycles"),
               ready_at_glue_before=b.get("ready_at_glue_max_cycles"))
    try:
        rel["ready_bound_recon_before"] = ready_bound(coll)
    except Exception as ex:      # report only
        rel["ready_bound_recon_before"] = f"n/a {ex}"
    deps = b.get("local_registered_depths") or {}
    changed_parts = {}
    for part, st in (coll.get("base_type_by_part") or {}).items():
        if st not in st_result or part not in deps:
            continue
        e = sct[st]; tr = e["tree"]; rootn = e.get("collector_root_node") or "rst_root_n"
        adj = {}
        for r in tr["relays"]:
            adj.setdefault(r["q"], []).append(r["d"]); adj.setdefault(r["d"], []).append(r["q"])
        dist = {rootn: 0}; todo = [rootn]
        while todo:
            n = todo.pop()
            for q in adj.get(n, []):
                if q not in dist:
                    dist[q] = dist[n] + 1; todo.append(q)
        nn = [x.get("node", f"rst_n_t{x.get('tap', 0)}") for x in e["local_sources"]] + [c["node"] for c in e["children"]]
        new = max([dist[n] + 1 for n in nn if n in dist] or [0])
        if new > deps[part]:
            changed_parts[part] = (deps[part], new); deps[part] = new
    rel["local_depth_changes"] = {k: list(v) for k, v in sorted(changed_parts.items())}
    rel["max_local_depth_before"] = max([v[0] for v in changed_parts.values()] or [0])
    rel["max_local_depth_after"] = max(deps.values() or [0])
    add = max((v["max_added_depth"] for v in report["types"].values()), default=0)
    rel["raw_copy_release_upper_after"] = (b.get("raw_reset_release_max_cycles") or 0) + add
    if b:
        b["ready_at_glue_max_cycles"] = ready_bound(coll)
        b["source_causal_bound_qualified"] = False
        b["rins_note"] = "KV-RCOLL-REBASE RINS: inserted collector copy relays (+k local registered depth on changed parts); START still waits for registered root ready"
    rel["ready_at_glue_after"] = b.get("ready_at_glue_max_cycles")
    report["release"] = rel

after = CR.find_all(raw)
report["after"] = dict(rows=len(after), sources=sum(r["kind"] == "source" for r in after),
                       edges=sum(r["kind"] == "edge" for r in after), types=len({r["type"] for r in after}))
report["added_relays"] = sum(v["added"] for v in report["types"].values())
report["max_added_depth"] = max((v["max_added_depth"] for v in report["types"].values()), default=0)
report["max_reset_depth_after"] = max((v["max_node_depth_after"] for v in report["types"].values()), default=0)
Path(plan_out).write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
if not DRY:
    (root / sc_out).write_text(json.dumps(sc, indent=1, ensure_ascii=False) + "\n")
    ab["clock_landing_table"] = sc_out
    (root / ab_out).write_text(json.dumps(ab, indent=1, ensure_ascii=False) + "\n")
if rep_path:
    Path(rep_path).write_text(json.dumps(report, indent=1) + "\n")
print(f"RINS before {report['before']} after {report['after']} types_changed {len(report['types'])} "
      f"added_relays {report['added_relays']} max_added_depth {report['max_added_depth']} "
      f"max_reset_depth_after {report['max_reset_depth_after']} left {len(report['left'])} {report['left'][:4]}")
if "release" in report:
    r = report["release"]
    print(f"RINS release: raw_reset_release_max {r['raw_reset_release_max_cycles']} (copies <= {r['raw_copy_release_upper_after']}), "
          f"ready_at_glue {r['ready_at_glue_before']} (recon {r['ready_bound_recon_before']}) -> {r['ready_at_glue_after']}, "
          f"local depth max -> {r['max_local_depth_after']}, parts changed {len(r['local_depth_changes'])}")
