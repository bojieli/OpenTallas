"""d44v reform_census.json: per RE-FORM core the plan-time numbers + owner of its RE-FORM (DIE-HBM-61 ruling 11-03)."""
import json, sys
C = json.load(open(sys.argv[1])); E = json.load(open(sys.argv[2])); out = sys.argv[3]
dec = {d['module']: d for d in E['decisions']}
PIN = {'ot_hfd_coll_q3_vm_core', 'ot_hfd_coll_q2n2_vm_core', 'ot_hbm_su_static_cxport_ij_q', 'ot_hnx_idxn_keybuf_slice',
       'ot_hbm_su_static_sfustore_hw', 'ot_hbm_sm_vm_wr_q_t_lanes4', 'ot_hbm_idx_rootctl_static_am'}
MAC = {'hfd_ep_static', 'ot_hbm_host_cp_rxs', 'ot_hbm_su_programme_pslice_c5', 'ot_hgi_sm_xload_cl2_bfqg',
       'ot_hbm_hc_bank128_pair_first_core', 'ot_hbm_svc_vmdel_lane_n'}
# part 2 (DIE-HBM-61 11-03 08:xx): XCHECK-1 RESHAPE-NOFIT rows + lane READYs folded into d44v
P2 = {'ot_hbm_idx_score_hcol_h0': 'SPLIT READY c4237519789: 2 sub slots ra/rb inside the parent slot (split_slots.json), 0 cycles; parent re-shape not needed',
      'ot_hgi_sfu_split3_lane_core__idpin': 'SPLIT READY 273120b2730: 3 sub slots fr/ex/bk (split_slots.json), +4 on write/reducer/status (crossing_latency core_internal)',
      'ot_hbm_su_static_pgslice_lg__lanes8_11': 'SPLIT READY 8dd205e8bcc: 4 identical sub slots (split_slots.json), 0 cycles',
      'hfd_ep_static': 'MEM READY 55c4a61894a: right-width SRAM 4x 64x306 (mem_recipe_delta.json); slot kept (any shrink +1 reg on vsN0/NW_io link stations); macros UNKNOWN until the RE-FORM kit',
      'ot_hbm_host_cp_rxs': 'MEM READY 55c4a61894a: right-width SRAMs; slot 434.808x480 -> 400.248x151.68 (channel_fit, 17.28 step); macros UNKNOWN until the RE-FORM kit',
      'ot_hnx_idxn_keybuf_slice': 'MEM READY 55c4a61894a: right-width SRAMs + plan pin move key_out -> E (W 1132 / E 1099 pins); slot kept, no parent re-shape',
      'ot_hbm_sm_vm_wr_q_t_lanes4': 'MEM: pins over all 4 faces at 0.168 mean pitch inside the 142.56x216 slot (a taller slot breaks 22 q_hub stations); no parent re-shape',
      'ot_hfd_coll_q3_edge_core': 'placeholder: SPLIT WIP d764970683d (3 LINK + ARG) / MEM right-width only if the current-kit run fails',
      'ot_hfd_coll_q3_body_core': 'placeholder: SPLIT WIP (CTL + 4 QCOL4)',
      'ot_hfd_coll_q3_vm_core': 'placeholder: PIN-BOUND, RTL (serialised face) owed; census slot 864x872.6 does not fit the hub room (+90.7/+34.6)',
      'ot_hfd_coll_q2n2_vm_core': 'placeholder: PIN-BOUND, RTL owed; census slot 1201x604.8 vs room +13/+130',
      'ot_hbm_su_static_cxport_ij_q': 'placeholder: PIN-BOUND, RTL owed; census grow +86.4 x vs room 38.9',
      'ot_hbm_svc_vmdel_lane_n': 'placeholder: census shrink W / grow H 4.32 with room 0 -> kept',
      'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b': 'UNCHANGED (ruling: fine to leave)'}
rows = []
for c in C:
    m = c['module']; d = dec.get(m, {})
    if str(d.get('decision', '')).startswith('RESHAPE (part 2'): cls, owner = 'RESHAPED (part 2 lane outline)', 'DIE-HBM-61/PLAN d44v'
    elif d.get('decision') == 'RESHAPE': cls, owner = 'RESHAPED (class 2)', 'DIE-HBM-61/PLAN d44v'
    elif (c.get('cells') or 0) > 150000: cls, owner = 'SPLIT placeholder (class 1, %d cells)' % c['cells'], 'DIE-HBM-61/SPLIT'
    elif m in PIN: cls, owner = 'PIN-BOUND placeholder (class 3)', 'DIE-HBM-61/MEM'
    elif m in MAC: cls, owner = 'MACRO-CHANNEL placeholder (class 4)', 'DIE-HBM-61/MEM'
    elif not c.get('cell_area'): cls, owner = 'NO PLAN DATA (no AUTO-GEOM attempt)', 'DIE-HBM-61'
    else: cls, owner = 'KEEP slot (class 5; RE-FORM is RTL/clock)', 'DIE-HBM-61/RTL'
    rows.append(dict(module=m, cls=cls, owner=owner, part2=P2.get(m), decision=d.get('decision'), old=c.get('old'), new=d.get('new'),
                     old_fill=c.get('old_fill'), new_fill=d.get('new_fill'), old_aspect=c.get('old_aspect'),
                     new_aspect=d.get('new_aspect'), cells=c.get('cells'), sinks=c.get('sinks'),
                     clock_regions_5k=c.get('clock_regions'), pins=c.get('pins'), pin_bound_min_wh=c.get('pin_need_wh'),
                     macros=c.get('macros'), parent_room_xy=c.get('room_xy'), n_inst=c.get('n_inst'), types=c.get('types')))
json.dump(dict(schema='opentallas.hbm_reform_census.v1', event='d44v', source='AUTO-GEOM d44o latest attempt metrics + d44v plan',
               rules='slot = cells/0.40 + macros (band 0.35-0.45), aspect <= 2.0, face >= pins/5 per um (M4/M5 one layer), '
                     'clock reach (W+H)/2 <= 220, one clock region per <= 5k sinks, macro channel >= pins x 0.048 / 2',
               cores=rows), open(out, 'w'), indent=1)
import collections
print(collections.Counter(r['cls'].split(' (')[0] for r in rows))
for r in rows: print(f"{r['module'][:46]:46s} {r['cls'][:40]:40s} {r['old_fill']} {r['old_aspect']} -> {r['new_fill']} {r['new_aspect']} {r['old']} -> {r['new']} cr{r['clock_regions_5k']}")
