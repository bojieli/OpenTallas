#!/usr/bin/env python3
"""el1013-s81-vmfe/B2: floorplan + cut/hop plan of the hierarchical VM front end dsfd_vm_fe_h (1,520.064 x 594.00).
Leaf outlines are placed in the parent; every inter-leaf net is flop-at-pin -> wire -> flop-at-pin.  The script measures
(a) bits per cut against free routing tracks (ASAP7 make_tracks pitches, 80 % usable) for vertical and horizontal cuts,
(b) the Manhattan length of every hop (bit-aligned pin segments: worst of the two segment ends).  Limits: cut <= 0.60,
hop <= 500 um.  Model: a net occupies the bounding box of its two pin segments (L route).  Layers: free parent area
H = M2/2 + M4 + M6, V = M3 + M5 + M7; over an M5 leaf H = M6, V = M7; over dsfd_vm_clt (M6 view) H = 0, V = M7.
Writes results/arch/s81_vm_fe_h_plan_1013.json; exit 1 when a cut or a hop fails.  Leaf areas are ESTIMATES from the
measured sink counts (results/arch/s81_vm_fe_h_sinks_1013.json) until the remote gate prints std_area_um2."""
import json, math, sys
from pathlib import Path
W, H = 1520.064, 594.0
TPU = {'M2': 7 / 0.270, 'M3': 1 / 0.036, 'M4': 1 / 0.048, 'M5': 1 / 0.048, 'M6': 1 / 0.064, 'M7': 1 / 0.064}
FREE, CUT_MAX, HOP_MAX = 0.80, 0.60, 500.0
HT = {'free': TPU['M2'] / 2 + TPU['M4'] + TPU['M6'], 'm5': TPU['M6'], 'm6': 0.0}
VT = {'free': TPU['M3'] + TPU['M5'] + TPU['M7'], 'm5': TPU['M7'], 'm6': TPU['M7']}
L = {}   # leaf -> (x0, y0, x1, y1, cap)
def leaf(n, x, y, w, h, cap='m5'): L[n] = (x, y, x + w, y + h, cap)
for i in range(16): leaf(f'clt{i}', 80.64 * i, 363.96, 80.64, 230.04, 'm6')
for i, x in enumerate((75.0, 370.0, 670.0, 955.0)): leaf(f'fxs{i}', x, 318.0, 280.0, 43.2)
for s in range(4): leaf(f'fsr{s}', 388.8 * s, 0.0, 345.6, 17.28)
leaf('flt0', 1300.0, 480.0, 108.0, 86.4); leaf('flt1', 1300.0, 380.0, 108.0, 86.4)        # svc lanes under f_svc
for i in range(4): leaf(f'flt{2 + i}', 250.0 + 112.0 * i, 216.0, 108.0, 86.4)              # coll
for i in range(4): leaf(f'flt{6 + i}', 560.0 + 112.0 * i, 118.0, 108.0, 86.4)              # sel col hc hc
leaf('fcn', 700.0, 216.0, 194.4, 86.4); leaf('fld', 905.0, 216.0, 151.2, 86.4)
leaf('fcw', 250.0, 118.0, 129.6, 86.4); leaf('fcc', 390.0, 118.0, 151.2, 86.4)
BSRC = ['fxs0', 'fxs1', 'fxs2', 'fxs3', 'fcw+fcc', 'fcn', 'fcn+fld']
def seg(n, face, f0=0.0, f1=1.0):
    x0, y0, x1, y1, _ = L[n]; y = y1 if face == 'N' else y0
    return (x0 + (x1 - x0) * f0, x0 + (x1 - x0) * f1, y)
def hop(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1])) + abs(a[2] - b[2])
NETS = []  # (name, bits, seg a, seg b, stages allowed = wires)
def net(name, bits, a, b, wires=1): NETS.append((name, bits, a, b, wires))
XR_W, XR_H = 64.8, 10.8
for b in range(7):
    for s in range(4):
        srcs = BSRC[b].split('+'); n0 = srcs[0]
        a = seg(n0, 'S', s / 4, (s + 1) / 4)                      # slice-major out pins, W -> E as the slices
        d = seg(f'fsr{s}', 'N', 0.10 + 0.11 * b, 0.10 + 0.11 * (b + 1))   # bundle b's ports inside i_d etc (bit-aligned)
        pts = []
        for r in range(2):                                         # fxr tiles at 1/3 and 2/3 of the straight line
            t = (r + 1) / 3; xc = (a[0] + a[1]) / 2 * (1 - t) + (d[0] + d[1]) / 2 * t
            yc = 96.0 - 26.0 * r - 0.0; yc = [100.0, 30.0][r] + 2.7 * (b % 4)
            nm = f'fxr_b{b}s{s}r{r}'; leaf(nm, xc - XR_W / 2, yc, XR_W, XR_H); pts.append(nm)
        for sn in srcs:
            net(f'{sn}->{pts[0]}', 592 // len(srcs), seg(sn, 'S', s / 4, (s + 1) / 4), seg(pts[0], 'N'))
        net(f'{pts[0]}->{pts[1]}', 596, seg(pts[0], 'S'), seg(pts[1], 'N'))
        net(f'{pts[1]}->fsr{s}', 596, seg(pts[1], 'S'), d)
for i in range(16):
    net(f'clt{i}->fxs{i // 4}', 547, seg(f'clt{i}', 'S', 0.0, 0.66), seg(f'fxs{i // 4}', 'N', (i % 4) / 4, (i % 4 + 1) / 4))
for i in range(4): net(f'fxs{i}.k_o->fcn (KD 2: 1 relay)', 132, seg(f'fxs{i}', 'S', 0.9, 1.0), seg('fcn', 'N'), 2)
for n in ('fld', 'fcc', 'fcw'): net(f'{n}.k_o->fcn (KD 2: 1 relay)', 66, seg(n, 'N'), seg('fcn', 'S'), 2)
for i in range(10):
    f = f'flt{i}'
    net(f'{f}.ret->fld (LDL 3: 1 relay)', 530, seg(f, 'S'), seg('fld', 'N'), 2)
    net(f'fld.g->{f} (LGL 2)', 1, seg('fld', 'N'), seg(f, 'S'), 1)
    net(f'fcn.arm->{f} (LAL 2)', 15, seg('fcn', 'N'), seg(f, 'S'), 1)
# die N-face pins dropped on M7 to their consumer (pin x requested ABOVE the consumer: slot change request)
for n, bits in (('flt0', 514), ('flt1', 514), ('flt2', 525), ('flt3', 525), ('flt4', 525), ('flt5', 525), ('flt6', 515),
                ('flt7', 515), ('flt8', 513), ('flt9', 513), ('fcw', 613), ('fcc', 542), ('fcn', 111)):
    s_ = seg(n, 'N'); net(f'N-face->{n}', bits, (s_[0], s_[1], H), s_)
def cuts():
    out = []
    for axis, span, TT in (('x', W, HT), ('y', H, VT)):
        worst = None; k = 0 if axis == 'x' else 1; step = 4.0
        for c in [step * i for i in range(1, int(span / step))]:
            # free tracks along the cut line
            ivs = sorted((l[1 - k], l[3 - k], l[4]) for l in L.values() if l[k] < c < l[k + 2])
            other = H if axis == 'x' else W; tr = other * TT['free']
            for a, b, cap in ivs: tr -= (b - a) * (TT['free'] - TT[cap])
            bits = 0
            for nm, nb, a, b, wires in NETS:
                if axis == 'x': lo, hi = min(a[0], b[0]), max(a[1], b[1]); lo2, hi2 = min(a[1], b[1]), max(a[0], b[0])
                else: lo2, hi2 = min(a[2], b[2]), max(a[2], b[2])
                if axis == 'x': lo2, hi2 = (min((a[0] + a[1]) / 2, (b[0] + b[1]) / 2), max((a[0] + a[1]) / 2, (b[0] + b[1]) / 2))
                if lo2 < c < hi2: bits += nb
            r = bits / (tr * FREE) if tr > 0 else (math.inf if bits else 0.0)
            if worst is None or r > worst['ratio']: worst = {'axis': axis, 'at': c, 'bits': bits, 'tracks_usable': round(tr * FREE), 'ratio': round(r, 3)}
        out.append(worst)
    return out
def main():
    hops = []
    for nm, nb, a, b, wires in NETS:
        d = hop(a, b); hops.append({'net': nm, 'bits': nb, 'um': round(d, 1), 'wires': wires, 'um_per_hop': round(d / wires, 1),
                                    'ok': d / wires <= HOP_MAX, 'stages_needed_wires': math.ceil(d / HOP_MAX)})
    ov = [(a, b) for a in L for b in L if a < b and L[a][0] < L[b][2] - 1e-6 and L[b][0] < L[a][2] - 1e-6
          and L[a][1] < L[b][3] - 1e-6 and L[b][1] < L[a][3] - 1e-6]
    inside = all(l[0] >= 0 and l[1] >= 0 and l[2] <= W + 1e-6 and l[3] <= H + 1e-6 for l in L.values())
    c = cuts(); bad = [h for h in hops if not h['ok']]
    res = {'schema': 'opentallas.s81_vm_fe_h.plan.v1', 'outline': [W, H], 'limits': {'cut': CUT_MAX, 'hop_um': HOP_MAX, 'free': FREE},
           'tracks_per_um': {k: round(v, 2) for k, v in TPU.items()}, 'area_basis': 'ESTIMATE (leaf areas not yet synthesized)',
           'leaves': {n: {'x': round(l[0], 3), 'y': round(l[1], 3), 'w': round(l[2] - l[0], 3), 'h': round(l[3] - l[1], 3),
                          'layer_cap': l[4].upper()} for n, l in L.items()},
           'overlaps': ov, 'inside_outline': inside, 'worst_cuts': c,
           'hop_max': max(hops, key=lambda h: h['um_per_hop']), 'hops_failing': bad,
           'hops': sorted(hops, key=lambda h: -h['um_per_hop'])[:40],
           'pass': inside and not ov and not bad and all(x['ratio'] <= CUT_MAX for x in c)}
    out = Path(__file__).resolve().parents[2] / 'results/arch/s81_vm_fe_h_plan_1013.json'
    out.write_text(json.dumps(res, indent=1) + '\n')
    print('cuts', c); print('overlaps', len(ov), ov[:6], 'inside', inside)
    print('hop max', res['hop_max']); print('failing hops', len(bad)); [print(' ', h['net'], h['um'], h['wires']) for h in bad[:30]]
    print('PLAN:', 'PASS' if res['pass'] else 'FAIL'); return 0 if res['pass'] else 1
if __name__ == '__main__': sys.exit(main())
