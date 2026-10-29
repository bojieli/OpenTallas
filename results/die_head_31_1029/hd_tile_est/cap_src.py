# for captures matching REGEX: launch-flop envelope (u=x+y, v=x-y min/max) -> feasible region to stay <=405 from all launchers
import sys, re
sys.path.insert(0, sys.argv[1]); import geom_rules as G
D = G.Design(sys.argv[2]); pat = re.compile(sys.argv[3])
from collections import defaultdict, deque, Counter
seq = {cid for cid, c in D.cells.items() if c[0] == 'S'}; comb = {cid for cid, c in D.cells.items() if c[0] in "BLK"}
def b(cid):
    x, y = G.ctr(D.cells[cid]); return x+y, x+y, x-y, x-y
st = {}; indeg = Counter(); succ = defaultdict(list)
for cid in comb:
    for n in D.drives.get(cid, []):
        for s in D.nets[n][2]:
            if s[0] == "i" and not s[2] and s[1] in comb: succ[cid].append(s[1]); indeg[s[1]] += 1
def merge(dst, e):
    o = st.get(dst)
    if o is None: st[dst] = list(e); return
    o[0] = min(o[0], e[0]); o[1] = max(o[1], e[1]); o[2] = min(o[2], e[2]); o[3] = max(o[3], e[3])
caps = defaultdict(list); fo = defaultdict(list)
for cid in seq:
    e = b(cid)
    for n in D.drives.get(cid, []):
        for s in D.nets[n][2]:
            if s[0] != "i" or s[2]: continue
            if s[1] in seq: caps[s[1]].append(e); fo[cid].append(s[1])
            elif s[1] in comb: merge(s[1], e)
dq = deque(c for c in comb if indeg[c] == 0)
while dq:
    cid = dq.popleft(); e = st.get(cid)
    for n in D.drives.get(cid, []):
        for s in D.nets[n][2]:
            if s[0] != "i" or s[2]: continue
            if e is not None:
                if s[1] in seq: caps[s[1]].append(e)
                elif s[1] in comb: merge(s[1], e)
    for t in succ.get(cid, []):
        indeg[t] -= 1
        if indeg[t] == 0: dq.append(t)
for cid, c in sorted(D.cells.items(), key=lambda k: k[1][6]):
    if cid in seq and pat.search(c[6]):
        L = caps.get(cid, [])
        if not L: print(c[6], 'no launchers'); continue
        u0 = min(e[0] for e in L); u1 = max(e[1] for e in L); v0 = min(e[2] for e in L); v1 = max(e[3] for e in L)
        x, y = G.ctr(c)
        print(c[6], 'at', round(x,1), round(y,1), 'launch u[%.0f,%.0f] v[%.0f,%.0f] n=%d' % (u0, u1, v0, v1, len(L)))
