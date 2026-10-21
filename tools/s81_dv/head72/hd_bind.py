#!/usr/bin/env python3
"""S81 head die H1 bind table (S81-HEAD / HD-CHAIN, 10-21) in the dv_bind / dv_diecase --bind real format
(schema opentallas.s81_dv.bind_table.v2), built from the routed H1 plan and the G7 base table.

  python3 hd_bind.py --plan PLAN_ROUTED --base BASE_TABLE --ports PORTS_JSON --land-plan LAND --out TABLE

What it takes from the G7 base table (results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json, the table frame_bind turns into
the G7 table): every die-infrastructure key UNCHANGED -- relay_views / relay_prefix (closed half-cycle dsfd_dvrlyh_*),
land_views + landing_reset_stages (closed dsfd_dvland_* views), reset_master (dsfd_rly_1_WN), rtl_refs / prefer / rtl_files /
defines / allow_model, and the ot_pdie_serdes master row (ot_pdie_serdes_col, the same stand-in G7 binds).  Frame keys
(frame_wrapper / frame_members / frame_lk / fault masters) are dropped: the head die has no frames.

Head masters (RTL of record: rtl/dsrom_sys/s81_head on this branch; ports from results/arch/s81_head_1021/ports.json):
  ot_s81hd_tile  (253)  i / o bus B 565; straps row0[16:0] / ten (rank 0 die variant, see strap_values_by_rank)
  ot_s81hd_spo / spr    i/o/ow/oe, i/iw/ie/o bus B 565
  ot_s81hd_ctl          sn/ss bus B, 13 lanes x (3 x 276 out, 3 x 276 in), lep 5 x 276 each way
  ot_s81hd_lep          core 5 x 276 each way, tx0..3 / rx0..3 on 2 x 276 lanes to lk_WN0..3; strap ch_b 1
  ot_s81hd_lane  (13)   core 3 x 276 each way, tx 512 / rx 514 on 562 to its SerDes; strap chb 1
  ot_pdie_serdes (13) / ot_pdie_serdes_l276 (4, the lep's lk_WN*: 2 x 276 lanes): module ot_pdie_serdes_col (G7 row)
Bus B rides 682-b lanes where a station / region crossing exists: 'lanes' split rules, so the 117 spare top bits are
declared lane-quantisation pads at station 0 (dv_bind), never 'plan bits dropped'.
No CLOSED view is bound for any head master (none exists): all are declared source-view / UNBOUND (view null, view_note).
"""
import argparse
import copy
import json
import re
from pathlib import Path

KEEP = ('rtl_refs', 'prefer', 'allow_model', 'relay_views', 'reset_master', 'rtl_files', 'child_views', 'relay_views_retired',
        'relay_prefix', 'defines', 'rtl_files_note_die8', 'clock_domains', 'spare_out_rules', 'land_views', 'landing_reset_stages')
BUSB = 565
LANE = 276
LANE_K = {'mesh': ('m', 6), 'host': ('h', 2), 'draft': ('d', 5)}   # ctl port letter, lane count


def chunks(port, lo, n, w=LANE):
    """n bits of port from lo, packed into consecutive w-bit lanes -> [[(port, rtl lo, lane lo, bits)], ...]"""
    out, pos = [], 0
    while pos < n:
        b = min(w, n - pos)
        out.append([[port, lo + pos, 0, b]])
        pos += b
    return out


def pack(fields, w=LANE):
    """fields [(port, rtl lo, bits)] packed in order over w-bit lanes (a field may straddle lanes)"""
    lanes, cur, used = [], [], 0
    for port, lo, n in fields:
        while n:
            b = min(n, w - used)
            cur.append([port, lo, used, b])
            lo += b; n -= b; used += b
            if used == w:
                lanes.append(cur); cur, used = [], 0
    if cur:
        lanes.append(cur)
    return lanes


def L(lanes, land=False):
    r = dict(lanes=[dict(split=s) for s in lanes])
    if land:
        r['land'] = True
    return r


def busb(port, land=False):
    return L([[[port, 0, 0, BUSB]]], land)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True); ap.add_argument('--base', required=True); ap.add_argument('--ports', required=True)
    ap.add_argument('--land-plan', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--rank', type=int, default=0, help='TP4 rank die variant bound (straps row0 / ten)')
    a = ap.parse_args()
    plan = json.load(open(a.plan)); base = json.load(open(a.base)); ports = json.load(open(a.ports))
    T = {k: copy.deepcopy(base[k]) for k in KEEP if k in base}
    T['schema'] = base['schema']
    T['plan'] = f'S81 HEAD H1 (results/arch/s81_head_1021/h1, routed {Path(a.plan).name})'
    T['land_plan'] = a.land_plan
    T['note'] = ('S81-HEAD HD-CHAIN 10-21: head die H1 bind table (tools/s81_dv/head72/hd_bind.py) = G7 base die-infrastructure keys '
                 '(relays, landings, reset station, RTL refs, ot_pdie_serdes row) + the head masters from ports.json; no frames.')
    pw = {m: {p['name']: p['width'] for p in v['ports']} for m, v in ports['masters'].items()}
    rw = T['rtl_widths'] = {
        'ot_s81hd_tile': dict(ck=1, rst_n=1, i=BUSB, o=BUSB, row0=17, ten=1),
        'ot_s81hd_spo': dict(ck=1, rst_n=1, i=BUSB, o=BUSB, ow=BUSB, oe=BUSB),
        'ot_s81hd_spr': dict(ck=1, rst_n=1, i=BUSB, iw=BUSB, ie=BUSB, o=BUSB),
        'ot_s81hd_ctl': pw['ot_s81hd_ctl'], 'ot_s81hd_lep': pw['ot_s81hd_lep'], 'ot_s81hd_lane': pw['ot_s81hd_lane'],
        'ot_pdie_serdes_col': base['rtl_widths'].get('ot_pdie_serdes_col') or base['rtl_widths']['ot_pdie_serdes']}
    assert pw['ot_s81hd_ctl']['mtx_d'] == 6 * 553 and pw['ot_s81hd_ctl']['htx_d'] == 2 * 553 and pw['ot_s81hd_ctl']['dtx_d'] == 5 * 553
    blocks = plan['blocks']
    facts = plan['facts']
    M = {}
    src_note = 'RTL rtl/dsrom_sys/s81_head (claude/s81-head-h1-1021); no CLOSED view: source-view stand-in in the die case (UNBOUND)'
    # ---------------------------------------------------------------- tile / spine
    ts = facts['tile_straps']['per_instance']
    M['ot_s81hd_tile'] = dict(
        module='ot_s81hd_tile', view=None, view_note=f'{src_note}; kits s81hd_tile_m (648 x 648, = plan) / _f gates pending (HD-TILE)',
        clk='ck', rst=['rst_n', 'low'], params=dict(IOREG=1), instance_param='INSTANCE',
        ports={'i.i': busb('i', land=True), 'o.o': busb('o')},
        straps=['row0', 'ten'],
        strap_values=dict(row0={n: f"17'd{v['row0_by_rank'][a.rank]}" for n, v in ts.items()},
                          ten={n: f"1'b{v['ten_by_rank'][a.rank]}" for n, v in ts.items()}),
        strap_values_by_rank={n: dict(row0=v['row0_by_rank'], ten=v['ten_by_rank']) for n, v in ts.items()},
        strap_note=f'one die netlist per TP4 rank (ROM code per rank, spec s1): this table binds rank {a.rank}; ranks 1..3 differ only in '
                   'these strap constants (row0 = rank row base + 128 x bundle; ten = 0 for bundle 252 on ranks 2/3)',
        port_note='bus B 565 (spec s2); 682-b lane where a station / region crossing exists (117 spare top bits, declared pads)')
    M['ot_s81hd_spo'] = dict(module='ot_s81hd_spo', view=None, view_note=f'{src_note}; kits s81hd_spo_m (216 x 648) / _f',
                             clk='ck', rst=['rst_n', 'low'],
                             ports={'i.i': busb('i', land=True), 'o.o': busb('o'), 'ow.o': busb('ow'), 'oe.o': busb('oe')})
    M['ot_s81hd_spr'] = dict(module='ot_s81hd_spr', view=None, view_note=f'{src_note}; kits s81hd_spr_m (216 x 648) / _f',
                             clk='ck', rst=['rst_n', 'low'],
                             ports={'i.i': busb('i', land=True), 'iw.i': busb('iw', land=True), 'ie.i': busb('ie', land=True),
                                    'o.o': busb('o')})
    # ---------------------------------------------------------------- ctl
    cp = {'sn_o.o': busb('sn_o'), 'ss_o.o': busb('ss_o'), 'sn_i.i': busb('sn_i', land=True), 'ss_i.i': busb('ss_i', land=True)}
    lanes_seen = []
    for b in blocks:
        if b['master'] != 'ot_s81hd_lane':
            continue
        nm = b['name']
        mm = re.fullmatch(r'ln_(mesh|host|draft)(\d+)', nm)
        role, k = mm.group(1), int(mm.group(2))
        c, n = LANE_K[role]
        assert k < n, nm
        lanes_seen.append((nm, c, k))
        cp[f'{nm}_t.o'] = L(pack([(f'{c}tx_v', k, 1), (f'{c}tx_d', 553 * k, 553)]))
        cp[f'{nm}_r.i'] = L(pack([(f'{c}rx_v', k, 1), (f'{c}rx_d', 553 * k, 553), (f'{c}flt', 4 * k, 4)]), land=True)
    assert sorted((c, k) for _, c, k in lanes_seen) == sorted((LANE_K[r][0], k) for r in LANE_K for k in range(LANE_K[r][1]))
    cp['lep_t.o'] = L(pack([('ro', 0, 1104), ('mu_c', 0, 34), ('mu_rc', 0, 11), ('ctl_f', 0, 1)]))
    cp['lep_r.i'] = L(pack([('ri', 0, 1104), ('mu_rt', 0, 32), ('lw', 0, 11), ('lep_f', 0, 1)]), land=True)
    M['ot_s81hd_ctl'] = dict(module='ot_s81hd_ctl', view=None,
                             view_note=f'{src_note}; hard children dsfd_mtp_seq (CLOSED 10-08 kit) + 4 x ot_sram_1r1w_64x512_m1_r2c2; '
                                       'ctl kit MAIN/FALLBACK pending (HD-CTL)',
                             clk='ck', rst=['rst_n', 'low'], ports=cp,
                             port_note='lane k core: {m|h|d}tx_v[k] + {m|h|d}tx_d[553k +: 553] on 3 x 276 (bits 0..553), return '
                                       '{m|h|d}rx_v[k] + rx_d[553k +: 553] + flt[4k +: 4] on 3 x 276; lep: ro 1104 + mu_c + mu_rc + ctl_f '
                                       'out / ri + mu_rt + lw + lep_f in on 5 x 276 (276-b lanes: the long ctl links need the D 8 '
                                       'dsfd_dvland_276l landing, the only long closed landing)')
    # ---------------------------------------------------------------- lep / lane
    lp = {'core_i.i': L(pack([('ro', 0, 1104), ('mu_c', 0, 34), ('mu_rc', 0, 11), ('sl_f', 0, 1)]), land=True),
          'core_o.o': L(pack([('ri', 0, 1104), ('mu_rt', 0, 32), ('lw', 0, 11), ('fault', 0, 1)]))}
    for k in range(4):
        lp[f'tx{k}.o'] = L(chunks(f'tx{k}', 0, 512))
        lp[f'rx{k}.i'] = L(chunks(f'rx{k}', 0, 514), land=True)
    M['ot_s81hd_lep'] = dict(module='ot_s81hd_lep', view=None,
                             view_note=f'{src_note}; hard children 4 x dsfd_coll_lane_w_safe8_ntf, ot_s81sl_lep_mu_ab #(RX_SRAM 1, '
                                       'IN_PIPE 1, NATIVE32 1) (kit s81sl_lepmu gates live), dsdv_mu_land SRAM 1',
                             clk='ck', rst=['rst_n', 'low'], straps=['ch_b'], strap_values=dict(ch_b="1'b1"), ports=lp,
                             port_note='tx<k>/rx<k> <-> lk_WN<k> (pair A 0/1, pair B 2/3) on 2 x 276 lanes each; ch_b 1 = board lane')
    M['ot_s81hd_lane'] = dict(module='ot_s81hd_lane', view=None, view_note=f'{src_note}; hard child dsfd_coll_lane_w_safe8_ntf',
                              clk='ck', rst=['rst_n', 'low'], straps=['chb'], strap_values=dict(chb="1'b1"),
                              ports={'core_i.i': L(pack([('tx_v', 0, 1), ('tx_d', 0, 553)]), land=True),
                                     'core_o.o': L(pack([('rx_v', 0, 1), ('rx_d', 0, 553), ('flt', 0, 4)])),
                                     'tx.o': dict(port='tx', lane=512),
                                     'rx.i': L([[['rx', 0, 0, 514]]], land=True)},
                              port_note='rx 514 = {SerDes st, rx} on a 562 lane (landed); chb 1 = board lane (CH_BOARD)')
    # ---------------------------------------------------------------- SerDes (G7 row; lep SerDes on 2 x 276)
    sd = copy.deepcopy(base['masters']['ot_pdie_serdes'])
    M['ot_pdie_serdes'] = sd
    sl = copy.deepcopy(sd)
    sl['ports'] = {'tx.i': L(chunks('tx', 0, 512), land=True),
                   'rx.o': L([[['rx', 0, 0, 276]], [['rx', 276, 0, 236], ['st', 0, 236, 2]]])}
    sl['port_note'] = 'G7 ot_pdie_serdes row, lep SerDes lk_WN0..3: tx 512 / {st, rx} 514 on 2 x 276-b lanes (long lep links)'
    M['ot_pdie_serdes_l276'] = sl
    T['masters'] = M
    T['instance_orientations'] = dict(facts['instance_orientations'])
    T['unbound'] = {k: v['view_note'] for k, v in M.items()}
    used = {b['master'] for b in blocks}
    miss = used - set(M)
    assert not miss, miss
    Path(a.out).write_text(json.dumps(T, indent=1))
    print('HD_BIND_TABLE', a.out, 'masters', sorted(M), 'orientations', len(T['instance_orientations']), 'rank', a.rank)


if __name__ == '__main__':
    main()
