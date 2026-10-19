#!/usr/bin/env python3
"""SFUPLAN (HANDOFF 0gj, 10-18): SFU core orientation + k9 N-face pin grant + store r10 cluster origins in the d4g plan.

Decisions (coordinator 0gj, lanes/HBM-CRIT.md (2)):
  1. sfucore_<q> (ot_hgi_sfu_core_split3, kit k9) takes its store's orientation: SW R0, SE MY, NW MX, NE R180.
  2. k9 io_word / compiler_control / fault move from the core E face to the N face, core-local x 1040-1598.4
     (~2,284 pins, ~4.1 pins/um).  Written here as the plan pin grant; the SFU-K9PIN kit must match it.
  3. sfup_<q> (ot_hgi_sfu_programme_store_r10 cluster, now 1080 x 950.4) sits over the core's N-face centre-side corner
     (550 um x overlap, store S-face output end x 21.6-588.8 over core-local x 1040-1598), >= 20 um clear of
     everything.  HBM-CRIT gave clear origins with gaps 350/250/100/250 um (pre-SMFRAME y; +276.48 here).  Owner rule
     'no empty area on link paths': every gap is closed to ~20 um by moving the small cij_<q> join leaf (the blocker in
     every quadrant): SW cij (216 x 432) moves 138.8 um E; SE/NE cij (43.2 x 138.24) move into the existing 100-um
     channel between hc_<q> and the core; NW cij moves 39.5 um N inside the same channel.

    d4g_sfuplan.py [--write]
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/hbm_die_d4g'
GRANTS, BIND, PINS = D / 'grants_d4g.json', D / 'gen1_bindings_plan.json', D / 'plan/d4g_phy/pins/d4g_phy.pins.json'
CLR = 20.0
SW_, SH_ = 1080.0, 950.4                      # store r10 cluster outline
OVL = 550.0                                   # store x overlap with the core N-face pin corner
PIN_LO, PIN_HI = 1040.0, 1598.4               # core-local x of the k9 N-face io/ctl/fault window
ORIENT = dict(SW='R0', SE='MY', NW='MX', NE='R180')
TAG = 'SFUPLAN 10-18 (HANDOFF 0gj)'


def rect(s):
    w, h = s['outline']['w'], s['outline']['h']
    if s['origin'].get('orient', 'R0') in ('R90', 'R270'):
        w, h = h, w
    return s['origin']['x'], s['origin']['y'], w, h


def gap(a, b):
    """edge clearance (negative = overlap) between two (x, y, w, h)."""
    dx = max(b[0] - (a[0] + a[2]), a[0] - (b[0] + b[2]))
    dy = max(b[1] - (a[1] + a[3]), a[1] - (b[1] + b[3]))
    return max(dx, dy) if (dx >= 0 or dy >= 0) else max(dx, dy)


def centre(r):
    return r[0] + r[2] / 2, r[1] + r[3] / 2


def man(a, b):
    (ax, ay), (bx, by) = centre(a), centre(b)
    return round(abs(ax - bx) + abs(ay - by), 1)


def plan(S):
    """new origins {slot: (x, y)} per quadrant."""
    new = {}
    for q in ('SW', 'SE', 'NW', 'NE'):
        cx, cy, cw, ch = rect(S[f'sfucore_{q}'])
        hc = rect(S[f'hc_{q}'])
        east_end = q.endswith('W')                       # centre side of the core: E for SW/NW, W for SE/NE
        sx = cx + cw - OVL if east_end else cx + OVL - SW_
        if q.startswith('S'):                            # store above the core
            sy = max(cy + ch, hc[1] + hc[3] if hc[0] < sx + SW_ and sx < hc[0] + hc[2] else -1e9) + CLR
            sy = round(max(cy + ch + CLR, sy), 3)
        else:                                            # store below the core (MX / R180)
            top = min(cy, hc[1] if hc[0] < sx + SW_ and sx < hc[0] + hc[2] else 1e9) - CLR
            sy = round(top - SH_, 3)
        new[f'sfup_{q}'] = (round(sx, 3), sy)
        st = (sx, sy, SW_, SH_)
        jx, jy, jw, jh = rect(S[f'cij_{q}'])
        if q == 'SW':                                    # 216 x 432 rg leaf: east of store and of hc_SW
            new['cij_SW'] = (round(max(st[0] + st[2], hc[0] + hc[2]) + CLR, 3), jy)
        elif q == 'NW':                                  # already in the 100-um hc_NW <-> core channel: lift above the store
            new['cij_NW'] = (jx, round(st[1] + st[3] + CLR, 3))
        else:                                            # SE / NE: into the hc <-> core channel (100 um wide)
            x = round(hc[0] + hc[2] + CLR, 3)
            assert x + jw + CLR <= cx + 1e-6, (q, x, cx)
            y = round(st[1] - CLR - jh, 3) if q == 'SE' else round(st[1] + st[3] + CLR, 3)
            new[f'cij_{q}'] = (x, y)
    return new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    G = json.loads(GRANTS.read_text())
    S = {s['name']: s for s in G['slots'] if s.get('parent') == 'die' and s.get('origin')}
    before = {n: rect(S[n]) for n in S}
    new = plan(S)
    rep = dict(tag=TAG, moves={}, links={}, clearance={}, pin_grant={})
    for n, (x, y) in new.items():
        s = S[n]
        old = dict(s['origin'])
        if n.startswith('sfup_'):
            s['outline'] = dict(w=SW_, h=SH_)
        s['origin']['x'], s['origin']['y'] = x, y
        rep['moves'][n] = dict(old=[old['x'], old['y']], new=[x, y], orient=s['origin'].get('orient'))
        s['notes'] = (s.get('notes', '') + f' | {TAG}: moved ({old["x"]}, {old["y"]}) -> ({x}, {y})'
                      + (' outline 1080 x 950.4 (r10 cluster kit)' if n.startswith('sfup_') else '')).lstrip(' |')
    for q, o in ORIENT.items():
        c = S[f'sfucore_{q}']
        assert S[f'sfup_{q}']['origin']['orient'] == o, q
        c['origin']['orient'] = o
        c['faces'] = dict(c['faces'])
        c['faces']['E'] = 'clk_pe, lanes 8-11'
        c['faces']['N'] = ('clk (x 798.1-800.3) + rst_n/clk_lg/rst_lg_n, lanes 4-7; io_word/compiler_control/fault '
                           f'at core-local x {PIN_LO:g}-{PIN_HI:g} (~2,284 pins, ~4.1/um) facing sfup_{q} S-face output end')
        x0, y0, w, h = rect(c)
        lo, hi = (x0 + PIN_LO, x0 + PIN_HI) if o in ('R0', 'MX') else (x0 + w - PIN_HI, x0 + w - PIN_LO)
        die_face = 'N' if o in ('R0', 'MY') else 'S'
        g = dict(face='N', core_local_x=[PIN_LO, PIN_HI], pins=2284, density_per_um=round(2284 / (PIN_HI - PIN_LO), 2),
                 signals=['io_word', 'compiler_control', 'fault'], peer=f'sfup_{q}', orient=o, die_face=die_face,
                 die_x=[round(lo, 3), round(hi, 3)], die_y=round(y0 + h if die_face == 'N' else y0, 3),
                 status='PLAN GRANT (HANDOFF 0gj); kit SFU-K9PIN not committed at write time: the k9 kit pin regions must match this window',
                 was='E face (k9 kit hbm_sfucore_k9 15beb5d90)')
        c['k9_pin_grant_0gj'] = g
        c['notes'] = (c.get('notes', '') + f' | {TAG}: orient {o} (= sfup_{q}); io_word/compiler_control/fault E -> N face '
                      f'core-local x {PIN_LO:g}-{PIN_HI:g} (k9_pin_grant_0gj)').lstrip(' |')
        rep['pin_grant'][q] = g
    # checks: every moved/re-oriented slot >= CLR clear of every other die slot
    allr = {n: rect(S[n]) for n in S}
    chk = list(new) + [f'sfucore_{q}' for q in ORIENT]
    bad = []
    for n in chk:
        near = sorted(((round(gap(allr[n], allr[m]), 2), m) for m in allr if m != n))
        rep['clearance'][n] = near[:3]
        bad += [(n, m, d) for d, m in near if d < CLR - 1e-3 and abs(gap(before[n], before[m]) - d) > 1e-6]
    rep['violations'] = bad
    for q in ORIENT:
        st, co, cj = allr[f'sfup_{q}'], allr[f'sfucore_{q}'], allr[f'cij_{q}']
        su1 = allr[f'su_{q}1']; suc = allr[f'sucore_{q}']; col = allr[f'coll_{q}']
        g = rep['pin_grant'][q]
        ovl = min(st[0] + st[2], co[0] + co[2]) - max(st[0], co[0])
        o = ORIENT[q]
        out_lo, out_hi = (st[0] + 21.6, st[0] + 588.8) if o in ('R0', 'MX') else (st[0] + SW_ - 588.8, st[0] + SW_ - 21.6)
        win = min(out_hi, g['die_x'][1]) - max(out_lo, g['die_x'][0])
        rep['links'][q] = dict(
            store_core_gap_um=round(gap(st, co), 2), store_core_gap_hbmcrit_um={'SW': 350, 'SE': 250, 'NW': 100, 'NE': 250}[q],
            store_core_x_overlap_um=round(ovl, 2), store_out_vs_core_pin_window_overlap_um=round(win, 2),
            store_out_die_x=[round(out_lo, 2), round(out_hi, 2)],
            core_su1_gap_um=round(gap(co, su1), 2),
            core_face_to_su1=('W' if o in ('R0', 'MX') else 'W (mirrored to die E)'),
            cij_sucore_centre_manhattan_um=[man(before[f'cij_{q}'], suc), man(cj, suc)],
            cij_coll_centre_manhattan_um=[man(before[f'cij_{q}'], col), man(cj, col)])
    # gen1 binding plan + d4g.gen1 copy: sfup store re-plan entries follow
    B = json.loads(BIND.read_text())
    for tgt in (B.get('sfu_store_replan'), G.get('d4g', {}).get('gen1', {}).get('sfu_store_replan')):
        if not tgt:
            continue
        for m in tgt['moves']:
            x, y = new[m['slot']]
            m['new'] = dict(x=x, y=y, orient=m['new']['orient'])
        tgt['sfuplan_0gj'] = (f'{TAG}: store r10 cluster 1080 x 950.4 over the core N-face centre-side corner '
                              f'(550 um overlap), gap ~20 um in every quadrant (HBM-CRIT 350/250/100/250); cores take the '
                              f'store orientation; cij_<q> moved (d4g_sfuplan.py)')
    # plan pin file: sfucore N-face (core-local) window, in die coordinates
    PP = json.loads(PINS.read_text())
    for q, o in ORIENT.items():
        b = PP['blocks'].get(f'sfucore_{q}')
        if b is None:
            continue
        g = rep['pin_grant'][q]
        b['orient'] = o
        b['faces'][g['die_face']] = dict(face_len_um=1598.4, bits=2284, utilisation=round(2284 / 1598.4 / PP['pin_density_per_um'], 3),
                                         pins=[dict(link=f'sfup_{q}>sfucore_{q}:SFU_PROG', cls='SFU_PROG', peer=f'sfup_{q}', dir='in',
                                                    bits=2284, offset_um=PIN_LO, span_um=round(PIN_HI - PIN_LO, 2),
                                                    x=round(sum(g['die_x']) / 2, 1), y=g['die_y'],
                                                    note=f'{TAG}: k9 io_word/compiler_control/fault, core-local N face (die {g["die_face"]} after {o})')])
    print(json.dumps(rep, indent=1))
    if bad:
        raise SystemExit(f'clearance violations: {bad}')
    if a.write:
        G['updated'] = '2026-10-18'
        GRANTS.write_text(json.dumps(G, indent=1) + '\n')
        BIND.write_text(json.dumps(B, indent=1) + '\n')
        PINS.write_text(json.dumps(PP, indent=1) + '\n')
        (D / 'sfuplan_report.json').write_text(json.dumps(rep, indent=1) + '\n')


if __name__ == '__main__':
    main()
