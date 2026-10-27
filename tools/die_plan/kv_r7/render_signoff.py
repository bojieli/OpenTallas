#!/usr/bin/env python3
"""CLOCK-KV-R7 mesh sign-off render: every mesh load point (array stub input o, band-tree root input ^) coloured by its
worst |MC - nominal| arrival deviation (whole-die linear solve, TT), ngspice window boxes, straps faint.
usage: render_signoff.py REC SOLVE_TT NGDIR OUT_PNG"""
import json, sys, glob
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
rec, sol, ng, out = sys.argv[1:5]
R = json.load(open(rec)); S = json.load(open(sol))['samples']
a0 = S[0]['tap_arr_ps']; dev = {k: max(abs(s['tap_arr_ps'][k] - a0[k]) for s in S[1:]) for k in a0}
fig, ax = plt.subplots(1, 2, figsize=(16, 20))
for j, (val, lab) in enumerate(((dev, 'worst |MC - nominal| (ps)'), ({k: a0[k] - min(a0.values()) for k in a0}, 'nominal arrival - min (ps)'))):
    A = ax[j]
    for x in R['xs']: A.axvline(x, color='#cde', lw=0.4, zorder=0)
    for y in R['ys']: A.axhline(y, color='#cde', lw=0.4, zorder=0)
    for kind, mk in (('stub', 'o'), ('band_root', '^')):
        T = [t for t in R['taps'] if t['kind'] == kind]
        sc = A.scatter([t['tap'][0] for t in T], [t['tap'][1] for t in T], c=[val[t['part']] for t in T], marker=mk,
                       s=14 if kind == 'stub' else 30, cmap='viridis', vmin=0, vmax=max(val.values()), zorder=2)
    for f in sorted(glob.glob(ng + '/w_*_TT/meta.json')):
        w = json.load(open(f))['window']
        A.add_patch(plt.Rectangle((w[0], w[1]), w[2] - w[0], w[3] - w[1], fill=False, ec='red', lw=1.5, zorder=3))
        A.text(w[0], w[3] + 60, f.split('/')[-2], color='red', fontsize=8)
    A.set_aspect('equal'); A.set_xlim(-200, 11300); A.set_ylim(-200, 27300); fig.colorbar(sc, ax=A, shrink=0.5, label=lab)
    A.set_title(lab)
fig.suptitle(f'D-KV-CLK-R7 mesh sign-off on b3 (routed): {len(R["taps"])} mesh loads, 12 MC whole-die linear (TT); '
             f'nominal skew {S[0]["tap_skew_ps"]:.1f}, MC worst {max(s["tap_skew_ps"] for s in S[1:]):.1f} ps; red = ngspice windows', fontsize=11)
fig.tight_layout(); fig.savefig(out, dpi=80)
