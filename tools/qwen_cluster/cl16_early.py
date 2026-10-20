#!/usr/bin/env python3
"""Q-CLUSTER16 early die-clock crossing check (Q-CL16-EARLY, owner 10-18).
Inputs: xpaths_TT.txt / xpaths_FF.txt (xsta.tcl: every inter-clock path end of qfd_c_b16_dv at 4_1_cts, propagated
clocks, region roots driven at 0 = cluster-only skew), region_audit.json (the 73 crossings), detail (launch/capture
clock network delay per crossing).  Die model applied analytically per crossing:
  setup_TT(die) = s_TT + (d_dst - d_src)_TT - e        hold_FF(die) = h_FF - (d_dst - d_src)_FF - e
d_r = die drop arrival at the region's centre pin (relative), e = die delivery residual per pair."""
import json, re, sys, collections, itertools
import numpy as np
from scipy.optimize import linprog
D = sys.argv[1]; AUD = sys.argv[2]; OUT = sys.argv[3]
T_GATE, T_DIE = 770.0, 833.333
aud = json.load(open(AUD))
reg = lambda ck: 'c0r0' if ck == 'core_clk' else ck[3:]
REG = [f"c{c}r{r}" for c in range(4) for r in range(4)]
def toks(dst):
    i, _, p = dst.partition('.')
    return i, p
X = aud['crossing_list']
for k, c in enumerate(X): c['id'] = k
def match(sr, dr, ep):
    inst, pin = ep.rsplit('/', 1)
    inst = inst.replace('u_fab.', '')
    for c in X:
        if c['src_region'] != sr or c['dst_region'] != dr: continue
        i, p = toks(c['dst'])
        if p:
            if inst == i and pin.split('[')[0] == {'trst': 'rst_n'}.get(p, p): return c['id']   # audit 'trst' = tile pin rst_n
        elif inst == i or inst.startswith(i + '.'): return c['id']
    return None
rows = collections.defaultdict(lambda: collections.defaultdict(list))
extra = collections.defaultdict(lambda: collections.Counter())
ports = collections.Counter()
for C in ('TT', 'FF'):
    for l in open(f"{D}/xpaths_{C}.txt"):
        f = l.split()
        if f[0] != 'P': continue
        _, dly, A, B, sl, la, sp, ep = f
        if '/' not in sp or '/' not in ep: ports[(C, dly, A, B)] += 1; continue
        sr, dr = reg(A), reg(B)
        k = match(sr, dr, ep)
        if k is None:
            extra[(sr, dr, sp.split('/')[0], ep.split('/')[0] + '/' + ep.split('/')[1].split('[')[0])][(C, dly)] += 1
            continue
        rows[k][(C, dly)].append((float(sl), float(la), sp, ep))
# detail: clock network delays of the worst path per crossing
det = {}
for C in ('TT', 'FF'):
    try: txt = open(f"{D}/xdetail_{C}.txt").read()
    except FileNotFoundError: continue
    for blk in txt.split('D_BEGIN ')[1:]:
        hdr, body = blk.split('\n', 1)
        dly, A, B, pin = hdr.split()
        m1 = re.search(r'Startpoint: (\S+)', body); m2 = re.search(r'Endpoint: (\S+)', body)
        if not (m1 and m2): continue
        si, ei = m1.group(1), m2.group(1)
        lines = body.split('\n')
        ix = [i for i, l in enumerate(lines) if re.search(r'clock \S+ \((rise|fall) edge\)', l)]
        if len(ix) < 2: continue
        L, Cp = '\n'.join(lines[ix[0]:ix[1]]), '\n'.join(lines[ix[1]:])
        e0 = float(lines[ix[1]].split()[1])
        def pinarr(sec, inst):
            for l in sec.split('\n'):
                m = re.match(r'\s*[-\d.]+\s+([-\d.]+)\s+[\^v]\s+(\S+)/(\S+)\s+\(', l)
                if m and m.group(2) == inst: return float(m.group(1))
            return None
        la, ca = pinarr(L, si), pinarr(Cp, ei)
        if la is None or ca is None: continue
        det[(C, dly, pin)] = (la, ca - e0)
res = []
for c in X:
    r = rows.get(c['id'], {})
    def worst(key):
        v = r.get(key, [])
        return min(v, key=lambda t: t[0]) if v else None
    s = worst(('TT', 'max')); h = worst(('FF', 'min')); hT = worst(('TT', 'min')); sF = worst(('FF', 'max'))
    e = dict(id=c['id'], net=c['net'], src=c['src'], dst=c['dst'], src_region=c['src_region'], dst_region=c['dst_region'],
             bits=c['bits'], hop_um=c['hop_um'], n_ends=len(r.get(('TT', 'max'), [])),
             setup_tt_770=round(s[0], 1) if s else None, hold_ff=round(h[0], 1) if h else None,
             hold_tt=round(hT[0], 1) if hT else None, setup_ff_770=round(sF[0], 1) if sF else None,
             worst_setup_ep=s[3] if s else None, worst_hold_ep=h[3] if h else None)
    for (C, dly, ep) in ((('TT', 'max', e['worst_setup_ep'])), (('FF', 'min', e['worst_hold_ep']))):
        if ep and (C, dly, ep) in det:
            la, ca = det[(C, dly, ep)]
            e[f'clk_{C}_{dly}'] = dict(launch=la, capture=ca, skew=round(ca - la, 1))
    res.append(e)
miss = [e for e in res if e['setup_tt_770'] is None]
# region reference insertion = mean clock arrival at the crossing endpoints of the region (launch + capture), per corner
ins = {C: collections.defaultdict(list) for C in ('TT', 'FF')}
for e in res:
    for C, dly in (('TT', 'max'), ('FF', 'min')):
        k = f'clk_{C}_{dly}'
        if k in e:
            ins[C][e['src_region']].append(e[k]['launch']); ins[C][e['dst_region']].append(e[k]['capture'])
I = {C: {q: (sum(v) / len(v) if v else None) for q, v in ins[C].items()} for C in ins}
def evaluate(dTT, dFF, eps, per):
    out = []
    for e in res:
        if e['setup_tt_770'] is None: continue
        s = e['setup_tt_770'] + (per - T_GATE) + (dTT[e['dst_region']] - dTT[e['src_region']]) - eps
        h = e['hold_ff'] - (dFF[e['dst_region']] - dFF[e['src_region']]) - eps
        out.append((e['id'], round(s, 1), round(h, 1)))
    return out
RHO = 0.80   # die buffer/wire FF/TT ratio (F1 light hop 15 TT / 12 FF ps, METHOD.md)
models = {}
# M0: die delivers all 16 drops at the same time (no compensation): the cluster's own region skew
z = {q: 0.0 for q in REG}
models['M0_uncompensated'] = dict(dTT=z, dFF=z)
# M1: contract compensation: drop = -I_r(TT) (die trims at TT, FF tracks at RHO)
if all(I['TT'].get(q) is not None for q in REG if any(e['src_region'] == q or e['dst_region'] == q for e in res)):
    m = sum(v for v in I['TT'].values() if v is not None) / len([v for v in I['TT'].values() if v is not None])
    dT = {q: (m - I['TT'][q]) if I['TT'].get(q) is not None else 0.0 for q in REG}
    models['M1_contract_tt_trim'] = dict(dTT=dT, dFF={q: RHO * v for q, v in dT.items()})
    mF = sum(v for v in I['FF'].values() if v is not None) / len([v for v in I['FF'].values() if v is not None])
    models['M2_contract_two_corner'] = dict(dTT=dT, dFF={q: (mF - I['FF'][q]) if I['FF'].get(q) is not None else 0.0 for q in REG})
# M3: LP-optimal drops (TT trim, FF = RHO x TT): maximise the minimum of setup_TT(833) and hold_FF
def lp(rho, per=T_DIE):
    n = len(REG); ix = {q: i for i, q in enumerate(REG)}
    A, b = [], []
    for e in res:
        if e['setup_tt_770'] is None: continue
        s0 = e['setup_tt_770'] + (per - T_GATE); h0 = e['hold_ff']
        a = np.zeros(n + 1); a[ix[e['dst_region']]] -= 1; a[ix[e['src_region']]] += 1; a[n] = 1; A.append(a); b.append(s0)
        a = np.zeros(n + 1); a[ix[e['dst_region']]] += rho; a[ix[e['src_region']]] -= rho; a[n] = 1; A.append(a); b.append(h0)
    cobj = np.zeros(n + 1); cobj[n] = -1
    bnds = [(0, 0)] + [(-2000, 2000)] * (n - 1) + [(None, None)]
    r = linprog(cobj, A_ub=np.array(A), b_ub=np.array(b), bounds=bnds, method='highs')
    return {q: float(r.x[ix[q]]) for q in REG}, float(r.x[n])
dopt, topt = lp(RHO)
models['M3_lp_optimal_tt_trim'] = dict(dTT=dopt, dFF={q: RHO * v for q, v in dopt.items()}, t=topt)
summary = {}
for name, m in models.items():
    summary[name] = {}
    for eps in (0, 30, 60):
        ev = evaluate(m['dTT'], m['dFF'], eps, T_DIE)
        fs = [x for x in ev if x[1] < 0 or x[2] < 0]
        summary[name][f'e{eps}'] = dict(worst_setup_tt_833=min(x[1] for x in ev), worst_hold_ff=min(x[2] for x in ev),
                                        failing=len(fs), failing_ids=[x[0] for x in fs])
    summary[name]['drops_tt'] = {q: round(v, 1) for q, v in m['dTT'].items()}
    summary[name]['drops_ff'] = {q: round(v, 1) for q, v in m['dFF'].items()}
    summary[name]['per_crossing_e60'] = evaluate(m['dTT'], m['dFF'], 60, T_DIE)
json.dump(dict(schema='opentallas.qcluster.cl16_early.v1', rho_die=RHO, period_gate=T_GATE, period_die=T_DIE,
               region_ref_insertion=I, crossings=res, missing=[e['id'] for e in miss],
               extra_inter_region_paths=[dict(src_region=k[0], dst_region=k[1], start=k[2], end=k[3], counts={f'{a}_{b}': n for (a, b), n in v.items()}) for k, v in extra.items()],
               port_paths={f'{a}|{b}|{c}|{d}': n for (a, b, c, d), n in ports.items()},
               models=summary), open(OUT, 'w'), indent=1)
print('crossings', len(res), 'missing', len(miss), 'extra groups', len(extra))
for k, v in extra.items(): print(' EXTRA', k, dict(v))
for name, s in summary.items():
    print(name, {k: (v['worst_setup_tt_833'], v['worst_hold_ff'], v['failing']) for k, v in s.items() if k.startswith('e')})

# ---- verdicts (appended): timing window with cluster hold repair, and the 80-ps neighbour-skew test ----
KH = 1 / 0.82   # TT ps of setup consumed per FF ps of hold buffering (ASAP7 data-path FF/TT ~0.82)
R = json.load(open(OUT))
win = {}
for eps in (30, 60):
    bad = []
    for e in res:
        if e['setup_tt_770'] is None: continue
        s = e['setup_tt_770'] + (T_DIE - T_GATE) - eps; h = e['hold_ff'] - eps
        w = s - max(0.0, -h) * KH
        e.setdefault('window_833', {})[f'e{eps}'] = round(w, 1)
        if w < 0: bad.append(dict(id=e['id'], net=e['net'], pair=f"{e['src_region']}->{e['dst_region']}", hop_um=e['hop_um'],
                                  setup_tt_833=round(s, 1), hold_ff=round(h, 1), window=round(w, 1)))
    win[f'e{eps}'] = bad
def skew_lp(two):
    Xs = [e for e in res if 'clk_TT_max' in e and 'clk_FF_min' in e]; ixx = {q: i for i, q in enumerate(REG)}
    nv = (32 if two else 16) + 1; A, b = [], []
    for e in Xs:
        for C, k in (('TT', 'clk_TT_max'), ('FF', 'clk_FF_min')):
            a = np.zeros(nv); off = 16 if (two and C == 'FF') else 0; sc = 1.0 if (two or C == 'TT') else RHO
            a[off + ixx[e['dst_region']]] += sc; a[off + ixx[e['src_region']]] -= sc
            for sg in (1, -1):
                r = sg * a; r = r.copy(); r[-1] = -1; A.append(r); b.append(-sg * e[k]['skew'])
    cobj = np.zeros(nv); cobj[-1] = 1
    bnd = [(0, 0)] + [(-3000, 3000)] * 15 + ([(0, 0)] + [(-3000, 3000)] * 15 if two else []) + [(0, None)]
    r = linprog(cobj, A_ub=np.array(A), b_ub=np.array(b), bounds=bnd, method='highs')
    dT = {q: r.x[ixx[q]] for q in REG}; dF = {q: (r.x[16 + ixx[q]] if two else RHO * r.x[ixx[q]]) for q in REG}
    over = [e['net'] for e in Xs if abs(e['clk_TT_max']['skew'] + dT[e['dst_region']] - dT[e['src_region']]) > 80
            or abs(e['clk_FF_min']['skew'] + dF[e['dst_region']] - dF[e['src_region']]) > 80]
    return dict(minimax_skew_ps=round(r.x[-1], 1), over80=len(over), judged=len(Xs), drops_tt={q: round(v, 1) for q, v in dT.items()})
raw_over = sum(1 for e in res if 'clk_TT_max' in e and 'clk_FF_min' in e and (abs(e['clk_TT_max']['skew']) > 80 or abs(e['clk_FF_min']['skew']) > 80))
R['crossings'] = res
R['verdict'] = dict(
    timing_window_drops_phase_aligned=win,
    skew80=dict(raw_over80=raw_over, tt_trim_ff_tracks=skew_lp(False), two_corner_trim=skew_lp(True)),
    note="window = setup_TT(833) - e - max(0, e - hold_FF) / 0.82 (hold repaired by data buffering inside the cluster); "
         "skew80 = best 16 die drop offsets (LP minimax) against the 80 ps neighbour budget at the crossing pins")
json.dump(R, open(OUT, 'w'), indent=1)
print('window fails', {k: [x['net'] for x in v] for k, v in win.items()})
print('skew80', json.dumps(R['verdict']['skew80'])[:400])
