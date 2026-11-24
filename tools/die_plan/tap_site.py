"""tap_site.py -- TAPKEY-SITE (COORD 11-24): plan tables keyed by tap NAME survive a tap re-solve.

Why: schema.tap_grid numbers the clock taps clk_t<i> from the type geometry at EVERY generation (grid / density / grid+explicit /
sink modes), so moving a macro, core or band renumbers them.  A table written by port name against the older grid then silently
times / shapes ANOTHER place (S81 c8: leaf t37 49/49 rows on moved taps, t25 cl431c660f 38/38 up to 199 um, slice_station t14 31/31,
leaf t21 16/55; QC st_a r9 kept 5-22 of 225-408 rows on their own tap).

Form: a per-type SITE STAMP  partition_types[T].clock.tap_sites_um = {port: [x, y]}  (type frame, the tap grid the type's name-keyed
tables were written against).  rekey maps every stamped port to the CURRENT port at the same site (Manhattan <= TOL_UM, one-to-one,
nearest first) and renames the port keys of every name-keyed table of the type, then re-stamps on the current grid:
  die  clock.tap_offset.per_port_ps[T]{port}      die  clock.tap_window.per_port_ps[T]{port}
  type clock.tap_pin_heights_um{port}             type clock.tap_group.fixed_taps{group: port}
A stamped port with no current tap within TOL_UM is UNSITED: its rows are dropped (tap_offset_cover fill / census then sees the port as
missing instead of timing another place).  Ports not in the stamp, and core taps clk_c<k> (named by taps[] order, not by the grid),
are left as they are.  No stamp = unchanged (legacy tables; ADV-TAPOFF-SITE judges them against a baseline plan).
gen_phys applies rekey to its working copy before anything reads these tables; writers stamp the grid they wrote against (stamp()).

CLI:  tap_site.py stamp PLAN --out OUT [--types a,b]   stamp each type's current grid (tables assumed to match it NOW)
      tap_site.py rekey PLAN --out OUT [--types a,b]   re-key stamped tables to the current grid and re-stamp
                  [--baseline BASE]                  = stamp --baseline BASE (unstamped types) then rekey, in one pass
      tap_site.py check PLAN [--types a,b]             report only (exit 0)
      tap_site.py diff PLAN --baseline BASE [--types]  report only: per type, every tap name present in BOTH grids whose site moved
                                                      > TOL_UM, and the name-keyed tables of PLAN that reference it (gate-post line)
"""
import argparse
import copy
import json
import sys
from pathlib import Path

TOL_UM = 9.0
STAMP = "tap_sites_um"


def _is_core(p):
    return str(p).startswith("clk_c")


def site_map(old, new, tol=TOL_UM):
    """old/new {port: (x, y)} -> ({old port: new port}, [unsited old ports]).  One-to-one, nearest pair first; ties by name."""
    pairs = []
    for o, (ox, oy) in old.items():
        for n, (nx, ny) in new.items():
            d = abs(ox - nx) + abs(oy - ny)
            if d <= tol:
                pairs.append((d, o != n, o, n))
    pairs.sort()
    m, used = {}, set()
    for _d, _r, o, n in pairs:
        if o in m or n in used:
            continue
        m[o] = n
        used.add(n)
    return m, sorted(o for o in old if o not in m)


def _rename(tab, m, unsited):
    """{port: v} -> (renamed dict, renamed count, dropped count).  Unstamped ports keep their key unless a stamped port takes it."""
    out, ren, drop = {}, 0, 0
    stamped = set(m) | set(unsited)
    for p, v in tab.items():
        if p in unsited:
            drop += 1
        elif p in m:
            out[m[p]] = v
            ren += m[p] != p
    for p, v in tab.items():
        if p not in stamped and p not in out:
            out[p] = v
    return out, ren, drop


def _revalue(tab, m, unsited):
    """{key: port} (tap_group.fixed_taps) -> same with ports re-keyed; a group on an unsited port is dropped."""
    out, ren, drop = {}, 0, 0
    for g, p in tab.items():
        if p in unsited:
            drop += 1
            continue
        q = m.get(p, p)
        out[g] = q
        ren += q != p
    return out, ren, drop


def type_tables(raw, tn):
    """[(label, container dict, key, form)] of the name-keyed tables of type tn present in raw; form 'keys' = {port: v},
    'values' = {group: port}."""
    ck = raw.get("clock") if isinstance(raw.get("clock"), dict) else {}
    tck = raw["partition_types"][tn].get("clock") or {}
    res = []
    for fld in ("tap_offset", "tap_window"):
        pp = (ck.get(fld) or {}).get("per_port_ps")
        if isinstance(pp, dict) and isinstance(pp.get(tn), dict):
            res.append((f"clock.{fld}.per_port_ps", pp, tn, "keys"))
    if isinstance(tck.get("tap_pin_heights_um"), dict):
        res.append(("tap_pin_heights_um", tck, "tap_pin_heights_um", "keys"))
    tg = tck.get("tap_group")
    if isinstance(tg, dict) and isinstance(tg.get("fixed_taps"), dict):
        res.append(("tap_group.fixed_taps", tg, "fixed_taps", "values"))
    return res


def current_sites(P, raw, tn):
    """{grid port: (x, y)} of the current tap grid (core taps excluded) or raises."""
    import schema as S
    return {n: (float(x), float(y)) for n, x, y in S.tap_grid(P, tn) if not _is_core(n)}


def _stamped(raw, tn):
    s = ((raw["partition_types"][tn].get("clock") or {}).get(STAMP))
    if not isinstance(s, dict):
        return None
    return {p: (float(xy[0]), float(xy[1])) for p, xy in s.items() if isinstance(xy, (list, tuple)) and len(xy) == 2}


def stamp_type(raw, tn, sites):
    raw["partition_types"][tn].setdefault("clock", {})[STAMP] = {p: [round(x, 3), round(y, 3)] for p, (x, y) in sorted(sites.items())}


def rekey_type(raw, tn, sites, tol=TOL_UM):
    """re-key type tn's stamped tables onto `sites` (current grid) in place and re-stamp -> report dict, or None without a stamp."""
    old = _stamped(raw, tn)
    if old is None:
        return None
    m, unsited = site_map(old, sites, tol)
    rep = dict(type=tn, stamped=len(old), renamed=sum(1 for o, n in m.items() if o != n), unsited=unsited, tables={})
    for label, box, key, form in type_tables(raw, tn):
        new, ren, drop = (_rename if form == "keys" else _revalue)(box[key], m, set(unsited))
        box[key] = new
        rep["tables"][label] = dict(renamed=ren, dropped=drop)
    stamp_type(raw, tn, sites)
    return rep


def check_type(raw, tn, sites, tol=TOL_UM):
    """report only: (moved [(port, new port or None, um)], stamped count) for type tn, or None without a stamp."""
    old = _stamped(raw, tn)
    if old is None:
        return None
    m, unsited = site_map(old, sites, tol)
    moved = []
    for p in sorted(old):
        if p in m and m[p] == p:
            continue
        q = m.get(p)
        d = (min(abs(old[p][0] - x) + abs(old[p][1] - y) for x, y in sites.values()) if sites else float("inf"))
        moved.append((p, q, d))
    return moved, len(old)


ROOTS = {}     # plan path -> repo root its repo-relative inputs (physical/.../sink_bins/x.json) resolve against (diff --root/--base-root)


def _plandir(plan_path):
    """plan-relative tap inputs (sink_bins/) resolve against the plan's folder (as bind.py sets it, KW-FIX-45), then that plan's
    repo root (ROOTS) or the tool tree."""
    try:
        import taps as _T
        _T.PLAN_DIR = str(Path(plan_path).resolve().parent)
        r = ROOTS.get(str(plan_path))
        if r:
            _T._root = lambda r=r: Path(r)
    except Exception:  # noqa: BLE001
        pass


def _plan(raw, plan_path):
    import schema as S
    _plandir(plan_path)
    return S.Plan(raw, Path(plan_path))


def rekey_plan(raw, plan_path, types=None, P=None, log=print):
    """gen_phys hook: re-key every stamped type (in place) -> [report]; a type whose grid cannot be evaluated is left unchanged."""
    P = P or _plan(raw, plan_path)
    reps = []
    for tn in sorted(raw.get("partition_types") or {}):
        if types and tn not in types or _stamped(raw, tn) is None:
            continue
        try:
            sites = current_sites(P, raw, tn)
        except Exception as e:  # noqa: BLE001
            log(f"TAPKEY-SITE {tn}: grid not evaluable ({type(e).__name__}), stamped tables left as written")
            continue
        r = rekey_type(raw, tn, sites)
        if r and (r["renamed"] or r["unsited"]):
            log(f"TAPKEY-SITE {tn}: re-keyed by site: {r['renamed']} of {r['stamped']} stamped taps renamed, {len(r['unsited'])} unsited "
                f"({','.join(r['unsited'][:6])}); " + "; ".join(f"{k} {v['renamed']} renamed / {v['dropped']} dropped" for k, v in r["tables"].items()))
        reps.append(r)
    return reps


def diff_type(raw, braw, tn, sites, bsites, tol=TOL_UM):
    """-> dict(type, common, moved [(port, um, [tables referencing it in raw])], new, gone, tables {label: rows})"""
    refs = {}
    for label, box, key, form in type_tables(raw, tn):
        ports = box[key].keys() if form == "keys" else box[key].values()
        for q in ports:
            refs.setdefault(q, []).append(label)
    tabs = {label: len(box[key]) for label, box, key, form in type_tables(raw, tn)}
    common = sorted(set(sites) & set(bsites))
    moved = []
    for q in common:
        d = abs(sites[q][0] - bsites[q][0]) + abs(sites[q][1] - bsites[q][1])
        if d > tol:
            moved.append((q, d, refs.get(q, [])))
    moved.sort(key=lambda x: -x[1])
    # carried = a moved name whose row VALUE in raw equals the baseline's row for that name: the row came over unchanged from the
    # old site (stale unless re-measured to the same value); re-written rows are probably measured on the new grid
    btabs = {label: box[key] for label, box, key, form in type_tables(braw, tn) if form == "keys"}
    carried = 0
    for q, _d, labs in moved:
        for label, box, key, form in type_tables(raw, tn):
            if form == "keys" and label in labs and q in box[key] and q in (btabs.get(label) or {}) and box[key][q] == btabs[label][q]:
                carried += 1
                break
    return dict(type=tn, common=len(common), moved=moved, carried=carried, new=len(set(sites) - set(bsites)), gone=len(set(bsites) - set(sites)),
                tables=tabs)


def diff_plans(raw, plan_path, braw, base_path, types=None, tol=TOL_UM):
    """-> (rows [diff_type dict], unevaluable [(type, why)]) for every type in both plans."""
    P, PB = _plan(raw, plan_path), _plan(braw, base_path)
    rows, unev = [], []
    for tn in sorted(set(raw.get("partition_types") or {}) & set(braw.get("partition_types") or {})):
        if types and tn not in types:
            continue
        try:
            _plandir(plan_path)
            sites = current_sites(P, raw, tn)
            _plandir(base_path)
            bsites = current_sites(PB, braw, tn)
        except Exception as e:  # noqa: BLE001
            unev.append((tn, f"{type(e).__name__}: {str(e)[:120]}"))
            continue
        rows.append(diff_type(raw, braw, tn, sites, bsites, tol))
    return rows, unev


def stamp_from_baseline(raw, braw, base_path, types=None, force=False):
    """stamp every type of raw that has name-keyed tables (and no stamp, unless force) with its tap sites in the BASELINE plan
    (the grid its rows were written on) -> number of types stamped.  A type absent from / not evaluable in the baseline is left."""
    PB = _plan(braw, base_path)
    n = 0
    for tn in sorted(raw.get("partition_types") or {}):
        if (types and tn not in types) or not type_tables(raw, tn) or tn not in (braw.get("partition_types") or {}):
            continue
        if _stamped(raw, tn) is not None and not force:
            continue
        try:
            _plandir(base_path)
            stamp_type(raw, tn, current_sites(PB, braw, tn))
            n += 1
        except Exception as e:  # noqa: BLE001
            print(f"TAPKEY-SITE baseline stamp {tn}: grid not evaluable ({type(e).__name__}), left unstamped", file=sys.stderr)
    return n


def needs_rekey(raw):
    return any(isinstance((t.get("clock") or {}).get(STAMP), dict) for t in (raw.get("partition_types") or {}).values())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("stamp", "rekey", "check", "diff"))
    ap.add_argument("--baseline")
    ap.add_argument("--root", help="repo root of PLAN's repo-relative inputs (sink_bins); default the tool tree")
    ap.add_argument("--base-root", help="same for --baseline")
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--types", default="")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    if a.root:
        ROOTS[str(a.plan)] = a.root
    if a.base_root and a.baseline:
        ROOTS[str(a.baseline)] = a.base_root
    types = [t for t in a.types.split(",") if t] or None
    P = _plan(raw, a.plan)
    if a.mode == "diff":
        braw = json.loads(Path(a.baseline).read_text())
        rows, unev = diff_plans(raw, a.plan, braw, a.baseline, types)
        nm = sum(1 for r in rows if r["moved"])
        nref = sum(1 for r in rows for m in r["moved"] if m[2])
        for r in sorted(rows, key=lambda r: -len(r["moved"])):
            if not r["moved"]:
                continue
            refd = [m for m in r["moved"] if m[2]]
            print(f"MOVED\t{r['type']}\t{len(r['moved'])} of {r['common']} common tap names moved > {TOL_UM:g} um "
                  f"(worst {r['moved'][0][0]} {r['moved'][0][1]:.0f} um); {len(refd)} referenced by name-keyed tables, "
                  f"{r['carried']} of them with a row value carried unchanged from the baseline: "
                  + " ".join(f"{q}({','.join(sorted(set(t)))})" for q, _d, t in refd[:10]))
        if types:
            for r in rows:
                print(f"TYPE\t{r['type']}\tcommon {r['common']}, moved {len(r['moved'])}, new {r['new']}, gone {r['gone']}, "
                      + ", ".join(f"{k} {v} rows" for k, v in r["tables"].items()))
        for tn, why in unev:
            print(f"NOT-EVALUABLE\t{tn}\t{why}")
        print(f"SUMMARY\ttypes {len(rows)} evaluated, {len(unev)} not evaluable; {nm} types with moved tap names, "
              f"{sum(len(r['moved']) for r in rows)} moved names, {nref} of them referenced by a name-keyed table, "
              f"{sum(r['carried'] for r in rows)} with the row carried unchanged from the baseline "
              f"(tap_offset / tap_window per_port_ps, tap_pin_heights_um, tap_group.fixed_taps); tol {TOL_UM:g} um")
        return 0
    if a.mode == "check":
        for tn in sorted(raw.get("partition_types") or {}):
            if types and tn not in types:
                continue
            try:
                r = check_type(raw, tn, current_sites(P, raw, tn))
            except Exception as e:  # noqa: BLE001
                print(f"{tn}\tNOT-EVALUABLE\t{type(e).__name__}")
                continue
            if r is not None:
                print(f"{tn}\tstamped {r[1]}\tmoved {len(r[0])}\t" + " ".join(f"{p}->{q or 'UNSITED'}" for p, q, _ in r[0][:8]))
        return 0
    if not a.out:
        ap.error("--out is required for stamp / rekey")
    out = copy.deepcopy(raw)
    if a.baseline and a.mode in ("stamp", "rekey"):
        # tables written on the BASELINE grid and never stamped: stamp each with the baseline sites of its type
        n = stamp_from_baseline(out, json.loads(Path(a.baseline).read_text()), a.baseline, types, force=(a.mode == "stamp"))
        print(f"TAPKEY-SITE stamp --baseline: {n} types stamped with {a.baseline} sites", file=sys.stderr)
        if a.mode == "stamp":
            Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
            return 0
        P = _plan(out, a.plan)
    if a.mode == "rekey":
        _plandir(a.plan)
        reps = rekey_plan(out, a.plan, types, P=P)
        tot = {}
        for r in reps:
            for k, v in r["tables"].items():
                t = tot.setdefault(k, [0, 0, 0])
                t[0] += v["renamed"]
                t[1] += v["dropped"]
        kept = 0
        for r in reps:
            for label, box, key, form in type_tables(out, r["type"]):
                kept += len(box[key])
        print(f"TAPKEY-SITE rekey: {len(reps)} stamped types, {sum(r['renamed'] for r in reps)} stamped taps renamed, "
              f"{sum(len(r['unsited']) for r in reps)} unsited; rows: " + "; ".join(f"{k} {v[0]} re-keyed / {v[1]} dropped" for k, v in sorted(tot.items()))
              + f"; {kept} rows after", file=sys.stderr)
    elif a.mode == "stamp":
        for tn in sorted(out.get("partition_types") or {}):
            if types and tn not in types:
                continue
            if not type_tables(out, tn):
                continue
            try:
                stamp_type(out, tn, current_sites(P, out, tn))
            except Exception as e:  # noqa: BLE001
                print(f"TAPKEY-SITE stamp {tn}: grid not evaluable ({type(e).__name__}), not stamped", file=sys.stderr)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
