"""Cold bounded-stream metadata model; no checkpoint restore or numerical work."""
import hashlib
import json
from pathlib import Path
import ds_composite_weight_delegation_r1 as D
ORIGINAL='results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'

def build():
    out=D.ROOT/D.OUT;enrollment,esha=D.C.load_enrollment()
    fit,selected,adapted=D.source_fit(D.ROOT/ORIGINAL,out/'inputs/actual-r58-bound-native.json.gz',
        json.loads((out/'inputs/actual-r58-home-binding.json').read_bytes()),enrollment)
    policy=D.delegation_policy(fit,esha,D.sha(D.__file__))
    # All owner calls use their captured home-bound operation, with emitted order.
    plans=[]
    for op in selected['instructions']:
        for owned in op['rank_bindings']:
            tid=owned['template']
            plans.append(D.C.resolve_call(selected,adapted,'weight',op['provider_bindings'][tid]['weight'],owned,selected['templates'][tid]['providers']['weight']))
    if len(plans)!=288:raise ValueError('all actual composite call owners required')
    model=dict(schema='DS_EXTERNAL_DATA_ONLY_COMPOSITE_DELEGATION_MODEL_R1',
        source_fit=fit,policy=policy,actual_selected_call_count=len(plans),
        minimum_contiguous_resume_PC=11,first_delegated_PC=115,
        additional_producer_state_or_checkpoint_payload_copy_bytes=0,
        baseline_V3_restore_and_RAM_projection_reused_not_zero=True,
        metadata_policy_serialized_bytes=len(D.C.canonical(policy)),
        max_selected_checkpoint_read_bytes=max(p['selected_checkpoint_bytes'] for p in plans),
        max_selected_output_bytes=max(p['output_bytes'] for p in plans),
        max_selected_temporary_and_output_bytes=max(p['temporary_and_output_bound_bytes'] for p in plans),
        no_state_conversion_or_identity_relabel=True,
        actual_checkpoint_receipt=None,actual_PC10_restore_receipt=None,
        payload_comparison_receipt=None,resource_reservation_receipt=None,
        external_controller_source_sha256=None,admission=False,
        remaining=['actual PC10 checkpoint and exact-class V3 restore, preserving state/history/journal/shards/witness',
            'explicit external controller source and complete resource projection/reservation',
            'independent selected real-checkpoint BF16 read/run comparison with Sagan after resource admission',
            'contiguous PC11+ native execution/publication/release/retirement and independent witness; no prefix repeat'],
        delegation_seam=['external controller selects exact PC/owner/weight binding through resolve_call',
            'original p._read_one(op, owned, template, bindings_without_weight, generation) through original complete MRO reads all other operands and registers actual views',
            'after separately admitted selected BF16 reader, insert original typed tensor-list weight provenance into that SAME registered views dict; do not replace owner object or copy it',
            'unchanged primitive code/output ordering; publish through existing Observed owner for independent witness; original release_views uses exact registered dict identity',
            'on any failure retain original view/source debt; no retry, auto-retire, inferred ACK or automatic release',
            'original lifecycle/state owners remain; externally bound controller is first-class source/journal provenance in future source_contract, not an untracked callback'],
        baseline_795_payload_status='UNEXECUTED. Its prototype header-preflight full-stat comparison includes atime; delegation reader must use original locked-reader stable dev/ino/size/mtime/ctime and independently validate before payload admission.',
        source_sha256={p:D.sha(D.ROOT/p) for p in [ORIGINAL,
            'tools/ds_composite_weight_delegation_r1.py','tools/ds_composite_delegation_model_r1.py',
            'tools/ds_producer_checkpoint_resume_v3.py','tools/h3_ds_composite_weight_binding_r1.py',
            'results/uarch/ds_composite_weight_binding_20261003/enrollment-r1.json',
            str(D.OUT/'inputs/actual-r58-bound-native.json.gz'),str(D.OUT/'inputs/actual-r58-home-binding.json')]})
    return dict(model=model,selected_native=selected,adapted_enrollment=adapted)

if __name__=='__main__':
    records=build();out=D.ROOT/D.OUT
    for key,name in [('model','model-r1.json'),('selected_native','selected-bound-native-r1.json'),('adapted_enrollment','adapted-call-enrollment-r1.json')]:
        p=out/name
        if p.exists():raise ValueError('preserve frozen evidence')
        p.write_text(json.dumps(records[key],indent=2,sort_keys=True)+'\n')
