import json, sys, collections
d = json.load(open(sys.argv[1]))
m = d['modules'][sys.argv[2]]
cells = m['cells']
FF = {'$adff', '$dff', '$sdff', '$dffe', '$adffe', '$aldff', '$sdffe', '$sdffce', '$dffsr'}
drv = {}    # bit -> (cell, port)
loads = collections.defaultdict(list)
for cn, c in cells.items():
    for p, bits in c['connections'].items():
        dirn = c.get('port_directions', {}).get(p)
        for b in bits:
            if isinstance(b, str): continue
            if dirn == 'output': drv[b] = (cn, p)
            else: loads[b].append((cn, p))
portbits = set()
for pn, p in m['ports'].items():
    for b in p['bits']:
        if not isinstance(b, str): portbits.add(b)
ffs = {cn for cn, c in cells.items() if c['type'] in FF}
types = collections.Counter(c['type'] for c in cells.values())
print('cell types', types.most_common(12))
def ok(cn):
    c = cells[cn]
    if c['type'] != '$adff': return False
    for b in c['connections']['D']:
        if isinstance(b, str): return False
        dv = drv.get(b)
        if not dv or dv[0] not in ffs or dv[1] != 'Q': return False
    for b in c['connections']['Q']:
        if b in portbits: return False
        L = loads.get(b, [])
        if not L: return False
        for (ln, lp) in L:
            if ln not in ffs or lp != 'D': return False
    return True
pipe = sorted(cn for cn in ffs if ok(cn))
w = collections.Counter(); bits = 0
for cn in pipe:
    n = len(cells[cn]['connections']['Q']); w[n] += 1; bits += n
allbits = sum(len(cells[cn]['connections']['Q']) for cn in ffs)
print('ff cells', len(ffs), 'ff bits', allbits)
print('pipe cells', len(pipe), 'pipe bits', bits, 'width hist', sorted(w.items()))
# clocks/resets used by pipe
ck = collections.Counter(); ar = collections.Counter(); rv = collections.Counter()
for cn in pipe:
    c = cells[cn]
    ck[tuple(c['connections']['CLK'])] += 1; ar[tuple(c['connections']['ARST'])] += 1
    rv[(c['parameters'].get('ARST_VALUE','?')[:8], c['parameters'].get('ARST_POLARITY'))] += 1
print('clocks', ck); print('arst', ar); print('rstval', rv)
with open(sys.argv[3], 'w') as f:
    for cn in pipe: f.write(f"{sys.argv[2]}/{cn}\n")
# boundary bits
inb = set(); outb = set(); pset = set(pipe)
for cn in pipe:
    for b in cells[cn]['connections']['D']:
        if drv[b][0] not in pset: inb.add(b)
    for b in cells[cn]['connections']['Q']:
        if any(ln not in pset for ln, _ in loads[b]): outb.add(b)
print('seam in bits', len(inb), 'seam out bits', len(outb))
