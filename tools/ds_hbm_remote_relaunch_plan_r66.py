"""Frozen remote-only gate sequence; no launch and no estimated costs as zero."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_hbm_remote_relaunch_r66_20261003'
ALLOWED_HOSTS=('ot-pve1','ot-agidock128')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_launch(plan,*,hostname,output_root,resources,dual_constructor,smoke):
    if hostname not in ALLOWED_HOSTS:raise ValueError('PVE1 or ot-agidock128 only; local launch prohibited')
    if str(Path(output_root).resolve())!=plan.get('resolved_output_root'):
        raise ValueError('exact priced remote output root required')
    if plan.get('projection_complete') is not True:raise ValueError('complete remote resource projection pending')
    for key in ('required_disk_bytes','required_RAM_bytes'):
        required=plan.get(key)
        if type(required)is not int or required<=0 or resources.get(key.replace('required','available'),-1)<required:
            raise ValueError('fresh full-size resource admission required: '+key)
    if dual_constructor.get('status')!='PASS_ACTUAL_PRODUCER_AND_COLD_ADDITIVE_CONSTRUCTORS':
        raise ValueError('actual full-size R64 dual constructors required')
    if smoke.get('status')!='PASS_ACTUAL_PC0_1_ATOMIC_CHECKPOINT_COLD_PROCESS_RESTORE':
        raise ValueError('mandatory actual PC0-1 checkpoint/restore smoke pending')
    if (smoke.get('retired_PCs')!=[0,1] or smoke.get('actual_payload_exact') is not True or
        smoke.get('all_owners_drained') is not True or smoke.get('live_debts')!=0 or
        smoke.get('sealed_journals_verified_after_producer_exit') is not True or
        type(smoke.get('producer_pid'))is not int or type(smoke.get('restore_pid'))is not int or
        smoke['producer_pid']==smoke['restore_pid']):
        raise ValueError('actual fresh-process restore/ownership evidence incomplete')
    return True


def prepare():
    baseline=ROOT/'results/uarch/ds_hbm_checkpoint_readiness_r64_20261003'
    plan=json.loads((baseline/'preflight_plan.json').read_bytes())
    model=json.loads((baseline/'preflight_model.json').read_bytes())
    source=dict(plan['source_sha256'])
    for path in ('tools/ds_hbm_atomic_checkpoint_r66.py','tools/ds_hbm_remote_relaunch_plan_r66.py'):
        source[path]=sha(ROOT/path)
    checked=[]
    for path,digest in sorted(source.items()):
        p=ROOT/path
        if sha(p)!=digest:raise ValueError('immutable source pin mismatch: '+path)
        if p.suffix=='.py':
            code=p.read_text();compile(code,str(p),'exec');ast.parse(code,filename=str(p))
            checked.append(path)
    # Original R55 full-aperture checkpoint overcharge covers source births
    # through PC10; refined R64 sector union only covers PC9. Never multiply
    # that smaller PC9 bound as though it covered the new PC10 checkpoint.
    full_snapshot=model['checkpoint']['old_checkpoint_new_bytes']+model['checkpoint']['components']['R64_source_contract_and_lineage_copies_bytes']
    full_snapshot+=sum((ROOT/p).stat().st_size for p in source if 'r66' in p)
    checkpoint_floor=11*full_snapshot
    old_checkpoint=model['checkpoint_new_bytes']
    disk_floor=sum(model[k] for k in ('journal_new_bytes','other_new_bytes'))+checkpoint_floor
    record=dict(schema='DS_HBM_REMOTE_ATOMIC_RELAUNCH_PLAN_R66',status='FROZEN_SOURCE_PREPARATION_NOT_LAUNCH_READY',
        allowed_hosts=list(ALLOWED_HOSTS),local_numerical_launch_allowed=False,
        source_sha256=source,original_R64_model_sha256=sha(baseline/'preflight_model.json'),
        ordered_gates=['static preflight ALL enrolled and dynamically loaded helpers',
          'fresh host/output/input/interpreter enrollment and unchanged full-size R64 dual-resource guard',
          'actual producer+cold R64 constructors on admitted remote host',
          'actual PC0 producer; atomic checksum checkpoint; producer exits with journal sealed',
          'fresh process exact cold restore PC0; execute actual PC1; atomic checkpoint',
          'another fresh process exact restore PC1; raw RF/state payload, ownership/version/counters and zero debts verified',
          'review smoke receipts plus aggregate resource proof; resume ACTUAL PC1 checkpoint for PC2..10',
          'atomic snapshot at every retired PC; exit sealed producer and restore into fresh process/journal before next PC'],
        resolved_output_root=None,projection_complete=False,required_disk_bytes=None,required_RAM_bytes=None,
        numerical_GO=False,actual_smoke_executed=False,actual_dual_constructors_executed=False,
        prices=dict(unchanged_R64_disk_floor_bytes=sum(model[k] for k in ('journal_new_bytes','checkpoint_new_bytes','other_new_bytes')),
            unchanged_R64_RAM_floor_bytes=model['RAM']['coexistence_RAM_peak_bytes'],
            retained_full_aperture_snapshot_count=11,full_snapshot_existing_source_envelope_bytes=full_snapshot,
            all_snapshot_disk_component_floor_bytes=checkpoint_floor,
            disk_floor_before_new_process_journals_and_metadata_bytes=disk_floor,
            original_single_snapshot_replaced_bytes=old_checkpoint,
            incremental_snapshot_disk_floor_bytes=checkpoint_floor-old_checkpoint,
            atomic_rename_payload_copy_bytes=0,
            atomic_publication_metadata_and_process_receipts_bytes=None,
            repeated_fresh_journal_dictionary_index_bytes=None,
            remote_input_staging_and_transfer_bytes=None,
            new_capture_and_cold_restore_RAM_bytes=None,
            retained_old_guard_lowered=False),
        checkpoint_contents=dict(actual_data=['cached producer arrays','RF/state/shared addressed sector bytes and validity masks'],
            identity=['exact program/homes/source/checkpoint shard identity','generation and published locations',
              'provider allocation identity/extents/tag generations/serial counters','route/query/history ownership and visibility',
              'compact lifecycle watermarks and capacities','retired PCs/group-completed state'],
            live_debts='refused, never discarded or converted to zero; only quiescent drained boundaries qualify',
            journals='immutable historical identity/evidence only, never restored arithmetic payload',
            checksum='V3 payload/state/observation seals plus atomic publication manifest',
            commit='fsync files and staging dir, sibling rename, fsync parent; incomplete staging preserved'),
        implementation_remaining=['actual per-PC process controller + complete helper/runtime source enrollment',
            'actual PC0-1 producer/fresh restore test runner and independent raw-state exactness receipt',
            'source-sized new journal/index/dictionary, metadata/diagnostics, full snapshot RAM and transfer composition',
            'resolved remote paths + source/data/interpreter identity + fresh host capacity'],
        static_preflight=dict(enrolled_source_count=len(source),compiled_python_files=checked,
            status='PASS_EXACT_ENROLLED_PINS_AND_COMPILE_ONLY',
            all_dynamic_helpers_enrolled=False,actual_constructor_or_smoke_credit=False),
        R58_failed_evidence='preserved unchanged; no checkpoint exists and no oracle/hash restore',
        hardware_qualified=False)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'plan.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    print(json.dumps(record['prices'],indent=2))

if __name__=='__main__':prepare()
