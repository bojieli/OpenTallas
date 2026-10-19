#!/usr/bin/env python3
"""Read exact original source evidence; never annotate a table to a guessed age."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'tools/die_port_bind.py').exists())
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/qwen_layerbench')]
import die_port_bind as P
import die_relay_check as RC
from qwen_split import record_bundles as RB
from qwen_split import d2d_link_calendar as CAL
import netlist_relay_stages as EX

HERE = Path(__file__).resolve().parent
read = lambda n: json.loads((HERE / n).read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for entry in read('source_paths.json').values():
    assert sha(HERE/'source'/entry['snapshot']) == entry['sha256']

def source_text(basename):
    found = [r for r in read('source_paths.json').values() if r['snapshot'].endswith('_'+basename)]
    assert found
    texts = {(HERE/'source'/r['snapshot']).read_text() for r in found}
    assert len(texts) == 1
    return next(iter(texts))

d2d = source_text('ot_qwen_d2d_dies.sv')
n59 = source_text('qfd_native59_dv_service.sv')
kvn = source_text('qfd_kvn_static_transport.sv')
assert re.search(r'parameter integer PR = 1', d2d)
input_captures = dict(tx_slot='p_ts', tx_slot_kind='p_tk', tx_slot_beat='p_tb',
    native_rx_v='p_rv', native_rx_payload='p_rp', rx_slot='p_rs',
    rx_slot_kind='p_rk', rx_slot_beat='p_rb', kv_x3_slot='p_x3s')
for port, flop in input_captures.items():
    assert f'{flop}<={port};' in n59
for port in ('native_tx_slot','native_tx_slot_kind','native_tx_slot_beat',
             'native_rx_v','native_rx_slot','native_rx_slot_kind','native_rx_slot_beat','rx_payload','kv_x3_slot'):
    assert f'always @(posedge ck) q_{port} <= c_{port};' in d2d
    assert f'assign {port} = PR ? q_{port} : c_{port};' in d2d
for port in ('native_tx_v','native_tx_payload','x3','x3_identity','x3_generation'):
    assert f'always @(posedge ck) q_{port} <= {port};' in d2d
    assert f'assign c_{port} = PR ? q_{port} : {port};' in d2d
assert 'seat[wp]<={word_generation,word_identity,word_tag,word_data}' in kvn
assert '{x3_generation,x3_identity,x3[522:0]}<=seat[rp]' in kvn
run = read('repaired_export.json')
old = read('compute_compiled.json')
assert run['problem_count'] == 0
assert run['digest'] == old['digest']
assert sha(HERE/'die.v') == '7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7'
lanes = {r['bid']: r for r in read('fwd_lanes.json')['lanes']}
insts = {name: (master, cm) for master, name, prm, cm in P.parse_die(HERE/'die.v')[3] if master != '__assign__'}
st, seam, problems = RB.seam_stages(HERE/'die.v', HERE/'fwd_lanes.json')
assert not problems, problems
bset = {b: {**RB.BUNDLES, **RB.SEAM_SINGLE}[b] for b in tuple(RB.COMPILER_BUNDLES) + tuple(RB.SEAM_SINGLE)}
bmap, info, problems = RB.netlist_members((HERE/'die.v').read_text(), bset)
assert not problems, problems
fields = []
for bid, pin in sorted(info.items()):
    src, dst = pin['key'].split('->')
    si, sp = src.split('.'); di, dp = dst.split('.')
    bus = next(b for b in run['buses'] if b['id'] == f'{src} -> {dst}')
    row = lanes[bid]
    chain = list(row['stations']) + [row['landing']]
    assert len(chain) == row['n'] == bus['stages']
    assert len(chain) == len(set(chain))
    first = insts[chain[0]][1]; last = insts[chain[-1]][1]
    assert first['a'] == pin['src_net'] and last['b'] == pin['dst_net']
    for a, b in zip(chain, chain[1:]):
        assert insts[a][1]['b'] == insts[b][1]['a']
        assert insts[a][1]['ck_o'] == insts[b][1]['ckf']
        assert insts[a][1]['eb'] == insts[b][1]['ea']
    launch_ck = insts[si][1]['ck']; capture_ck = insts[di][1]['ck']
    assert first.get('ck_s', first.get('ck')) == launch_ck
    assert last['ck'] == capture_ck
    assert EX.landing_strap(last) == row['K']
    assert row['cal'] == row['G_reset_tree'] - row['R0_reset_tree']
    assert row['K'] == (row['E'] + row['cal']) % 8
    assert bus['age_edges'] == row['E'] + 1
    fields.append(dict(bus=bus['id'], bid=bid, bundle=bmap[bid], width=bus['width'],
        raw_hops=bus['stages'], effective_pin_age=bus['age_edges'],
        source_net=pin['src_net'], destination_net=pin['dst_net'],
        actual_source_clock=launch_ck, actual_capture_clock=capture_ck,
        actual_ordered_instances=chain, E=row['E'], K=row['K'],
        hard_source_output_edge='D2D PR output FF' if si=='d2d_rom' else ('KVN seat pop FF' if sp.startswith('x3') else 'native548 codec output FF'),
        hard_destination_input_edges=1, hard_boundary_FFs_included_in_relay_age=False,
        declared_reset_calendar=row['cal'], declared_G=row['G_reset_tree'], declared_R0=row['R0_reset_tree'],
        calendar_scope='source GEN reset-tree ledger, not measured physical clock phase'))
assert len(fields) == 14
params = read('die.v.params.json')['masters']
assert params['qfd_d2d_static'].get('PR', 1) == 1
raw = CAL.producer_txd_c(st)
txd = [a+b for a,b in zip(raw, CAL.PINREG_EXT['C'])]
assert txd == [8,3,1,10]
assert CAL.txdp_word(txd) == params['qfd_d2d_static']['TXDP']
hist = read('historical_compile_manifest.json')
assert st == hist['compute_seam']['stages']
normal = int(re.search(r'D2D_TXDP_C\s*=\s*32.h([0-9a-f]+)', (HERE/'source_d2d_cal_image.svh').read_text())[1],16)
mu = int(re.search(r'D2D_TXDP_C\s*=\s*32.h([0-9a-f]+)', (HERE/'source_d2d_cal_image_mu.svh').read_text())[1],16)
assert normal == params['qfd_d2d_static']['TXDP']
assert mu != normal  # preserve the actual production MU image mismatch
report = RC.check(run, old, max_list=1000)
(HERE/'reexport_vs_historical_compiled_FAIL.json').write_text(json.dumps(report,indent=1)+'\n')
result = dict(schema='opentallas.qwen.source_age_1019.v1', verdict='SEAM_SOURCE_AGE_PASS',
    full_schedule_verdict=report['verdict'], full_schedule_age_differences=len(report['age_diffs']),
    unchanged_raw_bus_digest=run['digest'], fields=fields, seam_stages=st,
    producer_edges_before_d2d_pinregs=raw, d2d_external_pinreg_edges=CAL.PINREG_EXT['C'],
    bound_TXDP=txd, bound_TXDP_word=hex(normal), original_MU_image_TXDP_word=hex(mu),
    production_MU_image_verdict='FAIL: stale [8,3,1,9] image versus bound [8,3,1,10]',
    F16_profile=dict(NU=params['qfd_tt_ctlm_dv']['NU'], OPSEG=params['qfd_tt_ctlm_dv']['OPSEG'],
        STAGE_ME=params['qfd_tt_ctlm_dv']['STAGE_ME'], scope='original programme/profile; not SU/MU token qualification'),
    source_snapshots={r['snapshot']:r['sha256'] for r in read('source_paths.json').values()},
    limits=['ideal-clock RTL lane proof excludes physical clock insertion and wire timing',
            '109 historical non-seam scheduled effective ages require consumer recompile review',
            'production MU calendar mismatch remains; no heavy die admission or full-token PASS'])
(HERE/'source_age_truth.json').write_text(json.dumps(result,indent=1)+'\n')
print('SEAM_SOURCE_AGE_PASS fields=14 full_schedule='+report['verdict']+' age_diffs='+str(len(report['age_diffs'])))
