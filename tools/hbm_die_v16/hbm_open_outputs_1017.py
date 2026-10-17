#!/usr/bin/env python3
"""HBM-TIE 2026-10-17 (stub audit 0da item 5): classify every open output of the HBM d4f die contract.

Classes (coordinator 0da rules; an open output is legal only if nothing on the die needs its value):
  OBS      bench / observation outputs of a verified block (counters, ordinals, observe buses, S1 consumer copies,
           completion pulses whose timing the static schedule already fixes). Dropped by design: a die variant may
           remove them; they carry no production information.
  ROLE     outputs of a shared / universal master that this instance's role never drives or never needs (constant 0
           or unused mode). Dropped by design: listed per die (0da c); remove in a variant where it pays.
  REPLACED outputs of a master already superseded by a port-exact die variant (the variant drops them).
  MISSING  a real consumer is missing (a bug): fault / retry / status information that must reach the host status
           join (G-CIL-COLLSTAT) or a functional datum somebody needs.
usage: hbm_open_outputs_1017.py CONTRACT.json OUT.json
"""
import json
import sys
from collections import defaultdict

R = {
    # ---- observation
    ('ot_hbm_svc_sm_group_id', 'lt0'): ('OBS', 'S1 consumer copy observation bus of the feed (module header: "kept for benches")'),
    ('ot_hbm_svc_sm_group_id', 'lt1'): ('OBS', 'S1 consumer copy observation bus (bench)'),
    ('ot_hbm_svc_sm_group_id', 'lb0'): ('OBS', 'S1 consumer copy observation bus (bench)'),
    ('ot_hbm_svc_sm_group_id', 'lb1'): ('OBS', 'S1 consumer copy observation bus (bench)'),
    ('ot_hbm_svc_sm_group_id', 'fm'): ('OBS', 'S1 consumer copy observation (bench)'),
    ('ot_hbm_svc_sm_group_id', 'expected_request'): ('OBS', 'feed-side expected SM request: bench comparand of smh_attn.request (static schedule: SM never requests)'),
    ('ot_hbm_accel_smh_attn', 'request'): ('OBS', 'SM request observation; the feed is calendar-driven (static), so no consumer exists by design'),
    ('ot_hbm_svc_sm_group_id', 'run_done'): ('OBS', 'run completion pulse; program_active/running carry the state'),
    ('ot_hbm_idx_selector_static', 'out_line'): ('OBS', 'op-8 emit read-back of the compacted lines; the TOPK link consumes selected_line during compaction (ingest_v = &selected_v)'),
    ('ot_hbm_idx_selector_static', 'out_v'): ('OBS', 'valid of the emit read-back (see out_line)'),
    ('ot_hbm_idx_selector_static', 'threshold_observe'): ('OBS', 'radix threshold observe bus (bench)'),
    ('ot_hbm_idx_selector_static', 'selected_observe'): ('OBS', 'per-quarter selected counts (bench); the core faults on >512 internally'),
    ('ot_hbm_idx_topk_link_static', 'selected_count'): ('OBS', 'count observe (bench)'),
    ('ot_static_cmd_target', 'cycle'): ('OBS', 'free-running launch cycle counter export (MODE 1 DMA clock); MODE 0 instances have no consumer'),
    ('hfd_hgi_vm_calendar_f20', 'ordinal'): ('OBS', 'calendar word ordinal (bench)'),
    ('ot_hgi_sfu_programme_store', 'programme_ordinal'): ('OBS', 'ordinal (bench)'),
    ('ot_hgi_sfu_programme_store', 'io_ordinal'): ('OBS', 'ordinal (bench)'),
    ('ot_hbm_su_programme', 'edge_index'): ('OBS', 'programme edge index (bench)'),
    ('ot_hfd_coll_q2_hard_v5', 'stat_cycles'): ('OBS', 'statistics counter'),
    ('ot_hfd_coll_q3_hard_v7x', 'stat_cycles'): ('OBS', 'statistics counter'),
    ('ot_hgi_coll_tkm_m_tp192', 'stat_cycles'): ('OBS', 'statistics counter'),
    ('ot_hfd_coll_q2_hard_v5', 'inj_idx'): ('OBS', 'inject index observe (static inject calendar)'),
    ('hfd_hgi_vm_calendar_f20', 'client_seq'): ('OBS', 'sequence observe'),
    ('hfd_hgi_vm_calendar_f20', 'response_seq'): ('OBS', 'sequence observe'),
    ('ot_vms_status4_static', 'vmstat'): ('OBS', 'VM status word observe (faults also leave on the fault path)'),
    ('ot_hbm_status_join_fa', 'a_cause'): ('OBS', 'HBM-FAULT region cause register (sticky, cleared with the fault); the fault itself reaches the host as die_fault + block_ready low; host read map (ingress 0xf34) is a follow-up'),
    # completion pulses / busy of statically scheduled engines (the compiler fixes when they occur)
    **{(m, p): ('OBS', 'completion / busy pulse of a statically scheduled engine; programme activity reaches the host through the collar/target active/ready')
       for m, p in [('hfd_hgi_vm_calendar_f20', 'done'), ('hfd_hgi_vm_calendar_f20', 'calendar_v'),
                    ('ot_hbm_svc_sm_xcal_t', 'done'), ('ot_hbm_hc_q_static', 'residual_done'),
                    ('ot_hbm_hc_q_static', 'gather_done'), ('ot_hbm_hc_q_static', 'program_done'),
                    ('ot_hgi_sfu_programme_store', 'programme_done'), ('ot_hfd_coll_q2_hard_v5', 'program_init_busy'),
                    ('ot_hfd_coll_q2_hard_v5', 'hgi_done'), ('ot_hfd_coll_q2_hard_v5', 'done'),
                    ('ot_hfd_coll_q3_hard_v7x', 'program_init_busy'), ('ot_hfd_coll_q3_hard_v7x', 'hgi_done'),
                    ('ot_hfd_coll_q3_hard_v7x', 'done'), ('ot_hbm_argmax_static_sw_vm', 'done'),
                    ('ot_hgi_qdq_host_static', 'program_done'), ('ot_hgi_qdq_host_static', 'beat_done'),
                    ('ot_hgi_qdq_host_static', 'record_done'), ('ot_hbm_hc_eng_static', 'program_done'),
                    ('ot_hbm_idx_ctl_static', 'topk_done'), ('ot_hbm_svc_vmdel_lane', 'busy'),
                    ('ot_hbm_svc_vmdel_lane', 'block_ready'), ('hfd_ep_static', 'rx_block_ready'),
                    ('hfd_vms_bank_native_q0_faces', 'dq_done'), ('hfd_vms_bank_native_q0_faces', 'kq_done'),
                    ('hfd_vms_bank_native_q1_core_pr', 'kq_done'), ('hfd_vms_bank_native_q0_faces', 'wq_done1'),
                    ('hfd_vms_wq2_merge', 'wq_done1'), ('hfd_vms_wq2_merge', 'wq_done2'),
                    ('ot_hgi_dma_back_static_vp4_banks_cp', 'mv_done'), ('ot_hgi_dma_back_static_vp4_banks_cp', 'quiet'),
                    ('ot_hgi_dma_back_static_vp4_banks_cp', 'busy'), ('ot_hgi_dma_back_static_vp4_banks_cp', 'mv_src'),
                    ('hfd_hgi_vms_static_SW_glue', 'mirror_busy'), ('hfd_hgi_vms_static_SE_glue', 'mirror_busy'),
                    ('hfd_hgi_vms_static_NW_glue', 'mirror_busy'), ('hfd_hgi_vms_static_NE_glue', 'mirror_busy'),
                    ('ot_hbm_argmax_static_sw_vm', 'cq_seq'), ('ot_hbm_idx_ctl_static', 'cq_seq'),
                    ('ot_hgi_sm_xload_xq_pegress', 'x_done'), ('ot_hgi_sm_xload_xq_pegress', 'xw_last')]},
    # ---- role-unused outputs of shared / universal masters
    **{('hfd_hgi_vm_calendar_f20', p): ('ROLE', 'universal VM calendar: output of a role (LG / ring / replay / slot) this calendar instance does not play')
       for p in ['wslot', 'rslot', 'rslot_v', 'wslot_v', 'lg_local_read', 'lg_local_write', 'bank_client', 'ring_tx_source',
                 'ring_tx_enable', 'bank_enable', 'hub_ring_client', 'hub_ring_enable', 'response_enable',
                 'replay_enable', 'replay_source']},
    ('ot_hbm_static_cfg_collar', 'rec'): ('ROLE', 'record payload of collars with NREC=0 (SU, SFU x4): constant, no records exist'),
    ('ot_hbm_static_cfg_collar', 'go'): ('ROLE', 'record go of collars with NREC=0: constant 0'),
    ('ot_static_cmd_target', 'cmd_v'): ('ROLE', 'MODE 0 (RUN) instances: the SEQ command port is never driven (constant 0)'),
    ('ot_static_cmd_target', 'cmd'): ('ROLE', 'MODE 0 (RUN) instances: SEQ payload, constant 0'),
    ('ot_hbm_xp_aq_tree13_fmt', 'y'): ('ROLE', 'qdq (dequantised) result of the closed quantiser tile; the x-load consumes only q/e (FP8 codes + exponent)'),
    ('hfd_ckgen', 'pll_link'): ('ROLE', 'link-domain PLL root: no d4f block is clocked in the link domain (die links run in the stream domain); VERIFY with H-DIE'),
    ('hfd_ckgen', 'por_link'): ('ROLE', 'link-domain reset (see pll_link)'),
    ('hfd_hgi_vms_static_SW_glue', 'hub_status'): ('ROLE', 'hub status observe of the VMS glue (bench)'),
    ('hfd_hgi_vms_static_SE_glue', 'hub_status'): ('ROLE', 'hub status observe'),
    ('hfd_hgi_vms_static_NW_glue', 'hub_status'): ('ROLE', 'hub status observe'),
    ('hfd_hgi_vms_static_NE_glue', 'hub_status'): ('ROLE', 'hub status observe'),
    # ---- replaced by a port-exact variant
    **{('ot_hgi_sm_xload_cl2_ctlw', p): ('REPLACED', 'EGRESS_SPLIT=1: x egress leaves through the pair-egress leaves; ctlx (HBM-B 2c49a6986) drops these ports')
       for p in ['xw_data', 'xw_addr', 'xw_grp', 'xw_en', 'xw_last', 'x_done']},
}
MISSING_FAULT = 'fault / cause / retry with no consumer: must reach the host status join (G-CIL-COLLSTAT) or the stack fault join; a fault the host cannot see is a real gap'
MISSING_PORTS = {'fault', 'fault_cause', 'mv_fault', 'retry_requested', 'ring_fault', 'nan_flag', 'status'}


def main():
    c = json.load(open(sys.argv[1]))
    inst = c['instances']
    rows = defaultdict(lambda: dict(instances=[], bits=0))
    open_set = {(i, p) for i, p, _ in c['open_outputs']}
    for i, p, b in c['open_outputs']:
        m = inst[i]['master']
        if p == 'fault_cause' and (i, 'fault') not in open_set:
            cls, why = 'OBS', 'fault cause detail; the summary fault of the same instance is connected to the status path'
        elif (m, p) in R:
            cls, why = R[(m, p)]
        elif p in MISSING_PORTS:
            cls, why = 'MISSING', MISSING_FAULT
        else:
            cls, why = 'UNCLASSIFIED', ''
        r = rows[(m, p, cls)]
        r.update(master=m, port=p, cls=cls, why=why)
        r['instances'].append(i)
        r['bits'] += b
    out = sorted(rows.values(), key=lambda r: (r['cls'], -r['bits']))
    tot = defaultdict(lambda: [0, 0])
    for r in out:
        tot[r['cls']][0] += len(r['instances'])
        tot[r['cls']][1] += r['bits']
    json.dump(dict(schema='opentallas.hbm.open-outputs-1017.v1', contract=sys.argv[1], total_ports=len(c['open_outputs']),
                   by_class={k: dict(ports=v[0], bits=v[1]) for k, v in tot.items()}, rows=out),
              open(sys.argv[2], 'w'), indent=1)
    for k, v in sorted(tot.items()):
        print(f'{k:13s} ports={v[0]:4d} bits={v[1]}')
    for r in out:
        if r['cls'] in ('MISSING', 'UNCLASSIFIED'):
            print(r['cls'], r['master'], r['port'], len(r['instances']), r['bits'])


if __name__ == '__main__':
    main()
