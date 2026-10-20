#!/usr/bin/env python3
"""HBM-DIE11 10-20: station-bearing ESCAPE CHANNELS inside the HC hub clusters (hce_NE/NW/SE/SW).

Why (r10 + Codex die11 freechannel evidence): each hce_* plan block is a 3 x 3 abutted grid of 734.4 um tiles -- the
hub hc_* in the centre, its eight banks hcb_*0..7 around it with ZERO gaps.  Every hc_* pin therefore faces a bank
macro and the nearest legal relay cell is one bank away (~750 um): 32 hc source rows + ~10 hleaf->hc sink rows can
never meet the 405 um reach, whatever the planner does (reach_endpoint_probe: 40 endpoints > 405, HC ~750 um).

Fix (geometry only, no outline / pin / orientation change, reach 405 unchanged): open a channel of GAP um between the
grid columns and rows of each named cluster.  The cluster grows by 2*GAP in x (symmetric about its centre) and by
2*GAP in y AWAY from its anchored face (the face that abuts vmh_*: top for the N clusters, bottom for the S ones).
Each tile moves rigidly by (col-1)*GAP, (row-r0)*GAP.  The '#'-shaped channel grid touches every hc face and runs to
the cluster edge, so stations sit next to the hub pins.  GAP is a multiple of the 43.2 um macro lattice.

    d4g_cluster_spread.py --plan-dir IN --out OUT --gap 172.8 --cluster hce_NE:top --cluster hce_SE:bottom ...
copies IN/{grants_d4g.json, compact.P.json, lanes.json, d4g_region_map.json, coord_map.json} to OUT with the cluster
tiles, plan blocks and region sites moved; refuses on any NEW overlap (slots, plan blocks, slot vs foreign plan block)
or reticle failure; writes OUT/spread_report.json and OUT/spread.png (zoom on the clusters).
"""
import argparse, copy, json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d4g_channel_cuts import overlaps, wh  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--gap', type=float, default=172.8, help='x channel width (and y unless --gap-y)')
    ap.add_argument('--gap-y', type=float, default=None, help='y channel width (the die height is reticle-bound)')
    ap.add_argument('--shift', action='append', default=[],
                    help='x0:x1:y0:y1:dx:dy[:EXCL,..] rigid shift of every slot / plan block / region site whose CENTRE lies in the '
                         'box (ORIGINAL coordinates; cluster tiles excluded) -- makes room for the grown clusters')
    ap.add_argument('--move', action='append', default=[], help='NAME:dx:dy rigid move of one slot (and its same-name plan block)')
    ap.add_argument('--cluster', action='append', required=True, help='PLANBLOCK:top|bottom (anchored face)')
    ap.add_argument('--grid', type=int, default=3)
    a = ap.parse_args()
    gy = a.gap if a.gap_y is None else a.gap_y
    for v in (a.gap, gy):
        if abs(v / 43.2 - round(v / 43.2)) > 1e-6:
            raise SystemExit('CLUSTER_SPREAD: gaps must be multiples of the 43.2 um lattice')
    src, out = Path(a.plan_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    G = json.load(open(src / 'grants_d4g.json')); P = json.load(open(src / 'compact.P.json'))
    RM = json.load(open(src / 'd4g_region_map.json')); L = json.load(open(src / 'lanes.json'))
    G2, P2, RM2 = copy.deepcopy(G), copy.deepcopy(P), copy.deepcopy(RM)
    n, g = a.grid, a.gap
    rep = dict(schema='opentallas.hbm.d4g_cluster_spread.v1', gap_um=g, gap_y_um=gy, clusters={}, from_plan=str(src),
               shifts=a.shift, moves=a.move)
    cl = []
    for spec in a.cluster:
        name, anchor = spec.split(':')
        b = P[name]; cl.append((name, anchor, dict(b)))
        nb = P2[name]
        nb['x'] = round(b['x'] - g * (n - 1) / 2, 3); nb['w'] = round(b['w'] + g * (n - 1), 3)
        nb['h'] = round(b['h'] + gy * (n - 1), 3)
        nb['y'] = round(b['y'] - (gy * (n - 1) if anchor == 'top' else 0.0), 3)
        rep['clusters'][name] = dict(anchor=anchor, before=b, after=dict(nb), tiles={})

    def cell_shift(name, anchor, b, px, py):
        col = min(n - 1, max(0, int((px - b['x']) / (b['w'] / n))))
        row = min(n - 1, max(0, int((py - b['y']) / (b['h'] / n))))
        dx = (col - (n - 1) / 2) * g
        dy = (row - (n - 1)) * gy if anchor == 'top' else row * gy
        return dx, dy

    def owner(px, py):
        for name, anchor, b in cl:
            if b['x'] <= px <= b['x'] + b['w'] and b['y'] <= py <= b['y'] + b['h']:
                return name, anchor, b
        return None

    for s in G2['slots']:
        if s.get('kind') == 'die':
            continue
        w, h = wh(s); cx, cy = s['origin']['x'] + w / 2, s['origin']['y'] + h / 2
        o = owner(cx, cy)
        if not o:
            continue
        b = o[2]
        if not (b['x'] - 0.01 <= s['origin']['x'] and s['origin']['x'] + w <= b['x'] + b['w'] + 0.01
                and b['y'] - 0.01 <= s['origin']['y'] and s['origin']['y'] + h <= b['y'] + b['h'] + 0.01):
            raise SystemExit(f"CLUSTER_SPREAD: slot {s['name']} straddles cluster {o[0]}")
        dx, dy = cell_shift(*o, cx, cy)
        s['origin']['x'] = round(s['origin']['x'] + dx, 3); s['origin']['y'] = round(s['origin']['y'] + dy, 3)
        rep['clusters'][o[0]]['tiles'][s['name']] = [dx, dy]
    for k, b in P2.items():   # plan blocks nested inside a cluster (other than the cluster itself) move with their cell
        if not (isinstance(b, dict) and 'x' in b) or k in rep['clusters']:
            continue
        o = owner(P[k]['x'] + P[k]['w'] / 2, P[k]['y'] + P[k]['h'] / 2)
        if o:
            dx, dy = cell_shift(*o, P[k]['x'] + P[k]['w'] / 2, P[k]['y'] + P[k]['h'] / 2)
            b['x'] = round(P[k]['x'] + dx, 3); b['y'] = round(P[k]['y'] + dy, 3)
            rep['clusters'][o[0]]['tiles']['P:' + k] = [dx, dy]
    # room for the grown clusters: rigid box shifts / single moves (selection on ORIGINAL centres; cluster tiles excluded)
    ctiles = {t for c in rep['clusters'].values() for t in c['tiles']}
    boxes = []
    for sp in a.shift:
        f = sp.split(':')
        boxes.append(tuple(float(v) for v in f[:6]) + (set(f[6].split(',')) if len(f) > 6 and f[6] else set(),))
    moves = {m.split(':')[0]: (float(m.split(':')[1]), float(m.split(':')[2])) for m in a.move}

    def box_d(name, cx, cy):
        if name in moves:
            return moves[name]
        for x0, x1, y0, y1, dx, dy, ex in boxes:
            if name not in ex and x0 <= cx <= x1 and y0 <= cy <= y1:
                return dx, dy
        return None
    rep['shifted'] = {}
    for s0, s in zip(G['slots'], G2['slots']):
        if s.get('kind') == 'die' or s['name'] in ctiles:
            continue
        w, h = wh(s0); d = box_d(s['name'], s0['origin']['x'] + w / 2, s0['origin']['y'] + h / 2)
        if d:
            s['origin']['x'] = round(s0['origin']['x'] + d[0], 3); s['origin']['y'] = round(s0['origin']['y'] + d[1], 3)
            rep['shifted'][s['name']] = d
    for k, b in P2.items():
        if not (isinstance(b, dict) and 'x' in b) or k in rep['clusters'] or ('P:' + k) in ctiles:
            continue
        d = box_d(k, P[k]['x'] + P[k]['w'] / 2, P[k]['y'] + P[k]['h'] / 2)
        if d:
            b['x'] = round(P[k]['x'] + d[0], 3); b['y'] = round(P[k]['y'] + d[1], 3); rep['shifted']['P:' + k] = d
    moved_sites = 0
    for d in (RM2.get('instances', {}), RM2.get('regions', {})):
        for k, v in d.items():
            if isinstance(v, dict) and 'site' in v:
                o = owner(*v['site'])
                d = None if o else box_d(k, *v['site'])
                if d:
                    v['site'] = [round(v['site'][0] + d[0], 1), round(v['site'][1] + d[1], 1)]; moved_sites += 1
                if o:
                    dx, dy = cell_shift(*o, *v['site'])
                    v['site'] = [round(v['site'][0] + dx, 1), round(v['site'][1] + dy, 1)]; moved_sites += 1
    rep['region_sites_moved'] = moved_sites
    RM2['plan'] = str(out / 'compact.P.json')
    lanes_inside = [k for k, ln in L.items() if isinstance(ln, dict) and any(
        ('v' in ln and b['x'] < ln['v'] < b['x'] + b['w']) or ('h' in ln and b['y'] < ln['h'] < b['y'] + b['h'])
        for _, _, b in cl)]
    rep['lanes_crossing_clusters'] = lanes_inside   # lanes are die-wide rails; reported, not moved

    def prs(PP):
        return [('P:' + k, b['x'], b['y'], b['w'], b['h']) for k, b in PP.items() if isinstance(b, dict) and 'x' in b]

    def srs(GG):
        return [(s['name'], s['origin']['x'], s['origin']['y']) + wh(s) for s in GG['slots'] if s.get('kind') != 'die']
    new_ov = {}
    for tag, before, after in (('plan', prs(P), prs(P2)), ('slots', srs(G), srs(G2)),
                               ('slot_vs_plan', prs(P) + srs(G), prs(P2) + srs(G2))):
        b0 = set(map(frozenset, overlaps(before))); b1 = set(map(frozenset, overlaps(after)))
        new_ov[tag] = sorted(tuple(sorted(x)) for x in b1 - b0)
    # a moved cluster tile must stay inside its grown cluster block
    for name, anchor, b in cl:
        nb = P2[name]
        for s in G2['slots']:
            if s['name'] in rep['clusters'][name]['tiles']:
                w, h = wh(s); x, y = s['origin']['x'], s['origin']['y']
                if not (nb['x'] - 0.01 <= x and x + w <= nb['x'] + nb['w'] + 0.01 and nb['y'] - 0.01 <= y and y + h <= nb['y'] + nb['h'] + 0.01):
                    new_ov.setdefault('outside_cluster', []).append(s['name'])
    W, H = G2['floorplan']['die_um']
    for name, _, _ in cl:
        nb = P2[name]
        if nb['x'] < 0 or nb['y'] < 0 or nb['x'] + nb['w'] > W or nb['y'] + nb['h'] > H:
            new_ov.setdefault('outside_die', []).append(name)
    G2['floorplan']['cluster_spread'] = dict(tool='tools/hbm_die_v16/d4g_cluster_spread.py', gap_um=g, gap_y_um=gy,
                                             clusters=a.cluster, shifts=a.shift, moves=a.move)
    rep.update(die_um=[W, H], new_overlaps=new_ov, verdict='PASS' if not any(new_ov.values()) else 'FAIL',
               rule='rigid tile moves per 3x3 grid cell; die outline unchanged; no tile resized/re-pinned')
    json.dump(G2, open(out / 'grants_d4g.json', 'w'), indent=1)
    json.dump(P2, open(out / 'compact.P.json', 'w'), indent=1)
    json.dump(RM2, open(out / 'd4g_region_map.json', 'w'), indent=1)
    shutil.copy(src / 'lanes.json', out / 'lanes.json'); shutil.copy(src / 'coord_map.json', out / 'coord_map.json')
    json.dump(rep, open(out / 'spread_report.json', 'w'), indent=1)
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, axs = plt.subplots(2, len(cl), figsize=(4.5 * len(cl), 9), squeeze=False)
        for j, (name, _, b) in enumerate(cl):
            nb = P2[name]
            for i, (PP, GG) in enumerate(((P, G), (P2, G2))):
                ax = axs[i][j]; x0, y0 = nb['x'] - 900, nb['y'] - 900; x1, y1 = nb['x'] + nb['w'] + 900, nb['y'] + nb['h'] + 900
                for k, x, y, w, h in prs(PP):
                    if x < x1 and x + w > x0 and y < y1 and y + h > y0:
                        ax.add_patch(Rectangle((x, y), w, h, fill=False, ec='#1565c0', lw=0.8, ls='--'))
                for k, x, y, w, h in srs(GG):
                    if x < x1 and x + w > x0 and y < y1 and y + h > y0:
                        ax.add_patch(Rectangle((x, y), w, h, fc='#f4b183' if k.startswith('hc_') else '#c9d9ef', ec='k', lw=0.4))
                        if w > 300:
                            ax.text(x + w / 2, y + h / 2, k, fontsize=5, ha='center', va='center')
                ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
                ax.set_title(f"{name} {'before' if i == 0 else f'gap {g}/{gy}'}", fontsize=8)
        fig.tight_layout(); fig.savefig(out / 'spread.png', dpi=90)
    except Exception as e:  # noqa: BLE001
        print('PNG skipped', e)
    print('CLUSTER_SPREAD', rep['verdict'], json.dumps(dict(new_overlaps=new_ov, sites=moved_sites, shifted=len(rep['shifted']),
                                                             tiles={k: len(v['tiles']) for k, v in rep['clusters'].items()})))
    sys.exit(0 if rep['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
