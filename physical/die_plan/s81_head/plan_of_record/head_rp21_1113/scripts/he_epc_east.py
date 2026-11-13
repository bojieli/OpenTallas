"""HEAD-97 rp21: hd_host_e head SRAM column moved W of the u_epc hard core (43.2 street E of sf), u_epc moved to the E edge, so the lane path tx -> lo -> head no longer crosses u_epc (rp21x proof: 383 nets crossing, 10.8k H overflow, capacity 0 over u_epc).  Plan points inside a macro move off it."""
import json, sys, math
src, out = sys.argv[1:3]
P = json.load(open(src)); t = P['partition_types']['hd_host_e']; W, H = t['outline_um']
G = 8.64; up = lambda v: round(math.ceil(v / G - 1e-9) * G, 4)
hc = t['hard_cores']
epc = [h for h in hc if h['inst'].endswith('.u_epc')]; head = [h for h in hc if '.u_head.g_bank[' in h['inst']]
sf = [h for h in hc if '.u_sf.g_bank[' in h['inst']]
assert len(epc) == 1 and len(head) == 9 and len(sf) == 10 and len(hc) == 20
E = epc[0]; ew = E['outline_um'][0]
sf_x1 = max(h['origin_um'][0] + h['track_offset_um'][0] + h['outline_um'][0] for h in sf)
hx = up(sf_x1 + 43.2)                                   # head column: 43.2 street E of the sf column
hx1 = hx + max(h['track_offset_um'][0] + h['outline_um'][0] for h in head)
ex = round(math.floor((W - ew - 8.64) / G + 1e-9) * G, 4)  # epc to the E edge (no E-face pins), 8.64 off the outline
assert ex - hx1 >= 43.2, (hx, hx1, ex)
for h in head: h['origin_um'] = [hx, h['origin_um'][1]]
E['origin_um'] = [ex, E['origin_um'][1]]
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
_used = []
def _fixu(x, y):
    # reset local taps must stay distinct: a point already taken counts as blocked (8.64 clearance)
    global boxes
    n = fix(x, y)
    if any(abs(n[0] - u[0]) < 8.64 and abs(n[1] - u[1]) < 8.64 for u in _used):
        save = boxes; boxes = boxes + [(u[0] - 0.0, u[1] - 0.0, u[0] + 0.0, u[1] + 0.0) for u in _used]
        n = fix(n[0], n[1]); boxes = save
    if [x, y] != n and all(abs(v / 8.64 - round(v / 8.64)) < 1e-6 for v in n):
        n = [n[0], round(n[1] + 4.32, 4)]      # off the 8.64 clock-tap grid: a moved reset tap must not land on a clock tap
        assert not bad(*n), n
    _used.append(n); return n
t['reset']['local_taps_um'] = [_fixu(x, y) for x, y in t['reset']['local_taps_um']]
for s in t.get('count_straps', []):
    s['sites_um'] = [fix(x, y) for x, y in s['sites_um']]
moved.append(('reset', t['reset']['local_taps_um']))
t['note'] = t.get('note', '') + ' | HEAD-97 rp21 (rp21x proof GRT: the 555-bit lane tx -> lo -> head path crossed u_epc, which blocks M1-M7 with M8 grant-only = 0 H capacity): head SRAM column moved W of u_epc next to sf, u_epc to the E edge (no E-face pins)'
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
print('host_e head x', hx, 'epc x', ex, 'street head-epc', round(ex - hx1, 3)); print(json.dumps(moved))
