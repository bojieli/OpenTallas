"""HEAD-97 rp21: hd_host_e SRAM arrays re-blocked per R-STREET-6 (abutted blocks of <= 4, 43.2 streets between blocks),
on the 8.64 plan lattice: block macros at 17.28 pitch, abutment closed by the sub-lattice track_offset (+0.048 (one M4 track) per
macro in y, < 2.16 BASE_LATTICE), blocks start on the lattice.  Macros move only inside their own column; column x
snapped down to the lattice.  head banks 0..8: 3+3+3 from y 103.68; sf banks 9,0..8: 4+3+3 from y 216.0."""
import json, sys, math
src, out = sys.argv[1:3]
P = json.load(open(src)); t = P['partition_types']['hd_host_e']
G = 8.64; up = lambda v: round(math.ceil(v / G - 1e-9) * G, 4); dn = lambda v: round(math.floor(v / G + 1e-9) * G, 4)
def place(ms, start, blocks, mh=17.304, street=43.2):
    y, i = start, 0
    for n in blocks:
        for j in range(n):
            h = ms[i]; i += 1
            ox, oy = (h.get('track_offset_um') or [0.0, 0.0])
            h['origin_um'] = [dn(h['origin_um'][0]), round(y + j * 17.28, 4)]
            h['track_offset_um'] = [ox, round(0.012 + 0.048 * j, 4)]
        top = y + (n - 1) * 17.28 + 0.012 + 0.048 * (n - 1) + mh
        y = up(top + street)
head = sorted([h for h in t['hard_cores'] if '.u_head.g_bank[' in h['inst']], key=lambda h: h['origin_um'][1])
sf = sorted([h for h in t['hard_cores'] if '.u_sf.g_bank[' in h['inst']], key=lambda h: h['origin_um'][1])
assert len(head) == 9 and len(sf) == 10
place(head, 103.68, [3, 3, 3]); place(sf, 216.0, [4, 3, 3])
for h in t['hard_cores']:
    x, y = h['origin_um']
    if abs(x / G - round(x / G)) > 1e-6 or abs(y / G - round(y / G)) > 1e-6:
        h['origin_um'] = [dn(x), dn(y)]; print('snapped', h['inst'][-30:], [x, y], '->', h['origin_um'])
print('head', [h['origin_um'] for h in head]); print('sf', [h['origin_um'] for h in sf])
t['note'] = t.get('note', '') + ' | HEAD-97 rp21: SRAM arrays re-blocked (R-STREET-6: abutted blocks <= 4 via track_offset, 43.2 streets, 8.64 lattice) after the street_rule legalize'
json.dump(P, open(out, 'w'), indent=1); open(out, 'a').write('\n')
