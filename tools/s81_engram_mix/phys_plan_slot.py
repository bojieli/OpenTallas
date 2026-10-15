#!/usr/bin/env python3
"""S-ELEM-C 2026-10-15: MIX4 plan for the S-DIE home --mix4-slot 15714.0,9061.2,771.12,3229.2 (771 wide E-W, 3229
tall N-S, N short edge faces sp_vm).  Four copy clusters stacked N-S (one cluster master), the ck[0] top leaf on the N
edge, RS relay-station rows between the top and every shell.  Leaf outlines = v21 pin files (exact).
Reports: cluster / MIX4 footprint, intra-cluster seam reach, relay stages per cluster, and the N-S CUT: bits that
cross a horizontal line vs the vertical routing tracks over the 771 um width (owner cut rule <= 0.55-0.60)."""
import json, math
from pathlib import Path
R = Path(__file__).resolve().parents[2]
PD = R / 'physical/s81_die_pins/v21_engram_arithmetic'
O = {f.stem.replace('ot_s81_engram_', ''): json.loads(f.read_text())['outline_um'] for f in PD.glob('ot_s81_engram_*.json')}
SLOT = (15714.0, 9061.2, 771.12, 3229.2)
CH, M = 5.4, 2.16
# rows N -> S (column c = mul4 groups 2c, 2c+1 / add8 c / chunk8 (r, c) / shell column group c)
ROWS = [('shell', ['mixq_shell']), ('add8', ['add8'] * 4), ('mul4a', ['mul4'] * 4), ('mul4b', ['mul4'] * 4),
        ('chA', ['chunk8'] * 3 + ['sum'] + ['chunk8'] * 3), ('chB', ['chunk8'] * 3 + ['sum', 'sum'] + ['chunk8'] * 3),
        ('top', ['norm', 'signed_sqrt', 'mix_control', 'sigmoid', 'norm'])]
REACH = 500.0


def cluster():
    W = max(sum(O[m][0] for m in r) + CH * (len(r) - 1) for _, r in ROWS)
    boxes = []; y = 0.0                           # y measured southward from the cluster's N edge
    for tag, r in ROWS:
        w = sum(O[m][0] for m in r) + CH * (len(r) - 1); x = (W - w) / 2; h = max(O[m][1] for m in r)
        for i, m in enumerate(r):
            boxes.append(dict(row=tag, master=m, i=i, x=round(x, 3), y=round(y, 3), w=O[m][0], h=O[m][1])); x += O[m][0] + CH
        y += h + CH
    rly = dict(row='rly', master='rly', i=0, x=round(W / 2 - O['rly'][0] / 2, 3), y=round([b for b in boxes if b['row'] == 'chA'][0]['y'] - CH / 2 - O['rly'][1] / 2, 3), w=O['rly'][0], h=O['rly'][1])
    boxes.append(rly)
    return boxes, round(W, 3), round(y - CH, 3)


def main():
    boxes, W, H = cluster()
    cen = lambda b: (b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
    d = lambda a, b: round(abs(cen(a)[0] - cen(b)[0]) + abs(cen(a)[1] - cen(b)[1]) - a['h'] / 2 - b['h'] / 2, 1)
    by = lambda t: [b for b in boxes if b['row'] == t]
    sh = by('shell')[0]; ctl = [b for b in boxes if b['master'] == 'mix_control'][0]; rly = by('rly')[0]
    mul = by('mul4a') + by('mul4b'); ad = by('add8'); sm = [b for b in boxes if b['master'] == 'sum']
    chs = [b for b in boxes if b['master'] == 'chunk8']; top = by('top')
    seams = {'shell -> mul4 (column-aligned pins)': max(abs(cen(m)[1] - cen(sh)[1]) - m['h'] / 2 - sh['h'] / 2 for m in mul),
             'shell <-> add8': max(abs(cen(a)[1] - cen(sh)[1]) - a['h'] / 2 - sh['h'] / 2 for a in ad),
             'mul4 -> chunk8 (own column)': max(d(m, c) for m in by('mul4b') for c in chs if abs(cen(m)[0] - cen(c)[0]) < 100),
             'chunk8 -> sum': max(d(c, s) for c in chs for s in sm),
             'sum -> control / norm': max(d(s, t) for s in sm for t in top),
             'scalar row internal': max(d(a, b) for a in top for b in top),
             'mul4/add8/shell -> rly': max(d(x, rly) for x in mul + ad + [sh]),
             'rly -> control': d(rly, ctl)}
    over = {k: v for k, v in seams.items() if v > REACH}
    # MIX4 stacking: top leaf row at N, clusters with station rows
    TOPH = 21.6; n = 4; gap = (SLOT[3] - TOPH - CH - n * H) / n
    mix_h = TOPH + CH + n * (H + gap)
    shells = [TOPH + CH + q * (H + gap) + sh['h'] / 2 for q in range(n)]
    hops = [max(1, math.ceil((y + W / 2) / REACH)) for y in shells]   # N edge -> shell, worst corner of the face
    RS = max(hops) - 1
    per_cluster_bits = dict(down=2560 + 5 + 224 + 1, up=5 + 70 + 1 + 1 + 14 + 16 + 512 + 1 + 1)
    tracks = {}
    for lay, pitch in (('M7', .064), ('M9', .08)):
        tracks[lay] = int(W / pitch)
    cuts = []
    for q in range(n):
        crossing = (n - q - 1) * sum(per_cluster_bits.values())        # cut just S of cluster q: clusters q+1.. cross
        if crossing:
            cuts.append(dict(cut=f'S of cluster {q}', bits=crossing, ratio_M7=round(crossing / tracks['M7'], 2),
                             ratio_M7_M9=round(crossing / (tracks['M7'] + tracks['M9']), 2)))
    out = dict(schema='opentallas.s81.mix4.phys_plan_slot.v1', slot=SLOT, status='PLAN (v21 leaf outlines exact; parent not routed)',
               cluster=dict(w=W, h=H, fits_w=W <= SLOT[2] - 2 * M), mix4=dict(w=SLOT[2], h=round(mix_h, 2), cluster_gap_for_stations=round(gap, 2)),
               seams_um=seams, seams_over_500=over, relay=dict(hops_top_to_shell=hops, RS_each_way=RS, stations_flops=RS * n * sum(per_cluster_bits.values())),
               cut=dict(per_cluster_bits=per_cluster_bits, vertical_tracks_over_width=tracks, cuts=cuts,
                        rule='bits / tracks <= 0.55-0.60'), boxes=boxes)
    p = R / 'results/arch/s81_mix4_phys_plan_1015'; p.mkdir(exist_ok=True); (p / 'plan_slot.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'boxes'}, indent=1))


if __name__ == '__main__':
    main()
