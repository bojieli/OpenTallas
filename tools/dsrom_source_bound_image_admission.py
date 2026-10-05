#!/usr/bin/env python3
"""D2 preparation only: actual-source LAT binding and payload-free phase audit.

Reuses existing FAST/PP image implementation. No compiler, simulator, checkpoint,
golden payload, new FIFO or RTL arithmetic implementation.
"""
import ast
import collections
import hashlib
import inspect
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import v41_die_images_w17w10 as FAST
import w17_runtime_v41_die_images as PROD


def digest(data):
    return hashlib.sha256(data).hexdigest()


def actual_binding():
    path = 'rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv'
    text = (ROOT / path).read_text()
    cut = int(re.search(r'parameter \[8:0\] CUT = 9\x27b([01_]+)', text)[1].replace('_', ''), 2)
    assert 'localparam integer LAT = FAST != 0 ? 1 + CUT[0]' in text
    assert all('CUT[%d]' % i in text for i in range(9))
    lat = 1 + cut.bit_count()
    f = FAST.Field(8192, 128, 1024, fast=True, pp=True)
    if f.add_latency != lat:
        raise ValueError('existing generator LAT differs from actual source; new source review required')
    return dict(source=path, source_sha256=digest(text.encode()), FAST=1, PP=1, BP=0,
                FRONT_PAR=0, CUT=cut, actual_add_LAT=lat)


def refuse_stale(metadata, binding):
    p = metadata['params']
    for k in ('FAST', 'PP', 'BP', 'FRONT_PAR', 'actual_add_LAT'):
        if p.get(k) != binding[k]:
            raise ValueError('STALE_IMAGE_ADMISSION: missing/different ' + k)
    if not metadata.get('phases'):
        raise ValueError('STALE_IMAGE_ADMISSION: empty phase ledger')


def verify_phase_images(metadata, stream_words, phase_words):
    """Reject stale/forged tags by reconstructing complete source control images."""
    binding = actual_binding()
    refuse_stale(metadata, binding)
    p = metadata['params']
    f = FAST.Field(p['np'],p['regions'],p['nbf'],depth=p['depth'],active=p['active'],fast=True,pp=True)
    fn, transcription = metadata_function(FAST)
    phases = []
    for phase in metadata['phases']:
        audit_phase(f,phase,fn,binding)
        phases.extend(FAST.phase_words(f.phases[-1]))
    if stream_words[:len(f.stream)] != f.stream or any(stream_words[len(f.stream):]):
        raise ValueError('STALE_IMAGE_ADMISSION: source round stream differs')
    if phase_words[:len(phases)] != phases or any(phase_words[len(phases):]):
        raise ValueError('STALE_IMAGE_ADMISSION: source phase words differ')
    if len(f.stream) != metadata['stream_words'] or any(a['nbeat']!=b['nbeat'] for a,b in zip(f.phases,metadata['phases'])):
        raise ValueError('STALE_IMAGE_ADMISSION: phase cycle count differs')
    return dict(status='SOURCE_CONTROL_IMAGES_BOUND_NO_EXECUTION',binding=binding,
                transcription=transcription,phases=len(f.phases),stream_words=len(f.stream))


def metadata_function(module):
    """Only omit weight-word materialization; retain placement, fills and order."""
    source = inspect.getsource(module.add_phase)
    tree = ast.parse(source)
    removed = []

    class Payload(ast.NodeTransformer):
        def visit_For(self, node):
            if isinstance(node.target, ast.Name) and node.target.id == 'mb' and 'bf16_word' in ast.unparse(node):
                removed.append(ast.unparse(node))
                return None
            return self.generic_visit(node)

        def visit_If(self, node):
            if 'by_key = {}' in ast.unparse(node):
                # PP permutation payload is excluded; retain its configuration
                # base address. Phase word counts/ordering remain below intact.
                removed.append(ast.unparse(node))
                return ast.parse('if field.pp:\n    cfg[p][2*NSEG] |= phase_start << 6').body[0]
            return self.generic_visit(node)

        def visit_Return(self, node):
            return ast.parse('return ph, rounds, demand, segs, by_p').body[0]

    tree = Payload().visit(tree)
    ast.fix_missing_locations(tree)
    if len(removed) != (2 if module is FAST else 1):
        raise ValueError('unexpected payload transformation')
    if 'field.words' in ast.unparse(tree):
        raise ValueError('unremoved ROM payload access')
    ns = dict(vars(module))
    exec(compile(tree, '<source-bound-payload-free-phase>', 'exec'), ns)
    return ns['add_phase'], dict(source_sha256=digest(source.encode()),
        omitted_payload_sha256=[digest(x.encode()) for x in removed],
        transformed_ast_sha256=digest(ast.unparse(tree).encode()),
        excluded='ROM word payload and PP payload permutation only; no state/geometry/order/demand reductions')


def audit_phase(field, phase, function, binding):
    mats = [SimpleNamespace(name=m['name'], fmt=m['fmt'], rows=m['rows'][1]-m['rows'][0],
            K=m['cols'][1]-m['cols'][0], r0=m['rows'][0], k0=m['cols'][0]) for m in phase['matrices']]
    ph, rounds, demand, segs, by_p = function(field, mats, fmt_fp32=phase['fmt_fp32'], rsplit=phase['rsplit'])
    for key in ('index', 'bf', 'K', 'nrows', 'matrices', 'segments_per_pair_max', 't_read'):
        if ph[key] != phase[key]:
            raise ValueError('actual metadata reconstruction differs: ' + key)
    ledger = []
    for q, b in sorted(rounds):
        units = sorted(rounds[q,b])
        ds = {p:n for (qq,bb,p),n in demand.items() if (qq,bb)==(q,b)}
        groups = (len(units)+3)//4 if ph['bf'] else len(units)
        old = max(PROD.S.FADD_REC, groups, max(ds.values()))
        bound = max(binding['actual_add_LAT'], groups+int(ph['bf']), max(ds.values()))
        ledger.append(dict(q=q,b=b,units=units,groups=groups,active_pairs=len(ds),
            demand_words_histogram=dict(sorted(collections.Counter(ds.values()).items())),
            max_demand_words=max(ds.values()), old_SMIN5_round_words=old,
            actual_FAST1_bound_round_words=bound, delta_schedule_words=bound-old,
            per_pair_demand_sha256=digest(json.dumps(ds,sort_keys=True).encode())))
    base = 2*FAST.NSEG
    cfg = field.cfg[-1]
    odd = 0
    counts = collections.Counter()
    for p, ids in by_p.items():
        order = FAST.S.element_order([segs[i] for i in ids])
        count = len(order)
        counts[count] += 1
        odd += count % 2
        if cfg[p][base] >> 6 < 0:
            raise ValueError('negative PP base')
    return dict(index=phase['index'],pc=phase['pc'],kind=phase['kind'],key=phase['key'],
        formats=sorted(set(m.fmt for m in mats)), K=ph['K'],nrows=ph['nrows'],
        old_nbeat=sum(x['old_SMIN5_round_words'] for x in ledger),
        actual_bound_nbeat=ph['nbeat'],metadata_nbeat=phase['nbeat'],
        delta_schedule_words_per_position=sum(x['delta_schedule_words'] for x in ledger),
        rounds=ledger,per_pair_words_histogram=dict(sorted(counts.items())),
        potential_PP_same_bank_MTP_restarts_pairs=odd,
        PP_collision_contract='Consecutive issue parity alternates. Restart to phase base after odd word count has same bank; actual stall only if consecutive cycles. Hazard gaps may remove collision. Positions/start readiness required for actual event count.',
        BF16_contract='BP0 column multiplication, existing FAST grouped-round +1 reserve retained; no BP hold credit or grouped capture equivalence inferred.',
        config_sha256=digest(json.dumps(cfg,separators=(',',':')).encode()))


def audit_metadata(metadata):
    binding = actual_binding()
    params = metadata['params']
    field = FAST.Field(params['np'],params['regions'],params['nbf'],depth=params['depth'],
                       active=params['active'],pp=True,fast=True)
    fn, transcription = metadata_function(FAST)
    result = [audit_phase(field, phase, fn, binding) for phase in metadata['phases']]
    return dict(status='STATIC_PHASE_DEMAND_ENUMERATION_NOT_RTL_OR_FULL_CALENDAR',
        binding=binding,transcription=transcription,params=params,phases=result,
        phase_count=len(result),actual_bound_stream_words=len(field.stream),
        metadata_stream_words=metadata['stream_words'],
        delta_schedule_words_per_position=sum(p['delta_schedule_words_per_position'] for p in result),
        emitted_program_MTP_positions=None,actual_PP_collision_event_count=None,
        actual_fifo_occupancy=None,actual_last_leaf_to_root_retire=None,
        owner='Epicurus D2 phase subledger',calendar_owner='Maxwell R0/C1',
        missing='Join positions, VM availability, credits, bank start state, return/writer service and drain in owner calendar; do not zero-fill')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--metadata',required=True,type=Path)
    a = ap.parse_args()
    print(json.dumps(audit_metadata(json.loads(a.metadata.read_text())),indent=2,sort_keys=True))
