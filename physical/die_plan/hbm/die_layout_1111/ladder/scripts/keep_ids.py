"""Ladder post-step: a rebuilt port whose NEIGHBOUR end (non-bank part, its bus, face, window, layers, width) is
identical to a dropped old port of the same lane takes the old port id back, so pre-existing per-port G0 rows keep
their keys.  usage: keep_ids.py BASE.json NEW.json OUT.json"""
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
oldp = {p['id']: p for p in a['ports']}
newids = {p['id'] for p in b['ports']}
def nb_key(p):
    for sd in ('src', 'dst'):
        if '_b0' not in p[sd]['part'] or p[sd]['part'].endswith(('hub',)):
            if '_b0' not in p[sd]['part']:
                return (sd, p[sd]['part'], p[sd]['bus'], p.get('face'), json.dumps(p.get('window_um')), json.dumps(p.get('layers')), p['width'])
    return None
dropped = {pid: p for pid, p in oldp.items() if pid not in newids}
ren = {}
for p in b['ports']:
    if p['id'] in oldp:
        continue
    k = nb_key(p)
    if k is None:
        continue
    lane = p['id'].rsplit('_', 1)[0]
    c = [q for q in dropped.values() if q['id'].rsplit('_', 1)[0] == lane and nb_key(q) == k and q['id'] not in ren.values()]
    if len(c) == 1:
        ren[p['id']] = c[0]['id']
for p in b['ports']:
    if p['id'] in ren:
        p['id'] = ren[p['id']]
for ln in b['lanes']:
    ln['ports'] = [ren.get(x, x) for x in ln['ports']]
open(sys.argv[3], 'w').write(json.dumps(b, indent=1) + '\n')
print('renamed', len(ren), sorted(ren.items())[:10])
