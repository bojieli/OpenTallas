"""d44v reform_census.json: per RE-FORM core the plan-time numbers + owner of its RE-FORM (DIE-HBM-61 ruling 11-03)."""
import json, sys
C = json.load(open(sys.argv[1])); E = json.load(open(sys.argv[2])); out = sys.argv[3]
dec = {d['module']: d for d in E['decisions']}
PIN = {'ot_hfd_coll_q3_vm_core', 'ot_hfd_coll_q2n2_vm_core', 'ot_hbm_su_static_cxport_ij_q', 'ot_hnx_idxn_keybuf_slice',
       'ot_hbm_su_static_sfustore_hw', 'ot_hbm_sm_vm_wr_q_t_lanes4', 'ot_hbm_idx_rootctl_static_am'}
MAC = {'hfd_ep_static', 'ot_hbm_host_cp_rxs', 'ot_hbm_su_programme_pslice_c5', 'ot_hgi_sm_xload_cl2_bfqg',
       'ot_hbm_hc_bank128_pair_first_core', 'ot_hbm_svc_vmdel_lane_n'}
rows = []
for c in C:
    m = c['module']; d = dec.get(m, {})
    if d.get('decision') == 'RESHAPE': cls, owner = 'RESHAPED (class 2)', 'DIE-HBM-61/PLAN d44v'
    elif (c.get('cells') or 0) > 150000: cls, owner = 'SPLIT placeholder (class 1, %d cells)' % c['cells'], 'DIE-HBM-61/SPLIT'
    elif m in PIN: cls, owner = 'PIN-BOUND placeholder (class 3)', 'DIE-HBM-61/MEM'
    elif m in MAC: cls, owner = 'MACRO-CHANNEL placeholder (class 4)', 'DIE-HBM-61/MEM'
    elif not c.get('cell_area'): cls, owner = 'NO PLAN DATA (no AUTO-GEOM attempt)', 'DIE-HBM-61'
    else: cls, owner = 'KEEP slot (class 5; RE-FORM is RTL/clock)', 'DIE-HBM-61/RTL'
    rows.append(dict(module=m, cls=cls, owner=owner, decision=d.get('decision'), old=c.get('old'), new=d.get('new'),
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
