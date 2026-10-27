"""PLAN-ICG-MODEL fit + validation: routed signed-off gated cores (qxpq_w10 cpr, bf_col compact199).
Inputs: data/<core>/out/{stages,sinks}_{TT,FF}.tsv from icg_measure.tcl (6_final ODB + SPEF, OpenSTA propagated).
Fits OPEN_SUBTREE_CAL (per corner) on single-level gated domains; ICG arc = liberty NLDM (not fitted)."""
import csv, json, math, sys, statistics as st
from collections import defaultdict
sys.path.insert(0, sys.argv[2])
import core_infra_plan as CP, core_infra as CI, die_clock_128 as C128
DATA, LIB = sys.argv[1], sys.argv[3]
WR, WC = 0.0214161, 0.145426            # ASAP7 setRC.tcl set_wire_rc -clock (kohm/um, fF/um)
def rows(p): return list(csv.DictReader(open(p), delimiter='\t'))
pts = []
for core in ('qxpq', 'bfcol'):
    for c in ('TT', 'FF'):
        S = rows(f'{DATA}/{core}/out/stages_{c}.tsv'); K = rows(f'{DATA}/{core}/out/sinks_{c}.tsv')
        by = {r['name']: r for r in S}
        kids = defaultdict(list)
        for r in S: kids[r['parent']].append(r)
        dom = defaultdict(list)
        for r in K: dom[r['icg']].append(r)
        nested = defaultdict(int)
        for r in S:
            if r['kind'] == 'icg': nested[r['icg']] += 1
        for name, ss in dom.items():
            if name == 'ROOT' or nested[name]: continue          # single-level gated domains only (12.8b structure)
            g = by[name]; first = [r for r in kids[name]]
            if not first or any(r['kind'] == 'icg' for r in first): continue
            xs = [float(s['x_um']) for s in ss]; ys = [float(s['y_um']) for s in ss]; a = [float(s['arr']) for s in ss]
            pts.append(dict(core=core, corner=c, icg=name, master=g['master'], n=len(ss), rect=[min(xs), min(ys), max(xs), max(ys)],
                            icg_xy=[float(g['x_um']), float(g['y_um'])], clk_arr=float(g['in_arr']), clk_slew=float(g['in_slew']),
                            gclk_arr=float(g['out_arr']), gclk_fo=len(first),
                            root_in=st.mean(float(r['in_arr']) for r in first), root_xy=[st.mean(float(r['x_um']) for r in first), st.mean(float(r['y_um']) for r in first)],
                            mean=st.mean(a), min=min(a), max=max(a),
                            meas_levels=st.mean(int(s['below_icg']) for s in ss)))
def feats(p):
    k = CI._cts_levels(dict(domain_sinks=p['n'], cts_fanout=CI.CTS_FANOUT), 'x'); d = CP.region_reach(p['rect'], p['icg_xy']); return k, d, None
EXCL = set(sys.argv[5].split(',')) if len(sys.argv) > 5 and sys.argv[5] else set()
def fit(sub):
    # weighted LS through origin (each core = equal total weight): mean_sub = s*k + g*D ; hi = (max-mean)/D ; lo = (mean-min)/D
    sub = [p for p in sub if p['icg'] not in EXCL]
    nc = defaultdict(int)
    for p in sub: nc[p['core']] += 1
    W = [1.0 / nc[p['core']] for p in sub]
    A = [[feats(p)[0], feats(p)[1]] for p in sub]; y = [p['mean'] - p['root_in'] for p in sub]
    s11 = sum(w * r[0] * r[0] for w, r in zip(W, A)); s12 = sum(w * r[0] * r[1] for w, r in zip(W, A)); s22 = sum(w * r[1] * r[1] for w, r in zip(W, A))
    b1 = sum(w * r[0] * v for w, r, v in zip(W, A, y)); b2 = sum(w * r[1] * v for w, r, v in zip(W, A, y)); det = s11 * s22 - s12 * s12
    stage = (b1 * s22 - b2 * s12) / det; reg = (s11 * b2 - s12 * b1) / det
    dd = [feats(p)[1] for p in sub]
    hi = sum(w * (p['max'] - p['mean']) * d for w, p, d in zip(W, sub, dd)) / sum(w * d * d for w, d in zip(W, dd))
    lo = sum(w * (p['mean'] - p['min']) * d for w, p, d in zip(W, sub, dd)) / sum(w * d * d for w, d in zip(W, dd))
    return dict(stage_ps=stage, region_ps_per_um=reg, lo_ps_per_um=lo, hi_ps_per_um=hi)
libs = {c: {**C128.lib_cells(c, LIB, (CP.CTS_ROOT_MASTER,)), **CP.icg_lib_cells(c, LIB, ('ICGx1_ASAP7_75t_R',))} for c in ('TT', 'FF')}
def predict(p, cal):
    """Plan prediction of the domain given the MEASURED arrival/slew at the ICG CLK pin (upstream tree is not plan-built here)."""
    lib = libs[p['corner']]; k, d, _ = feats(p)
    L = 0.0                                                   # CTS root buffer next to the driver
    load = lib[CP.CTS_ROOT_MASTER]['cap'] + WC * L
    icg = C128._bilin(lib[p['master']]['delay'], p['clk_slew'], load)
    el = L * WR * (L * WC / 2 + lib[CP.CTS_ROOT_MASTER]['cap'])
    sub = CP.open_subtree(p['n'], p['rect'], p['corner'], p['icg_xy'], cal={p['corner']: cal, 'basis': ''})
    root_in = p['clk_arr'] + icg + el
    return dict(icg_stage=icg + el, mean=root_in + sub['mean_ps'], min=root_in + sub['min_ps'], max=root_in + sub['max_ps'], k=k, d=d)
def stats(v): return dict(n=len(v), bias=st.mean(v), max_abs=max(abs(x) for x in v), rms=math.sqrt(st.mean(x * x for x in v)))
report = dict(points=len(pts), cal={}, validation={})
for c in ('TT', 'FF'):
    P = [p for p in pts if p['corner'] == c]
    cal = fit(P); report['cal'][c] = cal
    res = {}
    for core in ('qxpq', 'bfcol'):
        Q = [p for p in P if p['core'] == core]
        # in-sample
        r_in = [predict(p, cal)['mean'] - p['mean'] for p in Q]
        # cross-core: fitted on the OTHER core only
        other = fit([p for p in P if p['core'] != core]) if len({p['core'] for p in P}) > 1 else None
        r_x = [predict(p, other)['mean'] - p['mean'] for p in Q] if other else None
        # leave-one-domain-out
        r_loo = [predict(p, fit([q for q in P if q is not p]))['mean'] - p['mean'] for p in Q] if core == 'bfcol' else None
        r_icg = [predict(p, cal)['icg_stage'] - (p['root_in'] - p['clk_arr']) for p in Q]
        r_max = [predict(p, cal)['max'] - p['max'] for p in Q]; r_min = [predict(p, cal)['min'] - p['min'] for p in Q]
        # whole-core gated-sink mean (sink-weighted)
        w = sum(p['n'] for p in Q); pm = sum(predict(p, cal)['mean'] * p['n'] for p in Q) / w; mm = sum(p['mean'] * p['n'] for p in Q) / w
        pmx = sum(predict(p, other)['mean'] * p['n'] for p in Q) / w if other else None
        res[core] = dict(domains=len(Q), gated_sinks=w, meas_mean=mm, pred_mean=pm, core_resid=pm - mm,
                         core_resid_crossfit=None if pmx is None else pmx - mm,
                         domain_resid=stats(r_in), domain_resid_crossfit=stats(r_x) if r_x else None,
                         domain_resid_loo=stats(r_loo) if r_loo else None, icg_stage_resid=stats(r_icg),
                         max_resid=stats(r_max), min_resid=stats(r_min),
                         meas_levels=sorted({round(p['meas_levels'], 2) for p in Q})[:6], plan_levels=sorted({feats(p)[0] for p in Q}),
                         fit_other_core=other)
    report['validation'][c] = res
    if c == 'TT':
        report['bfcol_domains_TT'] = [dict(icg=p['icg'], n=p['n'], d_um=round(feats(p)[1], 1), k_plan=feats(p)[0], meas_levels=round(p['meas_levels'], 2),
                                          clk_arr=p['clk_arr'], icg_meas=round(p['root_in'] - p['clk_arr'], 2), icg_pred=round(predict(p, cal)['icg_stage'], 2),
                                          meas_mean=round(p['mean'], 2), pred_mean=round(predict(p, cal)['mean'], 2), meas_max=round(p['max'], 2), pred_max=round(predict(p, cal)['max'], 2))
                                     for p in P if p['core'] == 'bfcol']
json.dump(report, open(sys.argv[4], 'w'), indent=1)
json.dump(pts, open(sys.argv[4].replace('.json', '_points.json'), 'w'))
print(json.dumps({c: {k: round(v, 4) for k, v in report['cal'][c].items()} for c in report['cal']}))
for c, res in report['validation'].items():
    for core, r in res.items():
        print(c, core, 'dom', r['domains'], 'sinks', r['gated_sinks'], 'core meas %.1f pred %.1f res %+.1f xfit %s' % (r['meas_mean'], r['pred_mean'], r['core_resid'], None if r['core_resid_crossfit'] is None else round(r['core_resid_crossfit'], 1)),
              '| dom in', {k: round(v, 1) for k, v in r['domain_resid'].items()}, '| xfit', r['domain_resid_crossfit'] and {k: round(v, 1) for k, v in r['domain_resid_crossfit'].items()},
              '| loo', r['domain_resid_loo'] and {k: round(v, 1) for k, v in r['domain_resid_loo'].items()}, '| icg', {k: round(v, 1) for k, v in r['icg_stage_resid'].items()},
              '| max', {k: round(v, 1) for k, v in r['max_resid'].items()}, 'lv meas', r['meas_levels'], 'plan', r['plan_levels'])
