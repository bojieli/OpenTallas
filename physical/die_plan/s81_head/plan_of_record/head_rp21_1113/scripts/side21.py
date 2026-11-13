"""HEAD-97 rp21: carry the landed sidecar to the stretched die: each region box_um = union of the NEW boxes of the
partitions whose OLD box lies in the old region box (part count must match); everything else unchanged."""
import json, sys
old, new, sin, sout = sys.argv[1:5]
A, B, S = (json.load(open(p)) for p in (old, new, sin))
def boxes(P):
    T = P['partition_types']; o = {}
    for p in P['partitions']:
        w, h = T[p['type']]['outline_um']
        if p.get('orient', 'R0') in ('R90', 'R270', 'MXR90', 'MYR90'): w, h = h, w
        x, y = p['origin_um']; o[p['name']] = (x, y, x + w, y + h)
    return o
ba, bb = boxes(A), boxes(B); bad = []
for r in S['regions']:
    x0, y0, x1, y1 = r['box_um']
    m = [n for n, b in ba.items() if b[0] >= x0 - .01 and b[1] >= y0 - .01 and b[2] <= x1 + .01 and b[3] <= y1 + .01]
    if len(m) != r['parts']:
        ov = [n for n, b in ba.items() if b[0] < x1 and x0 < b[2] and b[1] < y1 and y0 < b[3]]
        dx = {round(bb[n][0] - ba[n][0], 4) for n in ov}
        if r['parts'] == 1 and len(dx) == 1:
            d = dx.pop(); r['box_um'] = [round(x0 + d, 4), y0, round(x1 + d, 4), y1]; bad.append((r['tag'], 'shift', d, ov)); continue
        bad.append((r['tag'], r['parts'], len(m))); continue
    r['box_um'] = [round(min(bb[n][0] for n in m), 4), round(min(bb[n][1] for n in m), 4), round(max(bb[n][2] for n in m), 4), round(max(bb[n][3] for n in m), 4)]
print('regions', len(S['regions']), 'bad', bad[:10], len(bad))
print('collector types', sorted((S.get('collector') or {}).get('types', {}).keys()))
json.dump(S, open(sout, 'w'))
