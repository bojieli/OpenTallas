#!/usr/bin/env python3
"""MU-S81 (10-18): chain / array plan for the 520-die multi-user S81 (owner MU.DECIDE option A).

Places copy B of the 8 duplicated index-attention stage groups and lists every extra link they need, then checks the
two properties the static calendar (tools/s81_dv/dv_mu_calendar.py) relies on:
  (a) copy B is latency-identical to copy A on every crossing (same switched channel class: every peer is ONE crossing of
      the one-tier multi-plane switch, fixed delay 377.6 ns budget = PHY/FEC 100 + switch 250 + cable 27.6;
      lanes/TOKEN-XDIE-S81.md s2), so a copy-B user's windows are the copy-A windows (shift lemma unchanged);
  (b) no added link is a new bottleneck: per slot, every link carries at most one h message (652 cycles) per user.
Writes results/arch/mu_s81_1018/chain_plan.json.  Grade: modelled (plan + arithmetic); the RTL of the lep A/B select
is lane MU-S81/LINK, the multi-user bench MU.TOK.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_mu_calendar as M  # noqa: E402

H_BYTES = 40976          # stage h message a rank die (ROM-MULTIUSER item 3)
RANKS = 4                # TP4: the stage hop runs rank r -> rank r
# S81-LINK5 (owner 10-21 06:00): the stale p4l count (6 SerDes + 2 UCIe, in-package UCIe pair) is replaced by the
# real stage die: 10 SerDes = 5 lane-pair endpoints (8 copy-A SerDes on s_0S / s_7S / s_7N / s_0N pair A + 2 pair-B
# SerDes on s_0N), 0 UCIe (every die link leaves the package through the switch), + 2 reserved SerDes slots (E column B
# link_1_4/1_5 = the copy-A/B pair, blockage).  Circuit table: dv_mu_calendar.CIRCUITS.
LANES_PER_DIE = dict(serdes=M.LANE_COUNT['serdes'], ucie=M.LANE_COUNT['ucie'], circuits=M.LANE_COUNT['circuits'],
                     reserved_serdes_slots=M.LANE_COUNT['reserved_serdes_slots'])
CABLE_NS_PER_M, CABLE_BUDGET_NS = 4.6, 27.6               # twinax (rack.json link_basis), switch budget cable share
DIES_PER_TRAY = 8        # 1 OU tray = 4 two-die packages (dsrom_s81_rack_20261006 packing rule)


def plan():
    m = M.load_model()
    st = M.stage_windows(m)
    d = M.design(m)
    ar = json.loads((M.OUT / 'calendar_ar.json').read_text())
    ids = [g['id'] for g in st]
    per_copy = round(m.DIES_PER_LAYER)
    groups, links, die_id = [], [], m.S81['dies']
    for gid in M.DUP:
        i = ids.index(gid)
        up, dn = ids[i - 1], ids[i + 1]
        b_dies = list(range(die_id, die_id + per_copy))
        die_id += per_copy
        g = st[i]
        groups.append(dict(group=gid, label=g['label'], owns_layer=M.DUP_LAYER[gid], copy_b_dies=b_dies,
                           copy_b_trays=math.ceil(per_copy / DIES_PER_TRAY), copy_b_stacks=per_copy,
                           placement=f'copy B trays in the rack row of copy A ({gid}), same switch plane set; '
                                     'cable <= the 27.6 ns budget share (~6.0 m twinax) like every other crossing',
                           rom='copy B dies carry copy A\'s ROM content: the same die masks fabricated twice (no new '
                               'mask set); its HBM holds only copy-B users\' KV / index state',
                           upstream=up, downstream=dn,
                           occ_single=g['occ'], occ_per_copy_users=ar['tables'][gid]['users_per_copy']))
        for kind, src, dst in (('stage hop in (h message)', up, f'{gid}.B'), ('stage hop out (h message)', f'{gid}.B', dn)):
            links.append(dict(group=gid, kind=kind, src=src, dst=dst, circuits=RANKS, bytes_per_user_pos=H_BYTES * RANKS,
                              cycles_per_user_pos=M.H_MSG, slot=ar['slot'],
                              occupancy=round(M.H_MSG / ar['slot'], 4),
                              form=('copy A: the stage NEXT circuit s_0N pair A -> s_0N pair B (S81-LINK5); copy B: '
                                    'the reserved copy-A/B pair (link_1_4/1_5) = a 6th static circuit on the 4 '
                                    'upstream / 4 downstream rank dies (a destination field is NOT possible: the frozen '
                                    'lane tile link layer is end-to-end per peer pair; user 0 forced to copy A)')))
        links.append(dict(group=gid, kind='copy B internal (TP4 full mesh + intra-group stage hops)', src=f'{gid}.B',
                          dst=f'{gid}.B', circuit_ends=per_copy * LANES_PER_DIE['circuits'],
                          form='identical to copy A on the new dies\' own lanes (5 lane-pair endpoints a die: 3 TP4 '
                               'full-mesh ends + stage NEXT + stage PREV; 6 TP circuits a TP4 group = 4 S-ring + 2 '
                               'EN<->EN)'))
    new_dies = die_id - m.S81['dies']
    ok_occ = all(l.get('occupancy', 0) <= 1 for l in links)
    rec = dict(
        schema='opentallas.s81_dv.mu_chain_plan.v1', lane='MU-S81', grade='modelled',
        array=dict(dies=m.S81['dies'] + new_dies, stacks=m.S81['stacks'] + new_dies, added_dies=new_dies,
                   added_stacks=new_dies, added_trays=sum(g['copy_b_trays'] for g in groups),
                   die_mm2=m.S81['die_mm2'], total_mm2=d['total_mm2'],
                   switch_ports_added=dict(serdes=new_dies * LANES_PER_DIE['serdes'],
                                           note='0 UCIe: every die link leaves the package through the switch'),
                   extra_circuits_on_existing_dies=dict(circuits=2 * RANKS * len(M.DUP),
                                                        die_variant=('the 4 rank dies of each pre-group and post-group '
                                                                     'stage populate the 2 reserved SerDes slots '
                                                                     '(link_1_4/1_5, copy-A/B pair) = a 6th lane pair: '
                                                                     f'{2 * RANKS * len(M.DUP)} dies, a variant of the '
                                                                     'LINK5 stage die'),
                                                        note='+1 tx lane pair on each upstream rank die, +1 rx lane pair on '
                                                             'each downstream rank die (the s_0N pair B is the stage '
                                                             'PREV circuit and cannot be the copy-B circuit)'),
                   lanes_per_die=LANES_PER_DIE,
                   circuits_per_die=M.CIRCUITS,
                   circuits_array=dict(tp4_full_mesh_per_group=6, stage_per_boundary=RANKS,
                                       note='every circuit is one switch crossing; per die 5 = 3 TP endpoints (6 TP circuits '
                                            'x 2 ends / 4 dies) + stage NEXT + stage PREV')),
        reuse=('per the token DAG of record (results/arch/token_path_20261009/ds_rom.json) every layer writes and reads '
               'its own rows on its own stage (own_row_write / window_load / pv nodes); what later layers reuse from '
               'the owner layers 2/8/14/20 is the top-k selection, which rides the stage h message with the user tag. '
               'So copy B needs NO reuse link; the owner copy is addressed by user only through the h message order. '
               'Lane MU-S81/SVC confirms on the RTL (svc_bases.json).'),
        stage_hop=dict(circuit='s_0N pair A (TX, every window ab 0) -> next stage rank r s_0N pair B (RX -> ri)',
                       crossings=1, beats=321, E_cycles=1125,
                       E_basis='record token_compose stage_hop: 538 measured + 453 modelled PHY/switch + 134 priced '
                               'on-die legs (results/rtl/xdie_s81_1019/record.json)',
                       was='folded onto the ES TP circuit (tb_xdie_s81 d -> d+1 inside the group): no real circuit '
                           'to the next stage existed on the 4-endpoint die',
                       per_token_delta_cycles=0,
                       per_token_delta_why='the composition of record already prices every hop as ONE crossing of '
                                           '321 beats on one port; LINK5 makes that crossing real at the same cost. '
                                           'MU calendar: the fold had 0 collisions at stage granularity (min AR '
                                           'margin slot - (span + h) = 690.7 cycles, S005), the LINK5 calendar has '
                                           '0 collisions with the s_0N TX / RX resources'),
        latency=dict(copy_a='unchanged (the latency user is always on copy A: same dies, same circuits)',
                     copy_b_delta_cycles=0,
                     why='every crossing is the same fixed-delay switched channel (377.6 ns budget), so copy B\'s hop '
                         'latency equals copy A\'s; a copy-B user\'s windows are the copy-A windows shifted by its slot'),
        checks=dict(link_occupancy_le_slot='PASS' if ok_occ else 'FAIL',
                    cable_budget_m=round(CABLE_BUDGET_NS / CABLE_NS_PER_M, 1)),
        groups=groups, links=links,
        calendar=dict(ar_users=ar['users'], ar_agg_model=ar['aggregate_tok_s'], record='calendar_ar.json'))
    return rec


def main():
    rec = plan()
    f = M.OUT / 'chain_plan.json'
    txt = json.dumps(rec, indent=1) + '\n'
    if '--check' in sys.argv:
        same = f.exists() and f.read_text() == txt
        print('chain_plan', 'SAME' if same else 'DIFFERS')
        return 0 if same else 1
    f.write_text(txt)
    a = rec['array']
    print(f"chain: {a['dies']} dies / {a['stacks']} stacks (+{a['added_dies']}, {a['added_trays']} trays), "
          f"{len(rec['links'])} link sets, occupancy check {rec['checks']['link_occupancy_le_slot']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
