#!/usr/bin/env python3
"""H-DIE-R8b 2026-10-17: d4f grants r8 -> r8b (slot changes of the run8b bindings).

  * sfup_<q> (SFU programme store r10 parent cluster, coordinator 0dh++ DECISION B): 950.4 x 950.4 (lattice; was 447.12 x
    1023.84).  SW/SE/NE grow EAST from the same origin into free space (sfus_<q> keeps its abutment with sfucore_<q>,
    0 relays); NW has pgp_NW east and sfus_NW west, so sfup_NW sits above pgp_NW (y 20412) and sucore_NW moves 300 um
    east (x 9000, still W of su_NW2) to make room.
  * cij_SW -> ot_hgi_coll_inj_idx_join_rg (CLOSED hcoll_inj_idx_join_rg_1017, 216 x 432): abuts coll_SW on its W face.
  * LG fold (0db, CLOSED tap leaves 216 x 216): sfu_<q><g> = ot_hgi_sfu_lg_pair_tap_leaf 216 x 216 at the old leaf
    origin (nearest legal 10.8-um site if that overlaps); hc_<q><g> = ot_hgi_sfu_lg_pair_tap_leaf_term 216 x 216 at
    the W face of sfu_<q><g> (the 500 x 500 hfd_hc shell retires; HC<->SFU tap seam 0 um, no empty area on the LG chain).
Every changed slot is checked against every other die-level slot (no overlap) and the die outline.

    grants_r8b_d4f.py IN_grants.json OUT_grants.json
"""
import json
import sys

QS = ('SW', 'SE', 'NE', 'NW')
SFUP = (950.4, 950.4)   # SFU-PS-3: the 941.76-wide parent was off the 43.2 lattice; widened to 950.4 (pending_results 10-17)


def rect(s):
    o, w = s['origin'], s['outline']
    return (o['x'], o['y'], o['x'] + w['w'], o['y'] + w['h'])


def ov(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def main(gin, gout):
    g = json.load(open(gin))
    S = {s['name']: s for s in g['slots'] if s.get('parent') == 'die' and s.get('outline') and s.get('origin')}
    die = next(s for s in g['slots'] if s['name'] == 'die')['outline']
    log = []

    def set_slot(n, x, y, w, h, cell=None, why=''):
        s = S[n]
        old = [round(v, 2) for v in rect(s)]
        s['origin'] = dict(s['origin'], x=round(x, 3), y=round(y, 3))
        s['outline'] = dict(s['outline'], w=w, h=h)
        if cell:
            s['cell'] = cell
        s['notes'] = (s.get('notes', '') + f' | H-DIE-R8b 10-17: {why} (was {old})').strip(' |')
        log.append((n, old, [round(v, 2) for v in rect(s)], why))

    for q in ('SW', 'SE', 'NE'):
        o = S[f'sfup_{q}']['origin']
        set_slot(f'sfup_{q}', o['x'], o['y'], *SFUP, cell='ot_hgi_sfu_programme_store_r10',
                 why='SFU store r10 parent 3x4 leaves + centre head, grown east')
    set_slot('sucore_NW', 9000.0, 21000.0, S['sucore_NW']['outline']['w'], S['sucore_NW']['outline']['h'],
             why='300 um east to free the sfup_NW r10 slot (still W of su_NW2)')
    set_slot('sfup_NW', S['sfup_NW']['origin']['x'], 20412.0, *SFUP, cell='ot_hgi_sfu_programme_store_r10',
             why='SFU store r10 parent, above pgp_NW')
    set_slot('cij_SW', 16446.16, 9254.4, 216.0, 432.0, cell='ot_hgi_coll_inj_idx_join_rg',
             why='CLOSED cij rg 216x432 (2 regional roots), abuts coll_SW W face')
    for q in QS:
        for k in range(4):
            o = S[f'hc_{q}{k}']['origin']
            xs = S[f'sfu_{q}{k}']['origin']['x'] - 216.0     # abut the SFU-level fold (the HC<->SFU LG seam is 0 um)
            set_slot(f'hc_{q}{k}', xs, S[f'sfu_{q}{k}']['origin']['y'], 216.0, 216.0, cell='ot_hgi_sfu_lg_pair_tap_leaf_term',
                     why='LG fold: CLOSED HC pair leaf + terminal pair tap 216x216 abutting sfu W face (500x500 hfd_hc shell retired)')
    for q in QS:
        for k in range(4):
            n = f'sfu_{q}{k}'
            o = S[n]['origin']
            others = [rect(s) for m, s in S.items() if m != n]
            best = None
            for r_ in range(0, 40):
                for dx in range(-r_, r_ + 1):
                    for dy in range(-r_, r_ + 1):
                        if max(abs(dx), abs(dy)) != r_:
                            continue
                        x, y = o['x'] + 10.8 * dx, o['y'] + 10.8 * dy
                        c = (x, y, x + 216.0, y + 216.0)
                        if c[0] < 0 or c[1] < 0 or c[2] > die['w'] or c[3] > die['h']:
                            continue
                        if not any(ov(c, b) for b in others):
                            d = abs(dx) + abs(dy)
                            if best is None or d < best[0]:
                                best = (d, x, y)
                if best:
                    break
            assert best, n
            set_slot(n, best[1], best[2], 216.0, 216.0, cell='ot_hgi_sfu_lg_pair_tap_leaf',
                     why='LG fold: CLOSED SFU pair leaf + pair tap 216x216')
    bad = []
    names = sorted(S)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if ov(rect(S[a]), rect(S[b])):
                bad.append((a, b))
    changed = {x[0] for x in log}
    bad = [p for p in bad if p[0] in changed or p[1] in changed]
    for x in log:
        print('SLOT', *x)
    print('OVERLAPS on changed slots:', bad)
    assert not bad
    g['version'] = str(g.get('version', '')) + '+r8b'
    g.setdefault('notes_r8b', __doc__.split('    grants_r8b')[0].strip())
    json.dump(g, open(gout, 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:3])
