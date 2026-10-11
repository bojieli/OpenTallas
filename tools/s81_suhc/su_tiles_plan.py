#!/usr/bin/env python3
"""Hardened tile masters of the hierarchical SU slab dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the RTL wrappers
(rtl/dsrom_sys/s81_suhc/hier/dsfd_su_tiles.sv, production params, lane group 0 of each function) and their contract pin
plans (tools/s81_ph/s81_ph_tiles_plan.py conventions: M4 W / E, M5 N / S, x on 10.8, y on 2.16).

Every tile is 572.4 um wide (three columns across the 1,727.976-um slab) and <= ~600 um tall.  Engine tiles: the
down-spine tap enters on W (low half) + S (high half), the write slots leave on E, job announce / status / the norm
rung on N.  Pin owners: VM rows on W, spine slices on E, the control seam on N.  Control tile: controller pins N.

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
    """engine tile: the down-spine tap on W (low half) + S (high half), write slots on E, job / status / rung on N"""
    ports = [['dn_dl', HALF, 'input', 'W', 'M4', 2, 0.5], ['dn_dh', HALF, 'input', 'S', 'M5', 2, 0.45],
             ['ck', 1, 'input', 'S', 'M5', 1, 0.93], ['rst', 1, 'input', 'S', 'M5', 1, 0.95],
             ['dn_st', 1, 'input', 'N', 'M5', 1, 0.01], ['dn_kind', 4, 'input', 'N', 'M5', 2, 0.02],
             ['dn_gsel', 2, 'input', 'N', 'M5', 2, 0.03], ['dn_fp4', 1, 'input', 'N', 'M5', 1, 0.04],
             ['dn_jid', 8, 'input', 'N', 'M5', 2, 0.05], ['dn_v', S_RD, 'input', 'N', 'M5', 2, 0.07],
             ['x_pp_v_i', 1, 'input', 'N', 'M5', 1, 0.2], ['x_pp_i_i', 8, 'input', 'N', 'M5', 2, 0.22],
             ['x_pp_d_i', 32, 'input', 'N', 'M5', 2, 0.27], ['x_rb_v_o', 1, 'output', 'N', 'M5', 1, 0.32],
             ['x_rb_d_o', 32, 'output', 'N', 'M5', 2, 0.37],
             ['x_pp_v_o', 1, 'output', 'N', 'M5', 1, 0.6], ['x_pp_i_o', 8, 'output', 'N', 'M5', 2, 0.62],
             ['x_pp_d_o', 32, 'output', 'N', 'M5', 2, 0.67], ['x_rb_v_i', 1, 'input', 'N', 'M5', 1, 0.72],
             ['x_rb_d_i', 32, 'input', 'N', 'M5', 2, 0.77],
             ['o_fu', 1, 'output', 'N', 'M5', 1, 0.97], ['o_fo', 1, 'output', 'N', 'M5', 1, 0.972],
             ['o_alive', 1, 'output', 'N', 'M5', 1, 0.974], ['o_den', 1, 'output', 'N', 'M5', 1, 0.976],
             ['o_rdy', 1, 'output', 'N', 'M5', 1, 0.978], ['o_rjid', 8, 'output', 'N', 'M5', 2, 0.99],
             ['o_d', 512 * ws, 'output', 'E', 'M4', 2, 0.45], ['o_v', ws, 'output', 'E', 'M4', 2, 0.03],
             ['o_a', 14 * ws, 'output', 'E', 'M4', 2, 0.85], ['o_m', 16 * ws, 'output', 'E', 'M4', 2, 0.95]]
    return dict(master=master, w_um=W, h_um=h, domain='stream_1p2', note=note, ports=ports)


def pin_owner():
    """pin owner: its 4 VM read / 4 write slots on W (slab pins), its spine slices on E, the control seam on N"""
    K = 4
    ports = [['rs_d', 512 * K, 'input', 'W', 'M4', 2, 0.25], ['wq_d', 512 * K, 'output', 'W', 'M4', 2, 0.73],
             ['rs_v', K, 'input', 'W', 'M4', 2, 0.48], ['wq_v', K, 'output', 'W', 'M4', 2, 0.975],
             ['dn_d', 512 * K, 'output', 'E', 'M4', 2, 0.25], ['up_d', 512 * K, 'input', 'E', 'M4', 2, 0.73],
             ['dn_v', K, 'output', 'E', 'M4', 2, 0.48], ['up_v', K, 'input', 'E', 'M4', 2, 0.975],
             ['rq_v', K, 'output', 'S', 'M5', 2, 0.05], ['rq_row', 14 * K, 'output', 'S', 'M5', 2, 0.12],
             ['wq_row', 14 * K, 'output', 'S', 'M5', 2, 0.25], ['wq_mask', 16 * K, 'output', 'S', 'M5', 2, 0.38],
             ['up_a', 14 * K, 'input', 'S', 'M5', 2, 0.55], ['up_m', 16 * K, 'input', 'S', 'M5', 2, 0.68],
             ['ck', 1, 'input', 'S', 'M5', 1, 0.9], ['rst', 1, 'input', 'S', 'M5', 1, 0.92],
             ['c_rq_v', K, 'input', 'N', 'M5', 2, 0.05], ['c_rq_row', 14 * K, 'input', 'N', 'M5', 2, 0.15],
             ['c_rv', K, 'output', 'N', 'M5', 2, 0.3], ['c_rf', 30 * K, 'output', 'N', 'M5', 2, 0.5],
             ['c_uv', K, 'output', 'N', 'M5', 2, 0.75]]
    return dict(master='dsfd_su_t_pin', w_um=W, h_um=475.2, domain='stream_1p2',
                note='pin owner (one of 4): 4 VM read + 4 VM write slots, pin flops / registers, spine slices', ports=ports)


def ctl():
    """control tile: controller pins on N, pin owner seams on S, spine announce + status on E"""
    ports = [['c_cmd_v', 1, 'input', 'N', 'M5', 1, 0.1], ['c_cmd_d', 84, 'input', 'N', 'M5', 2, 0.2],
             ['c_done_v', 1, 'output', 'N', 'M5', 1, 0.32], ['c_done_tag', 8, 'output', 'N', 'M5', 2, 0.35],
             ['inp', 1, 'input', 'N', 'M5', 1, 0.4], ['flt', 1, 'output', 'N', 'M5', 1, 0.45],
             ['online', 1, 'output', 'N', 'M5', 1, 0.47], ['fcode', 4, 'output', 'N', 'M5', 2, 0.5],
             ['cck', 1, 'input', 'N', 'M5', 1, 0.6], ['crs', 1, 'input', 'N', 'M5', 1, 0.62],
             ['sk', 1, 'input', 'N', 'M5', 1, 0.8], ['srs', 1, 'input', 'N', 'M5', 1, 0.82],
             ['p_rq_v', S_RD, 'output', 'S', 'M5', 2, 0.03], ['p_rq_row', 14 * S_RD, 'output', 'S', 'M5', 2, 0.15],
             ['p_rv', S_RD, 'input', 'S', 'M5', 2, 0.3], ['p_rf', 30 * S_RD, 'input', 'S', 'M5', 2, 0.6],
             ['p_uv', S_WR, 'input', 'S', 'M5', 2, 0.9], ['rst_o', 1, 'output', 'S', 'M5', 1, 0.97],
             ['dn_st', 1, 'output', 'E', 'M4', 1, 0.1], ['dn_kind', 4, 'output', 'E', 'M4', 2, 0.15],
             ['dn_gsel', 2, 'output', 'E', 'M4', 2, 0.2], ['dn_fp4', 1, 'output', 'E', 'M4', 1, 0.25],
             ['dn_jid', 8, 'output', 'E', 'M4', 2, 0.3],
             ['up_fu', 1, 'input', 'E', 'M4', 1, 0.6], ['up_fo', 1, 'input', 'E', 'M4', 1, 0.62],
             ['up_alive', 1, 'input', 'E', 'M4', 1, 0.64], ['up_den', 1, 'input', 'E', 'M4', 1, 0.66],
             ['up_rdy', 1, 'input', 'E', 'M4', 1, 0.68], ['up_rjid', 8, 'input', 'E', 'M4', 2, 0.72]]
    return dict(master='dsfd_su_t_ctl', w_um=W, h_um=216.0, domain='stream_1p2',
                note='control tile: engine adapter (cck CDC) + ot_s81_su_hctl', ports=ports)


SPECS = [
    ctl(), pin_owner(),
    spec('dsfd_su_t_qn0', 8, 604.8, 'QN norm head tile: lanes 0-127, the rung add, vector levels, rstd tail'),
    spec('dsfd_su_t_qn1', 8, 604.8, 'QN norm lane tile: lanes 128-255'),
    spec('dsfd_su_t_kv0', 8, 604.8, 'KV norm head tile: lanes 0-255, the rung add, rstd tail'),
    spec('dsfd_su_t_kv1', 8, 604.8, 'KV norm lane tile: lanes 256-511 with the RoPE tail'),
    spec('dsfd_su_t_qb', 4, 637.2, 'QB lane tile 0 of 4: ot_dsrom_su_qbank NB 8'),
    spec('dsfd_su_t_sw', 2, 637.2, 'SW lane tile 0 of 8: ot_dsrom_su_swiglu W 128 ROUTED'),
    spec('dsfd_su_t_sm', 2, 637.2, 'SM head tile 0 of 8: ot_dsrom_su_softmax H 2 LPH 16'),
]


def main():
    summ = {}
    for sp in SPECS:
        ports = TP.plan(sp)
        for pp in ports.values():                     # a 1-bit port is a scalar in the RTL: 'ck', not 'ck[0]'
            if pp['bits'] == 1:
                pp['pins'][0][0] = pp['pins'][0][0].split('[')[0]
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
