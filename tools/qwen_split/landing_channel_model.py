#!/usr/bin/env python3
"""Finite full-shape GEN3 channel cost before generator/physical admission."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from qwen_split.dv_case import landing_column_channels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--geometry', type=Path, required=True)
    ap.add_argument('--landing-list', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    d = json.loads(a.geometry.read_text()); old = copy.deepcopy(d)
    ys = next(i['y'] for i in d['insts'] if i['n'] == 'dvs_W0')
    for i in d['insts']:
        if i['n'].startswith('dvs_'): i['y'] += 129.6
        elif i['n'].startswith('c16_') and i['y'] > ys: i['y'] += 259.2
    channels = landing_column_channels(d, 86.4)
    def outline(x, extra_y):
        return [round(max(i['x'] + i['w'] for i in x['insts']) + 21.6, 3),
                round(max(i['y'] + i['h'] for i in x['insts']) + extra_y + 21.6, 3)]
    for i in old['insts']:
        if i['n'].startswith('dvs_'): i['y'] += 43.2
        elif i['n'].startswith('c16_') and i['y'] > ys: i['y'] += 86.4
    before = outline(old, 0); after = outline(d, 0)
    array = [i for i in d['insts'] if i['n'].startswith(('c16_', 'dvs_'))]
    overlaps = [(x['n'], y['n']) for k,x in enumerate(array) for y in array[k+1:]
        if x['x'] < y['x']+y['w']-1e-3 and y['x'] < x['x']+x['w']-1e-3
        and x['y'] < y['y']+y['h']-1e-3 and y['y'] < x['y']+x['h']-1e-3]
    ll = json.loads(a.landing_list.read_text())
    result = dict(scope='source-owned full-shape geometry MODEL only; no GEN/placement/STA/clock closure',
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.geometry,a.landing_list]},
        hard_bodies=len(array), overlaps=overlaps, vertical_gap_um=86.4, slice_gap_um=129.6,
        old_slice_gap_um=43.2, channels=channels, before_outline_um=before, after_outline_um=after,
        delta_outline_um=[round(y-x,3) for x,y in zip(before,after)],
        delta_area_mm2=round((after[0]*after[1]-before[0]*before[1])/1e6,6),
        authority='docs/INTEGRATED_PHYSICAL_PLAN.md:9 owner 26 by 33 mm',
        fits_reticle=max(after)<=33000 and min(after)<=26000,
        listed_landings=ll['totals'],
        schedule={'per_new_landing_edges':3,'worst_extra_cycles_per_layer':45,'layers':36,
                  'token_extra_cycles':1620,'token_extra_us_at_1p2GHz':1.35,
                  'status':'existing conservative landing-list price; final GEN/compiler must rederive actual ages'},
        unresolved=['20 auto hard crossings beyond frozen446 list require actual GEN cost',
            'directional physical landing masters remain declared stand-ins',
            'complete clock/reset/PG/via/OBS/access and actual pin reach not yet measured',
            'OVL source/view and BOOTCTX/first-use joint closure pending',
            'no whole-system numeric or throughput qualification'])
    (a.out/'model.json').write_text(json.dumps(result,indent=2)+'\n')
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(14,11))
    for r in channels:
        x,y,z,w=r['rect']; ax.add_patch(Rectangle((x/1000,y/1000),(z-x)/1000,(w-y)/1000,color='#9be3bf'))
    for i in d['insts']:
        if i['n']=='outline_marker': continue
        color='#e3b16c' if i['n'].startswith('dvs_') else '#b0c6df'
        ax.add_patch(Rectangle((i['x']/1000,i['y']/1000),i['w']/1000,i['h']/1000,
                              facecolor=color,edgecolor='#354452',linewidth=.25))
        if i['n'].startswith('dvs_'):
            ax.text((i['x']+i['w']/2)/1000,(i['y']+i['h']/2)/1000,i['n'],ha='center',fontsize=6,rotation=90)
    ax.set(xlim=(0,33),ylim=(0,26),xlabel='mm',ylabel='mm',aspect='equal',
        title=f'GEN3 structural channel MODEL — {after[0]/1000:.3f} × {after[1]/1000:.3f} mm\n'
              'Green = source-owned 86.4 µm vertical channels; slice N/S gaps129.6 µm; no routed/PG claim')
    fig.tight_layout();fig.savefig(a.out/'geometry_model.png',dpi=150)
    print(json.dumps({k:result[k] for k in ['hard_bodies','overlaps','before_outline_um','after_outline_um','delta_area_mm2','fits_reticle']}))
    if overlaps or not result['fits_reticle']: raise SystemExit(1)

if __name__ == '__main__': main()
