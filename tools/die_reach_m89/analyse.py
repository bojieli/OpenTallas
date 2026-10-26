#!/usr/bin/env python3
"""REACH-M89: slack(L) per (relay, layer, buffer, spacing) -> stage ps/um and per-cycle reach (first failing L, interpolated)."""
import json, sys, statistics
from pathlib import Path


def load(d, fn):
    r = {}
    for line in (d / fn).read_text().split('\n'):
        f = line.split()
        if len(f) == 5:
            r[f[0]] = dict(slack=float(f[1]), arr=max(float(f[2]), float(f[3])), slew=float(f[4]))
    return r


def reach(rows, key):
    """largest L with slack >= 0 for every grid L' <= L, linearly interpolated to the first failing point"""
    prev = None
    for L, s in rows:
        if s < 0:
            if prev is None:
                return 0.0
            (L0, s0) = prev
            return round(L0 + (L - L0) * s0 / (s0 - s), 1)
        prev = (L, s)
    return float(rows[-1][0])   # no failure in the grid (>= max L)


def analyse(d, k_calib=None):
    P = json.loads((d / 'paths.json').read_text())
    out = dict(cell=P['cell'], die=P['die'], pin_layer=P['pin_layer'], worst_out_bit=P['worst_out_bit'],
               worst_in_bit=P['worst_in_bit'], calc={})
    for calc, fn in (('arnoldi', 'res.txt'), ('dmp_ceff_elmore', 'res_dmp.txt')):
        R = load(d, fn)
        cfg = {}
        for p in P['paths']:
            key = f"{p['layer']}/{p['buf']}/{p['d']}"
            ep = R[p['ep']]; a0 = R[p['mid'][0]]
            st = [(R[p['mid'][k + 1]]['arr'] - R[p['mid'][k]]['arr']) / p['d'] for k in range(1, p['nrep'] - 1)]
            c = cfg.setdefault(key, dict(layer=p['layer'], buf=p['buf'], d=p['d'], rows=[], stage=[], slew=[], o_eff=[]))
            c['rows'].append((p['L'], ep['slack'], ep['arr'] - a0['arr']))
            c['stage'] += st
            c['slew'].append(max([ep['slew']] + [R[m]['slew'] for m in p['mid']]))
            c['o_eff'].append(a0['arr'])
        res = {}
        for key, c in cfg.items():
            ps_um = round(statistics.median(c['stage']), 4) if c['stage'] else None
            r = dict(layer=c['layer'], buf=c['buf'], spacing_um=c['d'], stage_ps_per_um=ps_um,
                     launch_to_rep1_ps=round(statistics.median(c['o_eff']), 1),
                     max_slew_ps=round(max(c['slew']), 1), slew_legal_320=max(c['slew']) <= 320.0,
                     reach_um=reach([(L, s) for L, s, _ in c['rows']], key),
                     slack_ps={str(L): round(s, 1) for L, s, _ in c['rows'] if L % 250 == 0})
            if k_calib:
                r['reach_um_calibrated'] = reach([(L, s - (k_calib - 1) * w) for L, s, w in c['rows']], key)
            res[key] = r
        out['calc'][calc] = res
    return out


if __name__ == '__main__':
    root = Path(sys.argv[1])
    res = {}
    for d in sorted(root.iterdir()):
        if (d / 'paths.json').exists():
            a = analyse(d)
            cal = a['calc']['arnoldi']['M45/BUFx8_ASAP7_75t_R/160']['stage_ps_per_um']
            res[d.name] = analyse(d, k_calib=0.76 / cal)
            res[d.name]['calib_M45_BUFx8_160_ps_per_um'] = cal
    json.dump(res, open(sys.argv[2], 'w'), indent=1)
    for n, a in res.items():
        print(n, a['die'], 'calib', a['calib_M45_BUFx8_160_ps_per_um'], 'o_eff', a['calc']['arnoldi']['M8/BUFx16f_ASAP7_75t_R/600']['launch_to_rep1_ps'])
        for key, r in a['calc']['arnoldi'].items():
            print(f"   {key:32s} {r['stage_ps_per_um']}  reach {r['reach_um']:7.1f}  cal {r.get('reach_um_calibrated')}  slew {r['max_slew_ps']}  dmp {a['calc']['dmp_ceff_elmore'][key]['reach_um']}")
