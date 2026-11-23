"""IST-LEAFUP-FAM (OPUS-FIX-S81-LEAF-TAPHOLD-R2 11-23): leafup_o0 per-source station rows on every S81 leaf type.
A leaf type's leafup_o0 chain carries vs / vq / vp driver_lo / vn_u_b bits, but its plan rows name only some sources, so
kit_istations puts the unnamed bits on the merged site (t39: vp driver_lo 780-936 um, TT -186).  For each source core
whose bits resolve (kit_bus_bitgroups.out_bit_owners on the J8 bound RTL) and that has no row, add one row: to_um = the
core's box point nearest the face (vp: the centre of its u_b0/u_b1 bank union, where its soft driver regs place), regs_um = n sites (n = chain depth, 0 cycles) on the
Manhattan box between face point and core point, outside every hard core by >= 20 um (no flop piles in inter-core streets), max hop <= 400 um.  A source over 405 um
at depth n is written only when it is >= 50 um better than its merged-site hop (NEAR-REACH note), else listed for +1 station.
Kit-level OT_MACRO_MOVES (live wave item_env + pending rows, e.g. J9-LEAF-GRTCONG form M) override the plan box origin
(sites also stay clear of the unmoved plan box, which plan_gate_pre checks):
env OT_IST_FAM_MOVES=FILE.json {type: "inst:x:y[:orient],..."}.
usage: s81_ist_leafup_rows.py TOOLS PLAN RTL_DIR OUT_PLAN REPORT.json [TYPE ...]"""
import json, sys, os, re, itertools
sys.path.insert(0, sys.argv[1]); import kit_istations as KI, kit_bus_bitgroups as BG
plan, rtl, outp, rep_p = sys.argv[2:6]; only = set(sys.argv[6:])
MOVES = json.load(open(os.environ['OT_IST_FAM_MOVES'])) if os.environ.get('OT_IST_FAM_MOVES') else {}
p = json.load(open(plan)); REACH = 400.0; M = 20.0; BUS = 'leafup_o0'
SRC = ['u_lf.u_vp', 'u_lf.u_vq', 'u_lf.u_vn.u_b', 'u_lf.u_vs']
NOTE = "IST-LEAFUP-FAM (OPUS-FIX-S81-LEAF-TAPHOLD-R2 11-23): per-source stage site, 0 cycles (same u_ist chain, kit bit groups); "
def box(h):
    (x, y), (w, hh) = h['origin_um'], h['outline_um']; return (x, y, x + w, y + hh)
def inside(pt, bx):
    return any(b[0] - M < pt[0] < b[2] + M and b[1] - M < pt[1] < b[3] + M for b in bx)
def md(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
def near(b, f):
    return (min(max(f[0], b[0]), b[2]), min(max(f[1], b[1]), b[3]))
def sites(F, C, n, bx, W, H):
    """n sites, chain order face -> core is reversed later; minimise max hop over a 6-um grid in the F-C box (+60 um)"""
    x0, x1 = sorted((F[0], C[0])); y0, y1 = sorted((F[1], C[1]))
    gx = [x for x in frange(max(2, x0 - 60), min(W - 2, x1 + 60), 6.0)]
    gy = [y for y in frange(max(2, y0 - 60), min(H - 2, y1 + 60), 6.0)]
    free = [(x, y) for x in gx for y in gy if not inside((x, y), bx)]
    if n == 1:
        best = min(free, key=lambda s: (max(md(F, s), md(s, C)), md(F, s) + md(s, C)), default=None)
        return [best] if best else None
    # n == 2: greedy: site a near 1/3, b near 2/3 of the Manhattan path, each minimising its own hops
    best, bv = None, 1e9
    cand = sorted(free, key=lambda s: abs(md(F, s) - md(F, C) / 3) + abs(md(s, C) - 2 * md(F, C) / 3))[:400]
    for a in cand:
        for b in sorted(free, key=lambda s: abs(md(a, s) - md(a, C) / 2) + abs(md(s, C) - md(a, C) / 2))[:200]:
            v = max(md(F, a), md(a, b), md(b, C))
            if v < bv: best, bv = [a, b], v
    return best
def frange(a, b, s):
    v = a
    while v <= b: yield round(v, 3); v += s
rep = []; changed = []
for tn, t in sorted(p['partition_types'].items()):
    if not tn.startswith('ot_s81sl_leaf') or (only and tn not in only):
        continue
    sv = os.path.join(rtl, f's81p_{tn}.sv')
    ents = [x for x in KI.bus_entries(t) if x['conn'] == 'bus:' + BUS]
    if not ents or not os.path.exists(sv):
        rep.append(dict(type=tn, skip='no bound sv' if ents else 'no leafup_o0 stations')); continue
    e = ents[0]; rows = e.get('per_core_rows', [e]); n = len(e['regs_um'])
    hard = [h['inst'] for h in t.get('hard_cores', [])]
    have = {BG.core_of_entry(r, hard) for r in rows}
    if not have <= set(SRC) or n > 2:
        rep.append(dict(type=tn, skip=f'row form {sorted(map(str, have))} depth {n}')); continue
    txt = open(sv).read()
    ow = BG.out_bit_owners(txt, BG.re.sub(r'\W', '_', BUS) if hasattr(BG, 're') else BUS, 668, SRC)
    if ow is None:
        rep.append(dict(type=tn, skip='owners unresolved')); continue
    bits = {c: sum(1 for b, cs in ow.items() if c in cs) for c in SRC}
    F = tuple(rows[0]['from_um']); W, H = t['outline_um']
    mv = {}
    for it in filter(None, MOVES.get(tn, '').split(',')):
        f = it.split(':'); mv[f[0]] = (float(f[1]), float(f[2]), f[3] if len(f) > 3 else None)
    hcs = []
    for h in t['hard_cores']:
        h = dict(h)
        if h['inst'] in mv:
            x, y, o = mv[h['inst']]
            h['origin_um'] = [x, y]
            if o in ('R90', 'R270', 'MXR90', 'MYR90'):
                h['outline_um'] = [h['outline_um'][1], h['outline_um'][0]]
        hcs.append(h)
    hb = {h['inst']: box(h) for h in hcs}
    # obstacles: kit boxes (moved) AND plan boxes (plan_gate_pre GEOM-STATION-IN-CORE checks the plan origin)
    bx = [box(h) for h in hcs] + [box(h) for h in t['hard_cores'] if h['inst'] in mv]
    new = []
    for c in SRC:
        if c in have or not bits[c]:
            continue
        if c == 'u_lf.u_vp':
            bk = [hb[k] for k in hb if re.match(r'u_lf\.u_vp\.u_b\d+$', k)]
            if not bk:
                rep.append(dict(type=tn, core=c, skip='no vp banks')); continue
            cb = (min(b[0] for b in bk), min(b[1] for b in bk), max(b[2] for b in bk), max(b[3] for b in bk))
        elif c in hb:
            cb = hb[c]
        else:
            rep.append(dict(type=tn, core=c, skip='core box missing')); continue
        C = ((cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2) if c == 'u_lf.u_vp' else near(cb, F)   # vp: soft driver regs sit at the bank union centre (t39 placed 880,610)
        st = sites(F, C, n, [b for b in bx if b != cb or c != 'u_lf.u_vp'] if c != 'u_lf.u_vp' else bx, W, H)
        if not st:
            rep.append(dict(type=tn, core=c, bits=bits[c], skip='no free site')); continue
        path = [F] + st + [C]; hop = max(md(a, b) for a, b in zip(path, path[1:]))
        r = dict(type=tn, core=c, bits=bits[c], depth=n, moves=sorted(mv), face=F, core_pt=C, sites=st, max_hop_um=round(hop, 1),
                 manhattan_um=round(md(F, C), 1))
        mp = [F] + [tuple(x) for x in e['regs_um']] + [C]
        cur = max(md(a, b) for a, b in zip(mp, mp[1:])); r['merged_hop_um'] = round(cur, 1)
        if hop > REACH + 5 and hop > cur - 50:
            r['skip'] = f'max hop {hop:.0f} > {REACH:.0f} at depth {n} and not 50 um better than merged {cur:.0f}: +1 station'
            rep.append(r); continue
        if hop > REACH + 5:
            r['near_reach'] = True
        cap = {'u_lf.u_vp': 'u_lf.u_vp.driver_lo', 'u_lf.u_vq': 'u_lf.u_vq.xf', 'u_lf.u_vn.u_b': 'u_lf.u_vn.u_b.p', 'u_lf.u_vs': 'u_lf.u_vs.e_d'}[c]
        new.append(dict(bits=bits[c], capture=cap, conn='bus:' + BUS, from_um=list(F), launch='face bus ' + BUS,
                        note=NOTE + f"{c} {bits[c]} bits, max hop {hop:.0f} um (merged site {cur:.0f}, Manhattan {md(F, C):.0f})"
                        + ("; NEAR-REACH > 405: +1 station if TT fails" if hop > REACH + 5 else ""),
                        regs_um=[[round(s[0], 3), round(s[1], 3)] for s in st], to_um=[round(C[0], 3), round(C[1], 3)]))
        rep.append(r)
    if new:
        trial = dict(t, internal_stations=t['internal_stations'] + new)
        e2 = [x for x in KI.bus_entries(trial) if x['conn'] == 'bus:' + BUS][0]
        if not BG.merged_violates(e2['per_core_rows'], e2['regs_um'], False):
            # kit bit groups stay off (every source within reach of the merged stage): rows would only move the merged pile
            for r in rep:
                if r.get('type') == tn and 'sites' in r and 'skip' not in r:
                    r['skip'] = 'merged stage within reach of every source (kit bit groups auto-off): type unchanged'
            continue
        t['internal_stations'].extend(new); changed.append(tn)
json.dump(p, open(outp, 'w'), indent=1)
json.dump(dict(changed=changed, rows=rep), open(rep_p, 'w'), indent=1)
print('changed', len(changed), 'rows', sum(1 for r in rep if 'sites' in r and 'skip' not in r),
      'skipped', sum(1 for r in rep if 'skip' in r))
for r in rep:
    print(json.dumps(r)[:300])
