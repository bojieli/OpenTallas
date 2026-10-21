#!/usr/bin/env python3
"""greedy refinement of a legal placement with the realistic stand-in pin model of hr_parent (cost = wirelength + 300 x bits>405)."""
import contextlib, io, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hr_parent as HP
import hr_anneal as HA

src, out, iters, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
V0 = json.load(open(src))
_, blocks0 = HP.load(src)
nets = HP.net_members(blocks0)
geo = {k: (b['w'], b['h']) for k, b in blocks0.items()}
rnd = random.Random(seed)

def legal(place, PW, PH):
    L = list(place)
    for i, a in enumerate(L):
        xa, ya, _ = place[a]; wa, ha = geo[a]
        if xa < 21.6 or ya < 21.6 or xa + wa > PW - 21.6 or ya + ha > PH - 21.6:
            return False
        for b in L[i + 1:]:
            xb, yb, _ = place[b]; wb, hb = geo[b]
            if min(xa + wa + 21.6, xb + wb + 21.6) - max(xa, xb) > 1e-6 and min(ya + ha + 21.6, yb + hb + 21.6) - max(ya, yb) > 1e-6:
                return False
    return True

def cost(place):
    V = dict(V0); V['place'] = place
    blocks = {k: dict(b, pins={} if b['standin'] else b['pins']) for k, b in blocks0.items()}
    for k, p in place.items():
        blocks[k].update(x=p[0], y=p[1], o=p[2])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            HP.assign_standins(V, blocks, nets)
            rows, over, _, _ = HP.evaluate(V, blocks, nets, quiet=True)
    except SystemExit:
        return 1e18
    return sum(n * m for mx, m, n, k in rows if k[0] != 'BROADCAST') + 300 * over

PW, PH = V0['outline']
place = {k: list(v) for k, v in V0['place'].items()}
cur = cost(place); print('start', round(cur), flush=True)
names = list(place)
for it in range(iters):
    a = rnd.choice(names); np_ = {k: list(v) for k, v in place.items()}
    r = rnd.random()
    if r < 0.6:
        np_[a][0] = round(np_[a][0] + 43.2 * rnd.choice((-2, -1, 1, 2)), 3) if rnd.random() < .5 else np_[a][0]
        np_[a][1] = round(np_[a][1] + 43.2 * rnd.choice((-2, -1, 1, 2)), 3) if rnd.random() < .5 else np_[a][1]
    elif r < 0.85:
        np_[a][2] = rnd.choice(('R0', 'MX', 'MY', 'R180'))
    else:
        b = rnd.choice(names)
        if geo[a] == geo[b]:
            np_[a], np_[b] = np_[b], np_[a]
        else:
            continue
    if not legal(np_, PW, PH):
        continue
    c = cost(np_)
    if c < cur:
        place, cur = np_, c
        print(it, round(cur), flush=True)
V0['place'] = place
json.dump(V0, open(out, 'w'), indent=1)
print('final', round(cur))
