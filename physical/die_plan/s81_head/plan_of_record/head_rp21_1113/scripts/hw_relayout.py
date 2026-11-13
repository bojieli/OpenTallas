"""HEAD-97 rp21 (COORD GEOM-REVIEW 09:3x + R-STREET-6): hd_host_w macros re-drawn centred on the outline instead of
filling the W 55%: the 36 collector SRAMs (256x64) as a 3 x 3 grid of abutted 2 x 2 blocks (38.88 x 43.2 pitch,
>= 43.2 streets), centred in y, x 69.12-380.3 (8.64 lattice, abutment via track_offset); the 19 lane SRAMs (32x64) as two columns near the E (l1) face in
abutted blocks of <= 4 (21.6 pitch, 43.2 streets): head x 449.28 (MY: wd_in faces the rb_safe array), sf x 544.32.  Outline unchanged.  Plan points that
would sit inside a macro (taps, straps, reset local taps) move to the nearest point >= 8.64 off every macro."""
import json, sys, math
src, out = sys.argv[1:3]
P = json.load(open(src)); t = P['partition_types']['hd_host_w']; W, H = t['outline_um']
G = 8.64; up = lambda v: round(math.ceil(v / G - 1e-9) * G, 4)
hc = t['hard_cores']
big = sorted([h for h in hc if h['outline_um'][0] > 34], key=lambda h: h['inst'])
lsf = sorted([h for h in hc if '.u_sf.' in h['inst']], key=lambda h: h['inst'])
lhd = sorted([h for h in hc if '.u_head.' in h['inst']], key=lambda h: h['inst'])
assert len(big) == 36 and len(lsf) == 10 and len(lhd) == 9 and len(hc) == 55
bw, bh = 34.584, 41.352; px, py = 34.56, 43.2          # x abutment closed by +0.024 track offset
bx = up(px + bw + 0.024 + 43.2); by = up(py + bh + 43.2)
tot_h = 2 * by + py + bh; y0 = round(math.floor((H - tot_h) / 2 / G) * G, 4); x0 = 69.12
k = 0
for j in range(3):
    for i in range(3):
        for (a, b) in ((0, 0), (0, 1), (1, 0), (1, 1)):
            h = big[k]; k += 1
            ox, oy = (h.get('track_offset_um') or [0.0, 0.0])
            h['origin_um'] = [round(x0 + i * bx + a * px, 4), round(y0 + j * by + b * py, 4)]
            h['track_offset_um'] = [round(0.108 + 0.024 * a, 4), round(oy, 4)]
def col(ms, x, blocks, mh=17.304, street=43.2):
    y, i = y0, 0
    for n in blocks:
        for q in range(n):
            h = ms[i]; i += 1
            ox, oy = (h.get('track_offset_um') or [0.0, 0.0])
            h['origin_um'] = [x, round(y + q * 17.28, 4)]; h['track_offset_um'] = [ox, round(0.012 + 0.048 * q, 4)]
        y = up(y + (n - 1) * 17.28 + 0.012 + 0.048 * (n - 1) + mh + street)
col(lhd, 449.28, [3, 3, 3]); col(lsf, 544.32, [4, 3, 3])
for h in lhd: h['orient'] = 'MY'      # wd_in faces W, toward its rb_safe partner banks in the array
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
    s['sites_um'] = [fix(x, y) for x, y in s['sites_um']]
moved.append(('reset', t['reset']['local_taps_um']))
t['note'] = t.get('note', '') + ' | HEAD-97 rp21 (GEOM-REVIEW 09:3x, R-STREET-6): macros centred: collector SRAMs 3x3 abutted 2x2 blocks, lane SRAMs two E columns in abutted blocks <= 4'
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
print('y0', y0, 'array', x0, y0, x0 + 2 * bx + px + bw + 0.132, y0 + tot_h); print(json.dumps(moved))
