#!/usr/bin/env python3
"""FWDCLK-REPOINT-1124 (KV-HG-CAP, COORD 11-24): one class tool, both dies, for PRE ENTRYFOOT. It clears
STALE-EXPORT-TAP (a forwarded-clock output fed from a tap more than derived_drop.EXPORT_HOP_UM from its pin) and
core-tap follow (an early core tap left behind by its moved hard core). The move is checked on both sides of the ring.

  fwdclk_repoint.py fix PLAN_IN PLAN_OUT [--types a,b|ALL] [--whatif W.json] [--family T=REP ...] [--baseline BASE]
                    [--ledger L.json]
  fwdclk_repoint.py agg WHATIF_DIR OUT.json      (WHATIF_DIR/<kit type>/p<k>/eco3.tsv from fwdclk_whatif.tcl)

Pick for a stale export (source hop > EXPORT_HOP_UM, a tap within EXPORT_HOP_UM exists):
  * measured: the type's own kit, or a --family representative, has a two-sided what-if row for the ring. Those rows
    come from fwdclk_whatif.tcl run on a 4_cts kit with PASS=k, which moves the export to the k-th nearest kit tap within
    the limit and re-times data-fclk min/max at the port. Take the nearest candidate that keeps min >= MIN_PS (sender
    contract) and max <= max(max_before, MAX_PS) + TOL_PS, i.e. the receiver landing setup is no worse than today or
    than the bound. If no candidate qualifies, take the least-bad one (smallest max) and mark the ledger NEEDS-SENDER:
    the data launch needs to move to the port (a port station), not the clock.
    Kit tap -> plan tap: the plan tap within the limit of the plan pin that is nearest the kit tap (pin offset applied).
  * unmeasured: the reach_rules.fix_fwd form (nearest tap) at EXPORT_HOP_UM, the same as QC-FWDCLK-REPOINT fwd300.py;
    ledger UNMEASURED.
Core-tap follow (with --baseline): each early core tap whose hard core moved since BASE (same orient and outline) is
shifted by exactly its core's delta (derived_drop ENTRYFOOT b, same EPS). No other plan field changes."""
import argparse, csv, fnmatch, glob, json, math, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import derived_drop as DD  # noqa: E402

LIM = DD.EXPORT_HOP_UM
MIN_PS, MAX_PS, TOL_PS = -385.0, 166.6, 5.0
EPS = 1e-6


def man(a, b):
    return abs(float(a[0]) - float(b[0])) + abs(float(a[1]) - float(b[1]))


def taps_of(grid):
    return [n for n in grid if n != "clk"] or list(grid)


def stale_pins(t, grid, lim=LIM):
    """export pins whose source is gone or over lim with a tap within lim (the repointable STALE-EXPORT-TAP set)"""
    tp = taps_of(grid)
    out = []
    for q in DD.export_pins(t):
        s, xy = q["source_clock_port"], q["xy_um"]
        if s in grid and man(grid[s], xy) <= lim + EPS:
            continue
        if any(man(grid[n], xy) <= lim + EPS for n in tp):
            out.append(q)
    return out


def choose(cands, max_before, min_ps=MIN_PS, max_ps=MAX_PS, tol=TOL_PS):
    """cands: [{k, hop, min, max, ...}] (kit what-if passes) -> (cand, ok). Nearest qualifying candidate, else least max."""
    good = [c for c in cands if not math.isnan(c["min"]) and not math.isnan(c["max"])]
    if not good:
        return None, None
    bound = max(max_before if not math.isnan(max_before) else max_ps, max_ps) + tol
    ok = [c for c in good if c["min"] >= min_ps and c["max"] <= bound]
    if ok:
        return min(ok, key=lambda c: (c["hop"], c["k"])), True
    return min(good, key=lambda c: (c["max"], c["hop"], c["k"])), False


def map_tap(grid, pin_xy, cand, lim=LIM):
    """the plan tap within lim of the plan pin nearest the kit tap, with the kit -> plan pin offset applied"""
    want = (cand["xy"][0] + pin_xy[0] - cand["pin"][0], cand["xy"][1] + pin_xy[1] - cand["pin"][1])
    inr = [n for n in taps_of(grid) if man(grid[n], pin_xy) <= lim + EPS]
    if not inr:
        return None, None
    n = min(inr, key=lambda n: (man(grid[n], want), n))
    return n, round(man(grid[n], want), 1)


def set_source(lc, q, new):
    """the reach_rules.fix_fwd write form"""
    s = q["source_clock_port"]
    q["source_clock_port"] = new
    if q.get("source_clock_tap") in (s, "clk"):
        q["source_clock_tap"] = new
    if s == "clk":
        lc["forwarded_clock_only_inputs"] = True


def repoint_type(tn, t, grid, whatif=None, lim=LIM, kit=None, apply=None, only=None):
    """-> ledger rows; t is changed in place; kit = the what-if source type (own kit or --family representative);
    apply = the bases that are written (None = all); a row of another basis is listed with applied=False and its pin keeps its tap"""
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    rows = []
    tp = taps_of(grid)
    for q in stale_pins(t, grid, lim):
        s, xy, cn = q["source_clock_port"], q["xy_um"], q["name"]
        r = dict(type=tn, pin=cn, old=s, old_um=round(man(grid[s], xy), 1) if s in grid else None)
        w = (whatif or {}).get(cn)
        cands = [dict(c, k=int(k)) for k, c in sorted(((w or {}).get("cand") or {}).items(), key=lambda kv: int(kv[0]))]
        c, ok = choose(cands, (w or {}).get("max_b", float("nan"))) if cands else (None, None)
        new = None
        if c is not None:
            new, err = map_tap(grid, xy, c, lim)
            r.update(basis="measured" if ok else "NEEDS-SENDER", kit=kit, kit_pass=c["k"], kit_tap=c["tap"], map_err_um=err,
                     min_b=round(w["min_b"], 1), max_b=round(w["max_b"], 1), min_a=round(c["min"], 1),
                     max_a=round(c["max"], 1))
        if new is None:
            new = min(tp, key=lambda n: (man(grid[n], xy), n))
            r["basis"] = r.get("basis", "UNMEASURED") if c is not None else "UNMEASURED"
        r["applied"] = (apply is None or r["basis"] in apply) and (only is None or cn in only)
        if only is not None and cn not in only:
            r["held"] = "owned by another row (--only)"
        if new != s and r["applied"]:
            set_source(lc, q, new)
        r.update(new=new, new_um=round(man(grid[new], xy), 1))
        rows.append(r)
    return rows


def follow_type(tn, t, bt, eps=DD.FOLLOW_EPS):
    """early core taps follow their moved hard core since the baseline type bt (in place) -> ledger rows"""
    cores = {c["inst"]: c for c in t.get("hard_cores") or [] if isinstance(c, dict) and c.get("inst")}
    bcores = {c["inst"]: c for c in bt.get("hard_cores") or [] if isinstance(c, dict) and c.get("inst")}
    btaps = {tp.get("name"): tp for _, tp in DD._core_tap_names(bt)}
    rows = []
    for port, tp in DD._core_tap_names(t):
        i = DD._tap_inst(tp.get("name"), cores)
        c, bc, btp = cores.get(i), bcores.get(i), btaps.get(tp.get("name"))
        if not (c and bc and btp and c.get("origin_um") and bc.get("origin_um") and tp.get("xy") and btp.get("xy")):
            continue
        if (c.get("orient") or "R0") != (bc.get("orient") or "R0") or c.get("outline_um") != bc.get("outline_um"):
            continue
        dc = [float(a) - float(z) for a, z in zip(c["origin_um"], bc["origin_um"])]
        if max(abs(v) for v in dc) <= eps:
            continue
        dt = [float(a) - float(z) for a, z in zip(tp["xy"], btp["xy"])]
        if all(abs(u - v) <= eps for u, v in zip(dc, dt)):
            continue
        old = list(tp["xy"])
        tp["xy"] = [round(float(b) + d, 6) for b, d in zip(btp["xy"], dc)]
        rows.append(dict(type=tn, port=port, tap=tp.get("name"), core=i, core_delta=dc, old=old, new=tp["xy"]))
    return rows


def repick_report(raw, P, types=None, whatif=None, family=None, grid_of=None):
    """FWDCLK-REPICK (FABLE-RC-ALL class fix, r703 report-only): after any tap change (tap fill / compose), the pick this tool
    would make for every export whose source tap is over EXPORT_HOP_UM, two-sided when a what-if covers the ring.  raw is
    NOT changed (each type is evaluated on a copy).  -> ledger rows as repoint_type."""
    import copy
    if grid_of is None:
        import reach_rules as RR
        grid_of = lambda tn: RR._grid(P, tn)
    W, fam, rows = whatif or {}, family or {}, []
    for tn, t in sorted(((raw or {}).get("partition_types") or {}).items()):
        if not isinstance(t, dict) or (types is not None and tn not in types) or not DD.export_pins(t):
            continue
        g = grid_of(tn)
        if not stale_pins(t, g):
            continue
        kit = tn if tn in W else (fam.get(tn) if fam.get(tn) in W else None)
        rows += repoint_type(tn, copy.deepcopy(t), g, (W.get(kit) or {}) if kit else {}, kit=kit)
    return rows


def repick_lines(rows):
    out = [f"WARN FWDCLK-REPICK {r['type']}: {r['pin']} <- {r['old']} {r['old_um']} um -> {r['new']} {r['new_um']} um ({r['basis']}"
           + (f", min {r['min_b']}->{r['min_a']} max {r['max_b']}->{r['max_a']} ps" if 'max_a' in r else
              ", needs a two-sided what-if before apply") + ")" for r in rows]
    from collections import Counter
    out.append(f"FWDCLK-REPICK report-only: {len(rows)} export(s) over {LIM:g} um after the tap change "
               f"{dict(Counter(r['basis'] for r in rows))}; apply: fwdclk_repoint.py fix")
    return out


def agg(wdir):
    """fwdclk_whatif.tcl tables -> {kit type: {ring: {old, min_b, max_b, fclk_b, cand: {k: {...}}}}}"""
    out = {}
    for td in sorted(glob.glob(os.path.join(wdir, "*"))):
        R = {}
        for p in sorted(glob.glob(os.path.join(td, "p*", "eco3.tsv"))):
            k = int(Path(p).parent.name[1:])
            for r in csv.DictReader(open(p), delimiter="\t"):
                st = r.get("state") or ""
                if not st.startswith(("MOVED", "NOCAND", "NOSRC")):
                    continue
                f = lambda v: float(v) if v not in (None, "") else float("nan")
                d = R.setdefault(r["clk"], dict(old=r["old_tap"], min_b=f(r["min_b"]), max_b=f(r["max_b"]),
                                                fclk_b=f(r["fclk_b"]), cand={}))
                if st.startswith("MOVED"):
                    h = [float(x) for x in r["hops"].split()]
                    d["cand"][k] = dict(tap=st[6:], src_um=h[0], hop=h[1], xy=h[2:4], pin=h[4:6], min=f(r["min_a"]),
                                        max=f(r["max_a"]), fclk=f(r["fclk_a"]))
        out[Path(td).name] = R
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fwdclk_repoint", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fix")
    f.add_argument("plan_in"); f.add_argument("plan_out")
    f.add_argument("--types", default="ALL")
    f.add_argument("--whatif", action="append", default=[])
    f.add_argument("--family", action="append", default=[], help="TYPE=KITTYPE: use KITTYPE's what-if rows for TYPE")
    f.add_argument("--baseline", help="plan for core-tap follow (the PRE --baseline-plan)")
    f.add_argument("--ledger")
    f.add_argument("--only", action="append", default=[], help="TYPE=PIN[,PIN..]: on TYPE write only these pins (another row "
                   "owns the rest; TYPE= writes none)")
    f.add_argument("--apply", default="ALL", help="bases written: ALL, or e.g. measured (two-sided only; UNMEASURED and "
                   "NEEDS-SENDER pins keep their old tap, listed applied=false)")
    g = sub.add_parser("agg")
    g.add_argument("wdir"); g.add_argument("out")
    a = ap.parse_args(argv)
    if a.cmd == "agg":
        Path(a.out).write_text(json.dumps(agg(a.wdir), indent=1) + "\n")
        return 0
    import schema as S
    import reach_rules as RR
    raw = json.loads(Path(a.plan_in).read_text())
    P = S.Plan(raw, a.plan_in)
    W = {}
    for w in a.whatif:
        W.update(json.loads(Path(w).read_text()))
    fam = {}
    for x in a.family:                      # TYPE=KIT, or a glob: kv3_pc_v1__*=kv3_pc_v1__cl7f648944 (own kit wins)
        k, v = x.split("=", 1)
        for tn in fnmatch.filter(raw["partition_types"], k) if any(ch in k for ch in "*?[") else [k]:
            fam.setdefault(tn, v)
    only = {}
    for x in a.only:
        k, v = x.split("=", 1)
        only[k] = {("" if p.startswith("fclk_out_") else "fclk_out_") + p for p in v.split(",") if p}
    base = json.loads(Path(a.baseline).read_text()).get("partition_types", {}) if a.baseline else {}
    types = sorted(raw["partition_types"]) if a.types == "ALL" else [x for x in a.types.split(",") if x]
    led = dict(tool="fwdclk_repoint", plan_in=a.plan_in, limit_um=LIM, min_ps=MIN_PS, max_ps=MAX_PS, tol_ps=TOL_PS,
               repoints=[], follow=[])
    for tn in types:
        t = raw["partition_types"].get(tn)
        if not isinstance(t, dict):
            continue
        if isinstance(base.get(tn), dict):
            led["follow"] += follow_type(tn, t, base[tn])
        if DD.export_pins(t):
            kit = tn if tn in W else (fam.get(tn) if fam.get(tn) in W else None)
            led["repoints"] += repoint_type(tn, t, RR._grid(P, tn), (W.get(kit) or {}) if kit else {}, kit=kit,
                                         apply=None if a.apply == "ALL" else set(a.apply.split(",")),
                                         only=only.get(tn))
    Path(a.plan_out).write_text(json.dumps(raw, indent=1) + "\n")
    if a.ledger:
        Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    from collections import Counter
    print(f"FWDCLK-REPOINT stale {len(led['repoints'])} {dict(Counter(r['basis'] for r in led['repoints']))} "
          f"applied {sum(1 for r in led['repoints'] if r.get('applied', True))} "
          f"follow {len(led['follow'])} types {len(types)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
