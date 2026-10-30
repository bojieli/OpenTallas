#!/usr/bin/env python3
"""S81-CORE-LAT-R9: 12.8 d1 plan-computed per-driver sizing refined under the COORD predictor (uf_phys3 v1, GRT basis,
std-width) on an R8/R9 plan record.  Deterministic coordinate descent BEFORE any build: masters only (BUFx8..x24
gating envelope), no wire, no position, no measurement input.  Objective = max(TT window, FF window) of the uf_phys3
per-leaf mean arrivals (guard window <= 14); tie-break = fewer stages changed, then lower mean.  Each step (candidates evaluated in parallel, fork pool): take the
earliest and the latest leaf, try every envelope master on each driver of its root path that is NOT shared with the
other extreme leaf, keep the single change that lowers the objective most; stop when no change helps.
Slew guard (DIE-S81-27 10-29, ve_s: three leaf downsizes BUFx24->BUFx10 pushed TT leaf out slew 60.0 -> 81.5 > the 80-ps
slice gate and the converter refused the tree): a change is kept only if the calibrated leaf out/in slew at TT and FF stays
<= --slew (default 80 = core_family_slice GATES slew_ps; a plan already above it may not get worse); the next-best change
is tried instead.  Plans whose descent never crossed the limit are unchanged.
Opt-in --joint3 escapes a single-step plateau using at most three independent near-tied late paths,
strict full-tree TT/FF improvement and both corners IN/OUT slew <=80. Default behavior is unchanged.
usage: l0r_r9_d1.py PLAN.json GEO LIBDIR FIT OUT.json [--steps N] [--slew 80] [--joint3]   PLAN MODEL, UNCHECKED."""
import gzip, json, sys, time, multiprocessing as MP
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "core_lat_r8_1026"))
import l0r_r8_uf3 as A
U, V3 = A.U, A.V3
ENV = ['BUFx8_ASAP7_75t_R', 'BUFx10_ASAP7_75t_R', 'BUFx12_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx24_ASAP7_75t_R']


def evalp(P, L, pmax, pmin):
    tt = V3.basis_leaf(P, L, "TT", "max", pmax)
    ff = V3.basis_leaf(P, L, "FF", "min", pmin)
    return tt, ff


def obj(tt, ff):
    wt = max(tt.values()) - min(tt.values()); wf = max(ff.values()) - min(ff.values())
    return max(wt, wf), wt, wf


G = {}


def _try(um):
    u, m = um; P = G["P"]; m0 = P.nodes[u]["cell"]
    P.nodes[u]["cell"] = m
    t2, f2 = evalp(P, G["L"], G["pmax"], G["pmin"])
    P.nodes[u]["cell"] = m0
    return um, obj(t2, f2)


def main():
    rj, geo, libdir, fit, out = sys.argv[1:6]
    steps = int(sys.argv[sys.argv.index('--steps') + 1]) if '--steps' in sys.argv else 300
    slew_lim = float(sys.argv[sys.argv.index('--slew') + 1]) if '--slew' in sys.argv else 80.0
    op = gzip.open if rj.endswith(".gz") else open
    rec = json.load(op(rj, "rt"))[0]
    F = json.load(open(fit)); pmax, pmin = dict(F["PMAX"]), dict(F["PMIN"])
    for c in ENV + sorted({n[3] for n in rec["nodes_xy"]}):
        if c not in U.SIZES: U.SIZES.append(c)
    L = U.load_libs(libdir)
    P = A.PlanFromRecord(rec, geo)
    par = {n[0]: n[1] for n in rec["nodes_xy"]}
    fixed = {"root"}
    def path(k):
        p = [k]
        while par.get(p[-1]) is not None: p.append(par[p[-1]])
        return [x for x in p if x not in fixed]
    tt, ff = evalp(P, L, pmax, pmin); o0 = obj(tt, ff); cur = o0; log = []
    def slew_max():
        q = A.calibrated_summary(P, L, pmax, pmin)
        return max(q[c][k] for c in ("TT", "FF") for k in ("leaf_out_slew_max", "leaf_slew_in_max"))
    cap = max(slew_lim, slew_max()); rejected = 0
    t0 = time.time(); tried = set(); joint_log = []
    for s in range(steps):
        best = None
        cand = []
        for C, d in (("TT", tt), ("FF", ff)):
            lo = min(d, key=d.get); hi = max(d, key=d.get)
            plo, phi = path(lo), path(hi)
            cand += [u for u in plo if u not in phi] + [u for u in phi if u not in plo]
        jobs = sorted({(u, m) for u in set(cand) for m in ENV if m != P.nodes[u]["cell"]})
        G.update(P=P, L=L, pmax=pmax, pmin=pmin)
        with MP.get_context("fork").Pool(min(48, len(jobs))) as pool:
            res = pool.map(_try, jobs)
        good = sorted(((o, u, m) for (u, m), o in res if o[0] < cur[0] - 0.05), key=lambda b: (b[0][0], b[0][1] + b[0][2], b[1], b[2]))
        for o, u, m in good:
            keep = P.nodes[u]["cell"]; P.nodes[u]["cell"] = m
            sl = slew_max(); P.nodes[u]["cell"] = keep
            if sl <= cap:
                best = (o, u, m); break
            rejected += 1
        if best is not None:
            P.nodes[best[1]]["cell"], keep = best[2], P.nodes[best[1]]["cell"]
            t2, f2 = evalp(P, L, pmax, pmin); P.nodes[best[1]]["cell"] = keep
            best = best + (t2, f2)
        if best is None and '--joint3' in sys.argv:
            from joint_rvt import propose
            def evaluate_joint(assignments, need_slew):
                originals = {u: P.nodes[u]["cell"] for u in assignments}
                try:
                    for u, master in assignments.items(): P.nodes[u]["cell"] = master
                    jt, jf = evalp(P, L, pmax, pmin)
                    sl = {}
                    if need_slew:
                        summary = A.calibrated_summary(P, L, pmax, pmin)
                        sl = {c + "_" + label: summary[c][field]
                              for c in ("TT", "FF") for label, field in
                              (("in", "leaf_slew_in_max"), ("out", "leaf_out_slew_max"))}
                    return jt, jf, sl
                finally:
                    for u, master in originals.items(): P.nodes[u]["cell"] = master
            joint = propose(tt, ff, par, {u: n["cell"] for u, n in P.nodes.items()},
                            ENV, evaluate_joint, min(slew_lim, 80.0))
            if joint is not None:
                previous = cur
                for u, master in sorted(joint['assignments'].items()):
                    log.append(dict(step=s, node=u, frm=P.nodes[u]["cell"], to=master,
                                    joint=True, obj=round(joint['key'][0], 2)))
                    P.nodes[u]["cell"] = master
                tt, ff = joint['tt'], joint['ff']; cur = obj(tt, ff)
                joint_log.append(dict(step=s, near_leaves=joint['near_leaves'], corner=joint['corner'],
                                      assignments=joint['assignments'], before=previous, after=cur,
                                      full_tree_trials=joint['full_tree_trials'], slews=joint['slews']))
                print("joint step %d %s TTw %.2f FFw %.2f (%.0fs)" %
                      (s, joint['assignments'], cur[1], cur[2], time.time() - t0), flush=True)
                continue
        if best is None: break
        o, u, m, tt, ff = best
        log.append(dict(step=s, node=u, frm=P.nodes[u]["cell"], to=m, obj=round(o[0], 2), TTw=round(o[1], 2), FFw=round(o[2], 2)))
        P.nodes[u]["cell"] = m; cur = o
        print("step %d %s %s -> %s  TTw %.2f FFw %.2f  (%.0fs)" % (s, u, log[-1]["frm"], m, o[1], o[2], time.time() - t0), flush=True)
    rec = dict(rec)
    rec["nodes_xy"] = [[n[0], n[1], n[2], P.nodes[n[0]]["cell"], n[4]] for n in rec["nodes_xy"]]
    rec["frozen_masters"] = {n[0]: n[3] for n in rec["nodes_xy"]}
    rec["d1_uf3"] = dict(rule="12.8 d1 plan-computed sizing under uf_phys3 v1 (pre-build, no measurement)", start=dict(obj=round(o0[0], 2), TTw=round(o0[1], 2), FFw=round(o0[2], 2)), changes=log)
    if joint_log:
        rec["d1_uf3"]["joint3"] = joint_log
    if rejected:
        rec["d1_uf3"]["slew_guard"] = dict(limit_ps=cap, rejected_changes=rejected)
    rec["d1_uf3"]["prediction"] = A.calibrated_summary(P, L, pmax, pmin)
    rec["d1_uf3"]["fit_name"] = F["name"]
    rec["name"] = rec["name"] + "_uf3d1"
    Path(out).write_text(json.dumps([rec]))
    print("done", len(log), "changes; window TT %.2f FF %.2f (start %.2f/%.2f)" % (cur[1], cur[2], o0[1], o0[2]))


if __name__ == "__main__":
    main()
