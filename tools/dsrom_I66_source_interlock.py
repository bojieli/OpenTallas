#!/usr/bin/env python3
"""Additive source correction and native-edge consumer relations; no launcher.

These relations require qualified accepted events. They do not manufacture an
accepted PHW10 origin, establish a cross-domain deadline, or admit hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_I66_source_interlock_20261003'
SOURCE_PATHS = {
    'core': 'results/uarch/dsrom_I66_provider_clock_contract_20261002/inputs/core.sv.txt',
    'vec': 'results/uarch/dsrom_I66_consumer_deadline_20261002/inputs/vec.sv.txt',
    'lane': 'results/uarch/dsrom_I66_consumer_deadline_20261002/inputs/vec_lane.sv.txt',
    'tile': 'results/uarch/dsrom_I66_provider_clock_contract_20261002/inputs/tile.sv.txt',
    'rom_adapter': 'results/uarch/dsrom_I66_source_interlock_20261003/inputs/rom_adapt.sv.txt',
    'program_template': 'results/uarch/dsrom_I66_consumer_deadline_20261002/inputs/demand-r5.json.gz',
    'consumer_extractor': 'tools/dsrom_I66_consumer_deadline.py',
    'selected_calls': 'results/uarch/dsrom_I66_consumer_deadline_20261002/inputs/selected_six_calls.json',
    'patched_I66_word': 'results/uarch/dsrom_I66_provider_clock_contract_20261002/inputs/I66_current_patched_word.json',
    'selected_clock': 'results/uarch/dsrom_I66_phase_protocol_join_20261003/inputs/selected_clock_model.json',
    'prior_record': 'results/uarch/dsrom_I66_phase_protocol_join_20261003/model.json',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources():
    pins = json.loads((OUT / 'source_pins.json').read_text())
    for key, relative in SOURCE_PATHS.items():
        if pins[key] != {'path': relative, 'sha256': sha(ROOT / relative)}:
            raise ValueError('source identity changed: ' + key)
    return pins

def uint(value, bits=None):
    if type(value) is not int or value < 0 or (bits is not None and value >= 1 << bits):
        raise ValueError('exact nonnegative integer width required')
    return value

def waited(mask, idles, gos):
    """Source bit order ME, SU, QE, XU, HE (low to high)."""
    mask, idles, gos = (uint(v, 5) for v in (mask, idles, gos))
    return (mask & ~(idles & ~gos)) == 0

def rom_ready(state, spine_ready):
    uint(state, 3); uint(spine_ready, 1)
    return state == 0 and spine_ready == 1

def adapter_wait_exit(state, s_go, s_idle):
    uint(state, 3); uint(s_go, 1); uint(s_idle, 1)
    return state == 5 and s_go == 0 and s_idle == 1

def accepted_emit_relation(edge, bcast_stages, gathered, *, live_lane, reset_free):
    """Relative to preedge emit=1; no source issue/start bound is inferred.

    'live_lane' asserts source live0 (lin and in-range lane), not every physical
    lane. The event must belong to the enrolled command/epoch in a real trace.
    This helper computes expected edges; it does not qualify those assertions.
    """
    uint(edge); uint(bcast_stages)
    for v in (gathered, live_lane, reset_free):
        if type(v) is not bool:
            raise ValueError('boolean assertion required')
    if not live_lane or not reset_free:
        raise ValueError('pipeline relation requires live lane and reset-free interval')
    read = edge + bcast_stages + 2 + (2 if gathered else 0)
    return {'VM_read_preedge': read, 'X_tag_preedge': read + 2,
            'publication_latest_postNBA_edge': read - 1,
            'actual_trace_qualified': False}

def model():
    pins = sources()
    core = (ROOT / SOURCE_PATHS['core']).read_text()
    vec = (ROOT / SOURCE_PATHS['vec']).read_text()
    lane = (ROOT / SOURCE_PATHS['lane']).read_text()
    adapter = (ROOT / SOURCE_PATHS['rom_adapter']).read_text()
    needles = [(core, 'idles = {he_idle, xu_idle, qe_idle, su_idle, me_idle};'),
               (core, 'gos = {he_go, xu_go, qe_go, su_go, me_go};'),
               (core, "wire waited = ((d_wait & ~(idles & ~gos)) == 5'd0);"),
               (core, 'assign qe_ready = qe_rom ? rom_ready_w : qe_ready_e;'),
               (core, '.PHW(ROM_PHW), .VAW(AW)'),
               (core, 'S_GO: begin pc <= pc + 1\'b1; st <= S_FETCH; end'),
               (core, 'S_DEC: if (win_admit) st <= S_ISSUE;'),
               (adapter, 'assign ready = st == S_IDLE && s_ready;'),
               (adapter, 'S_WAIT: if (!s_go && s_idle) st <= S_IDLE;'),
               (vec, "if (!rst_n) b_emit <= 1'b0; else b_emit <= emit;"),
               (vec, '.LEAF((BCAST_STAGES > 0) ? 1 : 0)'),
               (lane, "else begin f_v <= live0; vi_re <= live0 && (aind_e != IND_NONE); end"),
               (lane, 'g1_v <= f_v && f_g; g2_v <= g1_v;'),
               (lane, 'm_v <= mr_v; x_v <= m_v;')]
    if any(needle not in text for text, needle in needles):
        raise ValueError('source edge contract changed')
    import gzip
    demand = json.loads(gzip.decompress((ROOT / SOURCE_PATHS['program_template']).read_bytes()))
    nodes = {n['instruction_index']: n for n in demand['nodes']
             if n.get('scope') == 0 and n.get('kind') == 'instruction'}
    for pc in [66, 67, 68, 69]:
        i = nodes[pc]['instruction']
        if (i['unit'], i['qe_mode'], i['wait']) != (3, 0, 0):
            raise ValueError('ROM command sequence changed')
    import dsrom_I66_consumer_deadline as D
    first_consumers = {o['producer_node']: o['first_static_consumer'][0]['consumer_node']
                       for o in D.source_model()['obligations']}
    if [first_consumers[f'L0.I{pc}'] for pc in (66, 67, 68)] != ['L0.I70', 'L0.I70', 'L0.I80']:
        raise ValueError('published lease overlap changed')
    i = nodes[70]['instruction']
    if (i['unit'], i['wait'], i['a_base'], i['c_base']) != (2, 2, 398720, 399296):
        raise ValueError('consumer dependency changed')
    return {
        'schema': 'opentallas.I66.source-interlock.v1', 'source_pins': pins,
        'corrects_preserved_commit': '19acbd015ec9a5796868fb2ecf3807d6d672079e',
        'correction': 'Prior wait2/QE circular-block statement is incorrect: wait2 is SU; QE is mask4. Historical record unchanged.',
        'wait_masks': {'ME': 1, 'SU': 2, 'QE_ROM': 4, 'XU': 8, 'HE': 16},
        'source_dependencies': {
            'I66_I69': 'QE LINQ next admission requires adapter IDLE and spine_ready; previous S_WAIT exits only !s_go && spine_idle.',
            'I70': 'SU wait2 drains SU only; reads I66 A and I67 C. Prior I66/I67/I68 spine retirements precede I69 admission via ROM ready serialization. I70 can overlap I69.',
            'program_evidence': 'Pinned demand-r5 template is static dependency evidence; not current four-rank compiled program enrollment.',
            'next_issue_no_stall_minimum_edges': 6,
            'next_issue_upper_bound': None,
            'upper_bound_gap': 'S_DEC win_admit and S_ISSUE waited/ready/source gates can stall; emit additionally depends on setup, checkpoints and chain credits.'},
        'relative_read_contract': {
            'native_preedge_accepted_emit_E_linear': 'R = E + BCAST_STAGES + 2',
            'native_preedge_accepted_emit_E_gather': 'R = E + BCAST_STAGES + 4',
            'observed_X_tag': 'R + 2, same enrolled command/rank/generation/user/Xversion',
            'required_visibility': 'Owned postNBA VM visibility strictly before R; visibility on R misses preedge read.',
            'conditions': ['live0 in-range lane (source lin flag), with gather selector independently bound', 'no reset through tag', 'compiled actual BCAST_STAGES', 'source-consistent gather selector and read owner'],
            'not_inferred': ['ROM accepted origin to first emit upper bound', 'current accepted user/generation', 'physical CDC edge mapping']},
        'one_candidate_required_contract': {
            'clock_commit': 'c9d19ed598077e4a4941c8548273f15deefb8c1a',
            'clock_main_intake': 'cd054f1d1495095ff47b68842b573e59eb193467',
            'credit_commit': '6f2c3b8f143fb6cecc5534b6cb9abbbd29166efb',
            'identity': '169 global context with full user32 plus separate physical shard1; Nash LSB header144/command237, not a truncated user.',
            'publication': 'Intercept scalar slot0; suppress/intercept ALL original ROM roots1..127 during captured phase; veto all other native writer-family address competitors even equal data.',
            'proposed_next_ROM_admission_fence': 'Current adapter spine idle/ready alone does not include remote capture visibility. Proposed replacement must prove previous owned publication complete before allowing next command, or provide row-specific actual deadline proof. This fence is not implemented.',
            'version_lease': 'Hold published addresses and owner/version through actual SU read R and observed aligned X tag R+2, separately from source-row credit.',
            'ordered_program_lease_lower_bound': 'At I69 admission, I66/I67/I68 published address/version associations remain live because first consumers are I70/I70/I80. A fourth active phase identity starts at I69; source capture storage may be reused only after its own visibility/credit fences. Retained VM lease metadata is separately required and not priced here.',
            'single_context_deadlock_control': 'If next ROM admission waits for prior address lease retirement at future SU read, I67 cannot issue and I70 cannot be reached. This is program ordering, not a wait2/QE dependency.',
            'source_credit': 'Retain source row until same-identity actual VM visibility plus positive captured return; no downstream seat assumed and no same-edge reuse.',
            'shared_calendar': 'Join source issued/read reply, gather grant, writer delivery, postNBA visibility, positive credit return and actual SU read/tag in one enrolled clock/CDC map.',
            'C': None, 'stations': None, 'CDC': None},
        'actual_current_PHW10': {'callback_implementation': None, 'accepted_journal': None,
            'program_source_binary_enrollment': None, 'accepted_origin_user_generation': None,
            'compiled_BCAST_STAGES': None, 'consumer_deadline': None},
        'status': 'BOUND_MISSING', 'scope': 'SOURCE_ANALYTICAL_NATIVE_EDGE_RELATIONS_ONLY',
        'hardware_admission': False, 'fulltoken': False, 'new_job': False,
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = model()
    serialized = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.verify:
        if (OUT / 'model.json').read_text() != serialized:
            raise SystemExit('model replay mismatch')
        print('source pins and canonical model PASS; BOUND_MISSING')
    elif args.out:
        args.out.write_text(serialized)
    else:
        print(serialized, end='')
