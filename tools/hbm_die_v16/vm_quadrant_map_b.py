#!/usr/bin/env python3
"""HBM-B-RTL1 2026-10-17 (owner 0do, plan (b) d4g): per-quadrant VM client-side mapping for the H-D4G contract.
Writes results/rtl/hbm_b_rtl1_1017/vm_quadrant_map.json: masters, straps, SM -> writer lane -> bank, SM group (vmks) ->
delivery lane slot, calendars, bank port groups, and the compiler latency / layout contract.  d4f instance names are kept
for the per-SM elements (sm_/xc_/svg_/vmks_<stack><k>, ctl_<stack>_p<n>); quadrant elements are named <prefix>_<Q>.
    vm_quadrant_map_b.py [--out PATH]
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
Q = {'SW': dict(stack='SW', sid=0, lb=0), 'SE': dict(stack='SW', sid=1, lb=4),
     'NW': dict(stack='NW', sid=2, lb=0), 'NE': dict(stack='NW', sid=3, lb=4)}
HUB = {'SW': 'hfd_hgi_vms_static_SW_glue', 'NW': 'hfd_hgi_vms_static_NW_glue',
       'SE': 'hfd_hgi_vms_static_SEb_glue', 'NE': 'hfd_hgi_vms_static_NEb_glue'}
out = {'schema': 'opentallas.hbm_d4g.vm_quadrant_map.v1', 'lane': 'HBM-B-RTL1', 'date': '2026-10-17',
       'basis': 'd4f run8b contract (claude/hdie-d4f-r8b-1017); plan (b) quad_of_sm: SMs / PC groups 0-3 of a stack -> W, 4-7 -> E',
       'quadrants': {}}
for q, c in Q.items():
    st, lb, sid = c['stack'], c['lb'], c['sid']
    sms = [f'sm_{st}{lb + k}' for k in range(4)]
    banks = {}
    for b in range(8):
        banks[f'vmb_{q}{b}'] = {
            'master': 'hfd_vms_bank_native_q0_faces', 'straps': {'bid': b, 'sid': sid},
            'ports': {'rq0/wq0': f'SU LG (su_{q}<s> pair taps, as d4f)', 'rq1': f'hb_dbk_{q} (DMA-back, quadrant instance)',
                      'rq2': f'xl_{q}_ctl (SM_X x-load, quadrant instance: plan item 9)', 'rq3': f'hb_coll_{q}' if q != 'NW' else 'hb_quant_NW (as d4f)',
                      'rq4': f'quadrant IDX ctl/query (HBM-B-RTL2)' if q != 'NW' else 'hb_coll_NW (as d4f)',
                      'wq1': (f'vmm_NW{b}.wq_m (quant + SM writer merge, as d4f)' if q == 'NW' else
                              f'smw_{q}.' + (f'wq_s{b - lb}' if 0 <= b - lb < 4 else f'wq_t{(b - lb - 4) % 8}')),
                      'dq': f'vmdel_{q}{b}.dq', 'kq': f'hb_coll_{q}.vm_kq', 'pq/pr/xq/xq2/eg/status': f'hb_vms_{q} (own hub only)',
                      'rslot/wslot': f'calendar_{q}'}}
    lanes = {}
    for b in range(8):
        lanes[f'vmdel_{q}{b}'] = {
            'master': 'ot_hbm_svc_vmdel_lane_n', 'params': {'NPC': 2}, 'straps': {'bank_id': b},
            'fill_slots': {str(g): f'vmks_{st}{lb + 2 * g + (b >= 4)}.fill_*[lane {b % 4}]' for g in range(2)},
            'begin/start': f'vmfc_{q}', 'status_ring': [f'vmdel_{q}{x}' for x in range(8)], 'dq': f'vmb_{q}{b}.dq',
            'fault': f'sfault_{st} del_fault (or a quadrant stack-fault home: H-D4G)'}
    out['quadrants'][q] = {
        'stack': st, 'sid': sid, 'sms': sms, 'pc_controllers': [f'ctl_{st}_p{n}' for n in range(16 * (lb // 4), 16 * (lb // 4) + 16)],
        'hub': {'inst': f'hb_vms_{q}', 'master': HUB[q],
                'local_clients': {'SW': ['hb_argmax (client 0)', 'IDX (client 1)'], 'NW': [],
                                  'SE': ['quadrant IDX ctl/query (client 0, HBM-B-RTL2)'], 'NE': ['quadrant IDX ctl/query (client 0, HBM-B-RTL2)']}[q],
                'ring': 'cw/ccw 2224 b to the neighbour hubs, unchanged (XQ lane)'},
        'calendar': {'inst': f'calendar_{q}', 'master': 'hfd_hgi_vm_calendar_f20',
                     'note': 'unchanged field mapping; serves only its own 8 banks + hub (as d4f); SE/NE now NC 1: client_seq 4 b, response_enable 2 b, response_seq 4 b, bank_client 8 b, hub_ring_client 2 b'},
        'fill_calendar': {'inst': f'vmfc_{q}', 'master': 'hfd_hgi_vm_calendar_f20',
                          'drives': [f'vmks_{st}{lb + k}.vm_*' for k in range(4)] + [f'vmdel_{q}{b}.begin/start' for b in range(8)],
                          'note': 'SE/NE outputs were unconnected in d4f; the W calendars drop the E groups'},
        'writer': {'inst': f'smw_{q}', 'master': 'ot_hbm_sm_vm_wr_q_t_lanes4', 'params': {'DEPTH': 4},
                   'straps': {'quad': sid, 'lbase': lb // 4, 'tgt': f'host cfg target of smw_{q} (new ids for SE/NE: host / H-D4G)'},
                   'lanes': {str(k): {'sm': sms[k], 'half0_bank': f'vmb_{q}{lb + k}', 'half1_bank': f'vmb_{q}{(lb + k + 4) % 8}'} for k in range(4)}},
        'vm_share': {f'vmks_{st}{lb + k}': {'pcs': [f'ctl_{st}_p{4 * (lb + k) + l}' for l in range(4)],
                                           'fill_lanes': {str(l): f'vmdel_{q}{l + 4 * (k % 2)} slot {k // 2}' for l in range(4)}} for k in range(4)},
        'per_sm_unchanged': [f'{p}_{st}{lb + k}' for p in ('xc', 'svg', 'vmks') for k in range(4)],
        'banks': banks, 'delivery_lanes': lanes}
out['retired_d4f'] = ['hfd_vms_bank_native_q1_core_pr (SE/NE banks)', 'hfd_hgi_vms_static_SE_glue / _NE_glue (NC 0)',
                      'smw_SW / smw_NW 8-SM writers (ot_hbm_sm_vm_wr_q_t_lanes)', 'ot_hbm_svc_vmdel_lane (NPC 4) x16']
out['compiler_contract'] = {
    'sm_writer': ['0 edges added: rv(t) -> wq slot 0 at t+3; calendar fire edge C_launch + 2 + LEAD + at (as d4f)',
                  'calendar entry payload 27 b: {half, fmt, mir, P4, stride10, base10}; half 0 -> bank LB+k, half 1 -> bank (LB+k+4)%8',
                  'VM sector of an SM result: quad = the SM\'s OWN quadrant (E SMs: SE/NE instead of SW/NW), bank as above, row/word as d4f',
                  'per-SM VM capacity: 2 banks x 1024 rows (d4f: 1 bank)'],
    'delivery': ['NPC 2: a lane block = 64 slots x 2 groups = 128 dq beats = 1024 sectors (d4f 2048)',
                 'beat (slot s, group g) sector = base + 16 s + 8 g (d4f base + 32 s + 8 g); leaves start + 2 + (2 s + g) edges after the start edge (d4f 4 s + g); first beat 3 edges after start (unchanged)',
                 'aperture: base 32-sector aligned, base <= 7168 (d4f 6144); block_ready = both PC slots full, STATUS_LAT 2, lane LAT 2 (unchanged)',
                 'a quadrant fills only its own 8 banks from its own 4 SM groups (16 PCs); the E banks no longer need ring mirrors of the fill'],
    'hub_and_banks': ['SE/NE hub, ring stop, replay, status: the SW slice logic unchanged (ring COMMIT_DELAY 5 + BANK_PIN_IN 1, bank input pin flop +1, return 7 / write 4 edges as SW)',
                      'SE/NE bank groups take the SW numbering: read 0 LG, 1 DMA-back, 2 x-load, 3 COLL, 4 IDX; write 0 LG, 1 SM writer; wslot codes WG+k unchanged (COLL 2, CW 3, packet 4, CCW 5, DMA 6); rslot width 3 b unchanged',
                      'SE/NE hub client 0 = quadrant IDX (response code 1 = replay)']}
p = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else ROOT / 'results/rtl/hbm_b_rtl1_1017/vm_quadrant_map.json'
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(out, indent=1) + '\n')
print('VM_QUADRANT_MAP', p, sum(len(v['banks']) for v in out['quadrants'].values()), 'banks',
      sum(len(v['delivery_lanes']) for v in out['quadrants'].values()), 'delivery lanes')
