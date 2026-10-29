# list launch flops (through comb) of the captures matching REGEX, with xy and whether they are in the relay targets
import sys, re
sys.path.insert(0, sys.argv[1]); import geom_rules as G
D = G.Design(sys.argv[2]); pat = re.compile(sys.argv[3]); tg = {l.split('\t')[0] for l in open(sys.argv[4])}
seq = {cid for cid, c in D.cells.items() if c[0] == 'S'}
drv = {}
for cid in D.cells:
    for n in D.drives.get(cid, []): drv[n] = cid
ins = {}
for n, net in (D.nets.items() if isinstance(D.nets, dict) else enumerate(D.nets)):
    for s in net[2]:
        if s[0] == 'i' and not s[2]: ins.setdefault(s[1], []).append(n)
from collections import Counter
agg = Counter(); ex = {}
for cid, c in D.cells.items():
    if cid not in seq or not pat.search(c[6]): continue
    st = list(ins.get(cid, [])); seen = set(); L = set()
    while st:
        n = st.pop()
        if n in seen: continue
        seen.add(n); d = drv.get(n)
        if d is None: continue
        if d in seq: L.add(d)
        elif D.cells[d][0] in 'BLK': st += ins.get(d, [])
    for l in L:
        nm = re.sub(r'\\\[\d+\\\]', '[*]', D.cells[l][6]); agg[nm] += 1
        x, y = G.ctr(D.cells[l]); ex.setdefault(nm, []).append((round(x), round(y), D.cells[l][6] in tg))
for nm, k in agg.most_common(40):
    xs = ex[nm]; print(k, nm, 'x', min(a for a,_,_ in xs), max(a for a,_,_ in xs), 'y', min(b for _,b,_ in xs), max(b for _,b,_ in xs), 'targeted', sum(t for *_,t in xs))
