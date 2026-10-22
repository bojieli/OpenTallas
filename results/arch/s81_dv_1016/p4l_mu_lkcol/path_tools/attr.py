#!/usr/bin/env python3
"""MU-DIE-S81/PATH: attribute die-net wire over macro bodies (p4l3_rv2 place.odb dump) to plan links / blocks."""
import sys, json, collections, fnmatch, re
obst_f, nets_f, plan_f, out_f = sys.argv[1:5]
EPS = 0.5; G = 200.0; WIRE = 160.0
O = {}; grid = collections.defaultdict(list)
for ln in open(obst_f):
    n, m, isb, x0, y0, x1, y1 = ln.rstrip('\n').split('\t')
    x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
    O[n] = (m, isb == '1', x0, y0, x1, y1)
    if isb == '1':
        for gx in range(int(x0 // G), int(x1 // G) + 1):
            for gy in range(int(y0 // G), int(y1 // G) + 1):
                grid[gx, gy].append(n)
plan = json.load(open(plan_f)); links = {l['i']: l for l in plan['links']}
bkind = {b['name']: b['kind'] for b in plan['blocks']}
def seg_in(x0, y0, x1, y1, r):
    _, _, bx0, by0, bx1, by1 = r
    bx0 += EPS; by0 += EPS; bx1 -= EPS; by1 -= EPS
    if y0 == y1:
        if not (by0 < y0 < by1): return 0.0
        a, b = sorted((x0, x1)); return max(0.0, min(b, bx1) - max(a, bx0))
    if not (bx0 < x0 < bx1): return 0.0
    a, b = sorted((y0, y1)); return max(0.0, min(b, by1) - max(a, by0))
def cands(x0, y0, x1, y1):
    s = set()
    for gx in range(int(min(x0, x1) // G), int(max(x0, x1) // G) + 1):
        for gy in range(int(min(y0, y1) // G), int(max(y0, y1) // G) + 1):
            s.update(grid.get((gx, gy), ()))
    return s
def path_in(segs):
    tot = 0.0; per = collections.Counter()
    for s in segs:
        if s[0] == s[2] and s[1] == s[3]: continue
        for n in cands(*s):
            v = seg_in(*s, O[n])
            if v > 0: tot += v; per[n] += v
    return tot, per
SKIP = ['n_clk_*', 'n_rst_*', 'n_ck_col_*', 'n_rs_col_*']
def lane(inst):
    for pre in ('st_', 'fwd_', 'ld_', 'rl_', 'rly_'):
        if inst.startswith(pre):
            r = inst[len(pre):]
            if r in links: return r
            r2 = r.rsplit('_', 1)[0]
            if pre == 'st_' and r2 in links: return r2
            return r if pre != 'st_' else r2
    return None
def blkof(inst):
    for k in (inst, inst[2:] if inst.startswith('u_') else inst, inst[3:] if inst.startswith('rv_') else inst):
        if k in bkind: return k
    return inst
def kind(inst):
    m = O.get(inst, ('?',))[0]
    if m.startswith('dsfd_dvrlyh') or m.startswith('dsfd_rly'): return 'relay'
    if m.startswith('dsfd_dvland'): return 'landing'
    b = blkof(inst)
    if b in bkind: return bkind[b]
    return m
agg = collections.defaultdict(lambda: dict(nets=0, um=0.0, rep=0.0, own_um=0.0, wire_um=0.0, by_blk=collections.Counter(), by_kind=collections.Counter(), ex=None))
blk_tot = collections.Counter(); kind_tot = collections.Counter(); nn = 0; tot_um = 0.0; tot_wire = 0.0
for ln in open(nets_f):
    f = ln.rstrip('\n').split('\t')
    if len(f) < 5: continue
    name, special, sig, drv, snk = f
    if special == '1' or sig not in ('SIGNAL', ''): continue
    if any(fnmatch.fnmatchcase(name, g) for g in SKIP): continue
    if not drv or not snk: continue
    def pt(e):
        a, xy = e.rsplit('@', 1); x, y = map(float, xy.split(',')); inst = a.rsplit('/', 1)[0]; return inst, x, y
    di, dx, dy = pt(drv); sinks = [pt(e) for e in snk.split(' ') if e]
    # lane key
    insts = [di] + [s[0] for s in sinks]
    key = None
    for i in insts:
        k = lane(i)
        if k: key = k; break
    if key and key.startswith('rsl_') and key[4:] in links: key = 'RESET:' + key[4:]
    if key is None: key = 'blk:' + blkof(di) + '>' + ','.join(sorted(set(blkof(s[0]) for s in sinks)))[:80]
    if di.startswith('PORT') or any(s_[0].startswith('PORT') for s_ in sinks):
        continue      # top-port nets: special in run.tcl before the step (skipped by repair)
    pins = [(di, dx, dy)] + sinks
    # rectilinear MST (Prim) over the pins; each edge routed as the better of its two L shapes
    edges = []
    if len(pins) == 2:
        edges = [(0, 1)]
    else:
        inT = {0}; best_d = {j: (abs(pins[j][1] - dx) + abs(pins[j][2] - dy), 0) for j in range(1, len(pins))}
        while best_d:
            j = min(best_d, key=lambda q: best_d[q][0]); _, i0 = best_d.pop(j); edges.append((i0, j)); inT.add(j)
            for q in best_d:
                dd = abs(pins[q][1] - pins[j][1]) + abs(pins[q][2] - pins[j][2])
                if dd < best_d[q][0]: best_d[q] = (dd, j)
    net_um = 0.0; own = 0.0; per_net = collections.Counter(); wl = 0.0
    for i0, j in edges:
        (ai, ax, ay), (si, sx, sy) = pins[i0], pins[j]
        best = None
        for segs in ([(ax, ay, sx, ay), (sx, ay, sx, sy)], [(ax, ay, ax, sy), (ax, sy, sx, sy)]):
            t, per = path_in(segs)
            if best is None or t < best[0]: best = (t, per)
        wl += abs(ax - sx) + abs(ay - sy)
        for n, v in best[1].items():
            if n in (ai, si): own += v
            else: per_net[n] += v
        net_um += best[0]
    nn += 1; tot_wire += wl
    a = agg[key]; a['nets'] += 1; a['wire_um'] += wl
    if net_um > 0:
        a['um'] += net_um; a['own_um'] += own; a['rep'] += net_um / WIRE; tot_um += net_um
        for n, v in per_net.items():
            a['by_blk'][n] += v; blk_tot[n] += v; a['by_kind'][kind(n)] += v; kind_tot[kind(n)] += v
        if own: a['by_kind']['OWN_END'] += own; kind_tot['OWN_END'] += own
        if a['ex'] is None: a['ex'] = [name, drv, snk[:200]]
rows = []
for k, a in agg.items():
    if a['um'] <= 0: continue
    l = links.get(k.split(':', 1)[1] if k.startswith('RESET:') else k)
    rows.append(dict(key=k, plan_link=bool(l), cls=('reset:' if k.startswith('RESET:') else '') + str((l or {}).get('c')), plan_bits=(l or {}).get('b'), plan_L=(l or {}).get('L'),
                     nets=a['nets'], bit_mm_over_block=round(a['um'] / 1000, 2), own_end_bit_mm=round(a['own_um'] / 1000, 2),
                     est_obst_repeaters=round(a['rep']), wire_bit_mm=round(a['wire_um'] / 1000, 1),
                     top_blocks=[(n, round(v / 1000, 2)) for n, v in a['by_blk'].most_common(4)],
                     by_kind={kk: round(v / 1000, 2) for kk, v in a['by_kind'].most_common()}, example=a['ex']))
rows.sort(key=lambda r: -r['bit_mm_over_block'])
cls = collections.Counter(); 
for r in rows: cls[r['cls'] if r['plan_link'] else ('nonplan:' + (r['key'].split(':')[0] if ':' in r['key'] else re.sub(r'[0-9].*', '', r['key'])))] += r['bit_mm_over_block']
res = dict(schema='mu_die_s81.path_attr.v1', source='case_p4l3_rv2 out/place.odb (pre-repeater), L-route min of HV/VH per driver-sink pair, macro bodies (isBlock), eps 0.5 um',
           nets_signal=nn, wire_bit_mm=round(tot_wire / 1000), over_block_bit_mm=round(tot_um / 1000), est_obst_repeaters=round(tot_um / WIRE),
           by_class={k: round(v, 1) for k, v in cls.most_common()}, by_kind={k: round(v / 1000, 1) for k, v in kind_tot.most_common()},
           top_blocks=[(n, O[n][0], round(v / 1000, 1)) for n, v in blk_tot.most_common(40)], lanes=rows)
json.dump(res, open(out_f, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('lanes',)}, indent=None)[:4000])
for r in rows[:40]: print(r['bit_mm_over_block'], r['est_obst_repeaters'], r['key'], r['cls'], r['plan_bits'], r['nets'], r['by_kind'], r['top_blocks'][:2])
