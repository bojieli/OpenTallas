"""Read-only dual-source preparation for released-checkpoint KV operator campaign.

This prepares exact identities and storage. It never executes a token/operator,
creates a service, admits a fleet lease, or relaxes original worker ROOT guards.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE='870c5fe581b768df28dd2998b2d0aecc24510c23'
ARTIFACT='results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz'
ADDONS=['qwen_kv_observation_adapter.py','qwen_kv_observation_verify.py','qwen_kv_observed_native.py',
    'qwen_kv_reference_u8.py','qwen_kv_released_operator_gate.py','qwen_kv_campaign_prepare.py','qwen_kv_campaign_run.py','qwen_kv_campaign_launcher.py','qwen_native_terminal_replay.py']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(root):
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=root):raise ValueError('source root must remain clean')
    return commit


def prepare(source_root, additive_root, archive, checkpoint, checkpoint_metadata=None):
    source_root=Path(source_root).resolve();additive_root=Path(additive_root).resolve();archive=Path(archive).resolve();checkpoint=Path(checkpoint).resolve()
    if identity(source_root)!=SOURCE:raise ValueError('unchanged original source root commit')
    additive_commit=identity(additive_root)
    go=json.loads((archive/'GO.json').read_text())
    for path,want in go['source_sha256'].items():
        if Path(path).is_absolute():
            data=archive/Path(path).name
        else:data=source_root/path
        if sha(data)!=want:raise ValueError('original admitted source frame '+path)
    native=json.load(gzip.open(source_root/ARTIFACT,'rt'))
    lock=json.loads((source_root/'compiler/models/qwen3-8b/checkpoint_source.json').read_text())
    metadata=Path(checkpoint_metadata).resolve() if checkpoint_metadata is not None else checkpoint
    for name in ('config.json','model.safetensors.index.json'):
        want=next(row for row in lock['expected_files']if row['path']==name)
        if sha(metadata/name)!=want['sha256']:raise ValueError('locked checkpoint metadata')
    terminal=json.loads((archive/'native/terminal.json').read_text())
    if terminal['native']['PCs']!=1737 or terminal['verdict']!='PASS_TRAINED_NATIVE_TOKEN_POSTCHECKED':raise ValueError('qualified preceding token')
    comparisons=json.loads((archive/'native/post_execution_comparisons.json').read_text())
    if len(comparisons)!=39 or any(row[k] for row in comparisons for k in ('bit_mismatches','actual_nonfinite','reference_nonfinite')):raise ValueError('independent predecessor comparisons')
    captures={str(path.resolve()):sha(path)for path in (archive/'native').glob('*.npy')}
    if len(captures)!=39:raise ValueError('exact39captures')
    return dict(schema='opentallas.Qwen.KV.operator-campaign-preparation.v1',status='PREPARED_REQUIRES_FRESH_SOURCE_GO_AND_FLEET_ADMISSION',
        original_source_root=str(source_root),original_source_commit=SOURCE,additive_source_root=str(additive_root),additive_source_commit=additive_commit,
        additive_source_sha256={str((additive_root/'tools'/name).resolve()):sha(additive_root/'tools'/name)for name in ADDONS},
        original_source_sha256=go['source_sha256'],checkpoint_revision=lock['revision'],checkpoint_lock_sha256=sha(source_root/'compiler/models/qwen3-8b/checkpoint_source.json'),
        checkpoint_snapshot=str(checkpoint),checkpoint_metadata_projection_used=metadata!=checkpoint,
        checkpoint_metadata_sha256={name:sha(metadata/name)for name in ('config.json','model.safetensors.index.json')},checkpoint_shards={row['path']:row for row in lock['expected_files']if row['path'].endswith('.safetensors')},
        native_sha256=hashlib.sha256((json.dumps(native,sort_keys=True,indent=2)+'\n').encode()).hexdigest(),capture_file_sha256=captures,
        native_terminal_sha256=sha(archive/'native/terminal.json'),comparison_sha256=sha(archive/'native/post_execution_comparisons.json'),
        storage=dict(groups=72,events=432,payload_U8_bytes=73728,committed_read_final_address_records_bytes=1990656,packed_state_snapshot_bytes=75008,
            independent_reference_address_records_bytes=663552,independent_prepack_FP32_bytes=294912,source_QKV_code_bytes_recomputed=905969664,
            JSON_and_Python_inventory='measure; addressed entries bounded73728, evententries432',charged_native_RF_vectors=32,charged_native_shared_bytes=17408,extra_native_HBM_bytes=0),
        resource_model=dict(previous_complete_run_max_sampled_memory_current_bytes=2762838016,
            maximum_checkpoint_file_cache_bytes=sum(row['size_bytes']for row in lock['expected_files']if row['path'].endswith('.safetensors')),
            proposed_memory_reservation_bytes=32*1024**3,
            memory_limit=None,swap_limit=None,OOM_forced_stop=False,
            reservation_basis='full16.38GB checkpoint cache plus measured2.76GB heap/charge and bounded QKV/tile/observation inventory; fresh hostreserve required',
            CPU_workers='fleetadmitted; priorunattributed28thread placement prevents assuming disjoint8worker slot',
            wall_limit=None,CPU_time_limit=None,FSIZE='unlimited',AS='unlimited',disk_guard='fresh fleetcapacityreserve plus pricedimages/receipts; no oldpilot quota'),
        phases=['strict terminal replay before trusting captures','independent releasedcheckpoint QKV/prepack/U8 reference only','actual FP8pack/BoundKVStorage writepublish/read/state operator gate','offline U8/readhash/state/event mutants and causalcalendarpacket'],
        native_decode=False,production_SCORES_PV_arithmetic=False,production_lifecycle_qualified=False,
        original_terminal_KV_lifecycle='UNKNOWN_NOT_CAPTURED',actual_RTL=False,physical_credit=False,rate_credit=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','additive-root','archive','checkpoint'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--checkpoint-metadata',type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.source_root,a.additive_root,a.archive,a.checkpoint,a.checkpoint_metadata),indent=2))
