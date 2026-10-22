#!/usr/bin/env python3
"""S81 selected72 G7 plan (S81-LINK5B L5B-G7 10-21): dv_plan72_g4 (G3 base + 5th lane pair) on the G7 floorplan
(dv_floorplan72_g7.py) + the S81-RTLGAP/eng die-top request (tools/s81_dv/eng_rr/die_bind_request.json @ccefda9d5):

  blocks  eng (dsdv_eng_rr, slot eng_00), etap_00 (dsdv_eng_tap_w), etap_01..15 (dsdv_eng_tap), slots etap_<k>.
  reader links through the taps (k = 2j + h, reader irg_j):  hrrq_k  irg_j.rqo -> etap_k.rqi   (+ erq_k etap_k.rqo -> ctrl_k.rrq)
                                                            hrrd_k  etap_k.rro -> irg_j.rri   (+ erd_k ctrl_k.rrd -> etap_k.rri)
     (the reader-side links keep their names, so the reader's lane order by link name is unchanged)
  request chain   erc_15 eng.rco -> etap_15.rci ; erc_k etap_(k+1).rco -> etap_k.rci (k = 14..0)        43 b on 276 lanes
  response chain  epc_k etap_k.pco -> etap_(k+1).pci (k = 0..14) ; epc_15 etap_15.pco -> eng.pci         268 b on 276 lanes
  f_ks fork       eks_7N s_7N.ks -> eng.f_ks (53 b; s_7N ks.o = a copy of the f_ks bits its hf lanes carry)
  column-6 rung   tvN_s_6S s_6S.vN -> eng.vS ; tvS_eng eng.vS -> s_6S.vN ; tvS_s_6N s_6N.vS -> eng.vN ; tvN_eng eng.vN -> s_6N.vS
                  (= the gunit rung on column 3)
Endpoint seeds: plan face seeds (dv_rvcase reprojects actual view pins), facing the peer.
"""
import argparse, copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dv_plan72 import build
from dv_plan72_g4 import augment


def seed(b, face, t):
    x, y, w, h = b['x'], b['y'], b['w'], b['h']
    t = min(0.95, max(0.05, t))
    return {'W': (x, y + t * h), 'E': (x + w, y + t * h), 'S': (x + t * w, y), 'N': (x + t * w, y + h)}[face]


def g7(p, packing):
    geo = {b['name']: b for b in packing['best']['blocks']}
    B = p['blocks']
    def add(name, slot, master):
        g = geo[slot]
        B.append(dict(name=name, master=master, kind='unit', group='south' if name.startswith('etap') else 'void',
                      x=g['x'], y=g['y'], w=g['w'], h=g['h'], reg=False))
        return len(B) - 1
    ix = {b['name']: i for i, b in enumerate(B)}
    ix['eng'] = add('eng', 'eng_00', 'dsdv_eng_rr')
    for k in range(16):
        ix[f'etap_{k:02}'] = add(f'etap_{k:02}', f'etap_{k:02}', 'dsdv_eng_tap_w' if k == 0 else 'dsdv_eng_tap')
    L = {l['i']: l for l in p['links']}
    def ep(name, port, face, t):
        x, y = seed(B[ix[name]], face, t)
        return [ix[name], port, round(x, 4), round(y, 4), 'box']
    def link(i, c, b, src, dst, faces, n):
        assert i not in L, i
        l = dict(i=i, c=c, b=b, d=1, e=[src, dst], n=n, endpoint_faces=list(faces)); p['links'].append(l); L[i] = l
    new = []
    for k in range(16):
        t = f'etap_{k:02}'; tb = B[ix[t]]
        q, r = L[f'hrrq_{k:02}'], L[f'hrrd_{k:02}']
        rd_face = 'W' if k < 8 else 'E'         # reader side of the tap (W pocket readers are west, E pocket east)
        ct_face = 'E' if k < 8 else 'W'
        cq, cr = q['e'][1], r['e'][0]            # ctrl ends (rrq in, rrd out), kept
        assert B[cq[0]]['name'] == f'ctrl_{k:02}' and B[cr[0]]['name'] == f'ctrl_{k:02}'
        q['e'][1] = ep(t, 'rqi', rd_face, 0.30); q['endpoint_faces'][1] = rd_face
        r['e'][0] = ep(t, 'rro', rd_face, 0.55); r['endpoint_faces'][0] = rd_face
        link(f'erq_{k:02}', 'hbm', q['b'], ep(t, 'rqo', ct_face, 0.30), cq, (ct_face, 'N'),
             'Engram tap -> controller reader request (tap register, +1 edge)')
        link(f'erd_{k:02}', 'hbm', r['b'], cr, ep(t, 'rri', ct_face, 0.55), ('N', ct_face),
             'controller reader response -> Engram tap (tap register, +1 edge)')
        new += [f'erq_{k:02}', f'erd_{k:02}']
    for k in range(16):                          # chains run along the tap row (N/S faces at the row ends would detour)
        t = f'etap_{k:02}'
        src = ep('eng', 'rco', 'S', 0.70) if k == 15 else ep(f'etap_{k + 1:02}', 'rco', 'N', 0.25)
        link(f'erc_{k:02}', 'unit', 276, src, ep(t, 'rci', 'N', 0.40), ('S' if k == 15 else 'N', 'N'),
             'Engram request chain {tag 7, sec 30, pc 5, v} (43 b), east -> west')
        if k < 15:
            link(f'epc_{k:02}', 'unit', 276, ep(t, 'pco', 'N', 0.60), ep(f'etap_{k + 1:02}', 'pci', 'N', 0.80), ('N', 'N'),
                 'Engram response chain {d 256, tag 7, own 4, v} (268 b), west -> east')
        else:
            link('epc_15', 'unit', 276, ep(t, 'pco', 'N', 0.60), ep('eng', 'pci', 'S', 0.85), ('N', 'S'),
                 'Engram response chain -> eng (268 b)')
        new += [f'erc_{k:02}', f'epc_{k:02}']
    hf = L['hf_7N_l2']; s7 = hf['e'][0]
    assert B[s7[0]]['name'] == 's_7N'
    link('eks_7N', 'unit', 276, [s7[0], 'ks', s7[2], s7[3], 'box'], ep('eng', 'f_ks', 'E', 0.5), (hf['endpoint_faces'][0], 'E'),
         's_7N f_ks (53 b) second sink: Engram window former (seqhost.f_ks unchanged)')
    new.append('eks_7N')
    a, b_ = L['tvN_s_6S'], L['tvS_s_6N']         # s_6S.vN -> s_6N.vS ; s_6N.vS -> s_6S.vN
    assert (B[a['e'][0][0]]['name'], B[a['e'][1][0]]['name']) == ('s_6S', 's_6N')
    assert (B[b_['e'][0][0]]['name'], B[b_['e'][1][0]]['name']) == ('s_6N', 's_6S')
    s6N_in, s6S_in = a['e'][1], b_['e'][1]
    f6N, f6S = a['endpoint_faces'][1], b_['endpoint_faces'][1]
    a['e'][1] = ep('eng', 'vS', 'S', 0.15); a['endpoint_faces'][1] = 'S'
    b_['e'][1] = ep('eng', 'vN', 'S', 0.45); b_['endpoint_faces'][1] = 'S'
    link('tvS_eng', a['c'], a['b'], ep('eng', 'vS', 'S', 0.30), s6S_in, ('S', f6S), 'column-6 rung via eng (eng.vo_s -> s_6S.vi)')
    link('tvN_eng', a['c'], a['b'], ep('eng', 'vN', 'S', 0.55), s6N_in, ('S', f6N), 'column-6 rung via eng (eng.vo_n -> s_6N.vi)')
    new += ['tvS_eng', 'tvN_eng']
    p['facts']['physical72']['g7'] = dict(
        floorplan='dv_floorplan72_g7.py: readers in the south pockets beside the PHY, 16 Engram taps in the ctrl/service strip, '
                  'eng above s_6S, bk_sel 907.2 x 4190.4, die 32648 x 25952.4',
        retargeted=['hrrq_00..15 -> etap_k.rqi', 'hrrd_00..15 <- etap_k.rro', 'tvN_s_6S -> eng.vS', 'tvS_s_6N -> eng.vN'],
        new_links=new, eng_request='tools/s81_dv/eng_rr/die_bind_request.json (ccefda9d5)')
    return p


def main():
    a = argparse.ArgumentParser(); a.add_argument('--base', required=True); a.add_argument('--inventory', required=True)
    a.add_argument('--packing', required=True); a.add_argument('--out', required=True); v = a.parse_args()
    base, inv, pk = [json.load(open(x)) for x in (v.base, v.inventory, v.packing)]
    p = g7(build(augment(base), inv, pk), pk)
    p['facts']['physical72']['g4'] = dict(lane_pair5='s_0N pair B (lepw_mab_mu_72) <-> lk_WN2/lk_WN3 = link_0_4/link_0_5',
                                          new_links=['lt_lk_WN2', 'lr_lk_WN2', 'lt_lk_WN3', 'lr_lk_WN3'],
                                          reserves=[r['name'] for r in p['blockages']])
    Path(v.out).write_text(json.dumps(p, indent=1))
    print(json.dumps(dict(blocks=len(p['blocks']), links=len(p['links']), blockages=len(p['blockages']), die=p['facts']['die_um'])))


if __name__ == '__main__':
    main()
