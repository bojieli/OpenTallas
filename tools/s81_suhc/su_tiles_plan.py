#!/usr/bin/env python3
"""Hardened tile masters of the hierarchical SU slab dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the RTL wrappers
(rtl/dsrom_sys/s81_suhc/hier/dsfd_su_tiles.sv, production params, lane group 0 of each function) and their contract pin
plans (tools/s81_ph/s81_ph_tiles_plan.py conventions: M4 W / E, M5 N / S, x on 10.8, y on 2.16).

Pin plan: the down-spine tap enters on the W face (row data low half, M4) and the S face (high half, M5) next to the
spine; the tile's write slots leave on the E face (QN / KV: the N face); job announce / status on the N face.

    python3 tools/s81_suhc/su_tiles_plan.py   -> physical/s81_ph_views/ports/contract/<master>/{ports.json,io_place.tcl,
                                                 ports.svh}, physical/s81_ph_views/specs/<master>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_tiles_plan as TP  # noqa: E402

S_RD, S_WR = 16, 16
HALF = S_RD * 512 // 2


def spec(master, ws, w, h, note):
    od_face, od_layer = ('N', 'M5') if ws == S_WR else ('E', 'M4')
    ports = [['dn_dl', HALF, 'input', 'W', 'M4', 2, 0.5], ['dn_dh', HALF, 'input', 'S', 'M5', 2, 0.45],
             ['ck', 1, 'input', 'S', 'M5', 1, 0.93], ['rst', 1, 'input', 'S', 'M5', 1, 0.95],
             ['dn_st', 1, 'input', 'N', 'M5', 1, 0.01], ['dn_kind', 4, 'input', 'N', 'M5', 2, 0.02],
             ['dn_gsel', 2, 'input', 'N', 'M5', 2, 0.03], ['dn_fp4', 1, 'input', 'N', 'M5', 1, 0.04],
             ['dn_jid', 8, 'input', 'N', 'M5', 2, 0.05], ['dn_v', S_RD, 'input', 'N', 'M5', 2, 0.07],
             ['dn_ph', 1, 'input', 'N', 'M5', 1, 0.09], ['dn_idx', 16, 'input', 'N', 'M5', 2, 0.11],
             ['o_fu', 1, 'output', 'N', 'M5', 1, 0.97], ['o_fo', 1, 'output', 'N', 'M5', 1, 0.972],
             ['o_alive', 1, 'output', 'N', 'M5', 1, 0.974], ['o_den', 1, 'output', 'N', 'M5', 1, 0.976],
             ['o_rdy', 1, 'output', 'N', 'M5', 1, 0.978], ['o_rjid', 8, 'output', 'N', 'M5', 2, 0.99]]
    if od_face == 'N':
        ports += [['o_d', 512 * ws, 'output', 'N', 'M5', 2, 0.55], ['o_v', ws, 'output', 'E', 'M4', 2, 0.1],
                  ['o_a', 14 * ws, 'output', 'E', 'M4', 2, 0.4], ['o_m', 16 * ws, 'output', 'E', 'M4', 2, 0.75]]
    else:
        ports += [['o_d', 512 * ws, 'output', 'E', 'M4', 2, 0.45], ['o_v', ws, 'output', 'E', 'M4', 2, 0.03],
                  ['o_a', 14 * ws, 'output', 'E', 'M4', 2, 0.85], ['o_m', 16 * ws, 'output', 'E', 'M4', 2, 0.95]]
    return dict(master=master, w_um=w, h_um=h, domain='stream_1p2', note=note, ports=ports)


SPECS = [
    spec('dsfd_su_t_qn', 16, 1209.6, 604.8, 'QN norm tile: ot_dsrom_su_norm N 256 D 1,280 + the q gain sets'),
    spec('dsfd_su_t_kv', 16, 1209.6, 604.8, 'KV norm tile: ot_dsrom_su_norm N 512 RD 64 + the kv gain sets'),
    spec('dsfd_su_t_qb', 4, 604.8, 604.8, 'QB lane tile 0 of 4: ot_dsrom_su_qbank NB 8'),
    spec('dsfd_su_t_sw', 2, 604.8, 604.8, 'SW lane tile 0 of 8: ot_dsrom_su_swiglu W 128 ROUTED'),
    spec('dsfd_su_t_sm', 2, 604.8, 604.8, 'SM head tile 0 of 8: ot_dsrom_su_softmax H 2 LPH 16'),
]


def main():
    summ = {}
    for sp in SPECS:
        ports = TP.plan(sp)
        rec = TP.write(sp['master'], sp['w_um'], sp['h_um'], sp['domain'], ports, sp)
        rec['generator'] = dict(file='tools/s81_suhc/su_tiles_plan.py')
        d = ROOT / 'physical/s81_ph_views/ports/contract' / sp['master']
        (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
        (d / 'io_place.tcl').write_text((d / 'io_place.tcl').read_text().replace('tools/s81_ph/s81_ph_tiles_plan.py',
                                                                                 'tools/s81_suhc/su_tiles_plan.py'))
        summ[sp['master']] = dict(w=sp['w_um'], h=sp['h_um'], pins=sum(len(p['pins']) for p in ports.values()))
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
