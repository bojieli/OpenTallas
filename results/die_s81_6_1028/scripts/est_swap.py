#!/usr/bin/env python3
"""DIE-S81-6 12.14b ESTIMATE: targeted feed re-parent ("clock follows data") on the MEASURED kit.
For each CHILD=NEWPARENT, the child region's root entry cell is fed from NEWPARENT's region-root cell by a new M8/M9 feed
hop (Manhattan, repeaters every rep_um, measured feed ps/mm unless --v); the whole child subtree keeps its measured
arrivals shifted by (new entry arrival - old entry arrival).  Old hop wire is dropped.  Writes a synthetic run dir for
the unchanged shared tools (landed_phase_ocv -> count_align_plan).
usage: est_swap.py TREE ARR_TT ARR_FF OUTDIR CHILD=NEWPARENT ... [--v ps/mm]"""
import argparse, json
from collections import defaultdict
from pathlib import Path


def arrivals(f):
    T, N = {}, {}
    for ln in Path(f).read_text().splitlines():
        x = ln.split()
        if x and x[0] in ("T", "N"):
            (T if x[0] == "T" else N)[x[1]] = float(x[2])
    return T, N


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree"); ap.add_argument("arr_tt"); ap.add_argument("arr_ff"); ap.add_argument("out")
    ap.add_argument("swaps", nargs="*")
    ap.add_argument("--v", type=float, default=None, help="new hop TT ps/mm (default measured feed p50)")
    ap.add_argument("--rep-um", type=float, default=250.0)
    a = ap.parse_args()
    t = json.loads(Path(a.tree).read_text())
    N, nb = t["nodes"], t["node_buf"]
    A = {"TT": arrivals(a.arr_tt), "FF": arrivals(a.arr_ff)}
    rr = {n["region_root"]: n for n in N.values() if "region_root" in n}
    cell = {r: nb[str(n["id"])] for r, n in rr.items()}
    po = dict(t["parent_of"]); sites = dict(t["sites"])

    def up_region(n):
        p = n["parent"]
        while p is not None:
            q = N[str(p)]
            if "region_root" in q:
                return q["region_root"]
            p = q["parent"]
    fpar = {r: up_region(n) for r, n in rr.items()}
    cal = []
    for r, p in fpar.items():
        if p:
            L = abs(rr[r]["x"] - rr[p]["x"]) + abs(rr[r]["y"] - rr[p]["y"])
            if L > 500:
                cal.append(((A["TT"][1][cell[r]] - A["TT"][1][cell[p]]) / (L / 1e3),
                            (A["FF"][1][cell[r]] - A["FF"][1][cell[p]]) / (A["TT"][1][cell[r]] - A["TT"][1][cell[p]])))
    v = a.v or sorted(c[0] for c in cal)[len(cal) // 2]
    ffr = sorted(c[1] for c in cal)[len(cal) // 2]
    shift = {"TT": {}, "FF": {}}
    rep = 0
    log = []
    wire_new = wire_old = 0.0
    for sw in a.swaps:
        c, np_ = sw.split("=")
        # cycle check on the CURRENT feed
        x = np_
        while x:
            if x == c:
                raise SystemExit(f"swap {sw}: {np_} is inside {c}'s subtree")
            x = fpar[x]
        L = abs(rr[c]["x"] - rr[np_]["x"]) + abs(rr[c]["y"] - rr[np_]["y"])
        Lold = abs(rr[c]["x"] - rr[fpar[c]]["x"]) + abs(rr[c]["y"] - rr[fpar[c]]["y"])
        wire_new += L; wire_old += Lold
        last = cell[np_]
        p0, p1 = (rr[np_]["x"], rr[np_]["y"]), (rr[c]["x"], rr[c]["y"])
        n = int(L // a.rep_um)
        for i in range(1, n + 1):
            rep += 1
            k = f"sw{rep}"
            f = i * a.rep_um / L
            sites[k] = [p0[0] + f * (p1[0] - p0[0]), p0[1] + f * (p1[1] - p0[1])]
            po[k] = last; last = k
            for C, s in (("TT", 1.0), ("FF", ffr)):
                A[C][1][k] = A[C][1][cell[np_]] + i * a.rep_um / 1e3 * v * s
        po[cell[c]] = last
        fpar[c] = np_
        for C, s in (("TT", 1.0), ("FF", ffr)):
            new = A[C][1][cell[np_]] + L / 1e3 * v * s
            shift[C][c] = new - A[C][1][cell[c]]
        log.append(dict(child=c, new_parent=np_, hop_um=round(L, 1), old_hop_um=round(Lold, 1),
                        shift_tt_ps=round(shift["TT"][c], 1)))
        # apply shift immediately to the subtree so later swaps see current arrivals
        sub = {c}
        changed = True
        kids = defaultdict(list)
        for r, p in fpar.items():
            if p:
                kids[p].append(r)
        q = [c]
        for r in q:
            q.extend(kids[r]); sub.add(r)
        # region membership of every cell: nearest region-root ancestor
        segcells = {cell[r]: r for r in rr}
        memo = {}

        def reg(x):
            path = []
            while x is not None and x not in memo:
                if x in segcells:
                    memo[x] = segcells[x]; break
                path.append(x); x = po.get(x)
            val = memo.get(x) if x is not None else None
            for p in path:
                memo[p] = val
            return val
        tapcell = {tp["port"]: nb[str(tp["node"])] for tp in t["taps"]}
        for C in ("TT", "FF"):
            s = shift[C][c]
            Tm, Nm = A[C]
            for k2 in list(Nm):
                if k2.startswith("sw") and k2 in sites and int(k2[2:]) > rep - n:
                    continue
                r = reg(k2)
                if r in sub:
                    Nm[k2] += s
            for port in list(Tm):
                if port in tapcell and reg(tapcell[port]) in sub:
                    Tm[port] += s
    out = Path(a.out); (out / "clk").mkdir(parents=True, exist_ok=True)
    for C in ("TT", "FF"):
        (out / f"out_{C}").mkdir(exist_ok=True)
        Tm, Nm = A[C]
        (out / f"out_{C}" / f"arr_{C}.txt").write_text(
            "".join(f"T {k} {x:.3f}\n" for k, x in Tm.items()) + "".join(f"N {k} {x:.3f}\n" for k, x in Nm.items()))
    t2 = dict(t, parent_of=po, sites=sites)
    (out / "clk" / "tree.json").write_text(json.dumps(t2))
    summ = dict(v_tt=round(v, 1), ff_over_tt=round(ffr, 4), swaps=log, new_hop_um=round(wire_new, 1),
                old_hop_um=round(wire_old, 1), new_repeaters=rep)
    (out / "est_swap.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
