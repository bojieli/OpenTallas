# openroad -python: S81-SLICE-J9 single-copy register reach census (FABLE-RC-ALL ee2fb1d2 class row).
# Every flip-flop output is traced through BUF/INV/HB repeaters to its real sinks (logic cells, flops, macro pins, ports).
# Per flop: placed position, sinks, fan-out box (flop + sinks), L1 reach to the farthest sink, repeater depth of the longest
# chain (wire-delay proxy: ~50 ps/stage in ASAP7 placed reports, 18 stages ~ 1 ns).  Flag: box side > REACH or depth >= DEPTH.
# env ODB OUT [REACH=405] [DEPTH=18].  Writes OUT (json: per-flagged-flop rows incl. sink keys + xy) and OUT.tsv (register groups).
import os, re, json, collections, odb
db = odb.dbDatabase.create(); odb.read_db(db, os.environ['ODB'])
blk = db.getChip().getBlock(); dbu = blk.getDbUnitsPerMicron()
REACH = float(os.environ.get('REACH', '405')); DEPTH = int(os.environ.get('DEPTH', '18'))
def xy(i):
    b = i.getBBox(); return ((b.xMin() + b.xMax()) / 2 / dbu, (b.yMin() + b.yMax()) / 2 / dbu)
def ixy(it):
    i = it.getInst()
    if i.getMaster().isBlock():
        ok, x, y = it.getAvgXY()
        if ok: return (x / dbu, y / dbu)
    return xy(i)
def rep(i):
    n = i.getMaster().getName(); return n.startswith('BUF') or n.startswith('INV') or n.startswith('HB')
def seq(i):
    n = i.getMaster().getName(); return 'DFF' in n or 'DHL' in n or 'DLL' in n
def key(nm):
    return re.sub(r'^u_bound[./]', '', re.sub(r'\$_[A-Za-z0-9_]*$', '', nm.replace('\\', '')))
def outnet(i):
    for it in i.getITerms():
        if it.isOutputSignal() and it.getNet() is not None:
            return it.getNet()
    return None
rows, n_ff = [], 0
for f in blk.getInsts():
    if not seq(f): continue
    n_ff += 1
    net = outnet(f)
    if net is None: continue
    sinks, depth, nrep = [], 0, 0
    stack = [(net, 0)]; seen = set()
    while stack:
        nt, d = stack.pop()
        if nt.getId() in seen: continue
        seen.add(nt.getId())
        for bt in nt.getBTerms():
            ok, x, y = bt.getFirstPinLocation() if hasattr(bt, 'getFirstPinLocation') else (False, 0, 0)
            sinks.append(('port:' + bt.getName(), (x / dbu, y / dbu) if ok else None, d))
        for it in nt.getITerms():
            if it.isOutputSignal(): continue
            i = it.getInst()
            if i.getMaster().isBlock() or not rep(i):
                sinks.append((key(i.getName()) + ('/' + it.getMTerm().getName() if i.getMaster().isBlock() else ''), ixy(it), d))
                depth = max(depth, d)
            else:
                nrep += 1
                o = outnet(i)
                if o is not None: stack.append((o, d + 1))
    pts = [s[1] for s in sinks if s[1] is not None]
    if not pts: continue
    fx, fy = xy(f)
    xs = [p[0] for p in pts] + [fx]; ys = [p[1] for p in pts] + [fy]
    side = max(max(xs) - min(xs), max(ys) - min(ys))
    reach = max(abs(p[0] - fx) + abs(p[1] - fy) for p in pts)
    sx = [p[0] for p in pts]; sy = [p[1] for p in pts]
    sink_side = max(max(sx) - min(sx), max(sy) - min(sy))
    if side > REACH or depth >= DEPTH:
        rows.append({'flop': key(f.getName()), 'cell': f.getMaster().getName(), 'xy': [round(fx, 2), round(fy, 2)], 'n_sinks': len(sinks),
                     'box_side': round(side, 1), 'sink_side': round(sink_side, 1), 'reach_l1': round(reach, 1), 'rep_depth': depth,
                     'n_rep': nrep, 'sinks': [[s[0], [round(s[1][0], 2), round(s[1][1], 2)] if s[1] else None] for s in sinks]})
def reg(k):
    return re.sub(r'\[\d+\]$', '', k)
def klass(r):
    if r['n_sinks'] >= 32: return 'select/enable'
    if r['sink_side'] > REACH: return 'spread-data'
    return 'far-data'
G = collections.OrderedDict()
for r in sorted(rows, key=lambda r: -r['box_side']):
    g = G.setdefault(reg(r['flop']), {'bits': 0, 'max_side': 0, 'max_reach': 0, 'max_depth': 0, 'max_sinks': 0, 'class': collections.Counter()})
    g['bits'] += 1; g['max_side'] = max(g['max_side'], r['box_side']); g['max_reach'] = max(g['max_reach'], r['reach_l1'])
    g['max_depth'] = max(g['max_depth'], r['rep_depth']); g['max_sinks'] = max(g['max_sinks'], r['n_sinks']); g['class'][klass(r)] += 1

# v2: movable sinks = DIRECT loads of the flop in the pre-global-place netlist (NETL odb, the state rs_split_all sees), same
# single-load chain (<= 4) and same key / ambiguity rules; position = placed DB (a repeater load: centre of its real sinks).
if os.environ.get('NETL'):
    db2 = odb.dbDatabase.create(); odb.read_db(db2, os.environ['NETL']); b2 = db2.getChip().getBlock()
    pos = {i.getName(): xy(i) for i in blk.getInsts()}
    raw1 = lambda nm: re.sub(r'\$_[A-Za-z0-9_]*$', '', nm.replace('\\', ''))
    by, byf = collections.Counter(), collections.Counter(); f2 = {}
    for i in b2.getInsts():
        k = raw1(i.getName()); ff = 'DFF' in i.getMaster().getName()
        for c in {k, re.sub(r'^[^./]*[./]', '', k)}:
            by[c.replace('/', '.')] += 1
            if ff: byf[c.replace('/', '.')] += 1
        if ff: f2.setdefault(key(i.getName()).replace('/', '.'), []).append(i)
    def real(net):
        out, st, sn = [], [net], set()
        while st:
            nt = st.pop()
            if nt.getId() in sn: continue
            sn.add(nt.getId())
            for it in nt.getITerms():
                if it.isOutputSignal(): continue
                i = it.getInst()
                if not i.getMaster().isBlock() and rep(i):
                    o = outnet(i)
                    if o is not None: st.append(o)
                elif i.getName() in pos: out.append(pos[i.getName()])
        return out
    def uniq(k): 
        k = k.replace('/', '.')
        return byf[k] == 1 or (byf[k] == 0 and by[k] == 1)
    st2 = collections.Counter()
    for r in rows:
        c = f2.get(r['flop'].replace('/', '.'), [])
        if len(c) != 1 or byf[r['flop'].replace('/', '.')] != 1: st2['flop_ambiguous_or_absent'] += 1; r['direct'] = None; continue
        qn = outnet(c[0])
        for h in range(4):
            ld = [it for it in qn.getITerms() if not it.isOutputSignal()]
            if len(ld) != 1 or len(qn.getBTerms()) or ld[0].getInst().getMaster().isBlock() or not rep(ld[0].getInst()): break
            o = outnet(ld[0].getInst())
            if o is None: break
            qn = o
        D, fx = {}, len(qn.getBTerms())
        # UNBUF: expand non-inverting BUF loads (what relay_split unbuffer does: BUF sinks re-hung on qn, the BUF removed)
        its, nb = [], 0; wl = [(it, 0) for it in qn.getITerms() if not it.isOutputSignal()]
        while wl:                                   # same rules as rs_unbuf: BUF dissolved, one INV level transparent
            it, lv = wl.pop(); i = it.getInst(); m = i.getMaster().getName(); on = None if i.getMaster().isBlock() else outnet(i)
            if m.startswith('BUF') and on is not None and not len(on.getBTerms()) and not i.isFixed() and not i.isDoNotTouch() and not on.isDoNotTouch():
                nb += 1; wl += [(x, lv) for x in on.getITerms() if not x.isOutputSignal()]
            elif m.startswith('INV') and lv == 0 and on is not None and not len(on.getBTerms()) and not i.isDoNotTouch():
                nb += 1; wl += [(x, 1) for x in on.getITerms() if not x.isOutputSignal()]
            else: its.append(it)
        r['unbuf'] = nb
        for it in its:
            i = it.getInst(); k = key(i.getName()); blkd = i.getMaster().isBlock()
            if not uniq(k): fx += 1; continue
            pp = real(outnet(i)) if (not blkd and rep(i) and outnet(i) is not None) else ([pos[i.getName()]] if i.getName() in pos else [])
            if not pp: fx += 1; continue
            xs = [p[0] for p in pp]; ys = [p[1] for p in pp]
            D[k] = [round((min(xs) + max(xs)) / 2, 2), round((min(ys) + max(ys)) / 2, 2), round(max(max(xs) - min(xs), max(ys) - min(ys)), 1)]
        r['direct'] = D; r['fixed'] = fx; st2['rows'] += 1
    print('OT_REG_REACH direct', dict(st2))
out = os.environ['OUT']
json.dump({'odb': os.environ['ODB'], 'reach': REACH, 'depth': DEPTH, 'flops': n_ff, 'flagged': len(rows), 'rows': rows}, open(out, 'w'))
with open(out + '.tsv', 'w') as t:
    t.write('register\tbits\tmax_box_side_um\tmax_reach_l1_um\tmax_rep_depth\tmax_sinks\tclass\n')
    for k, g in G.items():
        t.write(f"{k}\t{g['bits']}\t{g['max_side']}\t{g['max_reach']}\t{g['max_depth']}\t{g['max_sinks']}\t{','.join(f'{a}:{b}' for a, b in g['class'].most_common())}\n")
cc = collections.Counter(klass(r) for r in rows)
print(f"OT_REG_REACH flops {n_ff} flagged {len(rows)} registers {len(G)} classes {dict(cc)} reach {REACH} depth {DEPTH}")
