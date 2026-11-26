"""adv_pub_stale.py -- PRECHECK ADV-PUB-STALE (C-RST-RELAY-REACH / P-RESET-PUB-STALE, S81-RSTREACH 11-26; report only).

A type publishes its reset tree as clock.landing_contract.collector_tree; collectors, verify and landing_place read THAT tree
(landing_collector.effective_tree), while the reset relays in the bound RTL come from the tree the bind re-solves
(reset_tree.for_type).  When a tap / floorplan / ft_slots event changed the solve and the publication was not refreshed
(retap --republish-reset), the node names the plan and the landing sidecar carry (rst_n_t<k>, rst_rl_<k>) name other relays
in the RTL.  S81 v3 c25717c926ee: 126 types; col_h10_r2__t1__clac068e56 published 250 relays / 30 taps vs solved 245 / 32, 0
relays identical, u_cland_reset_rst_n_t30 fed by rst_rl_19 950 um away, the same number ADV-REF-SITE REACH reports.

Per type with a soft published tree and collector refs, the published tree is compared with the solved one:
  RELAYS  published relays that are not the solved relay of the same name (same depth and site, 0.05 um)
  TAPS    n_clock_taps / tap count differs
  REACH   collector_children / collector_local_sources node whose status pins are > 405 um from the SOLVED relay of that name
Depth is compared too (a different depth is a cycle change: the republish row must skip and report it).
Fix: retap.py --republish-reset on the type, graft the tree into plan + landing sidecar (S81-RST-SIDECAR treepub), srctap re-node.
Budget: OT_ADV_PUB_STALE_BUDGET_S seconds of solving (default 100); the rest is reported as not checked, never as clean.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.  kw: types= (set / list of type names), solved= {type: tree}
(tests / callers that already hold the solve), budget_s=.
"""
import os
import sys
import time
from pathlib import Path

CHECK = "ADV-PUB-STALE"
REACH_UM = 405.0
SITE_EPS_UM = 0.05
MAX_LINES = 25


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _w(*a):
    return f"WARN {CHECK} " + " ".join(str(x) for x in a)


def _pins(c):
    p = c.get("status_pins_xy_um") or ([c["xy_um"]] if c.get("xy_um") else [])
    return [x for x in p if isinstance(x, (list, tuple)) and len(x) == 2]


def _node(c):
    n = c.get("node")
    return n if isinstance(n, str) else (f"rst_n_t{c['tap']}" if isinstance(c.get("tap"), int) else None)


def judge_type(published, solved, children=(), sources=()):
    """-> dict(relays_pub, relays_same, taps_pub, taps_solved, depth_pub, depth_solved, reach: [(where, node, um)])"""
    pr = {r["q"]: r for r in published.get("relays") or []}
    sr = {r["q"]: r for r in solved.get("relays") or []}
    same = sum(1 for q, r in pr.items() if q in sr and sr[q].get("depth") == r.get("depth")
               and _d(sr[q]["xy"], r["xy"]) <= SITE_EPS_UM)
    xy = dict(sr)
    xy["rst_root_n"] = {"xy": solved.get("root")}
    reach = []
    items = [(f"children[{i}]", c) for i, c in enumerate(children)] + [(f"sources[{c.get('name')}]", c) for c in sources]
    for where, c in items:
        n, pts = _node(c), _pins(c)
        if not n or not pts:
            continue
        r = xy.get(n)
        if r is None or not r.get("xy"):
            reach.append((where, n, None))
            continue
        um = max(_d(p, r["xy"]) for p in pts)
        if um > REACH_UM:
            reach.append((where, n, round(um, 1)))
    return dict(relays_pub=len(pr), relays_same=same, relays_solved=len(sr),
                taps_pub=published.get("n_clock_taps"), taps_solved=solved.get("n_clock_taps"),
                depth_pub=published.get("depth"), depth_solved=solved.get("depth"), reach=reach)


def stale(j):
    return (j["relays_same"] < j["relays_pub"] or j["relays_pub"] != j["relays_solved"]
            or j["taps_pub"] != j["taps_solved"] or bool(j["reach"]) or j["depth_pub"] != j["depth_solved"])


def _line(tn, j):
    far = [r for r in j["reach"] if r[2] is not None]
    worst = max(far, key=lambda r: r[2]) if far else None
    miss = [r for r in j["reach"] if r[2] is None]
    t = (f"{tn}: published tree {j['relays_pub']} relays / {j['taps_pub']} taps vs solved {j['relays_solved']} / {j['taps_solved']}, "
         f"{j['relays_same']} relay(s) identical (name, depth, site)")
    if j["depth_pub"] != j["depth_solved"]:
        t += f"; DEPTH {j['depth_pub']} -> {j['depth_solved']} (a cycle change: the republish row must skip and report it)"
    if far:
        t += f"; {len(far)} collector ref(s) > {REACH_UM:g} um on the solved tree (worst {worst[1]} {worst[2]:g} um at {worst[0]})"
    if miss:
        t += f"; {len(miss)} collector node(s) not in the solved tree ({miss[0][1]})"
    return _w(t + "; fix: retap --republish-reset + treepub + srctap re-node (S81-RSTREACH row)")


def _solve_all(raw, plan_path, names, budget_s):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import schema
    import reset_tree as RT
    P = schema.Plan(raw, Path(plan_path).parent / "die_plan.json")
    out, t0 = {}, time.time()
    for tn in names:
        if time.time() - t0 > budget_s:
            break
        try:
            out[tn] = RT.for_type(P, tn)
        except Exception as e:  # noqa: BLE001 - a type whose tree cannot be solved is named, never clean
            out[tn] = e
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        want = set(kw["types"]) if kw.get("types") else None
        todo = []
        for tn, t in sorted(((raw or {}).get("partition_types") or {}).items()):
            if want is not None and tn not in want:
                continue
            lc = ((t.get("clock") or {}).get("landing_contract") or {})
            pub = lc.get("collector_tree")
            if not isinstance(pub, dict) or pub.get("hard") or not pub.get("relays"):
                continue
            if not (lc.get("collector_children") or lc.get("collector_local_sources")):
                continue
            todo.append((tn, lc, pub))
        solved = kw.get("solved")
        if solved is None:
            solved = {} if not todo else _solve_all(raw, plan_path, [x[0] for x in todo],
                                float(kw.get("budget_s") or os.environ.get("OT_ADV_PUB_STALE_BUDGET_S", "100")))
        out, n_stale, n_err, n_skip, n_depth = [], 0, 0, 0, 0
        for tn, lc, pub in todo:
            s = solved.get(tn)
            if s is None:
                n_skip += 1
                continue
            if isinstance(s, Exception):
                n_err += 1
                out.append(_w(f"{tn}: reset tree not solvable ({type(s).__name__}: {str(s)[:120]}); NOT checked"))
                continue
            j = judge_type(pub, s, lc.get("collector_children") or [], lc.get("collector_local_sources") or [])
            if stale(j):
                n_stale += 1
                n_depth += j["depth_pub"] != j["depth_solved"]
                out.append(_line(tn, j))
        out = out[:MAX_LINES] + ([_w(f"... {n_stale + n_err - MAX_LINES} more line(s)")] if len(out) > MAX_LINES else [])
        out.append(_w(f"summary {n_stale} of {len(todo)} types with a stale publication ({n_depth} with a depth change), "
                      f"{n_err} not solvable, {n_skip} not checked (budget)"))
        return out
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]
