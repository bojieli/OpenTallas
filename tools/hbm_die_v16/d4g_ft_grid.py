#!/usr/bin/env python3
"""HBM-DIE13 10-20: die relay FEEDTHROUGH GRID at <= 405 um pitch (owner DIE FLOORPLAN RULE 10-20 21:40).

Owner rule: every die plan reserves relay channels (cell rows) between macro blocks at intervals <= the 405 um reach, so
every die-level wire has a relay / repeater site within reach.  Between blocks the d4g die already has free channels
(r11/r12: 334-360 mm2 free); the rule fails only ACROSS a block whose width AND height exceed the reach (121 blocks,
lanes/HBM-DIE12.md).  Owner 10-20: over-the-block / feedthrough for pass-through buses.  This tool reserves, in every such
grant slot, die-owned feedthrough relay COLUMNS and ROWS (reserved_channels, slot-local coordinates, the schema the su_*
slots already carry) so that no stretch of the block is farther than the reach from a channel or a block face:

    k = ceil((D - reach) / (reach + w))   channels across a dimension D (w = channel width), evenly spaced,
    every segment (D - k w) / (k + 1) <= reach.

The die tools carve the channels out of the SYNTH abstract (OBS + placement occupancy; die_case_v16 --carve-reserved all)
and the relay router / station planner / GEN treat them as free cell rows (relay_router carved cells).  M6-M9 are open
over every SYNTH abstract (OBS M1-M5), so the wires cross on M6/M8 and the relay rows sit in the channel.
A REAL (hardened) tile must reserve the same channel in its own floorplan (hard placement + M5/M6 keepout) = the tile
redesign NOTICE list in the report (by master).

Excluded: die-edge hard macros (HBM PHY, SerDes column) -- no die wire passes over them.

    d4g_ft_grid.py --plan-dir IN --out OUT [--reach 405] [--width 43.2] [--lattice 0.216]
copies IN/{compact.P.json, lanes.json, d4g_region_map.json, coord_map.json, spread_report.json} and writes OUT/grants_d4g.json
(+ floorplan.ft_grid record), OUT/ft_grid_report.json, OUT/ft_grid.png.
"""
import argparse
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path

EDGE_EXCLUDE = ('ot_hbm3e_phy', 'ot_pdie_serdes', 'ot_pdie_ucie')


def snap(v, q):
    return round(round(v / q) * q, 3)


def cuts(D, reach, w, q):
    """channel [lo, hi] spans (slot-local) across dimension D, evenly spaced, every segment <= reach"""
    if D <= reach:
        return []
    k = int(math.ceil((D - reach) / (reach + w)))
    seg = (D - k * w) / (k + 1)
    out = []
    for i in range(k):
        lo = snap((i + 1) * seg + i * w, q)
        out.append([lo, round(lo + w, 3)])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan-dir', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reach', type=float, default=405.0)
    ap.add_argument('--width', type=float, default=43.2, help='channel width um (lattice; relay rows are 10.8-25 um)')
    ap.add_argument('--lattice', type=float, default=0.216)
    a = ap.parse_args()
    G = json.loads((a.plan_dir / 'grants_d4g.json').read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    for f in ('compact.P.json', 'lanes.json', 'd4g_region_map.json', 'coord_map.json', 'spread_report.json'):
        if (a.plan_dir / f).exists():
            shutil.copy2(a.plan_dir / f, a.out / f)
    rep = dict(schema='opentallas.hbm.d4g_ft_grid.v1', reach_um=a.reach, width_um=a.width, from_plan=str(a.plan_dir),
               slots={}, by_master=defaultdict(lambda: dict(slots=0, w=0, h=0, columns=0, rows=0, carved_frac=0.0)),
               excluded=[], replaced_existing={})
    tot_area = tot_carved = 0.0
    for s in G['slots']:
        if s.get('kind') == 'die':
            continue
        w, h = s['outline']['w'], s['outline']['h']
        if min(w, h) <= a.reach:
            continue
        cell = s.get('cell') or s['name']
        if any(str(cell).startswith(p) for p in EDGE_EXCLUDE):
            rep['excluded'].append(dict(slot=s['name'], cell=cell, why='die-edge hard macro (no pass-through wire)'))
            continue
        if s['origin'].get('orient', 'R0') in ('R90', 'R270', 'MXR90', 'MYR90'):
            rep['excluded'].append(dict(slot=s['name'], cell=cell, why='rotated slot (carve frame not mapped)'))
            continue
        if s.get('reserved_channels'):
            rep['replaced_existing'][s['name']] = s['reserved_channels']
        cx, cy = cuts(w, a.reach, a.width, a.lattice), cuts(h, a.reach, a.width, a.lattice)
        ch = [dict(kind='feedthrough_relay_column', x_um=c, y_um=[0, h], owner='die (relay stations, HBM-DIE13 ft grid)',
                   master_keepout='hard placement + M5/M6 route') for c in cx]
        ch += [dict(kind='feedthrough_relay_row', x_um=[0, w], y_um=c, owner='die (relay stations, HBM-DIE13 ft grid)',
                    master_keepout='hard placement + M5/M6 route') for c in cy]
        s['reserved_channels'] = ch
        carved = len(cx) * a.width * h + len(cy) * a.width * w - len(cx) * len(cy) * a.width ** 2
        tot_area += w * h; tot_carved += carved
        seg_x = (w - len(cx) * a.width) / (len(cx) + 1); seg_y = (h - len(cy) * a.width) / (len(cy) + 1)
        rep['slots'][s['name']] = dict(cell=cell, w=w, h=h, columns=len(cx), rows=len(cy), seg_x_um=round(seg_x, 1),
                                       seg_y_um=round(seg_y, 1), carved_frac=round(carved / (w * h), 3))
        b = rep['by_master'][cell]
        b.update(slots=b['slots'] + 1, w=w, h=h, columns=len(cx), rows=len(cy), carved_frac=round(carved / (w * h), 3))
    G['floorplan']['ft_grid'] = dict(tool='tools/hbm_die_v16/d4g_ft_grid.py', reach_um=a.reach, width_um=a.width,
                                     slots=len(rep['slots']), carved_mm2=round(tot_carved / 1e6, 2),
                                     rule='owner 10-20 21:40: relay channels at <= 405 um; feedthrough over/through blocks > reach')
    rep['by_master'] = dict(rep['by_master'])
    rep['totals'] = dict(slots=len(rep['slots']), block_mm2=round(tot_area / 1e6, 2), carved_mm2=round(tot_carved / 1e6, 2),
                         die_um=G['floorplan']['die_um'], die_area_change_mm2=0.0)
    (a.out / 'grants_d4g.json').write_text(json.dumps(G, indent=1))
    (a.out / 'ft_grid_report.json').write_text(json.dumps(rep, indent=1))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        W, H = G['floorplan']['die_um']
        fig, ax = plt.subplots(figsize=(10, 14))
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2))
        for s in G['slots']:
            if s.get('kind') == 'die':
                continue
            x, y, w, h = s['origin']['x'], s['origin']['y'], s['outline']['w'], s['outline']['h']
            ax.add_patch(Rectangle((x, y), w, h, fc='#c9d9ef' if s['name'] in rep['slots'] else '#eeeeee', ec='k', lw=0.2))
            if s['name'] in rep['slots']:
                o = s['origin'].get('orient', 'R0')
                for c in s['reserved_channels']:
                    (x0, x1), (y0, y1) = c['x_um'], c['y_um']
                    if o in ('MY', 'R180'):
                        x0, x1 = w - x1, w - x0
                    if o in ('MX', 'R180'):
                        y0, y1 = h - y1, h - y0
                    ax.add_patch(Rectangle((x + x0, y + y0), x1 - x0, y1 - y0, fc='#e65100', ec='none'))
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
        ax.set_title(f"d4g ft grid <= {a.reach:g} um: {len(rep['slots'])} blocks, carved {tot_carved / 1e6:.1f} mm2 (orange)")
        fig.tight_layout(); fig.savefig(a.out / 'ft_grid.png', dpi=80)
    except Exception as e:  # noqa: BLE001
        print('PNG skipped', e)
    print('FT_GRID', json.dumps(rep['totals']))
    for m, b in sorted(rep['by_master'].items(), key=lambda t: -t[1]['slots']):
        print(f"  {b['slots']:3d} x {m[:48]:48s} {b['w']:.0f}x{b['h']:.0f} cols {b['columns']} rows {b['rows']} carved {b['carved_frac']:.0%}")


if __name__ == '__main__':
    main()
