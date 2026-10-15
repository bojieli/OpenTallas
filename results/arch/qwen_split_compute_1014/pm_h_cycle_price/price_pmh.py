import json, re, sys
from pathlib import Path
from orientation_search import Graph, load
from pair_mirror import build
d, sha = load(Path(sys.argv[1])); g = Graph(d, d['constraints']['per_hop_um'])
base = {n: dict(i) for n, i in g.inst.items()}
def stagemap(m):
    ev = g.evaluate(m)
    return {g.data[k]['b']: ev[k][2] + 1 for k in range(len(ev))}, {b['b']: b['e'] for b in d['buses']}
def cost(S, B):
    s = lambda b: S.get(b, 1)
    COLS, ROWS = 48, 16; hc, hr = 24, 8
    head = {}
    for side, cols in (('W', range(hc-1, -1, -1)), ('E', range(hc, COLS))):
        acc = 0
        for c in cols:
            acc += s(f'head_{c}'); head[c] = acc
    bd, at = 0, None
    for c in range(COLS):
        a_s = a_n = head[c]
        for r in range(hr-1, -1, -1):
            a_s += s(f'cor_{c}_{r}')
            if a_s + s(f'tap_{c}_{r}') > bd: bd, at = a_s + s(f'tap_{c}_{r}'), (c, r)
        for r in range(hr, ROWS):
            a_n += s(f'cor_{c}_{r}')
            if a_n + s(f'tap_{c}_{r}') > bd: bd, at = a_n + s(f'tap_{c}_{r}'), (c, r)
    # per-side worst
    side = {}
    for c in range(COLS):
        a_s = a_n = head[c]; best = 0
        for r in range(hr-1, -1, -1):
            a_s += s(f'cor_{c}_{r}'); best = max(best, a_s + s(f'tap_{c}_{r}'))
        for r in range(hr, ROWS):
            a_n += s(f'cor_{c}_{r}'); best = max(best, a_n + s(f'tap_{c}_{r}'))
        k = 'W' if c < hc else 'E'; side[k] = max(side.get(k, 0), best)
    blocks = {}
    for b in S:
        mm = re.match(r'tree_(\d+)_(\d+)_(\d+)([ab])$', b)
        if mm: blocks.setdefault(int(mm[1]), []).append(b)
    tree = 0
    for nb, legs in blocks.items():
        out = {}
        for b in sorted(legs, key=lambda q: int(q.split('_')[2])):
            src, dst = B[b][0], B[b][-1]
            t0 = out.get(src[0], 0) if src[1] == 'n_y' else 0
            out[dst[0]] = max(out.get(dst[0], 0), t0 + s(b))
        tree = max(tree, max(out.values()))
    bw = max((v for b, v in S.items() if re.match(r'bword_\d+$', b)), default=None)
    return dict(bd=bd, bd_at=at, bd_side=side, tree=tree, bword_max=bw)
S0, B = stagemap(base); m, _ = build(base, keep_rows=(7, 8)); S1, _ = stagemap(m)
c0, c1 = cost(S0, B), cost(S1, B)
print(json.dumps(dict(input_sha256=sha, baseline=c0, pm_h=c1), default=str))
print('missing names', [n for n in ('head_0','cor_0_6','tap_0_0','tree_0_0_0a') if n not in S0])
#, B[next(b for b in S0 if b.startswith('tree_'))]['ends'] if any(b.startswith('tree_') for b in S0) else None)
