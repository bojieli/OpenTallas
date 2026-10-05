#!/usr/bin/env python3
"""Validate W16's pinned coarse owner inventory; never infer product topology."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(owner):
    errors = []
    count = owner.get('stage_count')
    if not isinstance(count, int) or count <= 0:
        return ['positive integer layer-stage count required']
    if owner.get('layer_dies') != 4 * count:
        errors.append('TP4 layer die count inconsistent')
    layers = owner.get('layer_owners', [])
    if [r.get('layer') for r in layers] != list(range(40)):
        errors.append('ordered layer0..39 coverage required')
    experts = owner.get('expert_count')
    for layer in layers:
        if not 0 <= layer.get('dense_owner_stage', -1) < count:
            errors.append('dense owner outside modeled stage range')
        ids = []
        for assignment in layer.get('routed_expert_candidate_owners', []):
            if not 0 <= assignment.get('stage', -1) < count:
                errors.append('expert owner outside modeled stage range')
            lo, hi = assignment['expert_ids']
            if not isinstance(lo, int) or not isinstance(hi, int) or hi < lo:
                errors.append('invalid exact expert ID interval')
            else:
                ids.extend(range(lo, hi + 1))
        if ids != list(range(experts)):
            errors.append('expert coverage has gap/overlap/order mismatch at layer' + str(layer['layer']))
    if len(owner.get('pairs_per_die_by_stage', [])) != count:
        errors.append('per-stage pair inventory length mismatch')
    return errors


def preflight(root):
    path = root / 'results/arch/v41_stage_owner_product.json'
    owner = json.loads(path.read_text())
    hashes = {}
    for name, expected in owner['source_sha256'].items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('W16 source identity mismatch: ' + name)
        hashes[name] = actual
    errors = validate(owner)
    if errors:
        raise ValueError('; '.join(errors))
    return dict(schema='opentallas.w17.physical_stage_mapping_preflight.v1',
        status='PINNED_COARSE_MAPPING_VALIDATED_PRODUCT_EXECUTION_BLOCKED',
        owner_record_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        model_basis=owner['basis'],
        source_sha256=hashes,
        functional_ops=dict(layer_ops=40, final_norm=1, vocabulary_head=1, total=42),
        modeled_inventory=dict(layer_TP4_groups=owner['stage_count'], layer_dies=owner['layer_dies'],
            conditional_45_candidate_not_bound=True,
            dense_and_expert_owners=owner['layer_owners'], pairs_per_die=owner['pairs_per_die_by_stage']),
        owner_status=owner['status'], owner_claim_boundary=owner['claim_boundary'],
        missing_owner_gates=owner['missing_gates'],
        physical_mapping='UNBOUND_EXECUTABLE_STAGE_PROGRAM_AND_ROM_ADDRESS',
        launch_allowed=False, adopt=False,
        next_bounded_gate=dict(
            prerequisites=['Source-pinned W16 assignment of actual physical layer/head/table stages',
                'Exact tensor/scale/metadata ROM-address manifest for chosen stage/rank',
                'Ordered stage program and selected-expert owner lookup',
                'Model hop payload/type/width, finite depth, ready-valid backpressure, clock domains, latency, area/tracks and replica count',
                'Full stage/rank DUT persistent KV/window/index owner allocation; preserve queued L0 pin'],
            implementation='New off-default replicated stage/rank companions plus finite RTL hop. Host clocks/wires/compares only; no activation arithmetic/gather or stage resets.',
            proof=['Bounded two physical-stage RTL producer/consumer execution with independent stage weights and actual producer KV writes',
                'Exact activation/expert-output/HC-state packet order, no truncation/duplicate/loss under stalls and queue-full cases',
                'Distinct per-stage/rank KV/index/window retained state; restart token without reconstructing DUTs',
                'Reject golden activation/current-KV injection, host gather/arithmetic, wrong stage/expert/user tags, state overwrite and dropped/duplicated beats',
                'Measure finite-hop cycles and feed composed model; SS/FF remain separate contextual gates']),
        contract='42 functional operations do not specify physical stage count. Coarse41 is not executable topology; conditional45 remains unbound. No single-DUT reload product claim.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=ROOT)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = preflight(args.source)
    with args.output.open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
