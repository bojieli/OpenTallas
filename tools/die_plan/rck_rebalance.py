#!/usr/bin/env python3
"""rck_rebalance.py -- branch-level clock-tree rebalance on EXTRACTED arrivals (RCK-REBALANCE-1, FABLE-FIX-S81-SERDES2 2026-11-18).

Why: a deep clock tree balanced with delay pads on placement RC and confirmed at GRT is not confirmed by extraction.  S81
serdes__t13 H17 (io_pma_rck, 63 stages, 2 ns): routed sink arrivals of related registers differ by 144-179 ps where GRT read them
balanced; routed TT setup -101.6 on 343 ends of one class, FF hold -55.9.  A per-register capture-skew ECO cannot open those windows
(the worst capture flops are 80-90 ps short on setup with about 10 ps of hold room): whole BRANCHES must move.

  plan   TREE.tsv [--stage-ps 24] [--tol-ps 8] [--max-pads 4000] [--max-per-node 40] [--paths CENSUS.tsv ...] --out DIR
         TREE.tsv = rck_tree_dump.tcl output (tree edges + extracted arrival of every sink).  Top-down: every clock cell whose latest
         sink is earlier than the tree's latest sink by at least one stage gets floor(gap / stage) inverter-PAIR pads in front of it
         (no duty change); children are then judged against what remains.  Only clock cells are padded, never a register pin, so the
         spread inside one leaf stays.  Writes DIR/pads.tsv (node, pads, x, y), DIR/sinks.tsv (pin, arrival, added, new arrival),
         DIR/plan.json (span before / after, pad count, per-level counts).
         --paths: endpoint census rows (mode, slack, startpoint, endpoint, launch clock, capture clock; the census.tcl format).  For
         every row whose two ends are sinks of this tree the slack is re-priced with the planned arrival shifts
         (setup: + capture shift - launch shift; hold: the opposite); CRPR is not re-priced.  Written to DIR/paths_pred.tsv and
         summarised in plan.json.  This is the dry run: nothing is edited.

The insert step (pads.tsv -> inverter pairs at the node inputs, legalisation, incremental route of the touched clock nets, re-extract)
is NOT in this file yet: the plan and its prediction come first.
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path


def load_tree(path):
    kids, sinks, loc = collections.defaultdict(list), collections.defaultdict(list), {}
    for line in Path(path).read_text().splitlines():
        f = line.split("\t")
        if f[0] == "K":
            kids[f[1]].append(f[2])
        elif f[0] == "S":
            # odb escapes bus brackets in instance names (o\[441\]); STA reports and the census do not: one spelling
            sinks[f[1]].append((f[2].replace("\\", ""), float(f[3])))
        elif f[0] == "X":
            loc[f[1]] = (int(f[2]), int(f[3]))
    return kids, sinks, loc


def order(kids, root="PORT"):
    out, st = [], [root]
    while st:
        n = st.pop()
        out.append(n)
        st.extend(kids.get(n, ()))
    return out


def plan(kids, sinks, stage=24.0, tol=8.0, max_pads=4000, max_per_node=40, root="PORT"):
    """-> dict(pads={node: k}, add={sink pin: ps}, before=(min, max), after=(min, max), target, capped)"""
    od = order(kids, root)
    hi = {}
    for n in reversed(od):
        h = max((a for _, a in sinks.get(n, ())), default=-math.inf)
        for c in kids.get(n, ()):
            h = max(h, hi[c])
        hi[n] = h
    allarr = [a for n in od for _, a in sinks.get(n, ())]
    if not allarr:
        raise SystemExit("tree has no sink with an arrival")
    target = max(allarr)
    pads, acc, total, capped = {}, {root: 0.0}, 0, False
    for n in od:                                   # parents come before children in this order
        a = acc[n]
        if n != root and hi[n] > -math.inf:
            gap = target - (hi[n] + a) - tol
            k = int(gap // stage) if gap >= stage else 0
            k = min(k, max_per_node)
            if k and total + k > max_pads:
                k, capped = max(0, max_pads - total), True
            if k:
                pads[n] = k
                total += k
                a += k * stage
        for c in kids.get(n, ()):
            acc[c] = a
        acc[n] = a
    add = {pin: acc[n] for n in od for pin, _ in sinks.get(n, ())}
    new = [a + acc[n] for n in od for _, a in sinks.get(n, ())]
    return dict(pads=pads, add=add, before=(min(allarr), max(allarr)), after=(min(new), max(new)), target=target, capped=capped,
                acc=acc)


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))]


def inst_of(name):
    """census startpoint = instance name; endpoint = pin name.  A sink pin is <inst>/<clock pin>."""
    return name.rsplit("/", 1)[0] if "/" in name else name


def reprice(rows, add_by_inst):
    """rows: (mode, slack, start, end) -> [(mode, slack, new slack, start, end)] for rows with both ends in the tree"""
    out = []
    for mode, slack, start, end in rows:
        # a startpoint is reported as the launch clock pin (inst/CLK) or as the instance; an endpoint as a data pin
        l = add_by_inst.get(start, add_by_inst.get(inst_of(start)))
        c = add_by_inst.get(inst_of(end))
        if l is None and c is None:
            continue
        l, c = l or 0.0, c or 0.0
        out.append((mode, slack, slack + (c - l if mode == "max" else l - c), start, end))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("tree")
    p.add_argument("--stage-ps", type=float, default=24.0)
    p.add_argument("--tol-ps", type=float, default=8.0)
    p.add_argument("--max-pads", type=int, default=4000)
    p.add_argument("--max-per-node", type=int, default=40)
    p.add_argument("--paths", action="append", default=[])
    p.add_argument("--setup-gate-ps", type=float, default=-42.0)
    p.add_argument("--hold-gate-ps", type=float, default=0.0)
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    kids, sinks, loc = load_tree(a.tree)
    pl = plan(kids, sinks, a.stage_ps, a.tol_ps, a.max_pads, a.max_per_node)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "pads.tsv").open("w") as f:
        for n, k in sorted(pl["pads"].items(), key=lambda kv: -kv[1]):
            x, y = loc.get(n, (-1, -1))
            f.write(f"{n}\t{k}\t{x}\t{y}\n")
    arr = {pin: v for n in sinks for pin, v in sinks[n]}
    with (out / "sinks.tsv").open("w") as f:
        for pin, v in arr.items():
            f.write(f"{pin}\t{v:.2f}\t{pl['add'][pin]:.2f}\t{v + pl['add'][pin]:.2f}\n")
    before, after = sorted(arr.values()), sorted(arr[p_] + pl["add"][p_] for p_ in arr)
    res = dict(tree=a.tree, sinks=len(arr), clock_cells=sum(len(v) for v in kids.values()), stage_ps=a.stage_ps, tol_ps=a.tol_ps,
               target_ps=pl["target"], pad_pairs=sum(pl["pads"].values()), padded_nodes=len(pl["pads"]), capped=pl["capped"],
               span_before_ps=round(before[-1] - before[0], 2), span_after_ps=round(after[-1] - after[0], 2),
               p1_p99_before_ps=round(pct(before, 0.99) - pct(before, 0.01), 2),
               p1_p99_after_ps=round(pct(after, 0.99) - pct(after, 0.01), 2), paths=[])
    add_by_inst = {inst_of(pin): v for pin, v in pl["add"].items()}
    for pf in a.paths:
        rows = []
        for line in Path(pf).read_text().splitlines():
            f = line.split("\t")
            if len(f) >= 4:
                rows.append((f[0], float(f[1]), f[2], f[3]))
        rp = reprice(rows, add_by_inst)
        with (out / (Path(pf).stem + "_pred.tsv")).open("w") as f:
            for r in rp:
                f.write("%s\t%.2f\t%.2f\t%s\t%s\n" % r)
        for mode, gate in (("max", a.setup_gate_ps), ("min", a.hold_gate_ps)):
            m = [r for r in rp if r[0] == mode]
            if not m:
                continue
            res["paths"].append(dict(file=pf, mode=mode, rows=len(m), gate_ps=gate,
                                     worst_before_ps=min(r[1] for r in m), worst_after_ps=round(min(r[2] for r in m), 2),
                                     below_gate_before=sum(r[1] < gate for r in m), below_gate_after=sum(r[2] < gate for r in m)))
    (out / "plan.json").write_text(json.dumps(res, indent=1) + "\n")
    print("OT_RCK_REBALANCE plan: %d sinks, %d pad pairs at %d nodes%s; span %.1f -> %.1f ps, p1..p99 %.1f -> %.1f ps" % (
        res["sinks"], res["pad_pairs"], res["padded_nodes"], " (CAPPED)" if res["capped"] else "", res["span_before_ps"],
        res["span_after_ps"], res["p1_p99_before_ps"], res["p1_p99_after_ps"]))
    for q in res["paths"]:
        print("OT_RCK_REBALANCE paths %s %s: %d rows, worst %.2f -> %.2f, below %g: %d -> %d" % (
            Path(q["file"]).name, q["mode"], q["rows"], q["worst_before_ps"], q["worst_after_ps"], q["gate_ps"],
            q["below_gate_before"], q["below_gate_after"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
