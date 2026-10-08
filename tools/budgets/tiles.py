#!/usr/bin/env python3
"""S81-PH placeholder-slab tiles -> tile interface table for budget_sheet.py --tiles (CLAUDE BUDGETS, 2026-10-06).

The S81 die places the spine / band slabs (dsfd_bk_selector, dsfd_bk_collector, dsfd_sp_capture, dsfd_sp_collective,
dsfd_ctrl, dsfd_svc, dsfd_sp_vm, dsfd_sp_gather) as single masters; the S81-PH redesign pass hardens each slab as
tiles (<= ~1 mm) joined by registered pin-to-pin hops.  Their geometry is in the S81-PH compositions (branch
claude/s81-placeholders-20261006): results/rtl/s81_ph_20261006/<kind>/tiles.json and physical/s81_ph_views/<kind>/
composition.json, tile outlines / pin directions in physical/s81_ph_views/ports/contract/<tile>/ports.json.

Edge lengths: intra-slab hops from the composition (a station chain of length L with S stations is S+1 segments of
L/(S+1)); abutting faces 0.192-6.544 um; die-facing tile ports INHERIT the worst die interface of the slab master
(the slab pin is the tile pin), resolved by budget_sheet.py from the die sheets.

  tiles.py --ph-root /path/to/s81-ph-checkout --out tiles.json
"""
import argparse
import json
from pathlib import Path

ABUT = 0.192


def E(ports, L=None, what='', peer='', cls='intra', inherit=None, basis='composition'):
    e = dict(ports=ports, what=what, peer=peer, skew_class=cls, basis=basis)
    if inherit:
        e['inherit'] = inherit
        e['length_um'] = 0.0
    else:
        e['length_um'] = round(L, 3)
    return e


def io(names, d):
    return [[n, d] for n in names]


def build(ph):
    rd = lambda p: json.loads((ph / p).read_text())  # noqa: E731
    sel = rd('results/rtl/s81_ph_20261006/selector/tiles.json')
    col = rd('results/rtl/s81_ph_20261006/collector/tiles.json')
    cap = rd('results/rtl/s81_ph_20261006/capture/tiles.json')
    svc = rd('physical/s81_ph_views/svc/composition.json')
    h0 = max((h for h in sel['hops'] if h.get('stations')), key=lambda h: h['length_um'])
    lane_seg = max(h['length_um'] / (h['stations'] + 1) for h in sel['hops'] if h.get('stations'))
    abut_sel = next(h['length_um'] for h in sel['hops'] if h.get('stations') == 0)
    colh = next(h for h in col['hops'] if h.get('stations'))
    col_seg = colh['length_um_max'] / (colh['stations'] + 1)
    caph = next(h for h in cap['hops'] if 'length_um_max' in h)
    stn_max = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for c in svc['station_chains'] for a, b in zip(c['xy'], c['xy'][1:]))
    T = {}

    def tile(m, slab, n, dom='stream_1p2', clock_ports=('ck',), edges=()):
        size = rd(f'physical/s81_ph_views/ports/contract/{m}/ports.json')
        T[m] = dict(slab=slab, instances=n, size_um=[size['w_um'], size['h_um']], domain=dom, clock_ports=list(clock_ports),
                    edges=list(edges))
    tile('dsfd_selt_q', 'dsfd_bk_selector', 4, edges=[
        E(io(['lane'], 'in'), lane_seg, f'die lane -> quarter: {h0["length_um"]} um, {h0["stations"]} common-clock stations', 'die station'),
        E(io(['t_s', 't_o'], 'out') + io(['f_c', 'f_cr'], 'in'), abut_sel, 'quarter <-> control (near-abutted)', 'dsfd_selt_c')])
    tile('dsfd_selt_c', 'dsfd_bk_selector', 1, edges=[
        E(io(['f_s', 'f_o'], 'in') + io(['t_c', 't_cr'], 'out'), abut_sel, 'control <-> quarters (near-abutted)', 'dsfd_selt_q'),
        E(io(['vd', 'vf'], 'out'), inherit=['dsfd_bk_selector', ['vd', 'vf']], what='control -> VM station chain (slab vd/vf)')])
    tile('dsfd_colt_lane', 'dsfd_bk_collector', 4, edges=[
        E(io(['c_in'], 'in'), inherit=['dsfd_bk_collector', None], what='die lane -> lane tile (slab die port)'),
        E(io(['t_w', 't_f'], 'out') + io(['f_cr'], 'in'), col_seg,
          f'lane <-> merger: {colh["length_um_max"]} um, {colh["stations"]} common-clock stations each way', 'die station')])
    tile('dsfd_colt_mrg', 'dsfd_bk_collector', 1, edges=[
        E(io(['f_w', 'f_f'], 'in') + io(['t_cr'], 'out'), col_seg, 'merger <-> lane stations', 'die station'),
        E(io(['vd', 'vf'], 'out'), inherit=['dsfd_bk_collector', ['vd', 'vf']], what='merger -> VM station chain')])
    for m, n in (('dsfd_capt_grp', 8), ('dsfd_capt_ctl', 1)):
        k = ['f_k', 't_sb'] if m == 'dsfd_capt_grp' else ['t_k', 'f_sb']
        dirs = (['in', 'out'] if m == 'dsfd_capt_grp' else ['out', 'in'])
        tile(m, 'dsfd_sp_capture', n, clock_ports=('ck', 'ckv'), edges=[
            E([[k[0], dirs[0]], [k[1], dirs[1]]], caph['length_um_max'] / 2,
              'ctl <-> group tiles in the S channel: one common-clock station each way (s81-die-timing 2026-10-08, KST 1)', 'capture station'),
            E(io(['f_row' if m == 'dsfd_capt_grp' else 'f_ctl'], 'in'), 21.6, 'gather t_capture -> tile through the 21.6-um channel', 'dsfd_sp_gather'),
            E(io(['t_vm' if m == 'dsfd_capt_grp' else 't_st'], 'out'), ABUT, 'tile -> VM (serial clock ckv, abutted N face)', 'dsfd_sp_vm')])
    for m in ('dsfd_coll_lane_w', 'dsfd_coll_lane_e'):
        tile(m, 'dsfd_sp_collective', 4, edges=[
            E(io(['lo_v', 'lo_d', 'li_r'], 'in') + io(['lo_r', 'li_v', 'li_d', 'flt'], 'out'), ABUT, 'lane <-> core skid (abutted, 0.192 gap)', 'dsfd_coll_core'),
            E(io(['rx'], 'in') + io(['tx', 'tf'], 'out'), inherit=['dsfd_sp_collective', None], what='lane <-> die link chain (slab rX/tdX/tfX)')])
    tile('dsfd_coll_core', 'dsfd_sp_collective', 1, edges=[
        E(io(['lo_r', 'li_v', 'li_d', 'flt'], 'in') + io(['lo_v', 'lo_d', 'li_r'], 'out'), ABUT, 'core <-> lane skids (abutted)', 'dsfd_coll_lane_*'),
        E(io(['f_vm', 'ts'], 'in') + io(['t_vm'], 'out'), inherit=['dsfd_sp_collective', None], what='core <-> VM (slab S face)')])
    tile('dsfd_coll_ck', 'dsfd_sp_collective', 1, clock_ports=(), edges=[])      # PLL + reset sequencer: clock sources
    tile('dsfd_ctrl_pc', 'dsfd_ctrl', 32, clock_ports=('cks', 'ckh'), edges=[
        E(io(['k_v', 'k_addr', 'k_len', 'k_tag', 'k_we', 'k_wdata', 'k_wstrb', 'kr_rdy'], 'out') +
          io(['k_rdy', 'k_wr_done', 'kr_v', 'kr_tag', 'kr_beat', 'kr_data'], 'in'), ABUT,
          'PC tile <-> HBM3E PHY pseudo-channel pins (abutted S face, ckh domain)', 'ot_hbm3e_phy'),
        E(io(['rq'], 'out') + io(['rk', 'wd', 'r_data', 'r_tag', 'r_beat', 'rv'], 'in'), ABUT,
          'PC tile <-> svc PC tile (abutted N face)', 'dsfd_svc_pc'),
        E(io(['co_w', 'co_e'], 'out') + io(['ci_w', 'ci_e'], 'in'), 265.584 - 121.068, 'status chain to the next PC tile (265.584 pitch)', 'dsfd_ctrl_pc')])
    tile('dsfd_ctrl_ctr', 'dsfd_ctrl', 1, clock_ports=('cks', 'ckh'), edges=[
        E(io(['co_w', 'co_e'], 'in'), 4155.486 - (3983.76 + 121.068), 'status from PC 15 / 16', 'dsfd_ctrl_pc'),
        E(io(['st'], 'out'), inherit=['dsfd_ctrl', None], what='status -> die (slab st)')])
    tile('dsfd_svc_pc', 'dsfd_svc', 32, edges=[
        E(io(['rq', 'qrk', 'qwd', 'qrv', 'qr_data', 'qr_tag', 'qr_beat'], 'out') + io(['qrq', 'rk', 'wd', 'rv', 'r_data', 'r_tag', 'r_beat'], 'in'),
          ABUT, 'svc PC tile <-> ctrl PC tile (S) / quadrant (N), abutted', 'dsfd_ctrl_pc / quadrant')])
    tile('dsfd_svc_stn', 'dsfd_svc', sum(c['stations'] for c in svc['station_chains']), edges=[
        E(io(['q_e', 'od_wv', 'od_wd', 'od_er', 'a0_wv', 'a0_wd', 'a0_er'], 'in') +
          io(['q_w', 'od_ev', 'od_ed', 'od_wr', 'a0_ev', 'a0_ed', 'a0_wr'], 'out'), stn_max,
          f'quadrant <-> IO hub station chain (max span {stn_max:.1f} um)', 'dsfd_svc_stn / dsfd_svc_io')])
    tile('dsfd_svc_io', 'dsfd_svc', 1, edges=[
        E(io(['q_q', 'od_r', 'a0_r', 'a1_r', 'x_r'], 'out') + io(['od_d', 'od_v', 'a0_d', 'a0_v', 'a1_d', 'a1_v', 'x_d', 'x_v'], 'in'),
          stn_max, 'IO hub <-> first station / quadrant 3', 'dsfd_svc_stn'),
        E(io(['od', 'of', 'xd', 'xf', 'ad', 'af', 'fault'], 'out') + io(['q'], 'in'), inherit=['dsfd_svc', None],
          what='IO hub <-> die (slab N-E pin group)')])
    tile('dsfd_vm_bg', 'dsfd_sp_vm', 4, dom='serial_0p9', edges=[
        E(io(['i_v', 'i_we', 'i_row', 'i_mask', 'i_d', 'r_v', 'r_d', 'r_f', 'r_o'], 'in') +
          io(['f_v', 'f_we', 'f_row', 'f_mask', 'f_d', 'o_v', 'o_d', 'o_f', 'o_o'], 'out'), ABUT,
          'bank-group chain by abutment (S face of t on N face of t+1; ends at the VM request / read ports)', 'dsfd_vm_bg')])
    tile('ot_s81ph_root_tile', 'dsfd_sp_gather', 128, edges=[
        E(io(['ci', 'sel', 'fi'], 'in') + io(['co', 'rso', 'fo'], 'out'), 125.28 - 124.2, 'root chain, abutted rows (125.28 pitch)', 'ot_s81ph_root_tile'),
        E(io(['li_w', 'lt_wi', 'li_e', 'lt_ei'], 'in') + io(['lt_wo', 'lt_eo'], 'out'), 237.6 - 237.168,
          'lane taps to the neighbour columns (237.6 pitch, abutted)', 'ot_s81ph_root_tile / trunk')])
    tile('ot_s81ph_root_blk', 'dsfd_sp_gather', 128, edges=[
        E(io(['i'], 'in') + io(['o', 'f'], 'out'), ABUT, 'root sub-block inside its root tile (abutted)', 'ot_s81ph_root_tile')])
    return T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ph-root', required=True, type=Path)
    ap.add_argument('--commit', default='')
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    T = build(a.ph_root)
    a.out.write_text(json.dumps(dict(schema='opentallas.budgets.tiles.v1', source_commit=a.commit, tiles=T), indent=1) + '\n')
    print(len(T), sorted(T))


if __name__ == '__main__':
    main()
