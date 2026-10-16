#!/usr/bin/env python3
"""H-NETLIST/smvm round 0030: static SM result -> VM writer, its command calendar and the SM status child join.
Writes tools/hbm_die_v15/v16_specs/smvm_0030.json and patches cp2.json (host_status child entry) and host_misc.json
(ingress TARGET_MASK bits 160..163).  Idempotent."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SP = ROOT / 'tools/hbm_die_v15/v16_specs'
Q = ('SW', 'SE', 'NW', 'NE')
WR_SRC = 'rtl/hbm_accel/generic/vm/static/ot_hbm_sm_vm_wr_q.sv'
CT_SRC = 'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv'
TGT0 = 160
# quadrants whose VM master has a free static write group for the SM writer (group index = calendar wslot code)
SM_WG = {'SW': 1, 'SE': 1, 'NW': 1, 'NE': 1}
s = dict(region='smvm_0030', author='Claude H-NETLIST/smvm (round 0030)', instances=[], edges=[], clocks=[], straps=[],
         gaps=[], notes=[])
def E(src, dst, bits, basis): s['edges'].append(dict(src=src, dst=dst, bits=bits, clock='stream', basis=basis))
for qi, q in enumerate(Q):
    wr, ct = f'smw_{q}', f'cp_smw_{q}'
    s['instances'].append(dict(name=wr, master='ot_hbm_sm_vm_wr_q', source=WR_SRC, params=dict(QUAD=qi, DEPTH=4),
        slot=f'vmh_{q}', owner='H-NETLIST/smvm',
        note='STATIC SM result -> VM writer (decision 23:21 SM_OUT sm->vmh). Pin-registered. SM k -> bank k only; word '
             '64*(base+p*stride+r[11:3])+8k+r[2:0], one masked write per (row, slot); fixed latency rv(t) -> wq slot0 valid t+3, '
             'slot p at t+3+p, serial P-cycle server per SM (DEPTH 4 rows). VM calendar_<q> reserves wslot[k]=GROUP on those '
             'cycles. Bench tb_hbm_sm_vm_wr_q (8 real ot_vms_bank_static + LG competitor) PASS, mutants wrong-row / late-phase FAIL.'))
    s['instances'].append(dict(name=ct, master='ot_static_cmd_target', source=CT_SRC,
        params=dict(TARGET=f"8'd{TGT0+qi}", MODE=1, CW=26, RELF=0, NA=1, NF=1), slot=f'vmh_{q}', owner='H-NETLIST/smvm',
        note=f'TARGET {TGT0+qi}: SM-writer descriptor calendar (128 x {{cmd 26, at 32}}, one 128x256 SRAM row/entry) fired at '
             'launch_base+loop*period+at; cmd = {fmt_bf16, mirror, P4, stride_row10, base_row10}; fired only while smw busy=0.'))
    for i in (wr, ct): s['clocks'].append(dict(inst=i, port='clk', domain='stream', kind='clock'))
    for p, w in [('cfg_v', 1), ('cfg_target', 8), ('cfg_addr', 12), ('cfg_data', 256), ('desc_v', 1),
                 ('desc_base', 12), ('desc_limit', 13), ('desc_loops', 16), ('launch_v', 1)]:
        E(['host_cp_ingress', p], [ct, p], w, 'static ingress F20 broadcast')
    E([ct, 'cmd_v', 0, 1], [wr, 'cmd_v', 0, 1], 1, 'compiler command calendar: descriptor pulse, no ready')
    E([ct, 'cmd', 0, 26], [wr, 'cmd', 0, 26], 26, 'descriptor {fmt,mirror,P,stride_row,base_row}')
    E([wr, 'busy', 0, 1], [ct, 'tgt_active', 0, 1], 1, 'writer busy -> target active (status)')
    E([wr, 'fault', 0, 1], [ct, 'tgt_fault', 0, 1], 1, 'writer sticky fault -> target fault (status)')
    for k in range(8):
        sm = f'sm_{q}{k}'; n = qi * 8 + k
        E([sm, 'rv', 0, 1], [wr, 'rv', k, k + 1], 1, 'SM_OUT sm->vmh (270 b grant link): result valid')
        E([sm, 'rrow', 0, 12], [wr, 'rrow', 12 * k, 12 * k + 12], 12, 'SM_OUT: result row')
        E([sm, 'rdata', 0, 256], [wr, 'rdata', 256 * k, 256 * k + 256], 256, 'SM_OUT: 8 x FP32 result (column p = slot p)')
        E([sm, 'fault', 0, 1], [wr, 'sm_fault', k, k + 1], 1, 'SM sticky result fault -> writer pin flop -> writer fault -> TARGET status')
        E([sm, 'schedule_fault', 0, 1], [wr, 'sm_sched_fault', k, k + 1], 1, 'SM static-schedule fault -> writer pin flop -> writer fault -> TARGET status')
    if q in SM_WG:
        g = SM_WG[q]
        E([wr, 'wq', 0, 2248], [f'hb_vms_{q}', 'wq', g * 2248, (g + 1) * 2248], 2248,
          f'SM writer = VM wide write group {g} (calendar wslot code {g}); SW/SE new group1; NW former CP and NE retired ATT group1')
s['notes'] = [
 'SM_RESULT_TO_VM: all 32 SMs rv/rrow/rdata -> smw_<q> (4 x one master); fault/schedule_fault -> smw_<q> pin flops -> sticky writer fault -> cp_smw_<q>.tgt_fault -> host_status row of TARGET 160+QID (participation-filtered; no child join: an empty child would veto launches that do not use the writer).',
 'Static timing: SM rv cycle t -> smw pin t+1 -> FIFO t+2 -> wq valid in cycle t+3 (slot 0), slot p at t+3+p; bank samples wq and '
 'wslot at the same edge (n), writes the macro at n+3. A row arriving while the SM lane still emits starts at the previous row end. '
 'Calendar owner: hfd_hgi_vm_calendar calendar_<q> (programme via cp_cal_<q> TARGET 96+QID) emits wslot_v[k]=1, wslot[k]=GROUP exactly '
 'on the writer emission cycles; one owner per bank per cycle is the calendar word itself (a single code per bank per cycle), and '
 'SM k only ever writes bank k, so the 8 lanes cannot collide; any calendar/writer phase error is a bank schedule FAULT (bench MUT=2).',
 'Descriptor calendar cp_smw_<q> TARGET 160+QID (parent allocation 160..163).',
 'COMPILER ROW-DEALING RULE (attn 2026-10-16, ARGMAX.LOCAL index = word position): VM word = 64*(base_row+p*stride_row+r[11:3])+8k+r[2:0]. '
 'For position == global row (the LM head read by hb_argmax via mirror=1 / a_mirror), quadrant q takes contiguous 64-row blocks '
 '(base_row_q = q*Bq) and SM k computes the rows g with ((g>>3)&7)==k at local row r = 8*((g>>6)-base_blk)+(g&7). The default contiguous '
 'per-SM shard s*Q+r gives wrong ids and tie order. DS head n=1347 = 22 blocks (6/6/5/5), SM imbalance at most 8 rows; logits unchanged.',
 'VM native compact ABI: every SM writer uses wq1. SW/SE WG2 adds the real port; NW/NE retain WG3. NE wq2 and new rq3 (HC), NW cq clients0..2, and SW cq client1 remain G-SMVM-VMCLIENT until genuine producers exist. Retired old NW/NE readgroup3 and NW client3 have no pins.']
(SP / 'smvm_0030.json').write_text(json.dumps(s, indent=1) + '\n')
# host_status rows / ingress mask for cp_smw_<q> (TARGET 160+QID) now live in tools/hbm_die_v15/complete_host_targets_2330.py
# (H-NETLIST integration 0030: one generator owns host_status so sibling regions cannot collide on NT/NF/TGTS).
print('smvm_0030 spec written')
