#!/usr/bin/env python3
"""Hardened tile masters of the hierarchical SU slab dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the RTL wrappers
(rtl/dsrom_sys/s81_suhc/hier/dsfd_su_tiles.sv, production params, lane group 0 of each function) and their contract pin
plans (tools/s81_ph/s81_ph_tiles_plan.py conventions: M4 W / E, M5 N / S, x on 10.8, y on 2.16).

Every tile is 572.4 um wide (three columns across the 1,727.976-um slab).  Engine tiles: the down-spine tap enters on
the W face (QN / KV both halves, others the low half + the high half on S), the write slots leave on E, job announce /
status on N.  Root tile (adapter + control): VM rows on W, the spines on E, controller pins on N.

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


W = 572.4      # every tile <= ~600 um (three tile columns across the 1,727.976-um slab), x on 10.8


def spec(master, ws, h, note):
    """engine tile: the down-spine tap on W (+ S when the W face is short), write slots on E, job / status on N"""
    tall = h > 1000
    ports = [['dn_dl', HALF, 'input', 'W', 'M4', 2, 0.25 if tall else 0.5],
             ['dn_dh', HALF, 'input', 'W' if tall else 'S', 'M4' if tall else 'M5', 2, 0.72 if tall else 0.45],
             ['ck', 1, 'input', 'S', 'M5', 1, 0.93], ['rst', 1, 'input', 'S', 'M5', 1, 0.95],
             ['dn_st', 1, 'input', 'N', 'M5', 1, 0.01], ['dn_kind', 4, 'input', 'N', 'M5', 2, 0.02],
             ['dn_gsel', 2, 'input', 'N', 'M5', 2, 0.03], ['dn_fp4', 1, 'input', 'N', 'M5', 1, 0.04],
             ['dn_jid', 8, 'input', 'N', 'M5', 2, 0.05], ['dn_v', S_RD, 'input', 'N', 'M5', 2, 0.07],
             ['dn_ph', 1, 'input', 'N', 'M5', 1, 0.09], ['dn_idx', 16, 'input', 'N', 'M5', 2, 0.11],
             ['o_fu', 1, 'output', 'N', 'M5', 1, 0.97], ['o_fo', 1, 'output', 'N', 'M5', 1, 0.972],
             ['o_alive', 1, 'output', 'N', 'M5', 1, 0.974], ['o_den', 1, 'output', 'N', 'M5', 1, 0.976],
             ['o_rdy', 1, 'output', 'N', 'M5', 1, 0.978], ['o_rjid', 8, 'output', 'N', 'M5', 2, 0.99],
             ['o_d', 512 * ws, 'output', 'E', 'M4', 2, 0.45], ['o_v', ws, 'output', 'E', 'M4', 2, 0.03],
             ['o_a', 14 * ws, 'output', 'E', 'M4', 2, 0.85], ['o_m', 16 * ws, 'output', 'E', 'M4', 2, 0.95]]
    return dict(master=master, w_um=W, h_um=h, domain='stream_1p2', note=note, ports=ports)


def root():
    """root tile at the c_cmd / VM pin edge: VM rd / wr on W (slab pins), spines on E, controller pins on N"""
    D = S_RD * 512
    ports = [['rs_d', D, 'input', 'W', 'M4', 2, 0.25], ['rs_v', S_RD, 'input', 'W', 'M4', 2, 0.48],
             ['rq_v', S_RD, 'output', 'W', 'M4', 2, 0.49], ['rq_row', 14 * S_RD, 'output', 'W', 'M4', 2, 0.505],
             ['wq_d', 512 * S_WR, 'output', 'W', 'M4', 2, 0.73], ['wq_v', S_WR, 'output', 'W', 'M4', 2, 0.975],
             ['dn_d', D, 'output', 'E', 'M4', 2, 0.25], ['up_a', 14 * S_WR, 'input', 'E', 'M4', 2, 0.48],
             ['up_m', 16 * S_WR, 'input', 'E', 'M4', 2, 0.505], ['up_d', 512 * S_WR, 'input', 'E', 'M4', 2, 0.73],
             ['up_v', S_WR, 'input', 'E', 'M4', 2, 0.975],
             ['wq_row', 14 * S_WR, 'output', 'S', 'M5', 2, 0.15], ['wq_mask', 16 * S_WR, 'output', 'S', 'M5', 2, 0.35],
             ['dn_v', S_RD, 'output', 'S', 'M5', 2, 0.5], ['dn_idx', 16, 'output', 'S', 'M5', 2, 0.53],
             ['dn_st', 1, 'output', 'S', 'M5', 1, 0.55], ['dn_kind', 4, 'output', 'S', 'M5', 2, 0.56],
             ['dn_gsel', 2, 'output', 'S', 'M5', 2, 0.57], ['dn_fp4', 1, 'output', 'S', 'M5', 1, 0.58],
             ['dn_jid', 8, 'output', 'S', 'M5', 2, 0.6], ['dn_ph', 1, 'output', 'S', 'M5', 1, 0.62],
             ['up_fu', 1, 'input', 'S', 'M5', 1, 0.7], ['up_fo', 1, 'input', 'S', 'M5', 1, 0.71],
             ['up_alive', 1, 'input', 'S', 'M5', 1, 0.72], ['up_den', 1, 'input', 'S', 'M5', 1, 0.73],
             ['up_rdy', 1, 'input', 'S', 'M5', 1, 0.74], ['up_rjid', 8, 'input', 'S', 'M5', 2, 0.76],
             ['rst_o', 1, 'output', 'S', 'M5', 1, 0.8], ['sk', 1, 'input', 'S', 'M5', 1, 0.9],
             ['srs', 1, 'input', 'S', 'M5', 1, 0.92],
             ['c_cmd_v', 1, 'input', 'N', 'M5', 1, 0.1], ['c_cmd_d', 84, 'input', 'N', 'M5', 2, 0.2],
             ['c_done_v', 1, 'output', 'N', 'M5', 1, 0.3], ['c_done_tag', 8, 'output', 'N', 'M5', 2, 0.33],
             ['inp', 1, 'input', 'N', 'M5', 1, 0.4], ['flt', 1, 'output', 'N', 'M5', 1, 0.45],
             ['online', 1, 'output', 'N', 'M5', 1, 0.47], ['fcode', 4, 'output', 'N', 'M5', 2, 0.5],
             ['cck', 1, 'input', 'N', 'M5', 1, 0.6], ['crs', 1, 'input', 'N', 'M5', 1, 0.62]]
    return dict(master='dsfd_su_t_root', w_um=W, h_um=1814.4, domain='stream_1p2',
                note='root tile: engine adapter (cck CDC) + VM pin flops + ot_s81_su_hctl', ports=ports)


SPECS = [
    root(),
    spec('dsfd_su_t_qn', 16, 1209.6, 'QN norm tile: ot_dsrom_su_norm N 256 D 1,280 + the q gain sets'),
    spec('dsfd_su_t_kv', 16, 1209.6, 'KV norm tile: ot_dsrom_su_norm N 512 RD 64 + the kv gain sets'),
    spec('dsfd_su_t_qb', 4, 637.2, 'QB lane tile 0 of 4: ot_dsrom_su_qbank NB 8'),
    spec('dsfd_su_t_sw', 2, 637.2, 'SW lane tile 0 of 8: ot_dsrom_su_swiglu W 128 ROUTED'),
    spec('dsfd_su_t_sm', 2, 637.2, 'SM head tile 0 of 8: ot_dsrom_su_softmax H 2 LPH 16'),
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
