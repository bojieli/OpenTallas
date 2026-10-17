#!/usr/bin/env python3
"""Q-DV -> die-trial inputs (Q-DIEPLAN3): per-link relay plan at 405 um + contract deltas for a model.
    export_trial_inputs.py MODEL.json OUTDIR TAG"""
import json, math, collections, sys
m, outd, tag = sys.argv[1:4]
d = json.load(open(m)); I = {i['n']: i for i in d['insts']}
cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
def face(i, P):
    x, y = P
    ds = {'W': abs(x - i['x']), 'E': abs(x - i['x'] - i['w']), 'S': abs(y - i['y']), 'N': abs(y - i['y'] - i['h'])}
    return min(ds, key=ds.get)
rows = []; ports = collections.defaultdict(list)
for b, c, bits, eps in d['buses']:
    if c in ('clock_trunk', 'reset'): continue
    p = [e for e in eps if e in I]
    for a, q in (zip(p, p[1:]) if len(p) == 2 else [(p[0], t) for t in p[1:]]):
        A, Q = cl(I[a], cen(I[q])), cl(I[q], cen(I[a])); L = abs(A[0] - Q[0]) + abs(A[1] - Q[1])
        rows.append(dict(bus=b, cls=c, bits=bits, src=a, dst=q, src_pin=[round(A[0], 2), round(A[1], 2)], dst_pin=[round(Q[0], 2), round(Q[1], 2)],
                         L_um=round(L, 1), stages405=max(0, math.ceil(L / 405) - 1), stages200=max(0, math.ceil(L / 200) - 1)))
        for n, P, dr, peer in ((a, A, 'out', q), (q, Q, 'in', a)):
            if n in ('dvs_W5', 'dvs_W2', 'c16_W2_1', 'c16_W2_0'):
                ports[n].append(dict(bus=b, dir=dr, bits=bits, face=face(I[n], P), peer=peer))
rows.sort(key=lambda r: -r['L_um'])
plan = dict(schema='opentallas.qwen.qdv_relay_plan.v1', model=m, hop_um=405,
            rule=('stages = ceil(L/405)-1 on face-projected Manhattan; every stage is a repeater-buffered relay station '
                  '(die-level buffering, H-REACH); recipe-4 hold_budget die (hold on relay stations, FLOW-HOLD); the 14-edge '
                  'rs_i -> rs_o feedthrough is INSIDE qfd_c_b16_dv, not a die relay'),
            totals=dict(links=len(rows), relay_bits405=sum(r['bits'] * r['stages405'] for r in rows),
                        relay_bits200=sum(r['bits'] * r['stages200'] for r in rows)),
            links=rows)
json.dump(plan, open(f'{outd}/relay_plan_{tag}.json', 'w'), indent=1)
rm = sorted({'qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3', 'qfd_sp_su64_sfu', 'qfd_seq_su_static', 'qfd_xs_tap', 'qfd_xcol_w',
             'qfd_xcol_e', 'qfd_su_cbuf_g', 'qfd_crom_g', 'qfd_port_half_b2', 'qfd_sp_halfband_lanes_b2_l2', 'qfd_res_train_issue_b2',
             'qfd_b2_word_status', 'qfd_band_upper_b2_l2_s4', 'qfd_static_command_fork42', 'qfd_static_selector_fork4'}
            | {f'qfd_res_train_half_b2_{k}' for k in range(6)})
deltas = dict(
    schema='opentallas.qwen.qdv_contract_deltas.v1', model=m, date='2026-10-17', remove_masters=rm,
    add_masters=dict(
        qfd_dv_slice2=dict(
            n=12, outline_um=[round(I['dvs_W0']['w'], 3), round(I['dvs_W0']['h'], 3)],
            rtl='claude/qdv-slice-1016 rtl/qwen_dv/qfd_dv_slice.sv (step 1 d54b67f56; step 2 adds 4 column heads + 32 x-leaves, hr_i/hr_o, pipelined root, argmax)',
            hold_budget='die (recipe 4, flop-first pins, no opt-out)',
            ports_note=('per slice: rs from the b1 / b2 clusters (each 2 x 514: own rs + far-band rs_o); 8 x 516 corridor words '
                        '(4 n_d -> band-2 bc, 4 s_d -> band-1 bc); W/E stream 2 x 1088 + scalar 96 + hr 453 (W->E); chain AR 546/518 '
                        'and D2D 548/520 toward W5; L9 514 with the pair slice. W5 additionally: io_collective AR, native59 D2D '
                        '2 x 1068, tt_ctlm hr 453'),
            ports_from_plan=dict(dvs_W5=ports['dvs_W5'], dvs_W2=ports['dvs_W2'])),
        qfd_c_b16_dv=dict(
            n=48, base='qfd_c_b16 (Q-CLUSTER claude/qcluster-1017 0131f6672: 2,285.28 x 5,184, corridors A/T/B 129.6)',
            add_ports=[dict(port='rs_i', dir='input', bits=514, face='master N (band-gap side, beside bc_o)'),
                       dict(port='rs_o', dir='output', bits=514, face='master S (beside rs)')],
            feedthrough='registered rs_i -> rs_o in corridor T, 14 edges (Q-CLUSTER measured)',
            positions='near bands (1, 2) carry the far cluster rs; far bands (0, 3) have no far neighbour: near/far master split or one master with a band strap is Q-CLUSTER\'s choice (OPEN)',
            ports_from_plan=dict(c16_W2_1=ports['c16_W2_1'], c16_W2_0=ports['c16_W2_0']))),
    moved=dict(
        w_column=('W edge, S->N: io_serdes_2, io_serdes_1, io_collective (beside dvs_W5), io_ucie, io_serdes (rotated 90); '
                  'N end: ucie_kv (N edge at the W corner), d2d_rom, native59 | sys_face, tt_ctlm | embed_prov / clk_rx / rstseq_rom; '
                  '216-um column channel for the native59 -> W5 lane'),
        native59='port re-partition: inputs from the dvs_W5 chain (2 x 1068) instead of SU kv_w* / VM q, ar, commit',
        tt_ctlm='ib/go/xpf as hr 453 b into dvs_W5; VM mx/ld/mo/mee ports and the forks removed'),
    open=['qfd_c_b16_dv far-position rs_i (Q-CLUSTER)', 'native59 / tt_ctlm port re-partition RTL', 'slice step 2 RTL (heads, hr, pipelined root, argmax)'])
json.dump(deltas, open(f'{outd}/contract_deltas_{tag}.json', 'w'), indent=1)
print(tag, len(rows), 'links; relay bits @405', plan['totals']['relay_bits405'])
