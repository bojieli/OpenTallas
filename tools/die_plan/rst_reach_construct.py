#!/usr/bin/env python3
"""rst_reach_construct.py -- RST-REACH-CONSTRUCT (CLASS-OWNERS-R2, class C-RST-RELAY-REACH): reset relay / raw / FSTART reach
within budget BY CONSTRUCTION, as one opt-in generator pass (default off everywhere; nothing calls it unless asked).

Why: a re-floor, grow or tap rewrite re-solves the reset tree, but the DERIVED reset state that points into it is not re-derived
by the same step, so the plan carries (11-25 21:00 released-plan baseline, PRE RSTREACH FAIL types: S81 26/394, HEAD 0/27,
QC 0/127, KV 0/91):
  RAW    START stage / landing_local_resets raw pointers (rr_t<N> / rst_n_t<N>) that name a tap or relay of the OLD tree, or sit
         more than the reset reach from their stage (S81 dsdv_slice_c1x_C, ot_s81sl_kv_leaf, ot_s81sl_leaf: 26 types);
  SEAT   plan relay_sites rows keyed <u_rrl_N|u_srl_N>/q name a reset-tree relay by NUMBER.  Since RELAY-SITES-WIN (main c92ea14ae6b1,
         default on) such a row WINS over the tree site in reset_tree.tcl, so a row left over from an older solve (the relay with
         that number is a different relay now) seats it far from its D source or its fanout (the one measured overwrite: HEAD
         hd_serdes R6 u_rrl_132 / u_srl_132; 3 of ~800k seats, every other seat is a ring/station/clone flop and survives);
  FSTART local FSTART reset copies seated for an older floorplan (landing_reset_reseat, 6a9b4606d8f, opt-in).
Pass (each step is an existing, tested tool; this module only sequences them and gates on the static check):
  1 seats    drop relay_sites reset-relay rows that are ORPHANS (no such relay in the solved tree) or HARMFUL (the seat makes a
             D-source -> seat or seat -> child leg longer than the type reset reach while the tree site does not).  The tree
             site is used instead; 0 cycles, 0 flops.  Rows that keep every leg within reach are kept (the plan's own seat).
  2 raw      retap.repick_start_raws: every raw pointer past the consumer taps or farther than 300 um from its stage is re-picked
             to the nearest consumer tap (all consumer taps release on the same wavefront: 0 cycles).
  3 edges    reach_rules._fix_raw_edges: START raws still missing / over their edge reach go to the nearest same-edge leaf tap.
  4 fstart   (--fstart-reseat) landing_reset_reseat.py on the types that still carry an FSTART finding.
  5 check    derived_drop.rstreach_type on every selected type; exit 1 when a FAIL line is left (--require).
Report = per type {before, after findings, seats dropped / kept, raw repoints}; the census alone is `census`.

  rst_reach_construct.py census PLAN [--tree TREE] [--types a,b] [--json OUT]
  rst_reach_construct.py fix PLAN OUT [--tree TREE] [--types a,b] [--fstart-reseat] [--report R.json] [--require]
"""
import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SEAT = re.compile(r"^(u_[rs]rl_\d+)/q$")
REACH_FLOOR = 300.0


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _modules():
    import derived_drop as D
    import reset_tree as RT
    return D, RT


def raw_diff(old, new):
    """[[where, was, now]] of every START stage raw_reset / landing_local_resets raw that differs between two type blocks"""
    import reach_rules
    a = {(k, b, i): st.get("raw_reset") for k, b, i, st in reach_rules._start_stages(old)}
    out = []
    for k, b, i, st in reach_rules._start_stages(new):
        if a.get((k, b, i)) != st.get("raw_reset"):
            out.append([f"{k.split('_', 1)[1]}:{b}:{i}", a.get((k, b, i)), st.get("raw_reset")])
    lo = {lr.get("name"): lr.get("raw") for lr in ((old.get("clock") or {}).get("landing_local_resets") or []) if isinstance(lr, dict)}
    for lr in ((new.get("clock") or {}).get("landing_local_resets") or []):
        if isinstance(lr, dict) and lo.get(lr.get("name")) != lr.get("raw"):
            out.append([f"local_reset:{lr.get('name')}", lo.get(lr.get("name")), lr.get("raw")])
    return out


def seat_rows(t):
    """{relay name: (key, [x, y])} of the type's plan relay_sites rows that seat a reset-tree relay"""
    out = {}
    for k, v in (t.get("relay_sites") or {}).items():
        m = SEAT.fullmatch(str(k))
        if m and isinstance(v, (list, tuple)) and len(v) >= 2:
            out[m.group(1)] = (k, [float(v[0]), float(v[1])])
    return out


def seat_audit(RT, tree, seats, reach):
    """-> (orphans, harmful, kept): seat rows against the solved tree.  A leg is D source -> relay and relay -> each child
    (the same edges rst_relay_census measures); a seat is harmful when it adds a leg over reach the tree site does not have."""
    rows = {r["name"]: r for r in RT.physical_reset_relays(tree)}
    base = {r["q"]: tuple(r["xy"]) for r in rows.values()}
    base["rst_root_n"] = tuple(tree["root"])
    if tree.get("start_in") is not None:
        base["run_root"] = tuple(tree["start_in"])
    kids = {}
    for r in rows.values():
        for key in ("d", "run"):
            if r.get(key):
                kids.setdefault(r[key], []).append(r)

    def worst(name, xy, over):
        r = rows[name]
        cur = dict(base, **{k: tuple(v) for k, v in over.items()})
        w = 0.0
        for key in ("d", "run"):
            s = r.get(key)
            if s in cur:
                w = max(w, man(cur[s], xy))
        for c in kids.get(r["q"], []):
            w = max(w, man(xy, cur.get(c["q"], tuple(c["xy"]))))
        return w
    pos = {rows[n]["q"]: xy for n, (_, xy) in seats.items() if n in rows}
    orphans, harmful, kept = [], [], []
    for n, (k, xy) in sorted(seats.items()):
        if n not in rows:
            orphans.append((k, xy))
            continue
        tree_w = worst(n, tuple(rows[n]["xy"]), {q: p for q, p in pos.items() if q != rows[n]["q"]})
        seat_w = worst(n, tuple(xy), pos)
        if seat_w > reach + 1e-6 and seat_w > tree_w + 1e-6:
            harmful.append((k, xy, round(seat_w, 1), round(tree_w, 1)))
        else:
            kept.append(k)
    return orphans, harmful, kept


def _plan_obj(raw, path):
    import schema
    return schema.Plan(raw, Path(path).parent / "die_plan.json")


def _types(raw, only):
    D, _ = _modules()
    ts = [tn for tn, _t in D.derived_todo(raw)] if hasattr(D, "derived_todo") else list(raw["partition_types"])
    return [t for t in ts if not only or t in only]


def census(raw, path, tree, only=None):
    D, RT = _modules()
    S = D.Solver(raw, path, tree)
    P = S._plan()
    todo = {tn for tn, _t in D.derived_todo(raw)}
    out = {}
    for tn in sorted(raw["partition_types"]):
        t = raw["partition_types"][tn]
        if only and tn not in only:
            continue
        seats = seat_rows(t)
        row = dict(reset_relay_seat_rows=len(seats))
        try:
            if seats or any(k in t for k in ("clock", "reset")):
                reach = float(RT.relay_um(P, tn))
                if seats:
                    o, h, k = seat_audit(RT, S.tree(tn), seats, reach)
                    row.update(orphan=len(o), harmful=len(h), kept=len(k), harmful_rows=[list(x) for x in h[:5]],
                               orphan_rows=[list(x) for x in o[:5]])
            if tn in todo:
                row["rstreach"] = D.rstreach_type(tn, t, S, None)
        except Exception as e:  # noqa: BLE001 a type without an evaluable tree is reported, not raised
            row["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        out[tn] = row
    return out


def summarize(c):
    n = dict(types=len(c), seat_rows=sum(r["reset_relay_seat_rows"] for r in c.values()),
             orphan=sum(r.get("orphan", 0) for r in c.values()), harmful=sum(r.get("harmful", 0) for r in c.values()),
             rstreach_fail_types=sum(any(x.startswith("FAIL") for x in r.get("rstreach", [])) for r in c.values()),
             rstreach_warn_types=sum(any(x.startswith("WARN") for x in r.get("rstreach", [])) for r in c.values()),
             unavailable=sum("error" in r for r in c.values()))
    return n


def fix(raw, path, tree, only=None, fstart=False, tree_for_reseat=None):
    D, RT = _modules()
    import reach_rules
    import retap
    rep = dict(types={}, steps={})
    before = census(raw, path, tree, only)
    rep["before"] = summarize(before)
    S = D.Solver(raw, path, tree)
    P = S._plan()
    # 1 seats
    dropped = 0
    for tn, t in raw["partition_types"].items():
        if only and tn not in only:
            continue
        seats = seat_rows(t)
        if not seats:
            continue
        try:
            reach = float(RT.relay_um(P, tn))
            o, h, _k = seat_audit(RT, S.tree(tn), seats, reach)
        except Exception:  # noqa: BLE001
            continue
        for k, *_ in list(o) + list(h):
            del t["relay_sites"][k]
            dropped += 1
        if o or h:
            rep["types"].setdefault(tn, {})["seats_dropped"] = [k for k, *_ in list(o) + list(h)]
    rep["steps"]["seats_dropped"] = dropped
    # 2-3 raw + edges + local taps, ONLY on types with a FAIL line (a WARN-only or clean type keeps every byte), each type
    # re-checked on its own and restored when the result is not strictly better (no FAIL left or fewer FAIL lines, tree solvable)
    def nfail(row):
        return sum(x.startswith("FAIL") for x in row.get("rstreach", []))
    todo = sorted(tn for tn, r in before.items() if nfail(r) and (not only or tn in only))
    rep["steps"].update(raw_repicked_types=0, edge_repoints=0, local_taps_added=0, reverted=[])
    for tn in todo:
        t = raw["partition_types"][tn]
        keep = copy.deepcopy(t)
        info = {}
        rp = retap.repick_start_raws(raw, path, {tn})
        if rp.get(tn):
            info["raw_repick"] = rp[tn][:6]
        P2 = _plan_obj(raw, path)
        try:
            r = dict(changed=[])
            reach_rules._fix_raw_edges(P2, t, tn, r)
            if r.get("raw_repoints"):
                info["edge_repoints"] = r["raw_repoints"]
        except Exception as e:  # noqa: BLE001
            info["edge_error"] = f"{type(e).__name__}: {str(e)[:160]}"
            lt = local_tap_fix(raw, path, tn)
            if lt:
                info["local_taps"] = lt
        info["raw_changes"] = raw_diff(keep, t)
        one = census(raw, path, tree, {tn})[tn]
        if "error" in one or nfail(one) >= nfail(before[tn]):
            t.clear()
            t.update(keep)
            rep["steps"]["reverted"].append(tn)
            info = dict(reverted=True, why=one.get("error") or f"FAIL lines {nfail(before[tn])} -> {nfail(one)}")
        else:
            rep["steps"]["raw_repicked_types"] += bool(info.get("raw_repick"))
            rep["steps"]["edge_repoints"] += info.get("edge_repoints", 0)
            rep["steps"]["local_taps_added"] += len(info.get("local_taps", []))
        if info:
            rep["types"].setdefault(tn, {}).update(info)
    return raw, rep


def local_tap_fix(raw, path, tn, step=4.32, rmax=216.0):
    """START raws that stay over their edge reach after the re-point: no consumer tap is within reach of the stage.  Append
    reset.local_taps_um (a terminal relay of the same release depth: 0 cycles, 0 clock ports; the bind numbers it after the
    clock taps) at the legal free site nearest each over-reach stage and point the raw at it.  Same-edge (rst_n_t) raws only.
    -> [[where, tap index, [x, y], hop_um]]"""
    import reach_rules
    import reset_tree as RT
    t = raw["partition_types"][tn]
    P = _plan_obj(raw, path)
    try:
        hops = reach_rules.raw_hops(P, t, tn)
    except Exception:  # noqa: BLE001
        return []
    bad = {h[0] for h in hops if h[2] != "same" or (h[3] is not None and h[3] > h[4] + 1e-6)}
    bad = {w for w in bad if not w.startswith("local_reset:")}
    if not bad:
        return []
    base = RT.consumer_taps(P, tn)
    w, h_ = t["outline_um"]
    boxes = RT.blockages(t)
    bounds = (RT.CLEAR_UM, RT.CLEAR_UM, w - RT.CLEAR_UM, h_ - RT.CLEAR_UM)
    pre = reach_rules._raw_prefix(P, t)
    extra = [list(map(float, x)) for x in (t.get("reset") or {}).get("local_taps_um") or []]
    taken = [(a, b) for _, a, b in base]
    out = []
    for key, b, i, st in reach_rules._start_stages(t):
        where = f"{key.split('_', 1)[1]}:{b}:{i}"
        if where not in bad:
            continue
        x0, y0 = st["xy_um"]
        best = None
        n = int(rmax / step)
        for dx in range(-n, n + 1):
            for dy in range(-n, n + 1):
                x, y = round((x0 + dx * step) / step) * step, round((y0 + dy * step) / step) * step
                d = abs(x - x0) + abs(y - y0)
                if d > rmax or (best is not None and d >= best[0]):
                    continue
                if not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
                    continue
                if not RT._free((x, y), boxes, bounds) or any(abs(x - a) < 1e-6 and abs(y - c) < 1e-6 for a, c in taken):
                    continue
                best = (d, round(x, 3), round(y, 3))
        if best is None:
            continue
        near = [j for j, e in enumerate(extra) if abs(e[0] - best[1]) + abs(e[1] - best[2]) <= 1e-6]
        if near:
            j = near[0]
        else:
            extra.append([best[1], best[2]])
            taken.append((best[1], best[2]))
            j = len(extra) - 1
        st["raw_reset"] = f"{pre}{len(base) + j}"
        out.append([where, len(base) + j, [best[1], best[2]], round(best[0], 1)])
    if out:
        t.setdefault("reset", {})["local_taps_um"] = extra
    return out


def after_check(raw, path, tree, only):
    return census(raw, path, tree, only)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    c.add_argument("plan")
    c.add_argument("--tree")
    c.add_argument("--types")
    c.add_argument("--json")
    f = sub.add_parser("fix")
    f.add_argument("plan")
    f.add_argument("out")
    f.add_argument("--tree")
    f.add_argument("--types")
    f.add_argument("--fstart-reseat", action="store_true")
    f.add_argument("--report")
    f.add_argument("--require", action="store_true")
    a = ap.parse_args(argv)
    only = set(filter(None, (a.types or "").split(",")))
    raw = json.loads(Path(a.plan).read_text())
    if a.cmd == "census":
        c = census(raw, a.plan, a.tree, only)
        print(json.dumps(summarize(c)))
        if a.json:
            Path(a.json).write_text(json.dumps(dict(summary=summarize(c), types=c), indent=1) + "\n")
        return 0
    raw, rep = fix(raw, a.plan, a.tree, only, a.fstart_reseat)
    txt = json.dumps(raw, indent=1) + "\n"
    Path(a.out).write_text(txt)
    c2 = census(json.loads(txt), a.plan, a.tree, only)   # same plan dir: the solver reads die_plan.json next to the plan
    rep["after"] = summarize(c2)
    rep["after_types_fail"] = sorted(tn for tn, r in c2.items() if any(x.startswith("FAIL") for x in r.get("rstreach", [])))
    if a.fstart_reseat:
        cmd = [sys.executable, "-I", str(HERE / "landing_reset_reseat.py"), a.out, a.out + ".fstart.json",
               "--types", ",".join(rep["after_types_fail"]) or ",".join(sorted(only)), "--report", a.out + ".fstart.rep.json"]
        if a.tree:
            cmd += ["--root", a.tree]
        rep["steps"]["fstart_cmd"] = " ".join(cmd)
        if rep["after_types_fail"]:
            r = subprocess.run(cmd, capture_output=True, text=True)
            rep["steps"]["fstart_rc"] = r.returncode
            if r.returncode == 0 and Path(a.out + ".fstart.json").exists():
                Path(a.out).write_text(Path(a.out + ".fstart.json").read_text())
                c3 = census(json.loads(Path(a.out).read_text()), a.plan, a.tree, only)
                rep["after"] = summarize(c3)
                rep["after_types_fail"] = sorted(tn for tn, r in c3.items()
                                                 if any(x.startswith("FAIL") for x in r.get("rstreach", [])))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(before=rep["before"], after=rep["after"], steps=rep["steps"])))
    return 1 if (a.require and rep["after_types_fail"]) else 0


if __name__ == "__main__":
    sys.exit(main())
