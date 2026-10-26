#!/usr/bin/env python3
"""H-D4G-GEN2 10-18 (coordinator 0gd C2 / HOSTEP 4ec71b108): own grant slots for the host control-plane endpoint pair.
host_ep (hfd_ep_static, CLOSED, 434.72 x 315.36; W face sd_* toward host_N) with host_cp_rxs (ot_hbm_host_cp_rxs, kit
hdie_host_cprxs_r1, SYNTH until it closes; 434.72 x 432; N face mirrors ep S pin-for-pin) DIRECTLY below it, abutted (no
relay: TXLAT 9 / RXLAT 6 assume 0 stages), both reset from the same reset-tree level (l5_host_ep clocks_of: same source).
host_ep sits just N of the host_cp box, E of hb_argmax (W face 162 um from host_N, no relay at reach 405), host_cp_rxs
below it inside the host_cp box N of host_cp_ingress (AXI-lite ~100 um).  Idempotent.
    d4g_gen2_grants_host.py [--grants results/arch/hbm_die_d4g/grants_d4g.json]"""
import argparse, json
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument('--grants', default='results/arch/hbm_die_d4g/grants_d4g.json'); a = ap.parse_args()
g = json.loads(Path(a.grants).read_text()); S = {s['name']: s for s in g['slots']}
hc, hn = S['host_cp'], S['host_N']
am = S['hb_argmax']
EP = (434.72, 315.36); RX = (434.72, 432.0)
x0 = round(am['origin']['x'] + am['outline']['w'] + 20.0, 3)          # E of hb_argmax (20 um clear)
y_ep = round(hc['origin']['y'] + hc['outline']['h'] + 20.0, 3)        # just N of the host_cp box
y_rx = round(y_ep - RX[1], 3)                                         # host_cp_rxs directly below, abutted
ing = S['host_cp_ingress']                                            # child of host_cp (parent-local)
assert y_rx >= hc['origin']['y'] + ing['origin']['y'] + ing['outline']['h'] + 20.0 or x0 >= hc['origin']['x'] + ing['origin']['x'] + ing['outline']['w'] + 20.0
new = {
  'host_cp_rxs': dict(cell='ot_hbm_host_cp_rxs', kind='tile', outline=dict(w=RX[0], h=RX[1]), origin=dict(x=x0, y=y_rx, orient='R0'),
                      notes='HOSTEP (4ec71b108): host control-plane tile, kit hdie_host_cprxs_r1 (gate WARN, SYNTH until closed); N face abutted to host_ep S face pin-for-pin; same reset level as host_ep'),
  'host_ep': dict(cell='hfd_ep_static', kind='tile', outline=dict(w=EP[0], h=EP[1]), origin=dict(x=x0, y=round(y_rx + RX[1], 3), orient='R0'),
                  notes='HOSTEP: CLOSED hfd_ep_static (hep_static_w5f_1016); W face sd_tx/sd_rx/sd_st -> host_N (18.9 um); S face abutted to host_cp_rxs'),
}
for n, d in new.items():
    s = S.get(n)
    if s is None:
        s = dict(name=n, parent='die', version=1); g['slots'].append(s); S[n] = s
    s.update(d, grant='gen2_hostep_0gd', pins=[], pin_status='FACES_ONLY')
def r(s):
    o, w = s['origin'], s['outline']; x, y = o['x'], o['y']
    if s.get('parent') not in (None, 'die') and s['parent'] in S:      # child slot: parent-local origin
        x += S[s['parent']]['origin']['x']; y += S[s['parent']]['origin']['y']
    return x, y, x + w['w'], y + w['h']
bad = []
for n in new:
    a0 = r(S[n])
    for m, s in S.items():
        if m in new or m == n or s.get('kind') == 'die' or not s.get('origin') or not s.get('outline') or m == 'host_cp':
            continue
        b = r(s)
        if a0[0] < b[2] + 20 and b[0] < a0[2] + 20 and a0[1] < b[3] + 20 and b[1] < a0[3] + 20:
            bad.append((n, m, [round(v, 1) for v in b]))
Path(a.grants).write_text(json.dumps(g, indent=1) + '\n')
print('host slots', {n: r(S[n]) for n in new}, 'clearance_violations', bad)
