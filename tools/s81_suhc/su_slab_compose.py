#!/usr/bin/env python3
"""Composition outline of the hierarchical SU slab dsfd_sp_su_h in the su_s W-floor slot (s81-suhc-hier-1011,
2026-10-11).  Three abutting 572.4-um tile columns (x on 10.8), a 21.6-um relay channel under every tile (the spine /
rung / seam relay stations of dsfd_sp_su_h live there; y on 2.16).  Spine order = dsfd_sp_su_h tile order:
  col 2 (E, under the VM pins): pin owners po0..po3, control tile, QN0 QN1 KV0 KV1 QB0 QB1   (top -> bottom)
  col 1:                        QB2 QB3 SW0..SW6                                              (bottom -> top)
  col 0 (W):                    SW7 SM0..SM7                                                  (top -> bottom)
Pin rows use the su_hc v2 contract names (physical/s81_ph_views/contracts_1011/su_hc.layer1suhc.json, sp_su_s):
N/E-face pins keep their offset from the NE corner, t_hc its y.

    python3 tools/s81_suhc/su_slab_compose.py  -> physical/s81_ph_views/su_hier/su_slab_composition.json (+ summary)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W_SLAB, CW, CH = 1727.976, 572.4, 21.6
SIZE = dict(po=475.2, ctl=216.0, qn=604.8, kv=604.8, qb=637.2, sw=637.2, sm=637.2)
MASTER = dict(po='dsfd_su_t_pin', ctl='dsfd_su_t_ctl', qn0='dsfd_su_t_qn0', qn1='dsfd_su_t_qn1', kv0='dsfd_su_t_kv0',
              kv1='dsfd_su_t_kv1', qb='dsfd_su_t_qb', sw='dsfd_su_t_sw', sm='dsfd_su_t_sm')
COLS = {2: (['po0', 'po1', 'po2', 'po3', 'ctl', 'qn0', 'qn1', 'kv0', 'kv1', 'qb0', 'qb1'], 'down'),
        1: (['qb2', 'qb3'] + [f'sw{i}' for i in range(7)], 'up'),
        0: (['sw7'] + [f'sm{i}' for i in range(8)], 'down')}


def h(name):
    return SIZE[name[:3] if name[:3] in SIZE else name[:2]]


def master(name):
    return MASTER.get(name) or MASTER[name[:2] if name[:2] in MASTER else name[:3]]


def main():
    col_h = {c: sum(h(n) + CH for n in ns) for c, (ns, _) in COLS.items()}
    H = round(round((max(col_h.values()) + CH) / 2.16) * 2.16, 3)
    tiles = []
    for c, (ns, d) in COLS.items():
        x = round(c * CW, 4)
        if d == 'down':
            y = H
            for n in ns:
                y = round(y - CH - h(n), 4)
                tiles.append(dict(inst=n, master=master(n), x=x, y=y, w=CW, h=h(n), col=c))
        else:
            y = CH
            for n in ns:
                tiles.append(dict(inst=n, master=master(n), x=x, y=round(y, 4), w=CW, h=h(n), col=c))
                y += h(n) + CH
    con = json.load(open(ROOT / 'physical/s81_ph_views/contracts_1011/su_hc.layer1suhc.json'))
    su = [i for i in con['instances'] if i['instance'] == 'sp_su_s'][0]
    H0 = su['outline_um'][1]
    pins = []
    for n, p in list(su['pins'].items()) + list(su['reserved_ctrl'].items()):
        a, b = p['span_um']
        if p['face'] == 'E' and n != 't_hc':
            a, b = H - (H0 - a), H - (H0 - b)
        pins.append(dict(pin=n, face=p['face'], layer=p['layer'], bits=p['bits'], span_um=[round(a, 3), round(b, 3)]))
    rec = dict(schema='opentallas.s81.su-slab-composition.v1', slab='dsfd_sp_su_h (su_s W-floor slot)',
               outline_um=[W_SLAB, H], columns_x_um=[0.0, CW, 2 * CW], channel_um=CH, tiles=tiles, pins=pins,
               spine_order=COLS[2][0][5:] + COLS[1][0] + COLS[0][0],
               notes=['spine: dsfd_sp_su_h stops in the order col 2 down (from QN0), col 1 up, col 0 down; SRD 2 relay '
                      'stations a stop in the channels (adjacent tile centres ~620 um)',
                      'pin owners po0..po3 sit directly W of f_vm (NE corner): VM read / write slots 4 each; NRL 4 relay '
                      'stations on every pin owner link (the stack spans ~2 mm)',
                      'csu / dsu (c_cmd / c_done, cck) reach the control tile over NRC 5 relay stations (~2.25 mm, <= 500 um '
                      'a station)',
                      'f_vm is the contract VM hub port (1,024 b); the slab RTL VM interface is 16 read + 16 write row '
                      'slots (rq / rs / wq): the VM hub binding is the generator\'s, its endpoint next to po0..po3',
                      'f_capture / t_hc are die hub pins of the contract that dsfd_sp_su_h does not bind (no capture / '
                      'HC port in the SU engine): generator to route through or retire'])
    out = ROOT / 'physical/s81_ph_views/su_hier/su_slab_composition.json'
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'outline {W_SLAB} x {H}; columns {col_h}')
    for t in tiles:
        print(f"  {t['inst']:4s} {t['master']:15s} xy ({t['x']}, {t['y']})  {t['w']} x {t['h']}")
    for p in pins:
        print(f"  pin {p['pin']:10s} {p['face']} {p['layer']} {p['bits']:5d} b  {p['span_um']}")


if __name__ == '__main__':
    main()
