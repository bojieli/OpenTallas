#!/usr/bin/env python3
"""QC-SU-PROG-L1 option (c): PLAN-COMPUTED PER-BRANCH SIZING (METHODOLOGY 12.8 d1) of a plan-built mscts_h tree.

Input = the spec the gate would build (sites, membership, repeater chain and stage count all fixed by su_kit_gate).
Only the CELL of each tree node (island drivers, L1/L2/L3 chain repeaters, B drivers) is chosen, from the fixed
buffer list phys_gate.SIZES_ALL, by the gating predictor uf_phys itself, before any build: no measured input, no
added or removed stage (every root->leaf path keeps its stage count), no site moved, root / leaf / macro-leaf cells
unchanged.  Deterministic coordinate descent (nodes in spec order, sizes in list order, strict improvement only):
  J = max(TT rise window, FF early window) - 0.5 min(m_TT, m_FF),  m_TT = 12 - |TT rise mean - 250|,
      m_FF = 15 - |FF early mean - 202.5|  (the guard-band margins: windows first, then the smaller margin)
subject to every predicted node input slew (TT and FF, max analysis) <= SLEW_MAX.
usage: su_branch_size.py SPEC.tcl ASBUILT.json GEO LIBDIR OUT.tcl [--passes N] [--slew-max PS]
writes OUT.tcl (sized spec) + OUT.size.json (every change, before/after prediction, provenance).  PLAN MODEL, UNCHECKED.
"""
import json
import multiprocessing as mp
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phys_gate as PG  # noqa: E402

U = PG.U
SLEW_MAX = 60.0


def objective(plan, L):
    r, e = PG.fast_obj(plan, L)
    a, b = PG.summ(r.values()), PG.summ(e.values())
    m_tt = (PG.BAND - PG.LOO_MAX["TT"]) - abs(a["mean"] - PG.TARGET["TT"])
    m_ff = (PG.BAND - PG.LOO_MAX["FF"]) - abs(b["mean"] - PG.TARGET["FF"])
    J = max(a["window"], b["window"]) - 0.5 * min(m_tt, m_ff)
    return J, a, b


def max_slew(plan, L):
    m = 0.0
    for C in ("TT", "FF"):
        for edge in ("rise", "fall"):
            _, arr = U.predict(plan, L, C, edge=edge, **PG.PMAX)
            m = max(m, max(s for _, s in arr.values()))
    return m


_CTX = {}


def _eval(s):
    plan, L, n = _CTX["plan"], _CTX["L"], _CTX["n"]
    plan.nodes[n]["cell"] = s            # forked copy (or restored below in the serial case)
    Jn = objective(plan, L)[0]
    sl = max_slew(plan, L)
    return Jn, sl


def size(spec, asb, geo, libdir, passes=3, slew_max=SLEW_MAX, sizes=None, workers=None):
    workers = workers if workers is not None else int(os.environ.get("OT_SIZE_WORKERS", "9"))
    sizes = sizes or PG.SIZES_ALL
    L = PG.libs(libdir)
    plan = U.Plan(spec, geo, json.load(open(asb))["seg_um"])
    nodes = [n for n, v in plan.nodes.items() if v["kind"] == "node"]
    orig = {n: plan.nodes[n]["cell"] for n in nodes}
    J0, a0, b0 = objective(plan, L)
    s0 = max_slew(plan, L)
    lim = max(slew_max, s0)
    J = J0
    hist = []
    for p in range(passes):
        changed = 0
        for n in nodes:
            cur = plan.nodes[n]["cell"]
            best = (J, cur)
            cand = [s for s in sizes if s != cur]
            _CTX.update(plan=plan, L=L, n=n)
            if workers > 1:
                with mp.get_context("fork").Pool(min(workers, len(cand))) as pool:
                    res = pool.map(_eval, cand)
            else:
                res = [_eval(s) for s in cand]
            for s, (Jn, sl) in zip(cand, res):      # same order + strict-improvement rule as a serial scan
                if Jn < best[0] - 1e-6 and sl <= lim:
                    best = (Jn, s)
            plan.nodes[n]["cell"] = best[1]
            if best[1] != cur:
                changed += 1
                J = best[0]
        hist.append(dict(pass_=p, J=round(J, 3), changed=changed))
        print("PASS", p, "J", round(J, 3), "changed", changed, flush=True)
        if not changed:
            break
    J1, a1, b1 = objective(plan, L)
    new = {n: plan.nodes[n]["cell"] for n in nodes}
    return dict(before=dict(J=round(J0, 3), TT_rise=a0, FF_early=b0, max_slew=round(s0, 2)),
                after=dict(J=round(J1, 3), TT_rise=a1, FF_early=b1, max_slew=round(max_slew(plan, L), 2)),
                slew_limit=round(lim, 2), passes=hist, sizes=sizes,
                changes={n: [orig[n], new[n]] for n in nodes if orig[n] != new[n]}, cells=new)


def write_spec(spec, cells, out, note):
    t = Path(spec).read_text()
    head, rest = t.split("set ot_ms_tree {", 1)
    blk, tail = rest.split("\n}", 1)
    lines = []
    for ln in blk.split("\n"):
        m = re.match(r"(\s*\{)(\S+) (\S+) ([\d.]+) ([\d.]+) (\S+)\}$", ln)
        if m and m.group(2) in cells:
            ln = f"{m.group(1)}{m.group(2)} {m.group(3)} {m.group(4)} {m.group(5)} {cells[m.group(2)]}}}"
        lines.append(ln)
    Path(out).write_text(f"# {note}\n" + head + "set ot_ms_tree {" + "\n".join(lines) + "\n}" + tail)


if __name__ == "__main__":
    spec, asb, geo, libdir, out = sys.argv[1:6]
    passes = int(sys.argv[sys.argv.index("--passes") + 1]) if "--passes" in sys.argv else 3
    sm = float(sys.argv[sys.argv.index("--slew-max") + 1]) if "--slew-max" in sys.argv else SLEW_MAX
    r = size(spec, asb, geo, libdir, passes, sm)
    write_spec(spec, r["cells"], out, "QC-SU-PROG-L1 per-branch sizing (12.8 d1, plan-computed by uf_phys before build; "
               "cells only, sites/stages unchanged) of " + Path(spec).name)
    r["provenance"] = dict(argv=[sys.executable] + list(sys.argv),
                           sha256={p: PG.sha(p) for p in (spec, asb, geo, __file__, PG.__file__, U.__file__, out)})
    Path(str(Path(out).with_suffix("")) + ".size.json").write_text(json.dumps(r, indent=1))
    print("SIZED", json.dumps(dict(before=r["before"], after=r["after"], n_changes=len(r["changes"]))))
