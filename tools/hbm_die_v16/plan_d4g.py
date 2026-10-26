#!/usr/bin/env python3
"""H-D4G 10-17 (owner 0do): HBM die d4g = plan (b) per-quadrant services (H-PLANSTUDY plan_b_inner) + two levers.

LEVER 1 -- each quadrant aligned with its HBM channels (shortest HBM -> SM data path):
  * the PHY/PC row of each stack is shifted so the channel split PC3 | PC4 sits on the die centre line: quadrant W
    owns PCs 0-3 (left half of the PHY), quadrant E owns PCs 4-7;
  * the 2.24 mm centre spine of plan (b) is removed from the SM row: the 4 SMs of a quadrant (with their XQL pair
    stores) are packed toward the centre, directly behind their own PC half, leaving one CENTRE LANE CHANNEL
    (--channel um) on the PC3 | PC4 line for the fat vertical HBM->core lanes (HBM_VM / VM_HBM / KV / IDX keys);
  * the IDX scorer quarters leave the spine.  They read the same 1,099-b SM packet as the SMs (svg -> scorer), so
    they sit BESIDE THE PHY (idx 'phy', adopted): in the corner below the SM row, next to the PC row; 'band' (core
    band centre gap) and 'corner' (outer SM-row corners) were measured and are worse.
LEVER 2 -- narrow buses bundled into wide fixed-pitch lanes with fixed station rows (S81-DV lane model, H-RELAY):
  * every bus is routed as in the plan-study bus model; buses that share (driver plan block, sink plan blocks,
    clock domain) share ONE lane bundle: lanes = ceil(sum bits / lane width) (624 point-to-point, 136 forks; the
    48-b class disappears inside bundles), stations = the bundle's longest member route / 380 um, at FIXED station
    rows (one row per 380 um of bundle route; T lane tiles per row);
  * a forwarded-clock lane ends in a LANDING (lanes/LANDING-CONTRACT.md) at every block input it feeds: one landing
    tile per (bundle, sink block), counted.

Metrics (the same tools for plan (b) and d4g; bus rows = the run8 generated contract with relay chains collapsed,
tools/hbm_die_v16/d4g_bus_rows.py, because the run9 dry-run rows the study used were deleted with the d4f cancel):
cut, graph bit-mm, per-class stages (v6_eval), bus bit-mm, relay tiles, station rows, longest link, equal-age
broadcast depth, clock regions / communicating pairs.
    plan_d4g.py --rows ROWS.json --manifest RUN8_MANIFEST.json --out results/arch/hbm_die_d4g/plan
"""
import argparse, collections, copy, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
import plan_study_1017 as S  # noqa: E402

CX = S.W_DIE / 2
BAND_Y0 = S.BAND_Y
SM_H0 = 6678.72          # d4f A2P SM column slot height (H-SM 4 x 4 rp4 tile column)


def sm_frame(PA, sm_dh=0.0):
    """SMFRAME (HANDOFF 0gd 10-18): the SM column slot grows by sm_dh um in y (the rp4 tile 1529.28 -> 1598.4 for the
    43.2-um macro lattice).  The S-half SM row keeps its PHY-side (bottom) edge; the XQL pair stores (anchored at the
    SM row's inner edge), the core band (S.BAND_Y), the centre strip and the whole N half (mirrored about the new die
    height) move by sm_dh, so every link keeps its length except the SM column itself.  Returns a PA copy; sets
    S.BAND_Y (module-level, used by plan_b and the quadrant core template)."""
    PA = copy.deepcopy(PA)
    S.BAND_Y = round(BAND_Y0 + sm_dh, 3)
    if not sm_dh:
        return PA
    for i in range(8):
        r = PA[f'sm_SW{i}']
        assert abs(r['h'] - SM_H0) < 1e-6, (i, r['h'])
        r['h'] = round(r['h'] + sm_dh, 3)
    for n, r in PA.items():
        if n.startswith('xq_SW_p'):
            r['y'] = round(r['y'] + sm_dh, 3)
    return PA


def plan_d4g(PA, channel=400.0, idx='band', sm_dh=0.0):
    """PA must already carry the SM frame (sm_frame(PA, sm_dh)); sm_dh here moves the PHY-side config leaves."""
    P, H = S.plan_b(PA, side='inner')
    P = copy.deepcopy(P)
    for st, north in (('SW', False), ('NW', True)):
        # PHY + PC row: PC3 | PC4 split on the centre line
        pcs = [P[f'pc_{st}{i}'] for i in range(8)]
        split = (pcs[3]['x'] + pcs[3]['w'] + pcs[4]['x']) / 2
        d = round(CX - split, 3)
        for n in [f'phy_{st}'] + [f'pc_{st}{i}' for i in range(8)]:
            P[n]['x'] = round(P[n]['x'] + d, 3)
        # SM row: W quadrant SMs 0-3 (+ XQL pair stores p0, p1) packed against the centre channel, E mirrored
        right = P[f'sm_{st}3']['x'] + P[f'sm_{st}3']['w']
        dw = round(CX - channel / 2 - right, 3)
        for i in range(8):
            P[f'sm_{st}{i}']['x'] = round(P[f'sm_{st}{i}']['x'] + (dw if i < 4 else -dw), 3)
        for p in range(4):
            for k in ('eg', 'bd', 'bfq0', 'bfq1', 'bfq2', 'bfq3'):
                n = f'xq_{st}_p{p}_{k}'
                P[n]['x'] = round(P[n]['x'] + (dw if p < 2 else -dw), 3)
        # IDX scorer quarters out of the SM row
        qW, qE = ('SW', 'SE') if not north else ('NW', 'NE')
        if idx == 'band':
            vW, vE = P[f'vmh_{qW}'], P[f'vmh_{qE}']
            gx0, gx1 = vW['x'] + vW['w'] + 40, vE['x'] - 40
            w = gx1 - gx0; h = round(1795.0 * 2590.0 / w, 2)
            band0 = S.BAND_Y if not north else H - S.BAND_Y - 2 * S.SU_H - S.ROWGAP
            ys = [band0 + 20, band0 + 20 + h + 60]
            if north:
                ys = ys[::-1]
            for q, y in zip((qW, qE), ys):
                P[f'idxs_{q}'] = S.rect(gx0, y, w, h)
        elif idx == 'phy':
            # beside the PHY, in the corner below the SM row: directly next to the PC row that feeds the scorer
            phy = P[f'phy_{st}']; sm0 = P[f'sm_{st}0']
            h = round((sm0['y'] - 60.0 - 21.6) if not north else (H - (sm0['y'] + sm0['h']) - 60.0 - 21.6), 2)
            w = round(1795.0 * 2590.0 / h, 2)
            y = 21.6 if not north else H - 21.6 - h
            P[f'idxs_{qW}'] = S.rect(phy['x'] - 60.0 - w, y, w, h)
            pcr = max(P[f'pc_{st}{i}']['x'] + P[f'pc_{st}{i}']['w'] for i in range(8))   # the PC row overhangs the PHY on E
            P[f'idxs_{qE}'] = S.rect(max(phy['x'] + phy['w'], pcr) + 60.0, y, w, h)
        else:
            sm0, sm7 = P[f'sm_{st}0'], P[f'sm_{st}7']
            w = sm0['x'] - S.EDGE - 40
            h = round(1795.0 * 2590.0 / w, 2)
            y = sm0['y'] + (sm0['h'] - h) / 2
            P[f'idxs_{qW}'] = S.rect(S.EDGE, y, w, h)
            P[f'idxs_{qE}'] = S.rect(S.W_DIE - S.EDGE - w, y, w, h)
        # PHY-side config leaf: in the centre lane channel at the top of the SM row (plan (b) height), next to the
        # quadrant core and the host tree, over the PC row of its stack
        for q, sgn in ((qW, -1), (qE, 1)):
            r = P[f'pleaf_{q}']
            ly = r['y'] + (-sm_dh if north else sm_dh)          # keeps its distance to the SM row's inner edge
            P[f'pleaf_{q}'] = S.rect(CX - r['w'] if sgn < 0 else CX, ly, r['w'], r['h'])
    return P, H


def host_block(P, cx, cy):
    hs = [b for b, r in P.items() if r['x'] <= cx <= r['x'] + r['w'] and r['y'] <= cy <= r['y'] + r['h']]
    if hs:
        return min(hs, key=lambda b: P[b]['w'] * P[b]['h'])
    return min(P, key=lambda b: max(P[b]['x'] - cx, 0, cx - P[b]['x'] - P[b]['w']) + max(P[b]['y'] - cy, 0, cy - P[b]['y'] - P[b]['h']))


def bundle_metrics(buses, pos, P):
    """lever 2: buses sharing (driver block, sink blocks, domain) share one lane bundle at fixed station rows"""
    blk = {}

    def bk(n):
        if n not in blk:
            r = pos[n]; blk[n] = host_block(P, r['x'] + r['w'] / 2, r['y'] + r['h'] / 2)
        return blk[n]
    groups = collections.defaultdict(list)
    for b in buses:
        if b['driver'] not in pos:
            continue
        rs = [x for x in b['sinks'] if x in pos]
        if not rs:
            continue
        key = (bk(b['driver']), tuple(sorted({bk(x) for x in rs})), b['domain'], bool(b.get('cfg')))
        groups[key].append(b)
    tiles = rows_ = land = 0
    per_lw = collections.Counter()
    biggest = []
    for key, L in groups.items():
        bits = sum(b['bits'] for b in L)
        fork = len(key[1]) > 1 or any(len(b['sinks']) > 1 for b in L)
        lw = 136 if fork else 624
        lanes = math.ceil(bits / lw)
        st = 0
        for b in L:
            rs = [pos[x] for x in b['sinks'] if x in pos]
            cen = (sum(S.centre(r)[0] for r in rs) / len(rs), sum(S.centre(r)[1] for r in rs) / len(rs))
            d = S.gapxy(pos[b['driver']], cen)
            pts = [S.gapxy(r, d) for r in rs]
            tree = S.mst_len(d, pts) if len(pts) > 1 else S.manh(d, pts[0])
            st = max(st, math.ceil(tree / S.SPACING) if tree > S.REACH else 0)
        if st == 0:
            continue
        tiles += lanes * st; rows_ += st; per_lw[lw] += lanes * st
        land += lanes * len(key[1])
        biggest.append((lanes * st, key[0], key[1][:4], key[2], len(L), bits, lanes, st))
    return dict(bundles=len(groups), relay_tiles=tiles, station_rows=rows_, landing_tiles=land,
                tiles_by_lane_width=dict(per_lw), biggest=sorted(biggest, reverse=True)[:12])


def sm_hbm_offsets(P):
    out = {}
    for st in ('SW', 'NW'):
        for i in range(8):
            s, p = P[f'sm_{st}{i}'], P[f'pc_{st}{i}']
            out[f'{st}{i}'] = round(abs((s['x'] + s['w'] / 2) - (p['x'] + p['w'] / 2)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rows', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--channel', type=float, default=400.0)
    ap.add_argument('--sm-dh', type=float, default=0.0,
                    help='SMFRAME (HANDOFF 0gd): SM column slot height growth in um (4 rp4 tile rows x 69.12 = 276.48)')
    ap.add_argument('--only', default='', help='comma list of plans to write (default all); geometry + graph eval only when '
                    'the bus rows / manifest are absent (the run8 manifest was deleted 10-17)')
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    PA = sm_frame(json.loads((S.A_DIR / 'compact.P.json').read_text()), a.sm_dh)
    GA = json.loads((S.A_DIR / 'compact.graph.json').read_text())
    for n, v in GA['nodes'].items():
        if n.startswith('sm_') and a.sm_dh:
            v['h'] = round(v['h'] + a.sm_dh, 3); v['area_mm2'] = round(v['w'] * v['h'] / 1e6, 4)
            v['provenance'] = v.get('provenance', '') + f' | SMFRAME 10-18: +{a.sm_dh:g} um (rp4 tile 1598.4 = 37 x 43.2)'
    PB, HB = S.plan_b(PA, side='inner')
    plans = {'b': PB, 'd4g_band': plan_d4g(PA, a.channel, 'band', a.sm_dh)[0], 'd4g_corner': plan_d4g(PA, a.channel, 'corner', a.sm_dh)[0],
             'd4g_phy': plan_d4g(PA, a.channel, 'phy', a.sm_dh)[0]}
    if a.only:
        plans = {k: v for k, v in plans.items() if k in a.only.split(',')}
    if not (Path(a.rows).is_file() and Path(a.manifest).is_file()):
        res = {}
        for t, P in plans.items():
            ev = S.write_plan(out / t, P, S.graph_b(GA), HB, t)
            cut = ev['cut_phy_unmasked']
            res[t] = dict(die_um=[S.W_DIE, round(HB, 2)], die_mm2=ev['die_mm2'], cut_v=cut['worst_v']['ratio'],
                          cut_h=cut['worst_h']['ratio'], graph_bit_mm=ev['sum_bits_mm'], stages_bw=ev['stages_bw'],
                          per_class_stages={k: v['stages_bw'] for k, v in ev['per_class'].items()},
                          longest_class_um=ev['by_class_longest_um'], overlaps=ev['overlaps'], outside=ev['outside'],
                          sm_hbm_offset_um=sm_hbm_offsets(P), sm_dh_um=a.sm_dh)
            print(t, json.dumps({k: res[t][k] for k in ('die_um', 'die_mm2', 'cut_v', 'cut_h', 'graph_bit_mm', 'stages_bw', 'overlaps', 'outside')}), flush=True)
        (out / 'plan_geometry.json').write_text(json.dumps(res, indent=1, default=list))
        if 'd4g_phy' in plans:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import plan_study_draw_1017 as Dr
            fig2, ax2 = plt.subplots(figsize=(6, 8.4), dpi=260)
            P = plans['d4g_phy']
            Dr.draw(ax2, P, S.graph_b(GA), S.W_DIE, HB, f'HBM die d4g plan, SM frame +{a.sm_dh:g} um ({S.W_DIE / 1000:.2f} x {HB / 1000:.2f} mm)',
                    Dr.quad_boxes(P, S.W_DIE, S.QS))
            fig2.tight_layout(); fig2.savefig(out / 'd4g_plan.png'); plt.close(fig2)
        return res
    rows = json.loads(Path(a.rows).read_text())['rows']
    for r in rows:
        r['cls'] = 'cfg_no_pad' if r['driver'].startswith('host_cp') and r['domain'] == 'serial' else r['cls']
    inst = {k: v for k, v in json.loads(Path(a.manifest).read_text())['placement'].items()
            if not v['m'].startswith(('hbfd_rly', 'hfd_stn'))}
    S.KNOWN.update(inst)
    host = S.a_hosts(PA, inst)
    res = {}
    for t, P in plans.items():
        ev = S.write_plan(out / t, P, S.graph_b(GA), HB, t)
        S.NEW_REPLICAS.clear()
        bl = S.rewire(rows, S.QS)
        pos = S.positions('b', P, PA, inst, host, S.QS)
        bm = S.bus_metrics(bl, pos, (S.W_DIE, HB, math.ceil(S.W_DIE / 4000), math.ceil(HB / 4000)))
        bm['relay_tiles_calibrated'] = int(round(bm['tiles'] * 1.376))
        bm.pop('deep', None)
        lever2 = bundle_metrics(bl, pos, P)
        cut = ev['cut_phy_unmasked']
        res[t] = dict(die_um=[S.W_DIE, round(HB, 2)], die_mm2=ev['die_mm2'], cut_v=cut['worst_v']['ratio'], cut_h=cut['worst_h']['ratio'],
                      graph_bit_mm=ev['sum_bits_mm'], stages_bw=ev['stages_bw'],
                      per_class_stages={k: v['stages_bw'] for k, v in ev['per_class'].items()},
                      longest_class_um=ev['by_class_longest_um'], overlaps=ev['overlaps'], outside=ev['outside'],
                      sm_hbm_offset_um=sm_hbm_offsets(P), bus=bm, lever2=lever2)
        print(t, 'cut', res[t]['cut_v'], res[t]['cut_h'], 'bitmm', ev['sum_bits_mm'], 'stages_bw', ev['stages_bw'],
              'SM_HBM', res[t]['per_class_stages'].get('SM_HBM'), 'HBM_VM', res[t]['per_class_stages'].get('HBM_VM'),
              'offs', sum(res[t]['sm_hbm_offset_um'].values()), '| bus tiles', bm['tiles'], 'bitmm', bm['bit_mm'], 'depth',
              bm['equal_age_depth'], 'longest', bm['longest'], '| L2 tiles', lever2['relay_tiles'], 'rows', lever2['station_rows'],
              'landing', lever2['landing_tiles'], 'overlaps', ev['overlaps'], flush=True)
    (out / 'd4g_vs_b.json').write_text(json.dumps(res, indent=1, default=list))
    draw(out, plans, res, S.graph_b(GA), HB, a.channel)


def draw(out, plans, res, G, H, channel):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import plan_study_draw_1017 as Dr
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 8.4), dpi=230)
    for ax, (k, name) in zip(axs, (('b', '(b) plan_b_inner (H-PLANSTUDY)'), ('d4g_phy', 'd4g = (b) + lever 1 (channel-aligned SMs, IDX beside PHY)'))):
        r = res[k]; b = r['bus']; L2 = r['lever2']; dep = b['equal_age_depth']
        t = (f"{name}\n{S.W_DIE / 1000:.2f} x {H / 1000:.2f} mm; cut {r['cut_v']:.2f}/{r['cut_h']:.2f}; graph bit-mm {r['graph_bit_mm'] / 1e6:.2f} M; "
             f"SM_HBM {r['per_class_stages']['SM_HBM']} st\nbus bit-mm {b['bit_mm'] / 1e6:.2f} M; relay tiles {b['tiles'] / 1000:.1f} k -> "
             f"lever 2 {L2['relay_tiles'] / 1000:.1f} k in {L2['station_rows'] / 1000:.1f} k rows; longest {b['longest'][0] / 1000:.1f} mm; "
             f"depth {dep.get('stream')}/{dep.get('hbm')}/{dep.get('serial')}")
        P = plans[k]
        Dr.draw(ax, P, G, S.W_DIE, H, t, Dr.quad_boxes(P, S.W_DIE, S.QS))
        if k != 'b':
            ax.add_patch(Rectangle(((CX - channel / 2) / 1000, 1.9), channel / 1000, H / 1000 - 3.8, fc='#ffeda0', ec='none', alpha=0.5, zorder=0))
            ax.text(CX / 1000, H / 2000 + 3, 'centre lane channel\n(PC3|PC4 line)', fontsize=4, ha='center', rotation=90)
    fig.suptitle('H-D4G 10-17: HBM die d4g plan vs plan (b) (same model, run8 bus rows; lines = plan-graph links)', fontsize=8)
    fig.tight_layout(); fig.savefig(out / 'd4g_vs_b.png'); plt.close(fig)
    fig2, ax2 = plt.subplots(figsize=(6, 8.4), dpi=260)
    Dr.draw(ax2, plans['d4g_phy'], G, S.W_DIE, H, 'HBM die d4g plan (H-D4G 10-17)', Dr.quad_boxes(plans['d4g_phy'], S.W_DIE, S.QS))
    fig2.tight_layout(); fig2.savefig(out / 'd4g_plan.png'); plt.close(fig2)


if __name__ == '__main__':
    main()
