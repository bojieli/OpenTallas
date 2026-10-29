"""HBM-BIND-8 estimate: for every GLUE cell on an UNPLANNED crossing (census.json), the best whole-cell re-home among
the partitions it connects to, scored by data-bit connections that would be FAR (no shared edge and gap > near_um).
Leaf (plan hard core) cells cannot move by a bind map: they are listed as plan-side. Plan arithmetic only (UNCHECKED
until a strict rebind)."""
import sys, json, collections
from pathlib import Path
w, plan, cen = sys.argv[1:4]
near = float(sys.argv[4]) if len(sys.argv) > 4 else 1200.0
sys.path.insert(0, str(Path(w) / 'tools/die_plan'))
import schema as S, lane_add as LA
P = S.Plan(json.loads(Path(plan).read_text()))
c = json.loads(Path(cen).read_text())
memo = {}
def far(a, b):
    if a == b: return False
    k = (a, b) if a < b else (b, a)
    if k not in memo:
        memo[k] = LA.shared_edge(P, a, b) is None and LA.gap_um(P, a, b) > near
    return memo[k]
moves, gain_tot = [], 0
for path, x in c['cells'].items():
    if x['kind'] != 'glue': continue
    conn = collections.Counter(x['inb']) + collections.Counter(x['outb'])
    cost = lambda h: sum(n for q, n in conn.items() if far(h, q))
    if not conn: continue
    cur = cost(x['part'])
    best = min(conn, key=lambda h: (cost(h), h != x['part']))
    if cost(best) < cur:
        moves.append(dict(path=path, frm=x['part'], to=best, far_before=cur, far_after=cost(best), conn=dict(conn)))
        gain_tot += cur - cost(best)
by = collections.Counter()
for m in moves: by[(m['frm'], m['to'])] += m['far_before'] - m['far_after']
print('glue cells on unplanned crossings', sum(1 for x in c['cells'].values() if x['kind'] == 'glue'),
      'leaf', sum(1 for x in c['cells'].values() if x['kind'] == 'leaf'))
print('moves', len(moves), 'far-bit-connection gain', gain_tot)
for k, v in by.most_common(40): print('  ', k, v)
json.dump(dict(near_um=near, moves=moves), open(Path(cen).with_name('rehome_est.json'), 'w'), indent=0)
