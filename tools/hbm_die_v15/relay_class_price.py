#!/usr/bin/env python3
"""Per-class bit-weighted relay stages of a die_relay_pass result -> an eval.json option for layout_ds_cost_1016.py (H-DIE 10-16).
    relay_class_price.py RELAY_PASS.json OUT_eval.json     SM_X = max(vms.rr->ctlw) + max(ctlw.xw_data->smh) (equal-age broadcast)."""
import json, sys
rp, out = sys.argv[1], sys.argv[2]
d = json.load(open(rp))
def q(o, s, default=0.0):
    r = [x for x in d['end_to_end'] if x['origin'] == o and x['sinks'] == s]
    return r[0]['total_mean'] if r else default
def qmax(o, s):
    r = [x for x in d['end_to_end'] if x['origin'] == o and x['sinks'] == s]
    return r[0]['total_max'] if r else 0.0
vms_ctl = max(q(f'hfd_hgi_vms_static_{Q}.rr', 'ot_hgi_sm_xload_cl2_ctlw.rr') for Q in ['NE', 'NW', 'SE', 'SW'])
vals = dict(
    SM_HBM=q('ot_hbm_svc_pc_ctrl_leaf.kr_data', 'ot_hbm_svc_vm_kshare.c_kr_data') + q('ot_hbm_svc_vm_kshare.g_kr_data', 'ot_hbm_svc_sm_group.kr_data') + q('ot_hbm_svc_sm_group.sm_packet', 'ot_hbm_accel_smh_attn.packet'),
    # broadcast: equal-age tree -> every SM sees the max depth
    SM_X=vms_ctl + qmax('ot_hgi_sm_xload_cl2_ctlw.xw_data', 'ot_hbm_accel_smh_attn.xw_data'),
    SM_OUT=q('ot_hbm_accel_smh_attn.rdata', 'ot_hbm_sm_vm_wr_q_t.rdata'),
    HBM_VM=q('ot_hbm_svc_vm_kshare.fill_data', 'ot_hbm_svc_vmdel_lane.fill_data_i'),
    VM_HBM=q('ot_hbm_svc_wb_kport.w_k_wdata', 'ot_hbm_svc_vm_kshare.w_k_wdata'),
    HC_ENG=q('ot_hbm_hc_q_static.x_wave', 'ot_hbm_hc_eng_static.x_wave'),
    SFU_CORE=q('ot_hgi_sfu_core_split.local_wq', 'ot_hgi_sfu_lg_pair_leaf.c_wq'),
    LG_HC=q('ot_hbm_hc_q_static.lg_wq', 'ot_hgi_sfu_lg_pair_leaf.c_wq'),
    COLL_EP=q('ot_hfd_coll_q2_static_host_v4.tx_pin_flit', 'hfd_ep_static.tx_frame'),
    VM_RING=q('hfd_hgi_vms_static_SW.ccw_out', 'hfd_hgi_vms_static_NW.ccw_in'),
    LG_SU=max(q(f'ot_hbm_vm_lg_static_bank.near_wq', f'hfd_hgi_vms_static_{Q}.wq') for Q in ['NE', 'NW', 'SE', 'SW']))
b = json.load(open('results/arch/hbm_die_v15/core4_sfu2_b3624/eval.json'))
A = json.loads(json.dumps(b))
for k, v in vals.items():
    A['per_class'][k]['stages_bw'] = v
A['per_class']['SU_CORE']['stages_bw'] = b['per_class']['SU_CORE']['stages_bw'] * 480 / 450   # partitioned programme, issue-ahead
json.dump(A, open(out, 'w'))
print({k: round(v, 2) for k, v in vals.items()})
