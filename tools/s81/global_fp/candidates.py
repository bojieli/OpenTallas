#!/usr/bin/env python3
"""Generate and score GLOBAL-FP-S floorplan candidates for the S81 die (screen only, nothing adopted).

C0  GEN18c construction pass0 as built (legacy single-slab VM 1.54x3.95 mm = area-infeasible for the real 4-slice VM;
    MIX4 at the S-DIE GEN18m2 proposal).  GEO-S pin overrides are represented by the facing-face pin estimator.
C1  owner direction 'B compact2x2' exactly as Codex system_geometry_options.py B: VM 2x2 at (13446,12804.48),
    HC towers +324 um east, everything else as GEN18c.
SA-*  slot-stack annealer (placer.py) over the whole hub region, VM shape fixed per run (2x2 = B, 1x4v = A).
RTMP  OpenROAD rtl_macro_placer results (rtlmp.py), one per net-multiplicity unit.
P1-*  architect pipeline-order topology around the compact 2x2 VM (architect.py): VM on the SU|HC_s|HC_t tower row,
      side column on the VM face, corridor on the VM's far face, rest annealed in the free tier.
*-RP  + return-tree re-partition by locality (structural, compiler-visible: gather lane <-> frame map).
"""
import argparse, copy, hashlib, json, math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score as S
import placer as P
import architect as A

REGION = [13592.0, 1807.9, 19538.0, 23632.0]
MOVABLE = ['sp_su_s', 'sp_vm', 'sp_capture', 'sp_gather', 'sp_pq', 'sp_wfc', 'sp_sseq', 'sp_collective', 'sp_host',
           'sp_hc_s', 'sp_hc_t', 'mix4', 'hcx_ctl', 'hcx_gatherpack', 'embed_expand', 'engram_dispatch']
VM_SHAPES = {'2x2': [4168.8, 3715.2], '1x4v': [2073.6, 4 * 1555.2 + 4 * 21.6 + 561.6], 'legacy': [1541.784, 3952.776]}
MIX_SHAPES = {'1x4': [771.12, 3229.2], '2x2': [1613.5, 1542.2]}


def base_rects(g):
    return {n: list(v['rect']) for n, v in g['nodes'].items()}


def c1_B(g):
    r = base_rects(g)
    r['sp_vm'] = [13446.0, 12804.48] + VM_SHAPES['2x2']
    for h in ('sp_hc_s', 'sp_hc_t'):
        r[h][0] += 324.0
    return r


def repartition(g, rects, seed=7, iters=40000):
    """balanced re-partition of frames over the existing return trees (same tree count and sizes) by locality:
    swap frames between trees when it lowers sum over trees of MST(leaves)+trunk to the gather."""
    g2 = copy.deepcopy(g)
    trees = [e for e in g2['edges'] if e['kind'] == 'tree' and e.get('tree_mode') == 'collect']
    ports = {n: v['port'] for n, v in g2['nodes'].items() if 'port' in v}
    gat = rects['sp_gather']
    root = [gat[0] + gat[2] / 2, gat[1] + gat[3] / 2]
    sets = [[f for f in e['ends'] if f.startswith('F')] for e in trees]

    def cost(fs):
        pts = [root] + [ports[f] for f in fs]
        par = S.mst(pts, 0)
        return sum(S.man(pts[i], pts[par[i]]) for i in range(1, len(pts)))
    rng = random.Random(seed)
    cs = [cost(s) for s in sets]
    for _ in range(iters):
        a, b = rng.sample(range(len(sets)), 2)
        i, j = rng.randrange(len(sets[a])), rng.randrange(len(sets[b]))
        sa, sb = sets[a][:], sets[b][:]
        sa[i], sb[j] = sb[j], sa[i]
        ca, cb = cost(sa), cost(sb)
        if ca + cb < cs[a] + cs[b]:
            sets[a], sets[b], cs[a], cs[b] = sa, sb, ca, cb
    for e, s in zip(trees, sets):
        bits = [e['leaf_bits'][f] for f in e['ends'] if f.startswith('F')]
        e['ends'] = [e['ends'][0]] + s
        e['leaf_bits'] = {f: b for f, b in zip(s, sorted(bits, reverse=True))}
        e['prov'] += ' | RE-PARTITIONED by locality (GLOBAL-FP-S): frame->return-tree map changed'
    mixed_before = sum(len(set(g['nodes'][f]['half'] for f in e['ends'] if f.startswith('F'))) > 1
                       for e in g['edges'] if e['kind'] == 'tree' and e.get('tree_mode') == 'collect')
    mixed_after = sum(len(set(g2['nodes'][f]['half'] for f in s)) > 1 for s in sets)
    return g2, dict(trees=len(sets), sizes=sorted(len(s) for s in sets), trees_spanning_both_halves_before=mixed_before,
                    trees_spanning_both_halves_after=mixed_after)


def _placer(g, vm_shape, base, seed):
    fixed = {n: r for n, r in base.items() if n not in MOVABLE}
    dims = {n: base[n][2:] for n in MOVABLE}
    dims['sp_vm'] = VM_SHAPES[vm_shape]
    dims['sp_pq'] = [1728.0, base['sp_pq'][3]]          # pq + its 3 pqrom macros on the E edge (column width 1728)
    return P.SlotStack(g, S, MOVABLE, dims, REGION, vm_shape, fixed, seed=seed, mix_shapes=MIX_SHAPES)


def _sa_job(args):
    g, vm_shape, base, sd, iters = args
    pl = _placer(g, vm_shape, base, sd)
    J, st = pl.anneal(pl.random_state(), iters=iters, T0=1.5e7, T1=2e3)
    J, pen, worst = pl.cost(st)
    return sd, J, pen, worst, st


def _arch_job(args):
    g, base, dims, side, ck, seeds, iters, flip = args
    try:
        return A.build(g, S, base, REGION, dims, side, ck, seeds=seeds, iters=iters, flip=flip)
    except AssertionError:
        return None


def run_sa(g, vm_shape, seeds, iters, base):
    import multiprocessing as mp
    with mp.Pool(len(seeds)) as pool:
        res = pool.map(_sa_job, [(g, vm_shape, base, sd, iters) for sd in seeds])
    best = None
    for sd, J, pen, worst, st in res:
        print('  seed', sd, vm_shape, round(J / 1e6, 3), 'pen', round(pen), 'worst', round(worst), flush=True)
        if pen == 0 and (best is None or J < best[0]):
            best = (J, st)
    if best is None:
        return None
    J, st = best
    pl = _placer(g, vm_shape, base, 0)
    rects, corr, pen = pl.realize(st)
    lay = dict(base); lay.update(rects)
    return dict(layout=lay, corridor=corr, state=dict(corr_y=st['corr_y'], mix=st['mix'], tiers=st['tiers']), J=J)


def free_band(rects):
    """widest horizontal band of the hub region crossed by no hub"""
    ys = sorted([(r[1], r[1] + r[3]) for r in rects.values()])
    best, cur = None, REGION[1]
    for lo, hi in ys + [(REGION[3], REGION[3])]:
        if lo - cur > (best[3] if best else 0):
            best = [REGION[0], cur, REGION[2] - REGION[0], lo - cur]
        cur = max(cur, hi)
    return best if best and best[3] >= 300 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--graph', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--iters', type=int, default=40000)
    ap.add_argument('--seeds', default='1,2,3,4')
    ap.add_argument('--rtlmp', nargs='*', default=[], help='rtlmp.py placement jsons to score as RTMP candidates')
    ap.add_argument('--arch-seeds', default='1,2,3,4')
    ap.add_argument('--arch-iters', type=int, default=12000)
    ap.add_argument('--arch-columns', nargs='*', default=['gcm'],
                    help='also keep the best architect variant with each of these VM-face columns (P1_pipeline2x2_<key>)')
    a = ap.parse_args()
    g = json.loads(Path(a.graph).read_text())
    out = Path(a.out_dir); (out / 'links').mkdir(parents=True, exist_ok=True)
    base = base_rects(g)
    hc_corr = [17312.4, 12443.76, 1728.0, 1512.0]
    cands = []

    def add(name, lay, vm_shape, corr, region_x, notes, graph=None, extra=None, graph_ref=None):
        m, lj = S.score(graph or g, lay, name, vm_shape, notes=notes, corridor=corr, region_x=region_x)
        if extra:
            m.update(extra)
        lj['source_graph'] = a.graph
        lj['source_graph_sha256'] = hashlib.sha256(Path(a.graph).read_bytes()).hexdigest()
        (out / 'links' / (name + '.links.json')).write_text(json.dumps(lj))
        cands.append(dict(metrics=m, graph_ref=graph_ref, layout={n: [round(v, 3) for v in r] for n, r in lay.items()}))
        print(name, json.dumps({k: m[k] for k in ('sum_bit_um_M', 'sum_traffic_bit_um_M', 'relay_flops', 'bits_over_500',
                                                 'field_worst_path_um', 'field_worst_cycles')}), m['cut'], m['legality']['overlaps'], flush=True)
        return m

    add('C0_GEN18c_as_built', base, 'legacy', hc_corr, (13900.0, 19540.0),
        ['VM legacy slab 1.54x3.95 mm = 6.1 mm2: the real 4-slice VM needs 4x2073.6x1555.2 + 1987.2x561.6 edge = 14.0 mm2 (area-infeasible baseline)',
         'MIX4 at S-DIE GEN18m2 proposal 15714.0,9061.2 (771.12x3229.2), not legal-built yet',
         'GEO-S pin overrides: represented by the facing-face pin estimator (pins packed on the facing face)'])
    c1 = c1_B(g)
    add('C1_B_compact2x2_codex', c1, '2x2', [13592.0, 12443.76, 5946.0, 360.72], (13900.0, 19540.0),
        ['Codex system_geometry_options.py option B applied to GEN18c: VM 2x2 4168.8x3715.2 at (13446,12804.48), HC +324 um E',
         'E-half crossing: the hc_corridor now ends at the VM; only the 361-um strip y 12443.8-12804.5 under the VM crosses the spine'])
    seeds = [int(s) for s in a.seeds.split(',')]
    sa = {}
    for vs in ('2x2', '1x4v'):
        print('SA', vs, flush=True)
        r = run_sa(g, vs, seeds, a.iters, base)
        if r:
            sa[vs] = r
            add('SA_%s' % vs.replace('x', 'x'), r['layout'], vs, r['corridor'], (REGION[0], REGION[2]),
                ['slot-stack annealer, full-width crossing corridor 1512 um at y %.0f' % r['state']['corr_y'],
                 'MIX4 shape %s' % r['state']['mix'], 'columns: ' + json.dumps(r['state']['tiers'])],
                extra=dict(sa_state=r['state']))
    for rp in a.rtlmp:
        rt = json.loads(Path(rp).read_text())
        lay = dict(base); lay.update(rt['rects'])
        band = free_band(rt['rects'])
        add('RTMP_' + rt.get('tag', 'u%g' % rt['unit']), lay, rt.get('vm_shape', '2x2'), band, (REGION[0], REGION[2]),
            rt.get('notes', []) + ['RTL-MP has no crossing-corridor model: widest free full-width band used as the corridor: %s' % (
                'none (E/W trees scored with no crossing)' if band is None else 'y %.0f..%.0f' % (band[1], band[1] + band[3]))],
            extra=dict(rtlmp_file=rp))
    # architect: pipeline order around the compact 2x2 VM, every core variant annealed in its free tier
    dims = {n: base[n][2:] for n in MOVABLE}
    dims['sp_vm'] = VM_SHAPES['2x2']; dims['sp_pq'] = [1728.0, base['sp_pq'][3]]; dims['mix4'] = MIX_SHAPES['2x2']
    aseeds = tuple(int(x) for x in a.arch_seeds.split(','))
    jobs = [(g, base, dims, side, ck, aseeds, a.arch_iters, flip) for flip in (True, False) for side in 'WE'
            for ck in A.COLUMN_VARIANTS]
    import multiprocessing as mp
    with mp.Pool(min(len(jobs), 28)) as pool:
        arch = [r for r in pool.map(_arch_job, jobs) if r]
    for r in sorted(arch, key=lambda r: r['J']):
        print('  P1', r['side'], r['column'], 'flip' if r['flip'] else 'up', round(r['J'] / 1e6, 3), 'worst', round(r['worst']), flush=True)
    arch.sort(key=lambda r: r['J'])
    best_arch = arch[0] if arch else None
    if best_arch:
        r = best_arch
        add('P1_pipeline2x2', r['layout'], '2x2', r['corridor'], (REGION[0], REGION[2]),
            ['architect pipeline order: VM 2x2 on the SU|HC_s|HC_t tower row (%s side, %s), VM-face column %s, corridor on the VM far face' % (
                r['side'], 'towers hang from the region top' if r['flip'] else 'towers stand on the region bottom',
                '+'.join(A.COLUMN_VARIANTS[r['column']])),
             'free tier annealed (slot-stack, same objective); %d core variants tried, best kept' % len(arch)],
            extra=dict(arch_variant=dict(side=r['side'], column=r['column'], flip=r['flip'], J=r['J']),
                       arch_variants=[dict(side=x['side'], column=x['column'], flip=x['flip'], J=round(x['J']), worst=round(x['worst'])) for x in arch]))
    # structural: return-tree re-partition on the best SA 2x2 and on C1
    best2 = sa.get('2x2')
    if best2:
        g2, info = repartition(g, best2['layout'])
        add('SA_2x2_RP', best2['layout'], '2x2', best2['corridor'], (REGION[0], REGION[2]),
            ['SA_2x2 + return trees re-partitioned by locality (same 14 trees, same sizes, lane_equal kept)'], graph=g2,
            extra=dict(repartition=info), graph_ref='graph_rp.json')
        (out / 'graph_rp.json').write_text(json.dumps(g2))
    for ck in a.arch_columns:
        alt = [r for r in arch if r['column'] == ck]
        if not alt or alt[0] is best_arch:
            continue
        r = alt[0]
        nm = 'P1_pipeline2x2_' + ck
        add(nm, r['layout'], '2x2', r['corridor'], (REGION[0], REGION[2]),
            ['architect pipeline order, VM-face column %s (every VM/capture/gather/MIX4 link abutted): %s side, %s' % (
                '+'.join(A.COLUMN_VARIANTS[ck]), r['side'], 'towers hang from the region top' if r['flip'] else 'towers on the region bottom')],
            extra=dict(arch_variant=dict(side=r['side'], column=r['column'], flip=r['flip'], J=r['J'])))
        g4, info4 = repartition(g, r['layout'])
        add(nm + '_RP', r['layout'], '2x2', r['corridor'], (REGION[0], REGION[2]),
            [nm + ' + return trees re-partitioned by locality'], graph=g4, extra=dict(repartition=info4),
            graph_ref='graph_rp_p1_%s.json' % ck)
        (out / ('graph_rp_p1_%s.json' % ck)).write_text(json.dumps(g4))
    if best_arch:
        g3, info3 = repartition(g, best_arch['layout'])
        add('P1_pipeline2x2_RP', best_arch['layout'], '2x2', best_arch['corridor'], (REGION[0], REGION[2]),
            ['P1_pipeline2x2 + return trees re-partitioned by locality (same 14 trees, same sizes)'], graph=g3,
            extra=dict(repartition=info3), graph_ref='graph_rp_p1.json')
        (out / 'graph_rp_p1.json').write_text(json.dumps(g3))
    g1, info1 = repartition(g, c1)
    add('C1_B_RP', c1, '2x2', [13592.0, 12443.76, 5946.0, 360.72], (13900.0, 19540.0),
        ['C1 + return-tree re-partition by locality'], graph=g1, extra=dict(repartition=info1), graph_ref='graph_rp_c1.json')
    (out / 'graph_rp_c1.json').write_text(json.dumps(g1))
    (out / 'candidates.json').write_text(json.dumps(dict(
        schema='opentallas.s81.globalfp.candidates.v1', scope='SCREEN_ONLY_BLOCK_LEVEL_NOT_ADOPTED_NOT_NATIVE',
        graph=a.graph, graph_sha256=hashlib.sha256(Path(a.graph).read_bytes()).hexdigest(),
        tool_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
        region=REGION, candidates=cands), indent=1))


if __name__ == '__main__':
    main()
