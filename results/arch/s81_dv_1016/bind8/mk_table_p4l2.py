#!/usr/bin/env python3
"""LANDFIX-SQ/F (10-18): bind_table_p4l2.json = bind_table_p4l.json (S81-DIE6 + S81-LEPV) with the frame column FIFO gap
closed: every frame binds the S81-LAND2 successor col_h9_l4 / col_h10_l4 / col_h9_MX_l4 (rtl/dsrom_sys/s81_dv/frame_l4,
tools/s81_dv/frame_l4.py: dsfd_cfifo_crs -> dsfd_cfifo_crs4, each x lane landed on ITS OWN forwarded clock xk[k], read
epoch = the frame's regional reset release) instead of col_h9 / col_h10 / col_h9_MX (lanes 0 / 3 on the neighbour lane's
clock, marker-sampled epoch).

lk strap per frame instance (identity strap, LANDING-CONTRACT L7): lk[3k +: 3] = lane k's K.  The four x lanes of one frame
are ONE bundle (the column word is assembled from all four rings on the same cr edge), so they share one K = the frame's
E = max over its lanes of the p4l land plan E (results/arch/s81_dv_1016/landing/p4l/land_plan.json, from the p4l unlanded
die STA TT/FF); the faster lanes stay inside the D = 4 window (setup_E grows, (E - D) T < dL holds: dL >= ~1 T on every
staged lane).  Lanes with no relay station (the 31 frames abutting their slice: 2 hops, 0 stations, absent from the
land plan) met single-cycle setup with margin (not in the worst-200k end lists at TT or FF; FF hold +54 ps): E = 1.
The frame return calendar for the _l4 frames is tools/s81_dv/frame_return_plan.py --land-e E (x_shift = E - 6).
"""
import collections, copy, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
B = ROOT / 'results/arch/s81_dv_1016/bind'
T = json.load(open(B / 'bind_table_p4l.json'))
M = T['masters']
plan = json.load(open(ROOT / 'results/arch/s81_dv_1016/p4l/plan.json'))
lp = json.load(open(ROOT / 'results/arch/s81_dv_1016/landing/p4l/land_plan.json'))
E = {r['link']: r['E'] for r in lp['links']}
frames = {b['name']: b['master'] for b in plan['blocks'] if b['master'] in ('col_h9', 'col_h10', 'col_h9_MX')}
lanes = collections.defaultdict(dict)
for l in plan['links']:
    m = re.match(r'x_f_(\w+)_l(\d)$', l['i'].replace('-', '_'))
    if m and f'f_{m.group(1)}' in frames:
        lanes[f'f_{m.group(1)}'][int(m.group(2))] = l['i'].replace('-', '_')
kf, rows = {}, []
for f in sorted(frames):
    es = {k: E.get(nm) for k, nm in sorted(lanes[f].items())}
    staged = [e for e in es.values() if e is not None]
    e = max(staged) if staged else 1
    assert 1 <= e <= 7, (f, es)                     # 3-bit strap; E > 7 would need the reset calendar (none here)
    kf[f] = e
    rows.append(dict(inst=f, master=frames[f] + '_l4', lanes=lanes[f], lane_E=es, K=e,
                     source='land plan max lane E' if staged else 'no station: single-cycle met (E 1)'))
for mm in ('col_h9', 'col_h10', 'col_h9_MX'):
    m = M[mm]
    m['module'] = mm + '_l4'
    m.pop('ref', None)                              # worktree RTL rtl/dsrom_sys/s81_dv/frame_l4 (emitted, sha in frame_l4.json)
    m['straps'] = m.get('straps', []) + ['lk']
    vals = {f: "12'h%03x" % sum(kf[f] << (3 * k) for k in range(4)) for f in frames if frames[f] == mm}
    m['strap_values'] = dict(m.get('strap_values', {}), lk=vals)
    m['view_note'] = ('frame cluster not hardened yet; LANDFIX-SQ/F: S81-LAND2 successor ' + mm + '_l4 (dsfd_cfifo_crs4, per-lane '
                      'landings, lk = per-frame K from the p4l land plan); frame bench _l4 each + plan (crs4 calendar) PASS')
    m['port_note'] = m.get('port_note', '') + '; lk[3k +: 3] = lane k K (one K per frame bundle)'
    T['rtl_widths'][mm + '_l4'] = dict(T['rtl_widths'][mm], lk=12)
T['frame_wrapper']['masters'] = ['col_h9_l4', 'col_h10_l4', 'col_h9_MX_l4']
T['frame_wrapper']['note'] = ('LANDFIX-SQ/F 10-18: frames bind the _l4 successors (dsfd_cfifo_crs4); ' + T['frame_wrapper'].get('note', ''))
T['rtl_refs'] = {r: [p for p in ps if '/s81_dv/frame/col_h' not in p] for r, ps in T['rtl_refs'].items()}
T['rtl_refs'] = {r: ps for r, ps in T['rtl_refs'].items() if ps}
T['prefer'] = [p for p in T['prefer'] if '/s81_dv/frame/col_h' not in p]
for fm in T['frame_members']:
    if fm['master'] == 'dsfd_cfifo_crs':
        fm.update(master='dsfd_cfifo_crs4', ref='HEAD', path='rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv', view=None,
                  view_note='successor of r5f-507e1b0c3 (dsfd_cfifo_crs CLOSED); crs4 not hardened yet (owed)',
                  replaces='dsfd_cfifo_crs (LANDING audit gaps 1+2)', ports_used=['xd', 'xd2', 'xk', 'lk', 'ri', 'rd', 'rst', 'cr',
                                                                                 'cr_s', 'xa', 'xb', 'x2', 'cc'],
                  decision='S81-LAND2 0dm+ (1); LANDFIX-SQ/F 10-18 binds it')
T['child_views_owed'] = dict(T.get('child_views_owed', {}), dsfd_cfifo_crs4='harden the crs4 column FIFO (successor of r5f-507e1b0c3)')
T['frame_lk'] = dict(rule='K = max over the frame x lanes of the p4l land plan E (one bundle, one K); no-station lanes E 1',
                     land_plan='results/arch/s81_dv_1016/landing/p4l/land_plan.json',
                     K_hist=dict(sorted(collections.Counter(kf.values()).items())), rows=rows)
T['land_plan'] = 'results/arch/s81_dv_1016/landing/p4l/land_plan.json'   # LANDFIX-SQ: landings take the p4l plan (per-link tile / K)
T['note'] = T['note'] + '; LANDFIX-SQ/F: frames -> _l4 (crs4) with per-frame lk (bind8/mk_table_p4l2.py)'
json.dump(T, open(B / 'bind_table_p4l2.json', 'w'), indent=1)
print('ok frames', len(frames), 'K hist', T['frame_lk']['K_hist'])
