"""ref_site.py -- REF-SITE (TAPKEY-SITE 11-24, FABLE flow review item 3; report only): every NAME or INDEX reference of a type to a
clock tap or reset-tree node is resolved to xy on the plan's CURRENT tap grid, then
  REACH   (one plan)   a LOCAL index-keyed reset reference (collector_children / collector_local_sources / landing_local_resets) rst_n_t<i> / rr_t<i> whose node (tap i's terminal relay, i < n_taps) lies more
                       than one relay hop (REACH_UM, the bind's 405-um gate) from the consumer it serves (status_pins_xy_um /
                       pin_xy_um / xy_um of the same entry).  QC sle_sc_v3: collector_children node rst_n_t69 was the seam output
                       n_taps + 0 with 69 taps; at 73 taps index 69 is clock tap 69, 1184 um from its monitors (-241 ps), and PRE,
                       strict, LATCHECK and G0 all passed.
  MOVED   (vs baseline = the plan the references were last bound / measured on) a reference present in both plans whose resolved
                       site moved > TOL_UM (9 um): name-keyed tap tables (tap_offset / tap_window per_port_ps, tap_pin_heights_um,
                       tap_group.fixed_taps, tap_site.type_tables) and the index-keyed reset references above.
  KIND    (vs baseline) an index reference that crossed the tap count: a seam output (i >= n_taps) became a clock tap's relay or back.
Index i >= n_taps names a reset-tree OUTPUT (seam), which has no tap site: counted, not sited.  Bit sites (internal_stations
bit_sites_um) are explicit xy, checked by ADV-BITSITE-SEAT in the same PRE run.  The published collector_tree is skipped (G0
collector_reach checks its own edges).

    python3 tools/die_plan/ref_site.py PLAN [--baseline BASE] [--types a,b] [--root R] [--base-root R]

COMPOSE re-key (COORD 11-24 ruling: a row that adds taps re-keys every index-keyed reference by site; report-only first, r703):
    python3 tools/die_plan/ref_site.py reindex NEW --baseline PREV [--out OUT] [--types a,b]
reset references (rst_n_t<i> / rr_t<i>: START raw_reset, raw branches, collector nodes) are re-keyed against the type's SOLVED
reset tree on PREV and on NEW (reset_tree.for_type: its emitted relay names and sites, NOT the clock tap count), by site, onto
names the NEW tree emits (reindex_type_tree); references a row rewrote after PREV are left; clock references (forwarded clock
pins) against the clock tap tables (retap.repoint_type reset=False).  Without --out nothing is written (report only); with --out the re-keyed
plan is written for the compose to adopt.  Exit 0 either way.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python3 -I drops the script folder: tap_site / schema / retap live here
import tap_site as TS  # noqa: E402

TOL_UM = TS.TOL_UM
REACH_UM = 405.0
REF = re.compile(r"^(rst_n_t|rr_t)(\d+)$")
# REACH applies to references that name the node SERVING the entry locally (collector ready/fault monitors, local resets);
# transport stages (landing_*_start raw_reset, landing_raw_branches original) carry the reset away from its tap by design
LOCAL_FAMILIES = ("collector_children", "collector_local_sources", "landing_local_resets")


def _reach_um():
    try:
        import cbc_rules as C
        return float(C.REACH_GATE_UM)
    except Exception:  # noqa: BLE001
        return REACH_UM


def tap_index(name):
    if name == "clk":
        return 0
    m = re.fullmatch(r"clk_t(\d+)", str(name))
    return int(m.group(1)) if m else None


def _pts(o):
    s = o.get("status_pins_xy_um")
    if isinstance(s, list) and s and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in s):
        return [tuple(map(float, p)) for p in s]
    for k in ("pin_xy_um", "xy_um"):
        p = o.get(k)
        if isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p):
            return [(float(p[0]), float(p[1]))]
    return []


def family(path):
    for f in ("collector_children", "collector_local_sources", "landing_local_resets", "landing_raw_branches",
              "landing_reader_start", "landing_writer_start", "reset."):
        if f in path:
            return f.rstrip(".")
    return path.split(".")[1] if "." in path else path


def index_refs(t):
    """[(path, value, index, consumer pts)] of every rst_n_t<i> / rr_t<i> string of a type (collector_tree skipped); list items are
    labelled by their 'name' when they have one, so a path is the same in two plans."""
    out = []

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "collector_tree":
                    continue
                if isinstance(v, str):
                    m = REF.match(v)
                    if m:
                        out.append((f"{p}.{k}", v, int(m.group(2)), _pts(o)))
                else:
                    walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                lab = v.get("name") if isinstance(v, dict) and isinstance(v.get("name"), str) else i
                walk(v, f"{p}[{lab}]")
    walk(t, "")
    return out


def tree_sites(T):
    """emitted reset names of a solved reset tree (reset_tree.for_type) -> dict(rel {name: (xy, depth)}, n (reset taps),
    seams {name: j}).  rst_n_t<i> = terminal relay of RESET tap i (T['taps'], which is NOT the clock tap table on types with
    extra reset taps, KV hg); seam output j = rst_n_t<n + j> at T['outs'][j]."""
    rel = {r["q"]: ((float(r["xy"][0]), float(r["xy"][1])), r.get("depth")) for r in T.get("relays") or [] if r.get("q")}
    n = len(T.get("taps") or [])
    seams = {}
    for j, xy in enumerate(T.get("outs") or []):
        q = f"rst_n_t{n + j}"
        seams[q] = j
        rel.setdefault(q, ((float(xy[0]), float(xy[1])), None))
    return dict(rel=rel, n=n, seams=seams)


def _tree(P, tn):
    import reset_tree as RT
    return tree_sites(RT.for_type(P, tn))


def _reset_site(v, ts):
    """xy of reset name v in tree sites ts (rr_t<i> = raw copy of rst_n_t<i>) or None (the tree does not emit it)."""
    if v in ts["rel"]:
        return ts["rel"][v][0]
    m = REF.match(v)
    if m and m.group(1) == "rr_t":
        r = ts["rel"].get(f"rst_n_t{m.group(2)}")
        return r[0] if r else None
    return None


def type_refs(P, raw, tn, tree=True):
    """{key: (kind, value, site or None, consumer pts)}; kind tap / reset / seam / unemitted.  Reset names resolve against the
    type's SOLVED reset tree (its emitted names); when the tree cannot be solved (or tree=False) against the clock tap table
    (kind reset-clk / seam-clk).  -> (refs, n) with n = reset taps (tree) or clock taps.  Raises if the grid cannot be evaluated."""
    import schema as S
    grid = S.tap_grid(P, tn)
    sites = {n: (float(x), float(y)) for n, x, y in grid}
    idx = {tap_index(n): xy for n, xy in sites.items() if tap_index(n) is not None}
    refs = {}
    for label, box, key, form in TS.type_tables(raw, tn):
        ports = list(box[key].keys()) if form == "keys" else list(box[key].values())
        for q in ports:
            if TS._is_core(q):
                continue
            refs[f"{label}[{q}]"] = ("tap", q, sites.get(q), [])
    irefs = index_refs(raw["partition_types"][tn])
    ts = None
    if tree and irefs:
        try:
            ts = _tree(P, tn)
        except Exception:  # noqa: BLE001
            ts = None
    if ts is not None:
        for path, v, i, pts in irefs:
            site = _reset_site(v, ts)
            base = f"rst_n_t{i}"
            kind = "unemitted" if site is None else ("seam" if base in ts["seams"] else "reset")
            refs[path] = (kind, v, site, pts)
        return refs, ts["n"]
    n_taps = len(idx)
    for path, v, i, pts in irefs:
        refs[path] = ("reset-clk", v, idx.get(i), pts) if i < n_taps else ("seam-clk", v, None, pts)
    return refs, n_taps


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reach_rows(refs, reach):
    rows = []
    for k, (kind, v, site, pts) in refs.items():
        if kind in ("reset", "reset-clk") and site and pts and family(k) in LOCAL_FAMILIES:
            d = max(_d(site, p) for p in pts)
            if d > reach:
                rows.append((k, v, d))
    return rows


def moved_rows(refs, brefs, tol=TOL_UM):
    mv, kind = [], []
    for k in sorted(set(refs) & set(brefs)):
        a, b = refs[k], brefs[k]
        if a[0] != b[0] and {a[0], b[0]} <= {"reset", "seam", "reset-clk", "seam-clk"} and (a[0] in ("seam", "seam-clk")) != (b[0] in ("seam", "seam-clk")):
            site = a[2] or b[2]
            kind.append((k, b[1], a[1], a[0], max((_d(site, q) for q in (a[3] or b[3])), default=None)))
        elif a[2] and b[2] and _d(a[2], b[2]) > tol:
            mv.append((k, a[1], _d(a[2], b[2])))
    return mv, kind


def run(raw, plan_path, braw=None, base_path=None, types=None, log=print):
    reach = _reach_um()
    P = TS._plan(raw, plan_path)
    PB = TS._plan(braw, base_path) if braw is not None else None
    tot = Counter()
    fam_reach, fam_moved, fam_kind, fam_une = Counter(), Counter(), Counter(), Counter()
    lines = []
    for tn in sorted(raw.get("partition_types") or {}):
        if types and tn not in types:
            continue
        t = raw["partition_types"][tn]
        if not TS.type_tables(raw, tn) and not index_refs(t):
            continue
        try:
            TS._plandir(plan_path)
            refs, n = type_refs(P, raw, tn)
        except Exception as e:  # noqa: BLE001
            tot["unev"] += 1
            lines.append((0, f"NOT-EVALUABLE\t{tn}\t{type(e).__name__}: {str(e)[:120]}"))
            continue
        tot["types"] += 1
        tot["refs"] += len(refs)
        tot["seam"] += sum(1 for r in refs.values() if r[0] in ("seam", "seam-clk"))
        une = [(k, r[1]) for k, r in refs.items() if r[0] == "unemitted"]
        for k, _v in une:
            fam_une[family(k)] += 1
        if une:
            lines.append((len(une), f"NOT-EMITTED\t{tn}\t{len(une)} reset refs name a relay the solved reset tree does not emit: "
                                    + " ".join(f"{k}={v}" for k, v in une[:5])))
        tot["clkfb"] += sum(1 for r in refs.values() if r[0] in ("reset-clk", "seam-clk"))
        rr = reach_rows(refs, reach)
        for k, _v, _d2 in rr:
            fam_reach[family(k)] += 1
        if rr:
            rr.sort(key=lambda x: -x[2])
            lines.append((len(rr), f"REACH\t{tn}\t{len(rr)} index-keyed reset refs > {reach:g} um from their consumer (n_taps {n}; worst "
                                   f"{rr[0][1]} {rr[0][2]:.0f} um at {rr[0][0]}): " + " ".join(f"{k}={v}:{d:.0f}" for k, v, d in rr[1:5])))
        if PB is None or tn not in (braw.get("partition_types") or {}):
            continue
        try:
            TS._plandir(base_path)
            brefs, bn = type_refs(PB, braw, tn)
        except Exception as e:  # noqa: BLE001
            tot["bunev"] += 1
            continue
        mv, kd = moved_rows(refs, brefs)
        tot["common"] += len(set(refs) & set(brefs))
        for k, *_ in mv:
            fam_moved[family(k) if not k.startswith("clock.") and not k.startswith("tap_") else k.split("[")[0]] += 1
        for k, *_ in kd:
            fam_kind[family(k)] += 1
        if mv or kd:
            mv.sort(key=lambda x: -x[2])
            lines.append((len(mv) + len(kd), f"MOVED\t{tn}\t{len(mv)} refs on a site moved > {TOL_UM:g} um, {len(kd)} index refs crossed the tap count "
                                             f"(n_taps {bn} -> {n})" + (f"; worst {mv[0][1]} {mv[0][2]:.0f} um at {mv[0][0]}" if mv else "")
                                             + (f"; KIND worst consumer distance {max(x[4] for x in kd if x[4] is not None):.0f} um" if any(x[4] is not None for x in kd) else "")
                                             + "".join(f"; KIND {k}: {a}->{b} now {c}" + (f" {d:.0f} um from consumer" if d is not None else "")
                                                       for k, a, b, c, d in sorted(kd, key=lambda x: -(x[4] or 0))[:3])))
    lines.sort(key=lambda x: -x[0])
    for _n, ln in lines:
        log(ln)
    log(f"SUMMARY\t{tot['types']} types, {tot['refs']} name/index refs resolved ({tot['seam']} seam-output indices, unsited), {tot['unev']} not evaluable; "
        f"NOT-EMITTED {sum(fam_une.values())} {dict(fam_une)}; {tot['clkfb']} refs resolved on the clock table (tree not solvable); "
        f"REACH {sum(fam_reach.values())} {dict(fam_reach)}"
        + (f"; vs baseline: {tot['common']} common refs, MOVED {sum(fam_moved.values())} {dict(fam_moved)}, KIND {sum(fam_kind.values())} {dict(fam_kind)}, "
           f"{tot['bunev']} baseline types not evaluable" if PB is not None else "; no baseline: MOVED/KIND not run"))
    return dict(tot=tot, reach=fam_reach, moved=fam_moved, kind=fam_kind, unemitted=fam_une)


def _walk_refs(t):
    """yield (container, key, value, path, consumer pts) of every rst_n_t<i> / rr_t<i> string in a type (collector_tree skipped)."""
    out = []

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "collector_tree":
                    continue
                if isinstance(v, str) and REF.match(v):
                    out.append((o, k, v, f"{p}.{k}", _pts(o)))
                elif not isinstance(v, str):
                    walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                lab = v.get("name") if isinstance(v, dict) and isinstance(v.get("name"), str) else i
                if isinstance(v, str) and REF.match(v):
                    out.append((o, i, v, f"{p}[{lab}]", []))
                else:
                    walk(v, f"{p}[{lab}]")
    walk(t, "")
    return out


def reindex_type_tree(t, old_ts, new_ts, base_vals=None, tol=TOL_UM):
    """re-key the reset references of type dict t (in place) from the OLD solved reset tree to the NEW one, by SITE, onto names
    the new tree emits -> [[path, key, was, now, um]].
      seam output j (old rst_n_t<n_old + j>)       -> rst_n_t<n_new + j>
      relay rst_n_t<i> still emitted at its old site (<= tol) -> kept
      otherwise                                    -> the new terminal relay nearest the old site; within tol of that distance
                                                      prefer the old depth, then the one nearest the consumer, then the name
      rr_t<i> follows rst_n_t<i>'s mapping (rr_t<j>); a sibling 'tap' == i follows to j.
    base_vals {path: value} = the baseline plan's references: a reference whose value differs from the baseline's at the same path
    was rewritten after the baseline (by a row) and is left as it is.  Names the old tree does not emit are left and reported."""
    rel_o, rel_n = old_ts["rel"], new_ts["rel"]
    cand = [(q, xy, dp) for q, (xy, dp) in rel_n.items() if q.startswith("rst_n_t") and q not in new_ts["seams"]]
    memo, out = {}, []

    def pick(i, pts):
        name = f"rst_n_t{i}"
        if name in old_ts["seams"]:
            j = old_ts["seams"][name]
            q = f"rst_n_t{new_ts['n'] + j}"
            return (q, 0.0) if q in new_ts["seams"] else (None, None)
        if name not in rel_o:
            return None, None
        oxy, od = rel_o[name]
        if name in rel_n and name not in new_ts["seams"] and _d(rel_n[name][0], oxy) <= tol:
            return name, _d(rel_n[name][0], oxy)
        if not cand:
            return None, None
        best = min(_d(xy, oxy) for _q, xy, _dp in cand)
        near = [c for c in cand if _d(c[1], oxy) <= best + tol]
        cx = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else oxy
        q, xy, _dp = min(near, key=lambda c: (c[2] != od, _d(c[1], cx), c[0]))
        return q, _d(xy, oxy)

    for o, k, v, path, pts in _walk_refs(t):
        if base_vals is not None and base_vals.get(path, v) != v:
            continue
        m = REF.match(v)
        i = int(m.group(2))
        key = (i, tuple(pts[:1]))
        if key not in memo:
            memo[key] = pick(i, pts)
        q, um = memo[key]
        if q is None:
            out.append([path, k, v, None, None])
            continue
        j = int(q[len("rst_n_t"):])
        now = f"{m.group(1)}{j}"
        if now != v:
            o[k] = now
            if isinstance(o, dict) and o.get("tap") == i:
                o["tap"] = j
            out.append([path, k, v, now, round(um, 3)])
    return out


def reindex_type(t, old, new):
    """CLOCK references only (landing_contract forwarded clock pins) from clock tap set old to new [(n, x, y)] (retap rule)."""
    import retap
    return retap.repoint_type(t, old, new, reset=False)


def reindex(raw, plan_path, braw, base_path, types=None, log=print):
    """raw re-keyed in place against braw -> {type: changes}: reset references against the solved reset trees (old tree on the
    baseline, new tree on raw), clock references against the clock tap tables."""
    import schema as S
    P, PB = TS._plan(raw, plan_path), TS._plan(braw, base_path)
    key = lambda ts: [(n, round(x, 6), round(y, 6)) for n, x, y in ts]  # noqa: E731
    rep, fam, unev, uns = {}, Counter(), 0, 0
    for tn in sorted(raw.get("partition_types") or {}):
        if (types and tn not in types) or tn not in (braw.get("partition_types") or {}):
            continue
        t = raw["partition_types"][tn]
        has_reset = bool(index_refs(t))
        if not has_reset and not (t.get("clock") or {}).get("landing_contract"):
            continue
        ch = []
        try:
            TS._plandir(base_path)
            old = [(n, float(x), float(y)) for n, x, y in S.tap_grid(PB, tn)]
            TS._plandir(plan_path)
            new = [(n, float(x), float(y)) for n, x, y in S.tap_grid(P, tn)]
            if key(old) != key(new):
                ch += reindex_type(t, old, new)
            if has_reset:
                TS._plandir(base_path)
                ots = _tree(PB, tn)
                TS._plandir(plan_path)
                nts = _tree(P, tn)
                bv = {path: v for _o, _k, v, path, _p in _walk_refs(braw["partition_types"][tn])}
                ch += reindex_type_tree(t, ots, nts, bv)
        except Exception as e:  # noqa: BLE001
            unev += 1
            log(f"NOT-EVALUABLE\t{tn}\t{type(e).__name__}: {str(e)[:160]}")
            continue
        miss = [c for c in ch if c[3] is None]
        ch = [c for c in ch if c[3] is not None]
        uns += len(miss)
        if ch or miss:
            rep[tn] = ch
            for w, *_ in ch:
                fam[family(w if w.startswith(".") else "." + w)] += 1
            log(f"REINDEX\t{tn}\t{len(ch)} references re-keyed by site, {len(miss)} left (old name not emitted by the old tree): "
                + " ".join(f"{w}:{a}->{b}" for w, _k, a, b, _u in ch[:5]) + (f" LEFT {miss[0][0]}={miss[0][2]}" if miss else ""))
    log(f"SUMMARY\treindex: {len(rep)} types, {sum(len(v) for v in rep.values())} references re-keyed by site {dict(fam)}, {uns} left; "
        f"{unev} not evaluable")
    return rep


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "reindex":
        ap = argparse.ArgumentParser(description="REF-SITE compose re-key by site (report only without --out)")
        ap.add_argument("mode")
        ap.add_argument("plan")
        ap.add_argument("--baseline", required=True)
        ap.add_argument("--out")
        ap.add_argument("--types", default="")
        ap.add_argument("--root")
        ap.add_argument("--base-root")
        a = ap.parse_args(argv)
        raw, braw = json.loads(Path(a.plan).read_text()), json.loads(Path(a.baseline).read_text())
        if a.root:
            TS.ROOTS[str(a.plan)] = a.root
        if a.base_root:
            TS.ROOTS[str(a.baseline)] = a.base_root
        reindex(raw, a.plan, braw, a.baseline, [t for t in a.types.split(",") if t] or None)
        if a.out:
            Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
        return 0
    return _main(argv)


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--baseline")
    ap.add_argument("--types", default="")
    ap.add_argument("--root")
    ap.add_argument("--base-root")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    braw = json.loads(Path(a.baseline).read_text()) if a.baseline else None
    if a.root:
        TS.ROOTS[str(a.plan)] = a.root
    if a.base_root and a.baseline:
        TS.ROOTS[str(a.baseline)] = a.base_root
    run(raw, a.plan, braw, a.baseline, [t for t in a.types.split(",") if t] or None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
