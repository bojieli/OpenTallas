#!/usr/bin/env python3
"""PLAN TIMING AUDIT (PLAN-READERS-1 11-15, FABLE-METHOD levers 1 and 8).  Runs on a plan + the signed core views, builds nothing.

(a) REACH.  Every register-to-register hop a plan lane creates (port -> face pin -> ft station -> ... -> face pin, the first
    internal hop of a normal ft slot, via mandatory slot pins; check.lane_geometry / lane_pin_hops, the same geometry the G0 hops
    check uses) is priced in ps:  hop_ps = CLKQ_PS + PS_PER_UM * hop_um   (PS_PER_UM = 0.65, FABLE-METHOD s1: buffered wire,
    hd_spn 806 ps / 1,261 um; REACH-M89 calibrated constant 0.76 is the planning value).  A hop FAILS when
    hop_ps > period - SETUP_PS - MARGIN_PS   (MARGIN_PS = 150 = the REACH-M89 setup uncertainty 60 + skew 90).
    Each failing lane is attributed to every partition type its route crosses.
(b) CORE BOUNDARY.  For every hard core instance / clock pin: the MEASURED clock depth I = the signed (or provisional) run's
    pin-register mean at TT (core_clock_contract.load: clock_contract.json / signoff.json insertion_pinflops / insertion.json,
    all raw flop clock arrivals of the routed database, NEVER liberty arcs), against the type clock budget T (clock.insertion_ps,
    else the die common latency; S81/QC 250, HEAD 450):
      - no early tap:   FAIL when I > T - DEPTH_MARGIN_PS (FABLE-METHOD lever 2: usable only if I <= T - ~50);
      - early tap:      FAIL when |I - tap.insertion_ps| > tol (tap.insertion_tol_ps, default 40): the declared early tap
                        does not match the measured core.  Deliverability of the early arrival (spine arrival) is not checkable
                        from the plan and is listed as a note, never assumed.
      - boundary arcs:  clk->q max + setup max of the core's liberty (zero wire, timing_type rising_edge / setup_rising) against
                        the cycle: headroom = period - clkq - setup; with an early tap clkq is credited by the tap: eff = common + clkq - tap insertion
                        (the liberty arc includes the core insertion); FAIL when headroom < MARGIN_PS.
      - no measurement: UNMEASURED (COORD 11-15: does NOT fail): the core has no clock contract / signoff / insertion.json;
                        reported with the liberty-derived fallback depth (basis LIB) and counted per die.
Output: per-die table of failing types with the numbers (tsv / json).  G0: check.py --timing-audit {off,warn,error}.

Not covered (listed gaps): reset / start relay chains (built by reset_tree with relay reach <= 405 um by construction; the QC
cland relay failures are kit-side), ring control, bin-to-core and core-to-core hops that are not plan lanes (needs core
connectivity, check.py --core-conns).

CLI: plan_timing_audit.py PLAN --root REPO_ROOT [--label S81] [--tsv OUT] [--json OUT] [--no-core-arcs]
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PS_PER_UM = 0.65
CLKQ_PS = 50.0
SETUP_PS = 25.0
MARGIN_PS = 150.0          # REACH-M89 setup uncertainty 60 + skew 90
DEPTH_MARGIN_PS = 50.0     # FABLE-METHOD lever 2
DEFAULT_TOL_PS = 40.0
EPS = 1e-6


def hop_limit_ps(period):
    return period - SETUP_PS - MARGIN_PS


def hop_ps(um):
    return CLKQ_PS + PS_PER_UM * um


# ------------------------------------------------------------------------------------------------- (a) reach
def _lane_types(P, lid, xs):
    """partition types a lane touches: every crossed partition plus the partitions at its port ends"""
    parts = {x["part"] for x in xs}
    for pid in P.lanes[lid]["ports"]:
        pr = P.ports.get(pid) or {}
        for side in ("src", "dst"):
            e = pr.get(side) or {}
            if e.get("part") in P.parts:
                parts.add(e["part"])
    return sorted({P.parts[p]["type"] for p in parts})


def audit_reach(P, geo=None):
    """[dict(lane, hop, hop_um, hop_ps, limit_ps, types, first)] of every lane hop over the limit, worst first."""
    import check as CK
    period = float(P.die["period_ps"]) if "period_ps" in P.die else 833.0
    limit = hop_limit_ps(period)
    rows = []
    first_cache, tables = {}, {}
    for lid in P.lanes:
        pts, regs, xs = geo[lid] if geo and lid in geo else CK.lane_geometry(P, lid)
        hops = CK.lane_pin_hops(P, lid, regs) or [0.0]
        first = 0.0
        try:
            from die_hop_scan import pin_table, first_internal_hops
            for x in xs:
                tn = P.parts[x["part"]]["type"]
                ck = (tn, x["slot"])
                if ck not in first_cache:             # per (type, slot), not per lane: pin_table / first hops are lane independent
                    slot = next((s for s in P.types[tn].get("ft_slots", []) if s["name"] == x["slot"]), None)
                    if slot is None:
                        first_cache[ck] = 0.0
                    else:
                        if tn not in tables:
                            tables[tn] = pin_table(P, tn)
                        first_cache[ck] = max((d for _b, d in first_internal_hops(P, tn, slot, pins=tables[tn])), default=0.0)
                first = max(first, first_cache[ck])
        except Exception:                                   # the first-hop view is best effort; the lane hops stay
            first = 0.0
        worst = max(hops + [first])
        ps = hop_ps(worst)
        if ps > limit + EPS:
            rows.append(dict(lane=lid, hop_index=hops.index(worst) if worst in hops else -1, hop_um=round(worst, 1),
                             hop_ps=round(ps, 1), limit_ps=round(limit, 1), over_ps=round(ps - limit, 1),
                             types=_lane_types(P, lid, xs), first_internal=first > max(hops)))
    rows.sort(key=lambda r: -r["over_ps"])
    return rows


# ------------------------------------------------------------------------------------------------- (b) cores
_ARC_CACHE = {}


def lib_boundary_arcs(path):
    """(clkq_max_ps, setup_max_ps) of a liberty: max over timing groups of the MEDIAN table entry for timing_type rising_edge (cell_rise / cell_fall)
    and setup_rising (rise / fall constraint), in ps (a typical slew / load point; the table corner is an upper bound that
    overstates the arcs, e.g. kp4 clk->q 609 corner vs ~480 typical)."""
    key = str(path)
    if key in _ARC_CACHE:
        return _ARC_CACHE[key]
    text = Path(path).read_text(errors="replace")
    m = re.search(r"time_unit\s*:\s*\"?1(ps|ns)\"?", text)
    k = 1000.0 if (m and m.group(1) == "ns") else 1.0
    clkq = setup = 0.0
    for chunk in re.split(r"timing\s*\(\s*\)\s*\{", text)[1:]:
        chunk = chunk[:60000]
        tt = re.search(r"timing_type\s*:\s*\"?(\w+)", chunk)
        if not tt:
            continue
        typ = tt.group(1)
        if typ == "rising_edge":
            tabs = re.findall(r"cell_(?:rise|fall)\s*\([^)]*\)\s*\{(.*?)\}", chunk, flags=re.S)
        elif typ == "setup_rising":
            tabs = re.findall(r"(?:rise|fall)_constraint\s*\([^)]*\)\s*\{(.*?)\}", chunk, flags=re.S)
        else:
            continue
        for tb in tabs:
            v = re.search(r"values\s*\((.*?)\)\s*;", tb, flags=re.S)
            vals = sorted(float(x) for x in re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", v.group(1))) if v else []
            if vals:
                med = vals[len(vals) // 2] * k              # median of the table: a typical slew / load point, not the corner
                if typ == "rising_edge":
                    clkq = max(clkq, med)
                else:
                    setup = max(setup, med)
    _ARC_CACHE[key] = (clkq, setup)
    return _ARC_CACHE[key]


def _shared_dir_guard(loaded):
    """an insertion.json / clock_contract.json / signoff.json measures ONE core; when its directory holds the liberties of several
    cores (S81 romq_split_1106: gb_he + gb_hw) core_clock_contract.load cannot tell whose number it is, so the measurement is not
    attributable: refuse it (UNMEASURED) instead of judging one core by another's depth."""
    import core_clock_contract as CC
    for v in loaded.values():
        src = Path(str(v.get("contract_source") or ""))
        if src.name in ("insertion.json", "clock_contract.json", "signoff.json") and src.parent.is_dir():
            n = len(list(src.parent.glob("*_tt.lib")))
            if n > 1:
                raise CC.ContractError(f"{src}: shared by {n} core libraries in one directory (measurement not attributable to one core)")


def type_budget(P, tn):
    ck = P.types[tn].get("clock") or {}
    if ck.get("insertion_ps") is not None:
        return float(ck["insertion_ps"])
    return float(P.clock["insertion_ps"])


def _tap_for(t, inst, pin):
    """the plan early core tap dict serving inst/pin, or None"""
    ck = t.get("clock") or {}
    if ck.get("core_taps") != "early":
        return None
    for tp in ck.get("taps", []) or []:
        if tp.get("kind") != "core":
            continue
        nm = tp["name"]
        if nm == inst or nm == f"{inst}.{pin}" or (tp.get("merged_clock_ports") and nm.startswith(inst + ".") and pin in tp["merged_clock_ports"]):
            return tp
    return None


def audit_cores(P, root=None, arcs=True):
    """one row per (type, core module, clock pin, tap kind): the measured depth vs the type budget + boundary arcs.
    Rows carry verdict PASS | FAIL | UNMEASURED and the failing reasons.  Instances of one module in one type with the same
    tap decision are folded (n_inst)."""
    import core_clock_contract as CC
    period = float(P.die["period_ps"]) if "period_ps" in P.die else 833.0
    common = float(P.clock["insertion_ps"])
    rows, fold = [], {}
    loaded_cache, _clk_cache = {}, {}
    for tn, t in P.types.items():
        if t.get("hard"):
            continue
        T = type_budget(P, tn)
        for core in t.get("hard_cores", []) or []:
            mod = core.get("module", core["inst"])
            key0 = (mod, core.get("lib"))            # one liberty parse per core view, not per type (S81: 334 types x one lib)
            try:
                if key0 in loaded_cache and isinstance(loaded_cache[key0], Exception):
                    raise loaded_cache[key0]
                if key0 not in loaded_cache:
                    try:
                        loaded_cache[key0] = CC.load(core, root, require_signed=False, plan_type=t)
                        _shared_dir_guard(loaded_cache[key0])
                    except (CC.ContractError, OSError, ValueError) as e0:
                        loaded_cache[key0] = e0
                        raise
                loaded = loaded_cache[key0]
            except (CC.ContractError, OSError, ValueError) as exc:
                # COORD 11-15: UNMEASURED does not fail.  Reported with the liberty-derived fallback depth (basis LIB: the lib's
                # max_clock_tree_path TT, a library arc, NOT a measurement) and what it would decide.
                lib_depth = None
                try:
                    import cores as C
                    ck = _clk_cache.get(key0)
                    if ck is None:
                        ck = _clk_cache[key0] = C.clock_pins(core, root)
                    if ck:
                        lib_depth = max(max(v["rise"], v["fall"]) for v in ck.values())
                except Exception:
                    lib_depth = None
                tp0 = _tap_for(t, core["inst"], "clk")
                k = (tn, mod, "-", "unmeasured", lib_depth)
                if k in fold:
                    fold[k]["n_inst"] += 1
                    continue
                would = None if not lib_depth else (lib_depth > T - DEPTH_MARGIN_PS + EPS if tp0 is None else
                                                    abs(lib_depth - float(tp0.get("insertion_ps", 0.0))) > float(tp0.get("insertion_tol_ps", DEFAULT_TOL_PS)) + EPS)
                fold[k] = dict(type=tn, module=mod, inst=core["inst"], pin="-", n_inst=1, budget_ps=T,
                               depth_ps=None if not lib_depth else round(lib_depth, 1),
                               over_ps=None if not lib_depth else round(lib_depth - T, 1), basis="LIB" if lib_depth else None,
                               signed=None, tap="early" if tp0 else "grid", verdict="UNMEASURED", lib_would_fail=would,
                               reasons=[f"no measured clock depth ({str(exc)[:110]}); LIB fallback depth "
                                        f"{'%.0f' % lib_depth + ' ps' if lib_depth else 'n/a'} (library arc, not a measurement)"])
                continue
            clkq = setup = None
            if arcs and core.get("lib"):
                import cores as C
                lib = C.resolve(core["lib"], root)
                try:
                    clkq, setup = lib_boundary_arcs(lib)
                except OSError:
                    pass
            for pin, val in sorted(loaded.items()):
                I = float(val["corners"]["tt"]["mean_ps"])
                tp = _tap_for(t, core["inst"], pin)
                reasons = []
                if tp is None:
                    kind = "grid"
                    if I > T - DEPTH_MARGIN_PS + EPS:
                        reasons.append(f"core clock depth {I:.0f} ps > budget {T:.0f} - {DEPTH_MARGIN_PS:.0f} with no early tap")
                else:
                    kind = "early"
                    ti = float(tp.get("insertion_ps", 0.0))
                    tol = float(tp.get("insertion_tol_ps", DEFAULT_TOL_PS))
                    if abs(I - ti) > tol + EPS:
                        reasons.append(f"early tap declares {ti:.0f} ps, measured depth {I:.0f} ps (|d| {abs(I - ti):.0f} > tol {tol:.0f})")
                head = None
                if clkq is not None and setup is not None and (clkq or setup):
                    # an early tap delivers the core clock earlier than the die common latency, and the liberty arc carries the
                    # core's own insertion (QC-CORES-HEAD 11-15): credit it.  eff clk->q = common + clk->q - tap insertion.
                    eff = clkq if tp is None else common + clkq - float(tp.get("insertion_ps", common))
                    head = period - eff - setup
                    if head < MARGIN_PS - EPS:
                        reasons.append(f"boundary arcs clk->q {eff:.0f} (lib {clkq:.0f}) + setup {setup:.0f} = {eff + setup:.0f} ps leave {head:.0f} ps "
                                       f"of {period:.0f} for wire (< {MARGIN_PS:.0f})")
                k = (tn, mod, pin, kind, round(I, 1), tuple(reasons))
                if k in fold:
                    fold[k]["n_inst"] += 1
                    continue
                fold[k] = dict(type=tn, module=mod, inst=core["inst"], pin=pin, n_inst=1, budget_ps=T, depth_ps=round(I, 1),
                               over_ps=round(I - T, 1), basis=val["corners"]["tt"]["basis"], signed=bool(val["signed"]),
                               tap=kind, tap_insertion_ps=(tp or {}).get("insertion_ps"), clkq_max_ps=None if clkq is None else round(clkq, 1),
                               setup_max_ps=None if setup is None else round(setup, 1),
                               arc_headroom_ps=None if head is None else round(head, 1),
                               verdict="FAIL" if reasons else "PASS", reasons=reasons)
    rows = list(fold.values())
    return rows


# ------------------------------------------------------------------------------------------------- report
def run(P, root=None, arcs=True, geo=None, reach_on=True):
    reach = audit_reach(P, geo) if reach_on else []
    cores = audit_cores(P, root, arcs)
    bad_types = defaultdict(lambda: dict(reach=[], cores=[]))
    for r in reach:
        for tn in r["types"]:
            bad_types[tn]["reach"].append(r)
    for r in cores:
        if r["verdict"] == "FAIL":
            bad_types[r["type"]]["cores"].append(r)
    return dict(reach=reach, cores=cores, failing_types=sorted(bad_types), by_type=dict(bad_types),
                params=dict(ps_per_um=PS_PER_UM, clkq_ps=CLKQ_PS, setup_ps=SETUP_PS, margin_ps=MARGIN_PS, depth_margin_ps=DEPTH_MARGIN_PS))


def tables(res, label="die"):
    """per-die text tables: failing types (reach lanes, core rows) with the numbers."""
    out = [f"== PLAN TIMING AUDIT {label}: failing types {len(res['failing_types'])}",
           f"-- (a) reach: lanes over the hop budget ({len(res['reach'])} lanes), worst first"]
    out.append("lane\thop_um\thop_ps\tlimit_ps\tover_ps\ttypes")
    for r in res["reach"][:200]:
        out.append(f"{r['lane']}\t{r['hop_um']}\t{r['hop_ps']}\t{r['limit_ps']}\t{r['over_ps']}\t{','.join(r['types'])}")
    out.append("-- (b) core boundary: FAIL / UNMEASURED cores (per type, module, pin); UNMEASURED rows carry the LIB fallback depth")
    out.append("type\tmodule\tpin\tn_inst\tbudget_ps\tdepth_ps\tover_ps\ttap\tclkq\tsetup\theadroom\tverdict\treasons")
    for r in sorted((c for c in res["cores"] if c["verdict"] != "PASS"), key=lambda c: (c["type"], c["module"], c["pin"])):
        out.append("\t".join(str(x) for x in (r["type"], r["module"], r["pin"], r["n_inst"], r["budget_ps"], r.get("depth_ps"), r.get("over_ps"),
                                              r.get("tap"), r.get("clkq_max_ps"), r.get("setup_max_ps"), r.get("arc_headroom_ps"),
                                              r["verdict"], "; ".join(r["reasons"]))))
    return "\n".join(out) + "\n"


def summary(res):
    c = defaultdict(int)
    for r in res["cores"]:
        c[r["verdict"]] += 1
    n_types = len({r["type"] for r in res["cores"]})
    lib = [r for r in res["cores"] if r["verdict"] == "UNMEASURED"]
    return dict(reach_failing_lanes=len(res["reach"]), core_rows=dict(c), failing_types=len(res["failing_types"]),
                unmeasured_rows=len(lib), unmeasured_types=len({r["type"] for r in lib}), unmeasured_instances=sum(r["n_inst"] for r in lib),
                unmeasured_lib_would_fail=sum(1 for r in lib if r.get("lib_would_fail")),
                core_types=n_types, worst_reach_over_ps=(res["reach"][0]["over_ps"] if res["reach"] else 0.0),
                worst_core_over_ps=max((r.get("over_ps") or 0.0 for r in res["cores"] if r["verdict"] == "FAIL"), default=0.0))


def g0(P, R, root=None, mode="warn", arcs=True, geo=None):
    """check.py hook: one finding per failing type (ERROR in mode error, WARN in mode warn); returns the summary."""
    if mode == "off":
        return None
    res = run(P, root, arcs, geo)
    emit = R.err if mode == "error" else R.warn
    for tn in res["failing_types"]:
        d = res["by_type"][tn]
        parts = []
        if d["reach"]:
            w = d["reach"][0]
            parts.append(f"reach: {len(d['reach'])} lane(s) over, worst {w['lane']} {w['hop_um']:.0f} um = {w['hop_ps']:.0f} ps > {w['limit_ps']:.0f}")
        if d["cores"]:
            w = max(d["cores"], key=lambda c: (c["verdict"] == "UNMEASURED", c.get("over_ps") or 0.0))
            parts.append(f"cores: {len(d['cores'])} row(s), e.g. {w['module']}.{w['pin']} {w['verdict']}: {'; '.join(w['reasons'])[:200]}")
        emit("timing_audit", f"type {tn}: " + " | ".join(parts), type=tn)
    sm = summary(res)
    if sm["unmeasured_rows"]:
        R.warn("timing_audit", f"{sm['unmeasured_rows']} core row(s) in {sm['unmeasured_types']} type(s) ({sm['unmeasured_instances']} instances) have "
               f"no measured clock depth (UNMEASURED, not a failure); LIB fallback would fail {sm['unmeasured_lib_would_fail']}")
    return sm


def main(argv=None):
    import argparse
    import schema as S
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--root", default=None)
    ap.add_argument("--label", default="die")
    ap.add_argument("--tsv")
    ap.add_argument("--json")
    ap.add_argument("--no-core-arcs", action="store_true")
    ap.add_argument("--no-reach", action="store_true", help="skip (a); cores only (fast)")
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan), path=a.plan)
    res = run(P, a.root, not a.no_core_arcs, reach_on=not a.no_reach)
    txt = tables(res, a.label)
    print(txt + json.dumps(summary(res)))
    if a.tsv:
        Path(a.tsv).write_text(txt)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=summary(res), reach=res["reach"], cores=res["cores"]), indent=1))
    return 1 if res["failing_types"] else 0


if __name__ == "__main__":
    sys.exit(main())
