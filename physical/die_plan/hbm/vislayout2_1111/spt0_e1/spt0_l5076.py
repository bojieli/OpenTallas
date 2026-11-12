"""VISLAYOUT2-HBM E1b: pv1 L5076x2 +1 station (COORD 11-11 19:1x approved; latency row +1, DIE-HBM-100 confirms).
L5076x2 (653 b, S->S x 1488 -> 53) already fails G0 in d49a (S0->S1 759 > 405) and is pv1's last hot face bin.
With 5 stations on the macro-free row y ROW between the xcal macros: S0 at the input pin, registers evenly by arc."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
ROW = float(sys.argv[3]) if len(sys.argv) > 3 else 140.0
p = json.load(open(src))
t = p['partition_types']['q_spt0__physical_v1']
s = next(x for x in t['ft_slots'] if x['name'] == 'L5076x2')
a = [sum(s['in_window_um']) / 2, 0.0]; b = [sum(s['out_window_um']) / 2, 0.0]
pts = [a, [a[0], ROW], [b[0], ROW], b]
seg = lambda u, v: abs(v[0] - u[0]) + abs(v[1] - u[1])
L = sum(seg(pts[i], pts[i + 1]) for i in range(3))
k0 = int(s['stations']); k = k0 + 1
regs = [[round(a[0], 2), 0.0]]
for j in range(1, k):
    d = L * j / k; i = 0
    while i < 2 and d > seg(pts[i], pts[i + 1]):
        d -= seg(pts[i], pts[i + 1]); i += 1
    u, v = pts[i], pts[i + 1]; f = d / seg(u, v)
    regs.append([round(u[0] + (v[0] - u[0]) * f, 2), round(u[1] + (v[1] - u[1]) * f, 2)])
s['stations'] = k; s['regs_um'] = regs
s.pop('bit_sites_um', None); s.pop('bit_site_cell_um', None)
s['note'] = (s.get('note', '') + f' | VISLAYOUT2-HBM 11-11 E1b: +1 station ({k0}->{k}), row y {ROW:g} between the xcal macros, hops {L / k:.0f} um').strip(' |')
lat = p['latency']['lanes']['L5076']
for key in ('cycles', 'stations', 'natural'):
    lat[key] = int(lat[key]) + 1
json.dump(p, open(dst, 'w'), indent=1)
print('L5076x2', k0, '->', k, 'L', round(L), 'hop', round(L / k), regs, lat)
