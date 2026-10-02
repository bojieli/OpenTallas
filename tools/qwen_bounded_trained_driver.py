#!/usr/bin/env python3
"""Source-pinned launch join for all1737 Qwen PCs and immutable/mutable storage.

Uses the reviewed bounded interpreter and Goodall's actual trained driver.
No operator arithmetic, checkpoint conversion or numerical oracle is added.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import qwen_trained_byte_provider as B
import qwen_trained_native_run as G
import h3_qwen_bounded_native as N

ROOT = B.ROOT
BOUNDED_MODULE = 'tools/h3_qwen_bounded_native.py'
BOUNDED_SHA256 = '282e57ab97f2dcdd0205b6f4e11ec189b669e3cc48548fab5f6d3c373d63c32b'
CANONICAL_NATIVE_SHA256 = 'ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354'
RELOCATED_ARTIFACT = 'results/uarch/h3_qwen_complete_native_20261002/bounded_r2/Qwen_tiled.json.gz'
MANIFEST = 'results/uarch/h3_qwen_complete_native_20261002/bounded_r2/manifest.json'
EXTRA_PINS = ['tools/qwen_bounded_trained_driver.py', 'tools/qwen_trained_native_run.py',
              'tools/qwen_trained_byte_provider.py', 'tools/qwen_hbm_complete_reference.py',
              'tools/qwen_hbm_complete_executor.py', 'tools/qwen3_deployment_quality.py',
              B.ARTIFACT, RELOCATED_ARTIFACT, MANIFEST,
              'compiler/models/qwen3-8b/checkpoint_source.json']


def canonical_identity(native):
    return hashlib.sha256(B.canonical(native)).hexdigest()


def storage_scope(native):
    extents = B.extents(native); all_refs = B.refs(native)
    immutable = B.immutable_refs(native); mutable = all_refs-immutable
    for op in native['operations']:
        refs = {r['provider_ref'] for r in op['provider_binding']['external_providers']}
        if op['opcode'] in ('KV_WRITE', 'KV_FENCE', 'KV_READ'):
            if not refs or refs-mutable: raise ValueError('KV refs require mutable native storage')
        elif refs & mutable: raise ValueError('mutable ref routed as immutable tile')
    return dict(immutable_checkpoint_refs=sorted(immutable), mutable_runtime_refs=sorted(mutable),
                immutable_count=len(immutable), mutable_count=len(mutable),
                mutable_extents={ref:dict(base=extents[ref]['base'], bytes=extents[ref]['bytes'],
                                         role=extents[ref]['role']) for ref in sorted(mutable)},
                mutable_memory_class='BoundKVStorage', immutable_backend_class='TrainedByteBackend',
                mutable_checkpoint_images_required=False, reader_completion_order=['SCORES','PV'])


def bind_runtime(native, backend):
    """Concrete constructor shared with trained launch preflight and VM tests."""
    scope = storage_scope(native)
    if set(backend.manifest['images']) != set(scope['immutable_checkpoint_refs']):
        raise ValueError('checkpoint image set must exclude mutable KV/state')
    machine = N.TiledMachine(native, N.HBMByteTileProvider(backend))
    if not isinstance(machine.memory, N.BoundKVStorage): raise ValueError('mutable KV storage binding')
    if machine.memory.pending or machine.memory.leases or machine.memory.published:
        raise ValueError('initial mutable KV must be unpublished')
    return machine


def readiness():
    if B.sha(ROOT/BOUNDED_MODULE) != BOUNDED_SHA256: raise ValueError('bounded module source pin')
    manifest = json.loads((ROOT/MANIFEST).read_text())
    for path, want in manifest['source_sha256'].items():
        if B.sha(ROOT/path) != want: raise ValueError('bounded dependency source pin: '+path)
    if B.sha(ROOT/RELOCATED_ARTIFACT) != manifest['artifact_sha256']:
        raise ValueError('relocated artifact byte pin')
    native = B.native()
    with gzip.open(ROOT/RELOCATED_ARTIFACT,'rt') as stream: relocated = json.load(stream)
    if canonical_identity(native) != CANONICAL_NATIVE_SHA256 or canonical_identity(relocated) != CANONICAL_NATIVE_SHA256:
        raise ValueError('producer and relocated native content identity')
    p = native['source_program']; scope = storage_scope(native)
    if (len(native['operations']),len(native['coverage']['families']),p['config']['num_hidden_layers'],
            len(p['weight_descriptors']),scope['immutable_count'],scope['mutable_count']) != (1737,21,36,290,586,146):
        raise ValueError('complete trained native program/scope required')
    # Goodall's repaired inventory admits all code descriptors while scales
    # absent from runtime consumption remain outside checkpoint manifests.
    inventory = B.matrix_inventory(native)
    sources = dict(manifest['source_sha256'])
    sources.update({path:B.sha(ROOT/path) for path in EXTRA_PINS})
    return dict(schema='opentallas.Qwen.bounded-trained-driver-ready.v1',
                status='DRIVER_READY_REQUIRES_COMPLETE_IMAGES_AND_FRESH_RESOURCE_GO',
                bounded_module=BOUNDED_MODULE, bounded_module_sha256=BOUNDED_SHA256,
                producer_native_artifact=B.ARTIFACT, relocated_native_artifact=RELOCATED_ARTIFACT,
                canonical_native_sha256=CANONICAL_NATIVE_SHA256, source_sha256=sources,
                PCs=1737,classes=21,layers=36,matrix_descriptors=290,
                matrix_inventory=inventory, storage_scope=scope,
                readiness_supersedes='Historical interface_handoff/prepare pending-module claims; historical files retained unchanged',
                executor='qwen_trained_native_run.run with exact relocated module path',
                commands=dict(execute=['python','tools/qwen_bounded_trained_driver.py','--images','<complete-image-root>',
                    '--out','<fresh-execution-root>','--admission','<fresh-admission.json>',
                    '--go-commit','<committed-GO>','--token','9707']),
                RF_vectors=32,shared_reserved_bytes=17408,additional_native_HBM_bytes=0,
                r22_augmentation_applied=False,diagnostic_ticks_added_to_existing_intervals=False,
                full_checkpoint_execution_performed=False,hardware_or_timing_credit=False)


def run(images, out, admission, go_commit, token=9707):
    report = readiness()
    for path,want in report['source_sha256'].items():
        if admission.get('source_sha256',{}).get(path) != want:
            raise ValueError('fresh GO missing exact driver/dependency pin: '+path)
    G.validate_admission(admission,go_commit)
    if Path(out).exists(): raise ValueError('fresh execution output required')
    native = B.native(); backend = B.TrainedByteBackend(images,native)
    try:
        machine = bind_runtime(native,backend)
        del machine # no full cache arrays or numerical execution in preflight
    finally:
        backend.close()
    try:
        # The actual driver selects this exact bounded module, runs all PCs,
        # captures published outputs, then compares independently after retire.
        return G.run(images,out,admission,go_commit,Path(BOUNDED_MODULE),token)
    finally:
        if Path(out).is_dir():
            with (Path(out)/'bounded_driver_join.json').open('xb') as stream:
                stream.write(B.canonical(report))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready-out',type=Path)
    parser.add_argument('--images',type=Path);parser.add_argument('--out',type=Path)
    parser.add_argument('--admission',type=Path);parser.add_argument('--go-commit')
    parser.add_argument('--token',type=int,default=9707)
    args=parser.parse_args()
    if args.ready_out:
        with args.ready_out.open('xb') as stream:stream.write(B.canonical(readiness()))
    elif all((args.images,args.out,args.admission,args.go_commit)):
        print(json.dumps(run(args.images,args.out,json.loads(args.admission.read_text()),args.go_commit,args.token),sort_keys=True))
    else: parser.error('provide --ready-out or all execution/admission arguments')
