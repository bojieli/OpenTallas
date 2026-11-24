# openroad -python is not enough for TCL rows: this checks the netlist equivalence of a relay_split run (BEFORE / AFTER odb).
# every data pin of every logic/flop/macro sink must trace back (through BUF/INV) to the same flop name modulo __rs<n>, same
# polarity; every copy has the same D / CLK / async nets (by name) as its source flop.
import os, re, odb
def load(p):
    d = odb.dbDatabase.create(); odb.read_db(d, p); return d, d.getChip().getBlock()
def seq(i): return 'DFF' in i.getMaster().getName()
def rep(i):
    n = i.getMaster().getName(); return n.startswith('BUF') or n.startswith('INV')
def drv(net):
    for it in net.getITerms():
        if it.isOutputSignal(): return it
    return None
def root(net):
    p = 0
    for _ in range(200):
        d = drv(net)
        if d is None: return ('port:' + (net.getBTerms()[0].getName() if len(net.getBTerms()) else net.getName()), p)
        i = d.getInst()
        if i.getMaster().isBlock() or not rep(i): return (i.getName() + '/' + d.getMTerm().getName(), p)
        p ^= i.getMaster().getName().startswith('INV')
        ins = [x for x in i.getITerms() if not x.isOutputSignal() and x.getSigType() == 'SIGNAL']
        net = ins[0].getNet()
        if net is None: return ('FLOAT:' + i.getName(), p)
    return ('LOOP', p)
norm = lambda n: re.sub(r'__rs\d+', '', n)
def table(b):
    T = {}; cache = {}
    for i in b.getInsts():
        if rep(i) and not i.getMaster().isBlock(): continue
        for it in i.getITerms():
            if it.isOutputSignal() or it.getSigType() in ('POWER', 'GROUND'): continue
            n = it.getNet()
            if n is None: T[(i.getName(), it.getMTerm().getName())] = None; continue
            c = cache.get(n.getId())
            if c is None: c = cache[n.getId()] = root(n)
            T[(i.getName(), it.getMTerm().getName())] = c
    for bt in b.getBTerms():
        if bt.getIoType() == 'OUTPUT' and bt.getNet(): T[('port', bt.getName())] = root(bt.getNet())
    return T
_d0, b0 = load(os.environ['A']); _d1, b1 = load(os.environ['B'])
T0, T1 = table(b0), table(b1); bad = 0; moved = 0
for k, v in T1.items():
    if '__rs' in k[0] and k[0] not in {x[0] for x in ()}:
        o = T0.get((norm(k[0]), k[1]))
        if o is None or (norm(v[0]), v[1]) != (norm(o[0]), o[1]): bad += 1; print('COPY_IN', k, v, o) if bad < 10 else None
        continue
    if k not in T0: bad += 1; print('NEW', k, v) if bad < 10 else None; continue
    o = T0[k]
    if v is None or o is None:
        bad += (v != o); continue
    if (norm(v[0]), v[1]) != (norm(o[0]), o[1]): bad += 1; print('DIFF', k, v, o) if bad < 10 else None
    elif v[0] != o[0]: moved += 1
miss = [k for k in T0 if k not in T1]
print(f"RS_LOCKSTEP pins {len(T1)} moved {moved} copies {len({k[0] for k in T1 if '__rs' in k[0]})} missing {len(miss)} bad {bad} {'PASS' if not bad and not miss and moved else 'FAIL'}")
