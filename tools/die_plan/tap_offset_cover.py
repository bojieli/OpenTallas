#!/usr/bin/env python3
"""tap_offset_cover.py: all-mode coverage of plan clock.tap_offset.per_port_ps (TAPOFF-ALL 11-23, FABLE-UNC-KV, DIE-FIX-LEDGER x10).

    tap_offset_cover.py census PLAN [--out TSV] [--types REGEX]                rc 0 = every listed type fully covered
    tap_offset_cover.py fill   PLAN OUT [--max-tol 40] [--report TSV] [--types REGEX]
    both: [--tools TREE/tools/die_plan] when PLAN is not inside the die tree whose plan folder it uses (else types come out UNEVALUATED)

Why: a type with a per_port_ps row times each tap port at its die arrival offset (R-CLOCK-7); a kit clock port MISSING from the row is charged
the full span early -W / late 0 (gen_phys.tap_offset_lines).  Rows that append taps (tap_split, hand rows) do not extend the table, so every added
tap is charged W against its neighbours: cross-tap hold TNS ~100k at CTS, RSZ-0060 at GRT (QC, KV 11-23).  The first census read tap_mode
"density" only; on KV that is 25 of 57 types, and 246 added taps on 11 grid+explicit types passed it unseen.

Ports of a type = schema.tap_grid(P, type): the grid taps the kit really gets, in EVERY tap mode (density, grid, grid+explicit, explicit), with
their sites.  Core taps (schema.core_taps, clk_c*) carry measured rows of their own and are never written here; a core tap without a row is
listed (core_missing) but does not fail the census.

census: one line per type with a table: grid ports, missing, stale (row port that is no longer a grid or core tap), W.  A type whose tap grid
cannot be evaluated (the tap solver raises, e.g. an added tap violating spacing) is UNEVALUATED: its added taps are still compared by name
(lower bound), and the census FAILS on it; it is never passed silently.  rc 1 when any listed type has a missing port or is unevaluated.

fill: each missing grid port gets a row ESTIMATED from the listed grid taps of the same type: offset = inverse-distance mean of the 3 nearest
(TT and FF), tol = max(type tol, the 95th percentile of the leave-one-out error of that estimate on the listed taps, half the offset range of the
3 neighbours), rounded up to 0.1 ps.  Copying a neighbour's tol understates: leave-one-out p95 on KV pv types is 13..62 ps against a tol of 10.1.
A type is skipped (and the run fails) when it has fewer than 4 listed sited taps, or when the leave-one-out p95 exceeds both --max-tol and half
the type's offset span (an estimate must beat the [-W, 0] it replaces).  An unevaluated type is filled from its listed ADDED taps (their sites
are in the plan) when it has at least 4 of them, added taps only.  Stale rows are removed.  Estimates stand until die_sta_related
--kit-offset-out re-measures; clock.tap_offset.source records the fill.  Die-agnostic: nothing here names a die or a type.

WINDOW form (TAPWIN-ALL, S81 x9): a type with a clock.tap_window.per_port_ps row and NO offsets row times each port with its measured window
D_p; a port missing from the row falls back to the type's flat W_t (gen_phys.port_window_ps), so taps added after the measurement are timed
against the wider window.  Both commands cover these types too (column form = window; --form offset|window|all, default all).  The census
rule is the same.  fill writes D = the LARGEST window of the 3 nearest listed taps of the type (a window is a per-tap uncertainty, not a
field over the die: no interpolation, the cautious neighbour), never above the type's largest listed window; tap_window_measure.py on the
kit CTS replaces it.
"""
import argparse
import json
import os
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The tap grid of a type reads plan-folder inputs (sink_bins ...) relative to the repo root of the tools that are imported.  A composed plan
# that lives outside its die tree therefore needs that tree's tools: --tools TREE/tools/die_plan (or OT_TAPOFF_TOOLS), read before the import.
_T = os.environ.get("OT_TAPOFF_TOOLS")
if "--tools" in sys.argv:
    _i = sys.argv.index("--tools")
    _T = sys.argv[_i + 1]
    del sys.argv[_i:_i + 2]
sys.path.insert(0, str(Path(_T).resolve() if _T else HERE))
import schema as S  # noqa: E402


def _up(v):
    return math.ceil(v * 10 - 1e-9) / 10.0


def type_ports(P, raw, tn):
    """-> (sites {grid port: (x, y)}, core port names, why): why is None, or the reason the tap grid could not be evaluated
    (then sites holds the plan's added taps only)."""
    ty = raw["partition_types"][tn]
    try:
        core = {c[0] for c in S.core_taps(P, tn)}
    except Exception:                                   # noqa: BLE001
        core = set()
    try:
        return {n: (float(x), float(y)) for n, x, y in S.tap_grid(P, tn)}, core, None
    except Exception as e:                              # noqa: BLE001  the census must report it, not die on it
        added = {a["name"]: (float(a["xy"][0]), float(a["xy"][1])) for a in (ty.get("clock") or {}).get("added_taps") or []
                 if isinstance(a.get("xy"), (list, tuple))}
        return added, core, f"{type(e).__name__}: {str(e)[:160]}"


def tables(raw, form="all"):
    """[(form, type, row)] the offsets rows, then the window rows of the types that have no offsets row (the offsets form wins in gen_phys)."""
    ck = raw.get("clock") or {}
    off = (ck.get("tap_offset") or {}).get("per_port_ps") or {}
    win = (ck.get("tap_window") or {}).get("per_port_ps") or {}
    out = [("offset", tn, off[tn]) for tn in sorted(off)] if form in ("all", "offset") else []
    if form in ("all", "window"):
        out += [("window", tn, win[tn]) for tn in sorted(win) if win[tn] and not off.get(tn)]
    return [x for x in out if x[1] in raw["partition_types"]]


def census(raw, plan_path=None, types=None, form="all", port_results=None):
    """[row dict] for every type with a per_port_ps table (offsets or window form)."""
    P = S.Plan(raw, Path(plan_path)) if plan_path else S.Plan(raw)
    rows = []
    for fm, tn, tab in tables(raw, form):
        if types and not re.search(types, tn):
            continue
        cached = port_results.get(tn) if port_results is not None else None
        sites, core, why = cached if cached is not None else type_ports(P, raw, tn)
        miss = [p for p in sites if p not in tab]
        rows.append(dict(type=tn, form=fm, tap_mode=(raw["partition_types"][tn].get("clock") or {}).get("tap_mode") or "grid",
                         status="UNEVALUATED" if why else ("MISSING" if miss else "OK"), grid_ports=len(sites), rows=len(tab),
                         missing=len(miss), core_missing=len([c for c in core if c not in tab]),
                         stale=0 if why else len([p for p in tab if p not in sites and p not in core]),
                         sample=",".join(miss[:4]), why=why or ""))
    return rows


def _est(xy, pts, k=3):
    d = sorted((abs(xy[0] - p[0]) + abs(xy[1] - p[1]), i) for i, p in enumerate(pts))[:k]
    w = [1.0 / max(x[0], 1.0) for x in d]
    sw = sum(w)
    tt = sum(wi * pts[i][2] for wi, (_d, i) in zip(w, d)) / sw
    ff = sum(wi * pts[i][3] for wi, (_d, i) in zip(w, d)) / sw
    return tt, ff, (max(pts[i][2] for _d, i in d) - min(pts[i][2] for _d, i in d)) / 2.0


def _fill_window(tab, sites, miss, r):
    """window form: D of a missing port = the largest window of its 3 nearest listed sited taps (<= the largest listed window)."""
    known = [(sites[p][0], sites[p][1], float(tab[p])) for p in tab if p in sites]
    if len(known) < 4:
        r["status"] = f"SKIP fewer than 4 listed sited taps ({len(known)})"
        return False
    top = max(q[2] for q in known)
    ds = []
    for p in miss:
        near = sorted((abs(sites[p][0] - q[0]) + abs(sites[p][1] - q[1]), q[2]) for q in known)[:3]
        d = min(top, max(x[1] for x in near))
        d = int(d) if float(d).is_integer() else _up(d)
        tab[p] = d
        ds.append(d)
    r.update(added=len(miss), tol=f"{min(ds):g}..{max(ds):g}")
    return True


def fill(raw, plan_path=None, max_tol=40.0, types=None, form="all", port_results=None):
    """extend raw's per_port_ps tables in place -> [report row dict]."""
    P = S.Plan(raw, Path(plan_path)) if plan_path else S.Plan(raw)
    rep = []
    nwin = 0
    for fm, tn, tab in tables(raw, form):
        if types and not re.search(types, tn):
            continue
        sites, core, why = type_ports(P, raw, tn)
        if port_results is not None:
            port_results[tn] = sites, core, why
        miss = [p for p in sites if p not in tab]
        stale = [] if why else [p for p in tab if p not in sites and p not in core]
        if not miss and not stale:
            continue
        r = dict(type=tn, form=fm, added=0, stale_removed=0, status="", loo_p95="", tol="", why=why or "")
        if fm == "window":
            if miss and not _fill_window(tab, sites, miss, r):
                rep.append(r)
                continue
            for p in stale:
                del tab[p]
            nwin += r["added"]
            r.update(stale_removed=len(stale), status="NEIGHBOUR-MAX (added taps only: grid unevaluated)" if why else "NEIGHBOUR-MAX")
            rep.append(r)
            continue
        known = [(sites[p][0], sites[p][1], float(tab[p]["TT"]), float(tab[p]["FF"])) for p in tab if p in sites]
        if miss and len(known) < 4:
            r["status"] = f"SKIP fewer than 4 listed sited taps ({len(known)})"
            rep.append(r)
            continue
        if miss:
            err = sorted(abs(_est(q[:2], known[:i] + known[i + 1:])[0] - q[2]) for i, q in enumerate(known))
            p95 = err[min(len(err) - 1, int(0.95 * len(err)))]
            span = max(q[2] for q in known) - min(q[2] for q in known)
            lim = max(float(max_tol), span / 2.0)
            if p95 > lim:
                r["status"] = f"SKIP leave-one-out p95 {p95:.1f} > {lim:.1f}: re-measure"
                rep.append(r)
                continue
            ttol = max(float(v["tol"]) for v in tab.values())
            tols = []
            for p in miss:
                tt, ff, rng = _est(sites[p], known)
                tol = _up(max(ttol, p95, rng))
                tols.append(tol)
                tab[p] = {"TT": round(tt, 1), "FF": round(ff, 1), "tol": tol}
            r.update(added=len(miss), loo_p95=f"{p95:.1f}", tol=f"{min(tols):.1f}..{max(tols):.1f}")
        for p in stale:
            del tab[p]
        r.update(stale_removed=len(stale), status="ESTIMATED (added taps only: grid unevaluated)" if why else "ESTIMATED")
        rep.append(r)
    if nwin:
        tw = raw["clock"]["tap_window"]
        tw["note"] = (str(tw.get("note") or "") + f" | tap_offset_cover fill: {nwin} grid tap ports without a per-port window took the largest "
                      "window of their 3 nearest listed taps; tap_window_measure.py on the kit CTS replaces them").strip(" |")
    n = sum(x["added"] for x in rep if x["form"] == "offset")
    if n:
        to = raw["clock"]["tap_offset"]
        to["source"] = (str(to.get("source") or "") + f" | tap_offset_cover fill: {n} grid tap ports without a row ESTIMATED from the 3 nearest "
                        "listed taps of their type (tol >= leave-one-out p95); die_sta_related --kit-offset-out replaces them").strip(" |")
    return rep


def _tsv(rows, cols):
    return "\t".join(cols) + "\n" + "".join("\t".join(str(r[c]) for c in cols) + "\n" for r in rows)


CCOLS = ["type", "form", "tap_mode", "status", "grid_ports", "rows", "missing", "core_missing", "stale", "sample", "why"]
FCOLS = ["type", "form", "added", "stale_removed", "status", "loo_p95", "tol", "why"]


def census_rc(rows):
    return 1 if any(r["status"] != "OK" for r in rows) else 0


def _report_census(rows, out):
    if out:
        Path(out).write_text(_tsv(rows, CCOLS))
    bad = [r for r in rows if r["status"] != "OK"]
    for r in bad:
        print("\t".join(str(r[k]) for k in CCOLS)[:300])
    print(f"TAPOFF-ALL census: listed types {len(rows)} ok {len(rows) - len(bad)} missing_types {sum(r['status'] == 'MISSING' for r in rows)} "
          f"missing_ports {sum(r['missing'] for r in rows if r['status'] == 'MISSING')} unevaluated_types {sum(r['status'] == 'UNEVALUATED' for r in rows)} "
          f"(added taps without a row there, by name: {sum(r['missing'] for r in rows if r['status'] == 'UNEVALUATED')}) stale_rows {sum(r['stale'] for r in rows)} "
          f"core_missing {sum(r['core_missing'] for r in rows)} -> {'FAIL' if bad else 'PASS'}")
    return census_rc(rows)


def fwdclk_repick(raw, plan_path, types=None, whatif=()):
    """FWDCLK-REPICK (FABLE-RC-ALL class fix 11-24, r703 report-only): a fill runs after every tap change of a compose, so it lists
    every forwarded-clock export whose source tap is now over derived_drop.EXPORT_HOP_UM with the two-sided pick of
    fwdclk_repoint (exports otherwise keep the tap of their first tree cut).  Never changes the plan or the rc;
    OT_FWDCLK_REPICK=0 turns it off."""
    if os.environ.get("OT_FWDCLK_REPICK", "1") == "0":
        return []
    try:
        import fwdclk_repoint as FR
        W = {}
        for w in whatif or ():
            W.update(json.loads(Path(w).read_text()))
        tl = None
        if types:
            rx = re.compile(types)
            tl = {tn for tn in raw.get("partition_types") or {} if rx.search(tn)}
        lines = FR.repick_lines(FR.repick_report(raw, S.Plan(raw, plan_path), tl, W))
    except Exception as e:  # noqa: BLE001 - report-only: never a fill failure, never a silent pass
        lines = [f"WARN FWDCLK-REPICK not checked ({type(e).__name__}: {str(e)[:160]})"]
    for x in lines:
        print(x)
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    c.add_argument("plan")
    c.add_argument("--out")
    c.add_argument("--types")
    c.add_argument("--form", choices=("all", "offset", "window"), default="all")
    f = sub.add_parser("fill")
    f.add_argument("plan")
    f.add_argument("out")
    f.add_argument("--max-tol", type=float, default=40.0)
    f.add_argument("--report")
    f.add_argument("--census-out", help="also run the completed plan census and write its TSV")
    f.add_argument("--types")
    f.add_argument("--form", choices=("all", "offset", "window"), default="all")
    f.add_argument("--fwdclk-whatif", action="append", default=[],
                   help="fwdclk_repoint agg json(s): the FWDCLK-REPICK report is two-sided where it covers a ring")
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    if a.cmd == "census":
        return _report_census(census(raw, a.plan, a.types, a.form), a.out)
    # Fill changes only per-port timing values. The geometry and relative inputs
    # are identical for sibling plans, so census can reuse their resolved ports.
    port_results = {} if a.census_out and Path(a.plan).resolve().parent == Path(a.out).resolve().parent else None
    rep = fill(raw, a.plan, a.max_tol, a.types, a.form, port_results)
    Path(a.out).write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    if a.report:
        Path(a.report).write_text(_tsv(rep, FCOLS))
    print(_tsv(rep, FCOLS), end="")
    skipped = [r for r in rep if r["status"].startswith("SKIP")]
    print(f"TAPOFF-ALL fill: ports {sum(r['added'] for r in rep)} types {sum(1 for r in rep if r['added'])} stale_removed {sum(r['stale_removed'] for r in rep)} "
          f"skipped {len(skipped)} -> {'FAIL' if skipped else 'OK'}")
    fwdclk_repick(raw, a.out, a.types, a.fwdclk_whatif)
    census_status = 0
    if a.census_out:
        rows = census(raw, a.out, a.types, a.form, port_results)
        census_status = _report_census(rows, a.census_out)
    return 1 if skipped else census_status


if __name__ == "__main__":
    sys.exit(main())
