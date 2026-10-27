#!/usr/bin/env python3
"""HEAD-R21 candidate: one PHY-band mesh row per die edge instead of extending every mesh column.

The die mesh (217 straps) ends at the two serdes_row M8 conductors (y 1251.74 / 16302.62).  The 12
hd_serdes tiles publish a 8x4 clock-tap grid each; their two outer tap rows (192 taps) sit 688..997 um
from the mesh, beyond the 450-um reach.  Instead of extending all 95 M9 columns through the PHY band
(COPY 0c7b31b74: +221 mm wire / +32.8 pF), this adds per edge:
  * one continuous M8 row in the PHY-band M8 PG gap nearest the midpoint of the two outer tap rows;
  * M9 risers from the serdes_row down to that row, two per serdes tile, each in a PHY M9 PG gap,
    with a real M8 bridge in the core/PHY PG domain transition gap when the core-legal and PHY-legal
    M9 tracks differ (same mechanism as head_pg_flank_mesh.py).
No buffers, stages, FFs or cycles are added; the mesh drivers are unchanged.  Clock/PG clearance is
the 1.0-um wide-PG rule, never relaxed.  In the PHY band the 8w conductor sits between actual
VDDPHY/VSS rails (PG-flanked, no drawn shield fits in the 2.40-um gap); that is reported per segment.
Outputs straps.json (mesh COPY), receipt.json, render PNGs.
"""
import argparse, json, sys, math
from pathlib import Path


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--tools', required=True); a.add_argument('--plan', required=True)
    a.add_argument('--straps', required=True); a.add_argument('--endpoints', required=True)
    a.add_argument('--out', required=True); a.add_argument('--risers-per-tile', type=int, default=2)
    x = a.parse_args(); sys.path.insert(0, x.tools)
    import schema as S, die_infra as DI, die_clock as DC, die_clock_mesh as D, explicit_clock_mesh as E
    p = S.Plan(S.load(x.plan)); ss = json.loads(Path(x.straps).read_text())
    ep = json.loads(Path(x.endpoints).read_text())['endpoints']
    o = Path(x.out); o.mkdir(parents=True, exist_ok=True)
    pg = DI.pg_rects(p, DI.pg_grid(p, None))
    nd = D.NDR['8w']; half = nd['width'] / 2; gap = 1.0; REACH = 450.0
    doms = [d for d in p.die['pg']['domains'] if d.get('name', '').startswith('phy_')]

    def dist(pt, z):
        px, py = pt
        if z[0] == 'M8': return abs(py - z[1]) + max(0, z[2] - px, px - z[3])
        return abs(px - z[1]) + max(0, z[2] - py, py - z[3])

    def clear(l, c, aa, bb):
        for n, lay, x0, y0, x1, y1 in pg:
            if lay != l: continue
            q0, q1, a0, a1 = (x0, x1, y0, y1) if l == 'M9' else (y0, y1, x0, x1)
            if min(bb, a1) - max(aa, a0) > 1e-6 and max(q0 - (c + half), (c - half) - q1) < gap - 1e-6:
                return False
        return True

    def cands(ideal, lim):
        k = round((ideal - .04) / .08); n = int(lim / .08)
        return sorted((round(.04 + .08 * j, 4) for j in range(k - n, k + n + 1)), key=lambda t: (abs(t - ideal), t))

    far = [e for e in ep if min(dist(e['die_xy_um'], z) for z in ss) > REACH]
    errors = []; new = []; bridges = []; rows = []
    for edge in ('bottom', 'top'):
        fe = [e for e in far if (e['die_xy_um'][1] < 8778) == (edge == 'bottom')]
        if not fe: continue
        band = [d['rect_um'] for d in doms if (d['rect_um'][1] < 8778) == (edge == 'bottom')]
        blo, bhi = min(r[1] for r in band), max(r[3] for r in band)
        sr = [z for z in ss if z[0] == 'M8' and z[4] == 'serdes_row' and ((z[1] < 8778) == (edge == 'bottom'))]
        assert len(sr) == 1, sr; sry = sr[0][1]
        ys = sorted({e['die_xy_um'][1] for e in fe}); ideal = (ys[0] + ys[-1]) / 2
        xs = [e['die_xy_um'][0] for e in fe]; x0, x1 = min(xs), max(xs)
        ry = next((v for v in cands(ideal, 20) if clear('M8', v, x0, x1)), None)
        if ry is None: errors.append(dict(kind='no_phy_M8_row', edge=edge, ideal=ideal)); continue
        new.append(['M8', ry, x0, x1, 'phy_band_row']); rows.append(dict(edge=edge, y=ry, x0=x0, x1=x1, ideal=ideal))
        # PHY/core PG transition gap (between the PHY rect edge and the first core M8 rail)
        tedge = bhi if edge == 'bottom' else blo
        by = next((v for v in cands(tedge, 6.0) if clear('M8', v, x0 - 20, x1 + 20)), None)
        if by is None: errors.append(dict(kind='no_transition_M8', edge=edge)); continue
        # riser ideals: per serdes tile, evenly inside its tap span
        tiles = {}
        for e in fe: tiles.setdefault(e['part'], []).append(e['die_xy_um'][0])
        for part, txs in sorted(tiles.items()):
            lo, hi = min(txs), max(txs); k = x.risers_per_tile
            for i in range(k):
                ix = lo + (hi - lo) * (i + .5) / k
                ya, yb = sorted([ry, by]); yc, yd = sorted([by, sry])
                px = next((v for v in cands(ix, 12) if clear('M9', v, ya, yb)), None)
                if px is None: errors.append(dict(kind='no_phy_M9', part=part, x=ix)); continue
                cx = next((v for v in cands(px, 12) if clear('M9', v, yc, yd)), None)
                if cx is None: errors.append(dict(kind='no_core_M9', part=part, x=ix)); continue
                if abs(cx - px) < 1e-6:
                    new.append(['M9', px, min(ya, yc), max(yb, yd), 'phy_band_riser'])
                else:
                    new.append(['M9', px, ya, yb, 'phy_band_riser'])
                    new.append(['M9', cx, yc, yd, 'phy_band_riser'])
                    bx0, bx1 = sorted([px, cx])
                    if not clear('M8', by, bx0 - half, bx1 + half): errors.append(dict(kind='bridge_PG', part=part, y=by))
                    new.append(['M8', by, bx0, bx1, 'pg_phase_bridge'])
                    bridges.append(dict(part=part, y=by, phy_x=px, core_x=cx, dx=round(cx - px, 4)))
    # Full re-check of every new conductor against actual PG (no relaxation)
    for l, c, aa, bb, *_ in new:
        if not clear(l, c, aa, bb): errors.append(dict(kind='new_segment_PG_clearance', segment=[l, c, aa, bb]))
    allc = ss + new
    # Same-layer clock/clock spacing among new and existing mesh conductors (8w + 1.0 um conservative)
    for i, z in enumerate(new):
        for w in allc:
            if w is z or w[0] != z[0]: continue
            if min(z[3], w[3]) - max(z[2], w[2]) > 1e-6 and 1e-6 < abs(z[1] - w[1]) < nd['width'] + gap:
                errors.append(dict(kind='clock_clock_spacing', a=z[:4], b=w[:4]))
    mesh = dict(M8=[dict(y=z[1], x0=z[2], x1=z[3]) for z in allc if z[0] == 'M8'],
                M9=[dict(x=z[1], y0=z[2], y1=z[3]) for z in allc if z[0] == 'M9'], drivers=[], taps=[])
    mesh['vias'] = [dict(x=v['x'], y=h['y']) for h in mesh['M8'] for v in mesh['M9']
                    if h['x0'] - 1e-6 <= v['x'] <= h['x1'] + 1e-6 and v['y0'] - 1e-6 <= h['y'] <= v['y1'] + 1e-6]
    graph = E.conductor_graph(mesh)
    newvias = [dict(x=v['x'], y=h['y']) for h in [dict(y=z[1], x0=z[2], x1=z[3]) for z in allc if z[0] == 'M8']
               for v in [dict(x=z[1], y0=z[2], y1=z[3]) for z in allc if z[0] == 'M9']
               if h['x0'] - 1e-6 <= v['x'] <= h['x1'] + 1e-6 and v['y0'] - 1e-6 <= h['y'] <= v['y1'] + 1e-6]
    # Reach census on the COPY mesh, every endpoint
    reach = [min(dist(e['die_xy_um'], z) for z in allc) for e in ep]
    over = [(e['part'], e['die_xy_um'], round(r, 2)) for e, r in zip(ep, reach) if r > REACH]
    wire = {l: sum(z[3] - z[2] for z in new if z[0] == l) for l in ('M8', 'M9')}
    cap = sum((z[3] - z[2]) * DC.LAYER_RC[z[0]][1] * nd['cf'] for z in new)
    # PG-flank record for PHY-band segments (no drawn shield fits the 2.40-um PHY gap)
    flank = []
    for l, c, aa, bb, kind in new:
        if kind == 'pg_phase_bridge': continue
        sh = [z for z in pg if z[1] == l]
        co = (lambda z: (z[2], z[4], z[3], z[5])) if l == 'M9' else (lambda z: (z[3], z[5], z[2], z[4]))
        side = {}
        for z in sh:
            q = co(z)
            if min(bb, q[3]) - max(aa, q[2]) <= 1e-6: continue
            if q[1] <= c: g = c - half - q[1]; s = 'low'
            elif q[0] >= c: g = q[0] - c - half; s = 'high'
            else: continue
            if s not in side or g < side[s][0]: side[s] = (g, z[0], [max(aa, q[2]), min(bb, q[3])])
        flank.append(dict(segment=[l, c, aa, bb], kind=kind, flanks={k: dict(gap_um=round(v[0], 3), net=v[1], span=v[2]) for k, v in side.items()}))
    # Elmore estimate (UNCHECKED; RCX owed): worst tap from serdes_row node through a riser and the row
    r8, c8 = DC.LAYER_RC['M8'][0] * nd['rf'] * 1e3, DC.LAYER_RC['M8'][1] * nd['cf']  # ohm/um, fF/um
    r9, c9 = DC.LAYER_RC['M9'][0] * nd['rf'] * 1e3, DC.LAYER_RC['M9'][1] * nd['cf']
    est = []
    for rw in rows:
        rs = sorted(z[1] for z in new if z[4] == 'phy_band_riser' and min(abs(z[2] - rw['y']), abs(z[3] - rw['y'])) < 1e-6)
        L1 = abs(next(z for z in ss if z[0] == 'M8' and z[4] == 'serdes_row' and (z[1] < 8778) == (rw['edge'] == 'bottom'))[1] - rw['y'])
        seg = max([rs[0] - rw['x0'], rw['x1'] - rs[-1]] + [(b - a) / 2 for a, b in zip(rs, rs[1:])])
        share = (rw['x1'] - rw['x0']) / len(rs)
        tap_ff = 16 * 2.0  # ASSUMED 2 fF per tap pin (tile Cin not published)
        Cr = c8 * share + tap_ff * len([1 for _ in range(1)])
        t = r9 * L1 * (c9 * L1 / 2 + Cr) + r8 * seg * (c8 * seg / 2 + tap_ff / 2)
        est.append(dict(edge=rw['edge'], riser_um=round(L1, 2), risers=len(rs), worst_row_seg_um=round(seg, 2), elmore_ps_unchecked=round(t * 1e-3, 2)))
    receipt = dict(status='FAIL' if errors or over else 'PASS_PLAN_GEOMETRY', errors=errors[:50], n_errors=len(errors),
                   endpoints=len(ep), far_before=len(far), over_reach_after=len(over), over=over[:20],
                   max_reach_after_um=round(max(reach), 3), rows=rows, risers=sum(1 for z in new if z[4] == 'phy_band_riser'),
                   bridges=len(bridges), bridge_list=bridges, new_wire_um=wire, new_wire_total_um=round(sum(wire.values()), 2),
                   added_wire_cap_ff=round(cap, 1), added_clock_dynamic_w_0p7v_833ps=round(cap * 1e-15 * .49 / 833e-12, 5),
                   vs_copy_0c7b31b74=dict(added_signal_um=220974.18, added_cap_ff=32832.2),
                   mesh_straps=len(allc), mesh_vias=len(mesh['vias']), components=graph['connected_components'],
                   pg_flank_min_gap_um=round(min(min(v['gap_um'] for v in f['flanks'].values()) for f in flank if f['flanks']), 3) if flank else None,
                   pg_flank_segments=flank, elmore=est,
                   scope='Plan-geometry COPY only: actual PG rects (die_infra.pg_rects on the plan), 1.0-um PG clearance unrelaxed, reach census on all endpoints. '
                         'OPEN: PHY macro upper-metal abstract permission, PG-flank (no drawn VSS) acceptance in PHY band, encoder/RCX/GRT/STA.')
    (o / 'straps.json').write_text(json.dumps(allc, indent=1) + '\n')
    (o / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        for name, box in [('overview', (0, 0, p.die['W'] if 'W' in p.die else 17521.92, 17556.48)),
                          ('zoom_ES0', (11500, 0, 14700, 1400)), ('zoom_riser_ES0', None)]:
            if box is None:
                b0 = next((b for b in bridges if b['part'] == 'lk_ES0'), None)
                if not b0: continue
                box = (b0['phy_x'] - 30, b0['y'] - 25, b0['phy_x'] + 30, b0['y'] + 25)
            fig, ax = plt.subplots(figsize=(14, 6 if name != 'overview' else 14), dpi=110)
            X0, Y0, X1, Y1 = box
            if name != 'overview':
                for n, l, a0, b0_, a1, b1 in pg:
                    if a1 < X0 or a0 > X1 or b1 < Y0 or b0_ > Y1: continue
                    col = {'VDDPHY': '#d9a', 'VSS': '#9ab', 'VDD': '#da9'}.get(n, '#ccc')
                    ax.add_patch(plt.Rectangle((a0, b0_), a1 - a0, b1 - b0_, color=col, alpha=.35 if l == 'M9' else .2, lw=0))
            for z in allc:
                isnew = z in new; col = 'red' if isnew else 'k'; w = (1.6 if isnew else .6)
                if z[0] == 'M8': ax.plot([z[2], z[3]], [z[1], z[1]], color=col, lw=w)
                else: ax.plot([z[1], z[1]], [z[2], z[3]], color=col, lw=w)
            tx = [e['die_xy_um'] for e in ep]
            okk = [t for t, r in zip(tx, reach) if r <= REACH]
            ax.scatter([t[0] for t in okk], [t[1] for t in okk], s=6, c='g', zorder=5)
            bad = [o_[1] for o_ in over]
            if bad: ax.scatter([t[0] for t in bad], [t[1] for t in bad], s=14, c='m', marker='x', zorder=6)
            ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal' if name != 'zoom_ES0' else 'auto')
            ax.set_title(f'HEAD-R21 PHY-band mesh rows {name}: black=existing mesh, red=new, green=taps<=450, magenta x=over reach; shaded=PG rails')
            fig.savefig(o / f'{name}.png', bbox_inches='tight'); plt.close(fig)
    except Exception as ex:
        receipt['render_error'] = repr(ex); (o / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('pg_flank_segments', 'bridge_list', 'errors')}, indent=1))
    return 0 if receipt['status'].startswith('PASS') else 2


if __name__ == '__main__':
    sys.exit(main())
