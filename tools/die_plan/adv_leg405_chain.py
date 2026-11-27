#!/usr/bin/env python3
"""adv_leg405_chain.py -- C-LEG405 recall for the legs the staged scan cannot see (R3-RSTREACH2 11-27, FABLE-RC-KV 11-27 09:40), report-only.

Three PRE advisories (WARN, never a gate).  ADV-LEG405-STAGED measures relay_depth rows, landing chains and per-bit seats; the placed
OT_FT_LANE / OT_TAIL_SITE / OT_RELAY_POLY lines of the retained KV 3_place views also read hops over 405 um that none of those see:

LEG405-POLY   plan relay_polylines (OT_RELAY_POLY_FILE): the n stations of a chain are spread evenly along the polyline of Manhattan length L
              (relay_mid.tcl: hop = L / (n + 1), 'OT_RELAY_POLY WARN <group> path L um, n+1 hops > 405 um').  n = D + stages_existing of the
              relay_depth row whose inst and port both appear in the entry's group_re.  Flagged when L / (n + 1) > the entry's max_hop_um
              (default 405).  No matching row = the station count is unknown: reported as UNKNOWN-STATIONS with the stations the path needs
              (ceil(L / 405) - 1), never as clean.  L is the sum of the plan waypoint legs, a lower bound (the source -> first waypoint and the
              last waypoint -> sink legs are not in the plan), so a flag is a real shortfall.
LEG405-RRL    reset relay chains (u_rrl_*): every relay q -> d edge of the published landing tree (clock.landing_contract.collector_tree), else of
              the SOLVED reset tree (reset_tree.for_type), whose Manhattan hop exceeds 405 um (published: only the relays behind a node a collector references,
              used_closure; the rest of the published tree is never instantiated) (HEAD hd_ctl / hd_spn_eshim_rx class: the chain the
              relay_depth and landing-chain scans do not read).  The plan's own cap (reset.reach_cap_um) is reported next to it.
LEG405-TAIL   landing-pad tail copies (asbuilt.land_pad_tail_split, bind_pad_tail_split.py; the option lives in the bind's asbuilt input, NOT in
              the plan: OT_ADV_LEG405_ASBUILT = that JSON).  The copy hops need the bound RTL's consumer pin
              groups (bind output), so with OT_ADV_LEG405_BOUND_DIR (a bind rtl dir holding <type>.sv) pad_reach_census prices every (bus bit, pad)
              group and the PLANNED worst hop + the placed tail drift (TAIL_DRIFT_UM) over 405 is flagged.  Without it the selected types are named
              as UNCHECKED -- a type that splits pads is never reported clean from the plan alone.

findings_by_check[name](raw, plan_path, tree=None, **kw) -> WARN lines, never raises.  kw: tree_of= / asbuilt= / census= (tests), bound_dir=, limit=.
"""
import math
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

LIMIT_UM = 405.0
TAIL_DRIFT_UM = float(os.environ.get("OT_LEG405_TAIL_DRIFT_UM", "30"))   # placed - planned tail hop (KV v3n 611 placed)
MAX_EX = 3
MAX_LINES = 25


def _w(check, *parts):
    return f"WARN ADV-{check} " + " ".join(str(p) for p in parts)


def _md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _types(raw):
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if isinstance(t, dict):
            yield tn, t


def _safe(check, fn):
    def run(raw, plan_path, tree=None, **kw):
        try:
            return fn(raw, plan_path, tree, **kw)
        except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
            return [_w(check, "not checked", f"{type(e).__name__}: {str(e)[:200]}")]
    return run


# ------------------------------------------------------------------ LEG405-POLY
def poly_length(pts):
    """Manhattan length through the plan waypoints (a leg is an L, so its length is the Manhattan distance)"""
    p = [(float(x), float(y)) for x, y in pts]
    return round(sum(_md(a, b) for a, b in zip(p, p[1:])), 1)


def stations_of(t, group_re):
    """n = D + stages_existing of the relay_depth row whose inst and port both appear in group_re, else None"""
    g = group_re.replace("\\", "")
    best = None
    for r in t.get("relay_depth") or []:
        if not isinstance(r, dict) or not r.get("inst") or not r.get("port"):
            continue
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(str(r["inst"])) + r"(?![A-Za-z0-9])", g) and str(r["port"]) in g:
            n = int(r.get("D") or 0) + int(r.get("stages_existing") or 0)
            best = n if best is None else min(best, n)
    return best


def poly_rows(t, limit=LIMIT_UM):
    """-> [(group_re, L, n or None, hop um or None, limit, needed stations)] of the type's multi-point polylines"""
    rows = []
    for e in t.get("relay_polylines") or []:
        pts = e.get("polyline_um") or []
        if not isinstance(e, dict) or len(pts) < 2:
            continue
        lim = float(e.get("max_hop_um") or limit)
        L = poly_length(pts)
        n = stations_of(t, str(e.get("group_re", "")))
        rows.append((e.get("group_re"), L, n, round(L / (n + 1), 1) if n is not None else None, lim, max(0, math.ceil(L / lim) - 1)))
    return rows


def _run_poly(raw, plan_path, tree=None, limit=LIMIT_UM, **_k):
    out, over, unk, judged = [], 0, 0, 0
    for tn, t in _types(raw):
        rows = poly_rows(t, limit)
        if not rows:
            continue
        judged += 1
        bad = sorted((r for r in rows if r[3] is not None and r[3] > r[4]), key=lambda r: -r[3])
        if bad:
            over += 1
            out.append(_w("LEG405-POLY", tn, f"{len(bad)} of {len(rows)} relay polyline(s) with hops over their limit, worst hop {bad[0][3]:g} um:",
                          "; ".join(f"{r[0]} path {r[1]:g} um / {r[2] + 1} hops = {r[3]:g} um (needs {r[5]} stations)" for r in bad[:MAX_EX])
                          + " (relay_mid.tcl hop = L / (n + 1); L is a lower bound; fix: stations or waypoints)"))
        no_n = [r for r in rows if r[2] is None and r[5] >= 1]
        if no_n:
            unk += 1
            out.append(_w("LEG405-POLY", tn, f"UNKNOWN-STATIONS {len(no_n)} polyline(s) with no relay_depth row for the group: "
                          + "; ".join(f"{r[0]} path {r[1]:g} um needs >= {r[5]} stations" for r in no_n[:MAX_EX])))
    return out[:MAX_LINES] + [_w("LEG405-POLY", f"summary {over} of {judged} types with polylines over limit, {unk} with unknown station counts (report only)")]


# ------------------------------------------------------------------ LEG405-RRL
def relay_edges(tree):
    """[(q, d, um)] of a reset tree's relay -> predecessor edges that both have a site"""
    xy = {r["q"]: r["xy"] for r in (tree or {}).get("relays") or [] if r.get("q") and isinstance(r.get("xy"), (list, tuple)) and len(r["xy"]) == 2}
    if (tree or {}).get("root") is not None and isinstance(tree.get("root"), (list, tuple)):
        xy.setdefault("rst_root_n", tree["root"])
    out = []
    for r in (tree or {}).get("relays") or []:
        q, d = r.get("q"), r.get("d")
        if q in xy and d in xy:
            out.append((q, d, round(_md(xy[q], xy[d]), 1)))
    return out


_NODE = re.compile(r"^(?:rst_n_t|rr_t)(\d+)$")


def used_closure(t, tree):
    """names of the published relays the bound RTL instantiates: the nodes the collectors reference (collector_children /
    collector_local_sources, as rst_n_t<i> names) and their q -> d ancestors up to the root.  The published tree lists every relay of the
    solve; u_cland_reset_<node> chains exist only behind referenced nodes (S81 c085: 69 types have an unreferenced edge over 405 um, 0 have
    one in the closure, worst 393.1 um)."""
    rel = {r["q"]: r for r in (tree or {}).get("relays") or [] if r.get("q")}
    lc = ((t.get("clock") or {}).get("landing_contract")) or {}
    start = set()
    for key in ("collector_children", "collector_local_sources"):
        for c in lc.get(key) or []:
            n = c.get("node") if isinstance(c, dict) else None
            if isinstance(n, str):
                m = _NODE.match(n)
                start.add(n if n in rel else (f"rst_n_t{m.group(1)}" if m else n))
    seen, stack = set(), [q for q in start if q in rel]
    while stack:
        q = stack.pop()
        if q in seen:
            continue
        seen.add(q)
        d = rel[q].get("d")
        if d in rel:
            stack.append(d)
    return seen


def _tree_of(raw, plan_path, tn, t, tree_of=None):
    """-> (tree, source): the published landing tree, else the solved reset tree; (None, why) when neither"""
    if tree_of is not None:
        r = tree_of(tn, t)
        return (r, "tree") if r else (None, "no tree")
    ct = (((t.get("clock") or {}).get("landing_contract")) or {}).get("collector_tree")
    if isinstance(ct, dict) and ct.get("relays"):
        return ct, "published"
    try:
        import tap_site as TS
        import reset_tree as RT
        return RT.for_type(TS._plan(raw, plan_path), tn), "solved"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}"


def _run_rrl(raw, plan_path, tree=None, limit=LIMIT_UM, tree_of=None, budget_s=None, **_k):
    """budget_s (default $OT_ADV_LEG405_RRL_S, 100 s) bounds the SOLVED-tree path; types left over are counted as not checked, never as clean"""
    budget = float(os.environ.get("OT_ADV_LEG405_RRL_S", "100")) if budget_s is None else budget_s
    t0 = time.time()
    out, over, judged, nosrc, late = [], 0, 0, 0, 0
    cap = (raw.get("reset") or {}).get("reach_cap_um")
    for tn, t in _types(raw):
        if t.get("hard"):
            continue
        has_pub = bool((((t.get("clock") or {}).get("landing_contract")) or {}).get("collector_tree"))
        if not has_pub and tree_of is None and not ((t.get("reset") is not None) or (raw.get("reset") or {}).get("in_sites", {}).get(tn)):
            continue
        if not has_pub and time.time() - t0 > budget:
            late += 1
            continue
        T, src = _tree_of(raw, plan_path, tn, t, tree_of)
        if T is None:
            nosrc += 1
            continue
        edges = relay_edges(T)
        idle = 0
        if src == "published":
            used = used_closure(t, T)
            idle = sum(1 for e in edges if e[0] not in used and e[2] > limit)
            edges = [e for e in edges if e[0] in used]
        if not edges:
            continue
        judged += 1
        bad = sorted((e for e in edges if e[2] > limit), key=lambda e: -e[2])
        if bad:
            over += 1
            out.append(_w("LEG405-RRL", tn, f"{len(bad)} of {len(edges)} reset relay hop(s) over {limit:g} um on the {src} tree, worst {bad[0][2]:g} um:",
                          "; ".join(f"{q}<-{d} {um:g}" for q, d, um in bad[:MAX_EX])
                          + (f" (plan reset.reach_cap_um {cap:g})" if isinstance(cap, (int, float)) else "")
                          + (f"; {idle} unreferenced published edge(s) over the limit not instantiated" if idle else "")))
    return out[:MAX_LINES] + [_w("LEG405-RRL", f"summary {over} of {judged} types with a reset relay hop over {limit:g} um, {nosrc} types with no tree, {late} not checked past the {budget:g} s budget (report only)")]


# ------------------------------------------------------------------ LEG405-TAIL
def _asbuilt(raw, asbuilt=None):
    """the as-built options: asbuilt= (tests / callers), else $OT_ADV_LEG405_ASBUILT (a JSON file: the bind's --asbuilt input), else raw['asbuilt'].
    The plan itself carries no asbuilt section (KV 5bee, S81 c085, HEAD 607d: none), so without one nothing selects a type."""
    if isinstance(asbuilt, dict):
        return asbuilt
    p = os.environ.get("OT_ADV_LEG405_ASBUILT")
    if p and os.path.isfile(p):
        import json
        with open(p) as fh:
            return json.load(fh)
    return raw.get("asbuilt") or {}


def tail_selected(raw, asbuilt=None):
    """-> ([type names selected by land_pad_tail_split.types], cfg) ([], None) when the option is absent"""
    import bind_pad_tail_split as TS
    cfg = TS.config(_asbuilt(raw, asbuilt))
    if not cfg:
        return [], None
    return [tn for tn, _t in _types(raw) if TS.selected(cfg, tn)], cfg


def _run_tail(raw, plan_path, tree=None, bound_dir=None, limit=LIMIT_UM, asbuilt=None, census=None, **_k):
    sel, cfg = tail_selected(raw, asbuilt)
    if not sel:
        return [_w("LEG405-TAIL", "summary 0 types select land_pad_tail_split (no asbuilt option given: OT_ADV_LEG405_ASBUILT) (report only)")]
    bound_dir = bound_dir or os.environ.get("OT_ADV_LEG405_BOUND_DIR")
    out, over, judged, unchecked = [], 0, 0, []
    for tn in sel:
        sv = Path(bound_dir) / f"{tn}.sv" if bound_dir else None
        if not sv or not sv.is_file():
            unchecked.append(tn)
            continue
        try:
            if census is None:
                import pad_reach_census as PC
                census = PC.census
            res = census(raw, tn, sv.read_text(), cfg)
        except Exception as e:  # noqa: BLE001
            unchecked.append(f"{tn}({type(e).__name__})")
            continue
        judged += 1
        worst = float(res.get("max_hop_um") or 0.0)
        if worst + TAIL_DRIFT_UM > limit:
            over += 1
            out.append(_w("LEG405-TAIL", tn, f"planned worst pad / tail-copy hop {worst:g} um + {TAIL_DRIFT_UM:g} um placed drift over {limit:g} um"
                          f" ({res.get('max_short', 0)} stage(s) short of the reach rule; pad_reach_census.py)"))
    if unchecked:
        out.append(_w("LEG405-TAIL", f"UNCHECKED {len(unchecked)} of {len(sel)} types select land_pad_tail_split but have no bound RTL "
                      f"(OT_ADV_LEG405_BOUND_DIR): " + ", ".join(unchecked[:MAX_EX]) + (" ..." if len(unchecked) > MAX_EX else "")))
    return out[:MAX_LINES] + [_w("LEG405-TAIL", f"summary {over} of {judged} measured types over {limit:g} um, {len(unchecked)} unchecked (report only)")]


F = {"LEG405-POLY": _run_poly, "LEG405-RRL": _run_rrl, "LEG405-TAIL": _run_tail}
findings_by_check = {k: _safe(k, v) for k, v in F.items()}
