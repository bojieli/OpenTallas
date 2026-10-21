#!/usr/bin/env python3
"""S81 G7 (L5B-G7 10-21): land plan = G4 rule (base p4l3 + the 5th-lane-pair sibling rows, mk_land_plan_g4.py) + a
MODEL row for every routed link that has no row or whose row names another receiver (the G7 IDX reader lanes moved to
the pockets, the Engram tap / chain / f_ks / rung links, and the 67 IDX-cluster landings that G3..G6 bound with the
dv_bind 'K 1 placeholder').  Model (fit of the p4l3 die-STA rows, forwarded-clock skew ~375 ps a station at T 833.3):
F = ceil(0.47 N) (N = routed stations), K = E = max(2, F + 1); tile = dsfd_dvland_<W> (D 4) when E <= 7, else the long tile dsfd_dvland_276l (D 8) for 276-b lanes; a non-276 lane with E > 7 is reported (no long tile).
The die STA (dv_land_pilot plan) re-derives E/K from the routed chains like every other row.
Usage: mk_land_plan_g7.py BASE_LAND_PLAN ROUTED_PLAN OUT"""
import copy, json, math, re, sys
# scope: the IDX cluster (readers / qf / chain / reader <-> ctrl incl. the svc hrq/hrd landings the IDX die-cut bench listed),
# the Engram links and the two retargeted rung links -- every other row stays exactly the G6 row set (frame lk straps etc.)
SCOPE = re.compile(r'^(hrrq_|hrrd_|hrq_|hrd_|iq_|is_|erq_|erd_|erc_|epc_|eks_|tvN_eng$|tvS_eng$|tvN_s_6S$|tvS_s_6N$)')
src, routed, out = sys.argv[1:4]
d = json.load(open(src)); rows = {r['link']: r for r in d['links']}
for new, old in (('WN2', 'WN0'), ('WN3', 'WN1')):
    for pre in ('lt', 'lr'):
        n = f'{pre}_lk_{new}'
        r = copy.deepcopy(rows[f'{pre}_lk_{old}']); r['link'] = n
        if r['dst'] == f'lk_{old}':
            r['dst'] = f'lk_{new}'
        r['g4_note'] = f'L5-G4: copied from {pre}_lk_{old} (5th lane pair); E/K re-derived by the die STA'
        d['links'].append(r); rows[n] = r
p = json.load(open(routed)); B = p['blocks']
added, replaced, over = [], [], []
for l in p['links']:
    nm = l['i'].replace('-', '_'); dst = B[l['e'][1][0]]['name']; N = l.get('s', 0); b = l['b']
    if not SCOPE.match(nm) or (nm in rows and rows[nm]['dst'] == dst):
        continue
    if N == 0:
        continue                       # 0-station link: no landing
    F = math.ceil(0.47 * N); E = max(2, F + 1)
    long_ = E > 7 and b == 276
    if E > 7 and not long_:
        over.append(dict(link=nm, bits=b, stages=N, E=E))   # no long tile for this width: left without a row (dv_bind K 1
        continue                                              # placeholder, as G6) -- needs a shorter lane or a D 8 tile
    r = dict(link=nm, cls=l['c'], dst=dst, bits=b, stages=N, s1={'tt': None, 'ff': None}, h0={'tt': None, 'ff': None},
             E=E, D=8 if long_ else 4, master=f'dsfd_dvland_{b}l' if long_ else f'dsfd_dvland_{b}', K=E,
             K_source=f'G7 MODEL (L5B-G7): F = ceil(0.47 x {N} stations) = {F}, K = E = F + 1; die STA re-derives',
             window_ok=None, model=True)
    if nm in rows:
        replaced.append(nm); d['links'] = [x for x in d['links'] if x['link'] != nm]
    else:
        added.append(nm)
    d['links'].append(r); rows[nm] = r
d['g4'] = 'L5-G4 10-21: +4 rows lt/lr_lk_WN2/3 (5th lane pair on s_0N)'
d['g7'] = dict(note='L5B-G7 10-21: model rows for links without a row / with a moved receiver (see docstring)',
               added=added, replaced=replaced, non276_over_E7=over)
json.dump(d, open(out, 'w'), indent=1)
print('LAND_PLAN_G7', len(d['links']), 'added', len(added), 'replaced', len(replaced), 'non276_E_over_7', over)
