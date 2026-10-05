#!/usr/bin/env python3
"""Selected-program VM output leases; no invented accepted edges or credits.

The ordered trace envelope releases consumed versions only at source collective
drains. It is a native single-clock conditional bound, not candidate enrollment,
a deadline, extra storage, or a full-context inventory.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_selected_context_lifetimes_20261003'


def sources():
    pins = json.loads((OUT / 'source_pins.json').read_text())
    for path, expected in pins.items():
        if hashlib.sha256((OUT / path).read_bytes()).hexdigest() != expected:
            raise ValueError('source pin changed: ' + path)
    return (json.loads((OUT/'inputs/instructions.json').read_text()),
            {name: (OUT/'inputs'/name).read_text() for name in ['core.sv', 'su_adapt.sv', 'vec.sv']})


def derive(nodes, rtl):
    required = {
        'core.sv': ['if (waited && (&idles) && !coll_busy)',
                    'S_COLL_WAIT: if (!coll_busy)',
                    'wire [4:0] idles = {he_idle, xu_idle, qe_idle, su_idle, me_idle}'],
        'su_adapt.sv': ['assign idle = !pend && v_idle;'],
        'vec.sv': ['wire pipe_live = b_emit || bt_live || rt_live || bz_f || vp || bz_m || (|vml) || bz_s || (|vsl);',
                   "wire idle_c = (pst == 2'd0) && !a_v && !pipe_live && !red_busy;",
                   'idle <= idle_c && !accept;']}
    for name, snippets in required.items():
        if any(s not in rtl[name] for s in snippets):
            raise ValueError('source drain formula changed: ' + name)
    ordered = sorted(nodes, key=lambda n: n['instruction_index'])
    if [n['instruction_index'] for n in ordered] != list(range(66,106)):
        raise ValueError('complete I66..I105 instruction slice required')
    if any(n['instruction'].get('pred',0) != 0 for n in ordered):
        raise ValueError('dynamic predicate requires actual acceptance binding')
    versions = []
    for n in ordered:
        i = n['instruction']; pc = n['instruction_index']
        if i.get('unit') != 3 or i.get('qe_mode') != 0:
            continue
        start, count = i['qe_obase'], i['qe_nout']
        if count not in (576,1280) or start < 0 or start + count > 2**19:
            raise ValueError('unbound geometry or VM address alias')
        consumers = []
        for later in ordered:
            li = later['instruction']; lp = later['instruction_index']
            if lp <= pc or li.get('unit') != 2:
                continue
            for operand in 'abcd':
                if (li.get(operand+'_src',0) == 0 and li.get(operand+'_base') == start
                        and li.get(operand+'_si',1) == 1 and li.get('su_nin') == count):
                    consumers.append(dict(pc=lp, operand=operand,
                        instruction_sha256=later['template_word_sha256']))
        if not consumers:
            raise ValueError('selected output has no complete source consumer')
        versions.append(dict(producer=pc, words=count, first=start, end=start+count,
            producer_sha256=n['template_word_sha256'], consumers=consumers,
            captured_candidate=count == 576, X_address=i['qe_xbase'],
            EID_address=i['qe_ibase'], actual_identity=None))
    if len(versions) != 18 or sum(v['captured_candidate'] for v in versions) != 12:
        raise ValueError('same18 selected phases /12 captured required')
    for a in versions:
        for b in versions:
            if a['producer'] < b['producer'] and max(a['first'],b['first']) < min(a['end'],b['end']):
                raise ValueError('output versions alias in native VM')
    by_pc = {v['producer']:v for v in versions}
    live = []; steps = []; drains = []
    for n in ordered:
        pc=n['instruction_index']; i=n['instruction']
        if pc in by_pc:
            live.append(by_pc[pc])
        released=[]
        if i.get('unit') == 6:
            if i.get('wait') != 31:
                raise ValueError('collective barrier source contract changed')
            released=[v['producer'] for v in live if max(c['pc'] for c in v['consumers']) < pc]
            live=[v for v in live if v['producer'] not in released]
            drains.append(dict(pc=pc, retired_output_versions=released,
                proof='Native SU !pend && registered vec idle: both stage lines/pipe_live/red_busy drained before collective admission.'))
        steps.append(dict(pc=pc, live_versions=[v['producer'] for v in live],
            version_count=len(live), FP32_words=sum(v['words'] for v in live)))
    # Necessary lower bound is from FUTURE consumers only; not dispatch release.
    future=[]
    for n in ordered:
        pc=n['instruction_index']
        vs=[v for v in versions if v['producer']<=pc and min(c['pc'] for c in v['consumers'])>pc]
        future.append(dict(pc=pc, live_versions=[v['producer'] for v in vs],
            version_count=len(vs), FP32_words=sum(v['words'] for v in vs)))
    peak=max(steps,key=lambda s:s['version_count']); witness=max(future,key=lambda s:s['version_count'])
    if peak['version_count'] != witness['version_count'] or peak['FP32_words'] != witness['FP32_words']:
        raise ValueError('source lower/upper envelopes do not close exact selected-output bound')
    words=max(s['FP32_words'] for s in steps)
    return dict(scope='SELECTED_OUTPUT_VERSION_SOURCE_BOUND_ONLY',
        selected_phases=18, captured_W1_W3=12, native_W2=6,
        versions=versions, drain_barriers=drains, ordered_envelope=steps,
        necessary_future_consumer_witness=witness,
        maximum_payload_witness=max(steps,key=lambda s:s['FP32_words']),
        conditional_maximum_selected_output_versions=peak['version_count'],
        conditional_maximum_selected_output_FP32_words=words,
        existing_VM_payload_bits_per_rank=words*32,
        existing_VM_payload_bytes_per_rank=words*4,
        existing_VM_payload_bytes_TP4=words*4*4,
        all18_output_frame_words=sum(v['words'] for v in versions),
        additional_payload_reservations=0, additional_credits=0,
        last_native_W2_producer=100, required_observer_consumer_end_pc=105,
        required_callback_tail='All consumer reads and observed R+2 tags after I105, not PC105 arrival.',
        conditions=['Exactly these18 descriptors accepted in source order with source template/patch enrollment.',
                    'Native source SU idle/drain remains sound for read and tag pipeline; selected CDC provider must separately demonstrate retirement.',
                    '576-seat intercepted W1/W3 and1280-word native W2 remain distinct; no transfer of capacity or credits.'],
        actual_maximum_full_contexts=None, absolute_F_bound=None, actual_journal=None,
        claim_determining_unknowns=[
            'Current accepted PC/phase/key/expert/rank/generation/user32/Xversion enrollment, not latest PC or wrapper user10.',
            'Input X/ACTALL and EID address-version acquisition, writers, final loader reads and generation lease retirement.',
            'Each output actual VM visibility, consumer sequence/address/read and observed matching R+2 tag.',
            'Positive captured CDC credit plus complete packet ACK debts before same-context WAIT exit F.',
            'Current c9 clock/reset/phase relation and finite provider accepted service/stall bound; callback maxima alone are measured extents, not universal deadlines.'],
        physical_route_admission=False, candidate_runtime_qualified=False)


def model():
    nodes, rtl = sources()
    result=derive(nodes,rtl)
    result['source_pins']=json.loads((OUT/'source_pins.json').read_text())
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    text=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if a.output:a.output.write_text(text)
    else:print(text,end='')
