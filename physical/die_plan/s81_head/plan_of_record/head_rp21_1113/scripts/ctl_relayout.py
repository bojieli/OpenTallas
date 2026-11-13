"""HEAD-97 rp21 (COORD ruling: hd_ctl streets in this event): the 4 hd_ctl logic cores re-spaced so every core-core gap is >= 43.2 (R-STREET), outline unchanged; plan points inside a macro move off it."""
import json, sys, math
src, out = sys.argv[1:3]
P = json.load(open(src)); t = P['partition_types']['hd_ctl']; W, H = t['outline_um']
G = 8.64; up = lambda v: round(math.ceil(v / G - 1e-9) * G, 4)
hc = t['hard_cores']
by = {h['inst'].rsplit('.', 1)[1]: h for h in hc}
assert sorted(by) == ['u_xa0', 'u_xa1', 'u_xb0', 'u_xb1'], sorted(by)
PY = up(77.784 + 0.012 + 43.2)               # 129.6: 43.2 street between the stacked cores (was 34.5)
for j, n in enumerate(('u_xa0', 'u_xa1', 'u_xb0')):
    by[n]['origin_um'] = [95.04, round(77.76 + j * PY, 4)]
by['u_xb1']['origin_um'] = [up(95.04 + 0.108 + 171.288 + 43.2), 138.24]   # 311.04: 43.2 street to the xa column (was 27.4)
boxes = [(h['origin_um'][0] + h['track_offset_um'][0], h['origin_um'][1] + h['track_offset_um'][1], h['origin_um'][0] + h['track_offset_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['track_offset_um'][1] + h['outline_um'][1]) for h in hc]
CL = 8.64
def bad(x, y): return any(b[0] - CL < x < b[2] + CL and b[1] - CL < y < b[3] + CL for b in boxes)
def fix(x, y):
    if not bad(x, y): return [x, y]
    best = None
    for r in range(1, 200):
        for dx in range(-r, r + 1):
            for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                nx, ny = round(x + dx * 4.32, 4), round(y + dy * 4.32, 4)
                if 8.64 <= nx <= W - 8.64 and 8.64 <= ny <= H - 8.64 and not bad(nx, ny):
                    d = abs(nx - x) + abs(ny - y)
                    if best is None or d < best[0]: best = (d, [nx, ny])
        if best: return best[1]
moved = []
ck = t['clock']
for key in ('tap_um', 'start_capture_um'):
    if ck.get(key):
        n = fix(*ck[key]);
        if n != ck[key]: moved.append((key, ck[key], n)); ck[key] = n
t['reset']['local_taps_um'] = [fix(x, y) for x, y in t['reset']['local_taps_um']]
for s in t.get('count_straps', []):
    if 'sites_um' in s: s['sites_um'] = [fix(x, y) for x, y in s['sites_um']]
moved.append(('reset', t['reset']['local_taps_um']))
t['note'] = t.get('note', '') + ' | HEAD-97 rp21 (COORD ruling 11-13, R-STREET): hd_ctl cores re-spaced to 43.2 streets: xa0/xa1/xb0 column pitch 129.6 from y 77.76, xb1 x 311.04'
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
print('ctl', {k: v['origin_um'] for k, v in by.items()}); print(json.dumps(moved))
