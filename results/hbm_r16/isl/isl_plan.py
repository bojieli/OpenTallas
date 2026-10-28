#!/usr/bin/env python3
"""HBM-R16/ISL: plan-level in-core island / centre-entry structured-tree design for three HBM core types
(METHODOLOGY 12.2a1 pushdown islands, 12.3 250 TT / 202.5 FF, 12.8a-c centre entry + structured tree, 12.8d1
plan-computed per-tap sizing).  PLAN MODEL ONLY -- every insertion number below is UNCHECKED until a core CTS.

No new tree generator: the tree is tools/die_plan/core_infra_htree.plan/model (shared NLDM+Elmore planner, buffer at
every branch point, equal level lengths + repeater counts, equal-count leaf clusters), the 12.8c fixed entry trunk is
tools/die_plan/core_trunk_plan.trunk (smallest |TT-250|+|FF-202.5| over N identical cells), and the measured-basis
offset is master_plan.PLAN_TREE_OFFSETS['core_infra_htree_nldm'].  The in-core islands are the tree nodes of level
`isl_level` (the node sites ARE the islands: 8.64 um squares on the 4.32 lattice, pushdown driver cells, dont_touch).

  isl_plan.py CFG.json OUTDIR --libtt TT.lib --libff FF.lib

CFG: {name: {geo, module, splits, isl_level, transpose, vpass, entry_um (core frame, must equal the plan entry),
             trunk_cell}}
Geometry input: placed core (3_place.odb) sequential clock pins + macros, dumped by dump_seq_geo.tcl.
"""
import argparse, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'die_plan'))
import core_infra_htree as H          # noqa: E402
import core_trunk_plan as TP          # noqa: E402

OFFS = dict(TT=-12.8, FF=-24.5)       # master_plan.PLAN_TREE_OFFSETS['core_infra_htree_nldm'] (raw -> GRT basis)
LAT, HALF = 4.32, 4.32
TGT = dict(TT=250.0, FF=202.5)


def snap(v):
    return round(round(v / LAT) * LAT, 3)


def transpose_geo(src, dst):
    out = []
    for l in open(src):
        f = l.split()
        if not f:
            continue
        if f[0] in ('DIE', 'CORE'):
            f = [f[0], f[2], f[1], f[4], f[3]]
        elif f[0] == 'PIN':
            f = f[:2] + [f[3], f[2]]
        elif f[0] == 'SINK':
            f = [f[0], f[2], f[1]] + f[3:]
        elif f[0] == 'MACRO':
            f = f[:3] + [f[4], f[3], f[6], f[5]] + (['CK', f[9], f[8]] if len(f) > 9 else [])
        out.append(' '.join(f))
    Path(dst).write_text('\n'.join(out) + '\n')


def set_entry(src, dst, e):
    out = []
    for l in open(src):
        f = l.split()
        if f and f[0] == 'PIN' and f[1] == 'ck':
            l = 'PIN ck %.3f %.3f\n' % tuple(e)
        out.append(l)
    Path(dst).write_text(''.join(out))


def run(name, c, outdir, libtt, libff):
    tp = c.get('transpose', False)
    H.MACRO_VPASS = bool(c.get('vpass', False))
    g0 = outdir / (name + '_geo_entry.txt')
    set_entry(c['geo'], g0, c['entry_um'])
    geo = g0
    if tp:
        geo = outdir / (name + '_geo_T.txt')
        transpose_geo(g0, geo)
    back = (lambda p: (p[1], p[0])) if tp else (lambda p: (p[0], p[1]))
    splits = c['splits']
    P = H.plan(str(geo), splits, c.get('smax', 70.0), [], None)
    mz = P['mz']
    kr, kc = 0.8, 0.9
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr
    cc = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    cell = c.get('trunk_cell', 'BUFx4_ASAP7_75t_R')
    libs = {'TT': H.lib_cells(libtt, [H.REP, H.BIG, cell]), 'FF': H.lib_cells(libff, [H.REP, H.BIG, cell])}
    cands = []
    for n in range(0, 16):
        res = {}
        for k in libs:
            if n:
                td, ts, per = TP.trunk(libs[k], cell, n, libs[k][H.BIG]['cin'], r, cc, 20.0)
            else:
                td, ts, per = 0.0, 20.0, []
            t = H.model(P, {k: libs[k]}, r, cc, ts)[k]
            raw = t['mean'] + td
            res[k] = dict(trunk_ps=round(td, 2), raw_mean=round(raw, 2), grt_basis_mean=round(raw + OFFS[k], 2),
                          window=t['window'], sink_min=round(t['sink_min'] + td, 2), sink_max=round(t['sink_max'] + td, 2))
        # the trunk is chosen on the GRT-basis prediction (offsets of the same tree model), deterministic
        cost = abs(res['TT']['grt_basis_mean'] - TGT['TT']) + abs(res['FF']['grt_basis_mean'] - TGT['FF'])
        cands.append((round(cost, 2), n, res))
    cost, n, pred = min(cands, key=lambda x: (x[0], x[1]))
    # islands = tree node sites of level isl_level, snapped to the nearest 4.32-lattice square that stays inside the
    # core and clears every macro (halo 0) -- the island square itself is a placement/macro blockage
    mlist = [tuple(map(float, l.split()[3:7])) for l in open(c['geo']) if l.startswith('MACRO')]
    corec = tuple(map(float, [l.split() for l in open(c['geo']) if l.startswith('CORE')][0][1:5]))

    def legal_snap(p):
        best = None
        for i in range(-3, 4):
            for j in range(-3, 4):
                q = (snap(p[0]) + i * LAT, snap(p[1]) + j * LAT)
                rc = (q[0] - HALF, q[1] - HALF, q[0] + HALF, q[1] + HALF)
                if rc[0] < corec[0] or rc[1] < corec[1] or rc[2] > corec[2] or rc[3] > corec[3]:
                    continue
                if any(rc[0] < m[2] and rc[2] > m[0] and rc[1] < m[3] and rc[3] > m[1] for m in mlist):
                    continue
                dd = abs(q[0] - p[0]) + abs(q[1] - p[1])
                if best is None or dd < best[0]:
                    best = (dd, (round(q[0], 3), round(q[1], 3)))
        return best[1] if best else (snap(p[0]), snap(p[1]))
    L = c['isl_level']
    isl = []
    for g in sorted(x for x in P['groups'] if len(x) == L):
        s = mz.xy(P['site'][g])
        sinks = P['groups'][g]
        d = [mz.md(P['site'][g], mz.cell(p[:2], node=False)) for p in sinks]
        d.sort()
        ctr = back(s)
        lq = legal_snap(ctr)
        isl.append(dict(name=P['nm'](g), centre_um=[round(ctr[0], 3), round(ctr[1], 3)],
                        centre_lattice_um=[lq[0], lq[1]], snap_displacement_um=round(abs(lq[0] - ctr[0]) + abs(lq[1] - ctr[1]), 3),
                        rect_um=[round(lq[0] - HALF, 3), round(lq[1] - HALF, 3),
                                 round(lq[0] + HALF, 3), round(lq[1] + HALF, 3)],
                        entry_maze_um=round(mz.md(P['ent'], P['site'][g]), 2),
                        load=len(sinks), load_frac=round(len(sinks) / sum(len(v) for v in P['leafsinks'].values()), 4),
                        reach_um=dict(mean=round(sum(d) / len(d), 1), p95=round(d[int(0.95 * (len(d) - 1))], 1),
                                      max=round(d[-1], 1))))
    leaves = [x for x in P['nodes'] if x[4] == 'leaf']
    lr = []
    for lf in leaves:
        ss = P['leafsinks'][lf[0]]
        lr.append(max(abs(p[0] - mz.xy(lf[2])[0]) + abs(p[1] - mz.xy(lf[2])[1]) for p in ss))
    allsink_far = max(mz.md(P['ent'], mz.cell(p[:2], node=False)) for v in P['leafsinks'].values() for p in v)
    par = {x[0]: x[1] for x in P['nodes']}
    depths = set()
    for lf in leaves:
        d, u = 1, lf[0]
        while par[u]:
            u = par[u]; d += 1
        depths.add(d)
    nodes = [(x[0], x[1], [round(v, 3) for v in back(mz.xy(x[2]))], x[3], x[4]) for x in P['nodes']]
    wires = []
    for w in P['wires']:
        pts = []
        for seg in w['cells']:
            pts += [list(back(mz.xy(q))) for q in seg]
        wires.append(dict(level=w['level'], edge=w['edge'], len_um=round(sum(w['segs']), 2), path=pts[::max(1, len(pts) // 40)] + [pts[-1]]))
    macros = []
    for l in open(c['geo']):
        f = l.split()
        if f and f[0] == 'MACRO':
            macros.append(dict(name=f[1], rect_um=[float(v) for v in f[3:7]]))
    core = [float(v) for v in [l.split() for l in open(c['geo']) if l.startswith('CORE')][0][1:5]]
    # island squares must clear every macro (halo 0, KV ruling: island rect (+halo) = macro blockage, so the
    # island may abut but never overlap a macro) and stay inside the core
    def clear(rc):
        inside = rc[0] >= core[0] and rc[1] >= core[1] and rc[2] <= core[2] and rc[3] <= core[3]
        return inside and not any(rc[0] < m['rect_um'][2] and rc[2] > m['rect_um'][0] and rc[1] < m['rect_um'][3]
                                  and rc[3] > m['rect_um'][1] for m in macros)
    e = c['entry_um']
    ent_rect = [round(snap(e[0]) - HALF, 3), round(snap(e[1]) - HALF, 3), round(snap(e[0]) + HALF, 3), round(snap(e[1]) + HALF, 3)]
    # 12.2a1 form: the die tree/mesh drops into every island (M9->M5 stack), so the core latency is island-rooted:
    # same splits below the island level, each island its own root (20 ps source slew at the drop)
    isl_rooted = {}
    macro_lines = [l for l in open(geo) if l.startswith('MACRO') or l.startswith('CORE') or l.startswith('DIE')]
    for g in sorted(x for x in P['groups'] if len(x) == L):
        if L == 0 or len(splits) <= L:
            break
        sg = outdir / ('%s_isl_%s_geo.txt' % (name, P['nm'](g)))
        sx, sy = mz.xy(P['site'][g])
        with open(sg, 'w') as fh:
            fh.writelines(macro_lines)
            fh.write('PIN ck %.3f %.3f\n' % (sx, sy))
            for p_ in P['groups'][g]:
                fh.write('SINK %.3f %.3f %s %s %s\n' % (p_[0], p_[1], p_[4], p_[2], p_[3]))
        try:
            Q = H.plan(str(sg), splits[L:], c.get('smax', 70.0), [], None)
            rq = {}
            for k in libs:
                t = H.model(Q, {k: libs[k]}, r, cc, 20.0)[k]
                rq[k] = dict(raw_mean=t['mean'], grt_basis_mean=round(t['mean'] + OFFS[k], 2), window=t['window'],
                             sink_max=t['sink_max'])
            isl_rooted[P['nm'](g)] = dict(level_len_um=[round(x, 2) for x in Q['T']], repeaters_per_edge=[k - 1 for k in Q['K']], pred=rq)
        except Exception as ex:   # planner refuses this sub-structure (e.g. mixed local/far fan): recorded, no number
            isl_rooted[P['nm'](g)] = dict(error=repr(ex))
    ok = {kk: v for kk, v in isl_rooted.items() if 'pred' in v}
    if ok and len(ok) == len(isl_rooted):
        for k in ('TT', 'FF'):
            ms = [v['pred'][k]['grt_basis_mean'] for v in ok.values()]
            isl_rooted['_summary_' + k] = dict(mean_min=min(ms), mean_max=max(ms), spread=round(max(ms) - min(ms), 2),
                                               window_max=max(v['pred'][k]['window'] for v in ok.values()))
    rep = dict(
        island_rooted_pred=isl_rooted,
        scope='PLAN MODEL ONLY: core_infra_htree NLDM+Elmore (rc 0.8/0.9) + core_trunk_plan fixed trunk; '
              'GRT basis = raw + PLAN_TREE_OFFSETS core_infra_htree_nldm (TT %.1f / FF %.1f); UNCHECKED' % (OFFS['TT'], OFFS['FF']),
        module=c['module'], core_um=core, entry_um=e, entry_island_um=ent_rect, entry_island_clear=clear(ent_rect),
        frame='core frame (kit 3_place), x right / y up; %s' % ('planned in the transposed frame (level-0 split N/S)' if tp else 'level-0 split W/E'),
        n_sinks=sum(len(v) for v in P['leafsinks'].values()), macros=macros,
        splits=splits, leaves=len(leaves), leaf_load=[min(len(v) for v in P['leafsinks'].values()), max(len(v) for v in P['leafsinks'].values())],
        level_len_um=[round(t, 2) for t in P['T']], repeaters_per_edge=[k - 1 for k in P['K']],
        stages_per_path=sorted(depths), path_wire_um=round(sum(P['T']), 2),
        leaf_radius_um=dict(max=round(max(lr), 1), mean=round(sum(lr) / len(lr), 1)),
        entry_to_farthest_sink_maze_um=round(allsink_far, 1),
        trunk=dict(cell=cell, n=n, site='entry island', dont_touch=True, rule='12.8c fixed trunk, same chain per type'),
        pred=pred, target=TGT,
        in_band=dict(TT=abs(pred['TT']['grt_basis_mean'] - 250) <= 20, FF=abs(pred['FF']['grt_basis_mean'] - 202.5) <= 20),
        islands=[dict(q, clear_of_macros=clear(q['rect_um'])) for q in isl], island_level=L,
        drivers=dict(branch=H.BIG, repeater=H.REP, leaf=H.BIG, count=len(P['nodes']) + n),
        nodes=nodes, wires=wires,
        candidates=[dict(n=x[1], cost=x[0], TT=x[2]['TT']['grt_basis_mean'], FF=x[2]['FF']['grt_basis_mean']) for x in cands])
    (outdir / (name + '_plan.json')).write_text(json.dumps(rep, indent=1) + '\n')
    H.MACRO_VPASS = False
    return rep


def render(name, rep, geo, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    xs, ys = [], []
    for l in open(geo):
        if l.startswith('SINK'):
            f = l.split(); xs.append(float(f[1])); ys.append(float(f[2]))
    c = rep['core_um']
    fig, ax = plt.subplots(figsize=(9, 9 * (c[3] - c[1]) / (c[2] - c[0]) + 0.6))
    hb = ax.hexbin(xs, ys, gridsize=40, extent=(c[0], c[2], c[1], c[3]), cmap='Greys', mincnt=1, alpha=0.8)
    fig.colorbar(hb, ax=ax, fraction=0.03, label='FF per bin')
    ax.add_patch(plt.Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fill=False, ec='k', lw=1.5))
    for m in rep['macros']:
        r = m['rect_um']
        ax.add_patch(plt.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='#9ecae1', ec='#08519c', alpha=0.6))
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, 'SRAM ' + m['name'].split('.')[-1], ha='center', fontsize=8)
    cols = ['#d62728', '#ff7f0e', '#2ca02c', '#9467bd', '#8c564b', '#17becf']
    for w in rep['wires']:
        p = np.array(w['path'])
        ax.plot(p[:, 0], p[:, 1], '-', color=cols[(w['level'] - 1) % len(cols)], lw=2.4 if w['level'] <= rep['island_level'] else 0.6,
                alpha=0.9 if w['level'] <= rep['island_level'] else 0.5)
    for n in rep['nodes']:
        if n[4] == 'leaf':
            ax.plot(n[2][0], n[2][1], 's', ms=2.5, color='#1f77b4')
    e = rep['entry_island_um']
    ax.add_patch(plt.Rectangle((e[0], e[1]), 8.64, 8.64, fc='gold', ec='k', lw=1.2, zorder=5))
    for q in rep['islands']:
        r = q['rect_um']
        ax.add_patch(plt.Rectangle((r[0], r[1]), 8.64, 8.64, fc='#d62728', ec='k', lw=1.2, zorder=5))
        ax.text(r[2] + 2, r[3] + 2, '%s (%.1f,%.1f) reach max %.0f' % (q['name'], q['centre_lattice_um'][0], q['centre_lattice_um'][1],
                                                                  q['reach_um']['max']), fontsize=8, zorder=6,
                bbox=dict(fc='white', alpha=0.8, lw=0))
    p = rep['pred']
    ax.set_title('%s  %.2fx%.2f  %d FF  splits %s  trunk %dx%s\nPLAN MODEL (UNCHECKED, GRT basis): TT %.1f / FF %.1f ps '
                 '(target 250/202.5), window TT %.1f FF %.1f; entry gold, islands red' %
                 (rep['module'], c[2], c[3], rep['n_sinks'], rep['splits'], rep['trunk']['n'], rep['trunk']['cell'].split('_')[0],
                  p['TT']['grt_basis_mean'], p['FF']['grt_basis_mean'], p['TT']['window'], p['FF']['window']), fontsize=9)
    ax.set_xlim(c[0] - 5, c[2] + 5); ax.set_ylim(c[1] - 5, c[3] + 5); ax.set_aspect('equal')
    ax.set_xlabel('x um (core frame)'); ax.set_ylabel('y um')
    fig.tight_layout(); fig.savefig(out, dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cfg'); ap.add_argument('outdir')
    ap.add_argument('--libtt', required=True); ap.add_argument('--libff', required=True)
    ap.add_argument('--only', default=None)
    a = ap.parse_args()
    cfg = json.loads(Path(a.cfg).read_text())
    od = Path(a.outdir); od.mkdir(parents=True, exist_ok=True)
    for name, c in cfg.items():
        if a.only and name not in a.only.split(','):
            continue
        rep = run(name, c, od, a.libtt, a.libff)
        render(name, rep, c['geo'], od / (name + '_plan.png'))
        p = rep['pred']
        print(name, 'splits', rep['splits'], 'trunk', rep['trunk']['n'], 'TT %.1f FF %.1f win %.1f/%.1f' % (
            p['TT']['grt_basis_mean'], p['FF']['grt_basis_mean'], p['TT']['window'], p['FF']['window']),
            'levels', rep['level_len_um'], 'reps', rep['repeaters_per_edge'], 'leafR', rep['leaf_radius_um'],
            'islands', [(q['centre_lattice_um'], q['reach_um']['max'], q['load'], q['clear_of_macros']) for q in rep['islands']],
            'entry_clear', rep['entry_island_clear'],
            'ISLROOT', {k: v for k, v in rep['island_rooted_pred'].items() if k.startswith('_')}, flush=True)


if __name__ == '__main__':
    main()
