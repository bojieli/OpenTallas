#!/usr/bin/env python3
"""ft_strip.py PLAN_IN PLAN_OUT DELTA : drop bit_sites_um/bit_site_cell_um/regs_um of every ft slot of the delta's types
with a site cell inside a hard-core box (so ft_sites_unblock.py re-sites it); move blocked reset local taps to the
nearest free 8.64-lattice point (cell clear of every core by 4.32)."""
import json, sys
pin, pout, dp = sys.argv[1:4]
P = json.load(open(pin)); D = json.load(open(dp)); CW, CH = 1.404, .27
def boxes(T): return [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1]) for h in T['hard_cores']]
def hit(x, y, B, w=CW, h=CH, c=0.0): return any(x < b[2] + c and x + w > b[0] - c and y < b[3] + c and y + h > b[1] - c for b in B)
for tn in D:
    T = P['partition_types'][tn]; B = boxes(T); W, H = T['outline_um']; n = []
    for s in T['ft_slots']:
        if any(hit(x, y, B, c=4.32) for st in (s.get('bit_sites_um') or []) for x, y in st) or any(hit(x - .7, y - .135, B, c=4.32) for x, y in (s.get('regs_um') or [])):
            for k in ('bit_sites_um', 'bit_site_cell_um', 'regs_um'): s.pop(k, None)
            n.append(s['name'])
    lt = T['reset']['local_taps_um']; mv = []
    for i, (x, y) in enumerate(lt):
        if hit(x - 4.32, y - 4.32, B, 8.64, 8.64):
            cand = [(abs(i_ * 8.64 - x) + abs(j * 8.64 - y), i_ * 8.64, j * 8.64) for i_ in range(1, int(W / 8.64)) for j in range(1, int(H / 8.64))
                    if not hit(i_ * 8.64 - 4.32, j * 8.64 - 4.32, B, 8.64, 8.64, 4.32)]
            _, nx, ny = min(cand); lt[i] = [round(nx, 4), round(ny, 4)]; mv.append(((x, y), lt[i]))
    print(tn, 'ft slots stripped', len(n), n[:6], 'reset taps moved', mv)
json.dump(P, open(pout, 'w'), indent=1); open(pout, 'a').write('\n')
