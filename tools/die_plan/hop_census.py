# openroad -python: census of register-to-register hops with NO logic (only BUF/INV/HB between), by name class.
# Generic long-hop / crossing-net preflight (GENBUG guard).  env ODB TAG [REACH=405]
import os, re, sys, odb, collections
db = odb.dbDatabase.create(); odb.read_db(db, os.environ['ODB'])
blk = db.getChip().getBlock(); dbu = blk.getDbUnitsPerMicron(); tag = os.environ.get('TAG', ''); REACH = float(os.environ.get('REACH', '405'))
macros = []
for i in blk.getInsts():
    if i.getMaster().isBlock():
        b = i.getBBox(); macros.append((b.xMin() / dbu, b.yMin() / dbu, b.xMax() / dbu, b.yMax() / dbu, i.getName()))
def loc(i):
    b = i.getBBox(); return ((b.xMin() + b.xMax()) / 2 / dbu, (b.yMin() + b.yMax()) / 2 / dbu)
def is_rep(i):
    n = i.getMaster().getName(); return n.startswith('BUF') or n.startswith('INV') or n.startswith('HB')
def is_seq(i):
    n = i.getMaster().getName(); return 'DFF' in n or 'DLL' in n or 'DHL' in n or 'LATCH' in n
def tloc(it):
    if it.getInst().getMaster().isBlock():
        b = it.getBBox(); return ((b.xMin() + b.xMax()) / 2 / dbu, (b.yMin() + b.yMax()) / 2 / dbu)
    return loc(it.getInst())
def cls(nm):
    nm = nm.replace('\\', '')
    nm = re.sub(r'^u_bound[./]', '', nm)
    nm = re.sub(r'\$_.*$', '', nm)
    nm = re.sub(r'\[\d+\]', '[#]', nm)
    nm = re.sub(r'\d+', '#', nm)
    p = re.split(r'[./]', nm)
    return '.'.join(p[:2])[:44]
def back(i):
    """(driver kind, name, loc, n_rep) of the data input through repeaters; None if logic."""
    cur = i; nb = 0
    for _ in range(80):
        net = None
        for it in cur.getITerms():
            if not it.isInputSignal() or it.getNet() is None or it.getNet().getSigType() != 'SIGNAL': continue
            if it.getMTerm().getName() in ('CLK', 'RESETN', 'SETN'): continue
            if net is not None: return None   # more than one data input on a repeater? not a repeater
            net = it.getNet()
        if net is None: return None
        d = None
        for o in net.getITerms():
            if o.isOutputSignal(): d = o
        if d is None:
            bts = net.getBTerms()
            if not bts: return None
            bb = bts[0].getBBox(); return ('port', bts[0].getName(), ((bb.xMin() + bb.xMax()) / 2 / dbu, (bb.yMin() + bb.yMax()) / 2 / dbu), nb)
        di = d.getInst()
        if di.getMaster().isBlock(): return ('core', di.getName() + '/' + d.getMTerm().getName(), tloc(d), nb)
        if is_seq(di): return ('reg', di.getName(), loc(di), nb)
        if not is_rep(di): return None
        cur = di; nb += 1
    return None
def crosses(a, b):
    for x0, y0, x1, y1, n in macros:
        if min(a[0], b[0]) < x0 and max(a[0], b[0]) > x1 and max(min(a[1], b[1]), y0) < min(max(a[1], b[1]), y1) + 1e-9 and min(a[1], b[1]) >= y0 - 1 and max(a[1], b[1]) <= y1 + 1: return n
        if min(a[1], b[1]) < y0 and max(a[1], b[1]) > y1 and min(a[0], b[0]) >= x0 - 1 and max(a[0], b[0]) <= x1 + 1: return n
    return None
G = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0, 0]); tot = 0; over = 0; xs = 0
for i in blk.getInsts():
    if i.getMaster().isBlock() or not is_seq(i): continue
    r = back(i)
    if r is None: continue
    kind, dn, dl, nb = r; l = loc(i); d = abs(l[0] - dl[0]) + abs(l[1] - dl[1]); tot += 1
    firm = i.getPlacementStatus() in ('FIRM', 'LOCKED')
    k = ((kind + ':' + cls(dn)) if kind != 'port' else 'port:' + re.sub(r'\d+', '#', dn)[:30], cls(i.getName()))
    g = G[k]; g[0] += 1; g[3] = max(g[3], d)
    if d > REACH:
        g[1] += 1; over += 1; g[4] += 1 if firm else 0; g[5] = max(g[5], nb)
        if crosses(dl, l): g[2] += 1; xs += 1
print('HOP\t%s\tsrc_class\tsink_class\thops\tover_%d\tcross_core\tmax_um\tsink_firm\tmax_rep' % (tag, REACH))
for k, g in sorted(G.items(), key=lambda x: -x[1][1])[:int(os.environ.get('TOP', '10'))]:
    if g[1]: print('HOP\t%s\t%s\t%s\t%d\t%d\t%d\t%.0f\t%d\t%d' % (tag, k[0], k[1], g[0], g[1], g[2], g[3], g[4], g[5]))
print('HOPSUM\t%s\tzero_logic_hops %d\tover_reach %d\tcrossing_a_core %d\tmacros %d' % (tag, tot, over, xs, len(macros)))

# GENBUG-5.2 placed-database preflight gate: GATE=1 -> crossing hops <= XMAX (20) and over-reach hops <= 1 % of zero-logic hops.
if os.environ.get('GATE', '0') == '1':
    xmax = int(os.environ.get('XMAX', '20')); frac = float(os.environ.get('OVER_FRAC', '0.01'))
    bad = xs > xmax or over > frac * max(tot, 1)
    print('OT_HOP_CENSUS %s zero_logic=%d over_reach=%d crossing=%d (limits crossing<=%d over<=%.0f%%)' % ('FAIL' if bad else 'PASS', tot, over, xs, xmax, frac * 100))
    if os.environ.get('OUT'):
        import json; json.dump(dict(schema='ot_hop_census/1', zero_logic=tot, over_reach=over, crossing=xs, fail=bad), open(os.environ['OUT'], 'w'))
    if bad: sys.exit(3)
