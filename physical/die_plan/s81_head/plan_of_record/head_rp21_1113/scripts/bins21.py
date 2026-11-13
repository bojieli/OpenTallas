"""HEAD-97 rp21: remap the hd_tile clock sink census (bins) to the rp21 hd_tile form with the ev21.py map (bins within
4.32 of an old core move with it; else W edge <= 17.28 stays, E edge >= 691.2 +D, interior +DM); a bin that would land
inside a new core is pushed to the nearest strip edge + 5.4.  Writes the event census and points the plan at it."""
import json, sys, hashlib, os
plan, repo, out_rel = sys.argv[1:4]
WS = float(os.environ.get('WS', '21.6')); ES = float(os.environ.get('ES', '21.6'))
NEWW = WS + 319.68 + 43.2 + 319.68 + ES; D = NEWW - 708.48; DM = WS - 17.28; XA1 = WS + 319.68 + 43.2
P = json.load(open(plan)); t = P['partition_types']['hd_tile']; ck = t['clock']
src = ck['sink_bins_file']; d = json.load(open(repo + '/' + src))
OLD = {'eA0': (17.28, 8.64, 319.68), 'eA1': (362.88, 8.64, 319.68), 'eA2': (17.28, 380.16, 319.68), 'eA3': (371.52, 380.16, 319.68), 'eB': (216.0, 734.4, 285.12)}
NEW = {'eA0': WS, 'eA1': XA1, 'eA2': WS, 'eA3': XA1, 'eB': 216.0 + DM}
H = 4.32
def mv(x, y):
    for k, (ox, oy, s) in OLD.items():
        if ox - H <= x <= ox + s + H and oy - H <= y <= oy + s + H: return round(x + NEW[k] - ox, 4)
    if x >= 691.2: return round(x + D, 4)
    if x <= 17.28: return x
    return round(x + DM, 4)
nb, pushed = [], 0
for x, y, n in d['bins']:
    nx = mv(x, y)
    for c, cx in NEW.items():
        oy, s = OLD[c][1], OLD[c][2]
        if cx < nx < cx + s and oy < y < oy + s:
            nx = round(cx - 5.4 if nx - cx < cx + s - nx else cx + s + 5.4, 4); pushed += 1
    nb.append([nx, y, n])
d['bins'] = nb
d['source'] = d['source'] + ' | HEAD-97 rp21 remap to the rp21 hd_tile form (%.2f wide), from %s' % (NEWW, src)
d['remap_from_sha256'] = hashlib.sha256(open(repo + '/' + src, 'rb').read()).hexdigest()
open(repo + '/' + out_rel, 'w').write(json.dumps(d, indent=1) + '\n')
ck['sink_bins_file'] = out_rel
json.dump(P, open(plan, 'w'), indent=1); open(plan, 'a').write('\n')
print('bins', len(nb), 'pushed', pushed, 'x range', min(b[0] for b in nb), max(b[0] for b in nb))
