import sys, json, re
sys.path.insert(0, sys.argv[1]); import geom_rules as G
D = G.Design(sys.argv[2])
R = G.R2R_MAX
# monkeypatch: capture per-capture worst by re-running r2r_metrics internals: copy minimal version
from collections import defaultdict, deque, Counter
seq = {cid for cid, c in D.cells.items() if c[0] == 'S'}
comb = {cid for cid, c in D.cells.items() if c[0] in "BLK"}
def b(cid):
    x, y = G.ctr(D.cells[cid]); return x+y, x+y, x-y, x-y
st = {}; indeg = Counter(); succ = defaultdict(list)
for cid in comb:
    for n in D.drives.get(cid, []):
        for s in D.nets[n][2]:
            if s[0] == "i" and not s[2] and s[1] in comb:
                succ[cid].append(s[1]); indeg[s[1]] += 1
def merge(dst, u0,u1,v0,v1,a,b_,c_,d_):
    e = st.get(dst)
    if e is None: st[dst] = [u0,u1,v0,v1,a,b_,c_,d_]; return
    if u0 < e[0]: e[0], e[4] = u0, a
    if u1 > e[1]: e[1], e[5] = u1, b_
    if v0 < e[2]: e[2], e[6] = v0, c_
    if v1 > e[3]: e[3], e[7] = v1, d_
caps = defaultdict(list)
for cid in seq:
    u0,u1,v0,v1 = b(cid)
    for n in D.drives.get(cid, []):
        for s in D.nets[n][2]:
            if s[0] != "i" or s[2]: continue
            if s[1] in seq: caps[s[1]].append((u0,u1,v0,v1,cid,cid,cid,cid))
            elif s[1] in comb: merge(s[1],u0,u1,v0,v1,cid,cid,cid,cid)
dq = deque(c for c in comb if indeg[c] == 0)
while dq:
    cid = dq.popleft(); e = st.get(cid)
    for n in D.drives.get(cid, []):
        for s in D.nets[n][2]:
            if s[0] != "i" or s[2]: continue
            if e is not None:
                if s[1] in seq: caps[s[1]].append(tuple(e))
                elif s[1] in comb: merge(s[1], *e)
    for t in succ.get(cid, []):
        indeg[t] -= 1
        if indeg[t] == 0: dq.append(t)
nm = lambda i: D.cells[i][6]
out = []
for cap, lst in caps.items():
    u0,u1,v0,v1 = b(cap); mx, src = 0, None
    for e in lst:
        for val, s in ((u1-e[0],e[4]),(e[1]-u0,e[5]),(v1-e[2],e[6]),(e[3]-v0,e[7])):
            if val > mx: mx, src = val, s
    if mx > R: out.append((round(mx,1), nm(src), [round(v,1) for v in G.ctr(D.cells[src])], nm(cap), [round(v,1) for v in G.ctr(D.cells[cap])]))
out.sort(reverse=True)
for o in out: print(*o, sep='\t')
pat = re.compile(sys.argv[3]) if len(sys.argv) > 3 else None
if pat:
    print('--- cells')
    for cid, c in D.cells.items():
        if pat.search(c[6]): print(c[0], c[1], [round(v,1) for v in G.ctr(c)], c[6])
