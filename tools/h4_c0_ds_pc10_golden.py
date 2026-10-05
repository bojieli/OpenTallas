"""Independent PC10 group reassembly from committed golden PC9 parts.

No checkpoint or native execution is repeated. The original golden pairwise
tree and its final BF16 round produce one 8192-word version replicated to96
ranks. Source/native/home metadata only binds identities; it never supplies
arithmetic. Expected bytes are a witness, never executor stimuli.
"""
import argparse
import gzip
import hashlib
import json
import os
import time
from pathlib import Path
import numpy as np
import hdc_golden_v41 as V

NATIVE = 'c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264'
REFERENCE = '91c803a93df18e011cd7ee6c5e0a84c8fc091136718ca329e5f2928349b3f342'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    p = Path(path)
    raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def assemble(parts):
    if set(parts) != set(range(64)):
        raise ValueError('exact64 independent source head contributors required')
    for a in parts.values():
        if a.dtype != np.dtype('<f4') or a.shape != (1024,) or not np.all(np.isfinite(a)):
            raise ValueError('exact finite source1024-word F32 part')
    # This is the independent golden's pairwise tree, not a compiler/kernel
    # callback and not a sequential accumulation or sum across ranks96.
    groups = [V.split_sum_parts([parts[8 * group + j] for j in range(8)])
              for group in range(8)]
    result = np.ascontiguousarray(V.to_bf16(np.concatenate(groups)), dtype='<f4')
    if not np.all(np.isfinite(result)):
        raise ValueError('nonfinite independent golden result')
    return result


def generate(reference_path, native_path, homes_path, binding_proof_path, out):
    out = Path(out)
    if out.exists():
        raise ValueError('fresh independent PC10 evidence required')
    out.mkdir(parents=True)
    record = dict(status='GENERATING_INDEPENDENT_PC10_GOLDEN', pid=os.getpid(),
                  start_ns=time.time_ns(), resource_caps_injected=False,
                  golden_stimuli_in_executor=False, hardware_qualified=False,
                  full_token_qualified=False)
    def save():
        (out / 'record.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    save()
    try:
        if sha(reference_path) != REFERENCE or sha(native_path) != NATIVE:
            raise ValueError('immutable independent PC1-9/currentnative pins')
        reference = load(reference_path)
        native = load(native_path)
        homes = load(homes_path)['homes']
        proof = load(binding_proof_path)
        if proof['original_native_sha256'] != NATIVE or proof['original_homes_sha256'] != sha(homes_path) or proof['independent_reference_sha256'] != REFERENCE or proof['arithmetic_and_provider_views_unchanged'] is not True:
            raise ValueError('R41 exact source/home/arithmetic binding proof')
        for path, digest in reference['reference_source_sha256'].items():
            if sha(path) != digest:
                raise ValueError('independent upstream golden source changed')
        producer = native['instructions'][9]
        op = native['instructions'][10]
        if (producer['family'], op['family']) != ('wo_a_part', 'all_reduce') or len(producer['writes']) != 1 or len(op['writes']) != 1:
            raise ValueError('exact actual PC9 producer/PC10 output family')
        source_version = producer['writes'][0]['version']
        if source_version not in [r['version'] for r in op['reads']]:
            raise ValueError('actual PC10 source version')
        ranks = [r['rank'] for r in op['rank_bindings'] if not r.get('empty_owned_extent')]
        if ranks != list(range(96)):
            raise ValueError('complete actual96 destination rank set')
        parts = {}
        inputs = []
        for row in reference['expectations']:
            if row['PC'] != 9:
                continue
            if row['version'] != source_version or row['rank'] in parts or row['field'] != 'data':
                raise ValueError('duplicate or wrong independent PC9 producer identity')
            path = Path(reference_path).parent / row['path']
            a = np.load(path, allow_pickle=False)
            if sha(path) != row['file_sha256'] or hashlib.sha256(a.tobytes()).hexdigest() != row['payload_sha256'] or list(a.shape) != row['shape'] or a.dtype.str != row['dtype']:
                raise ValueError('upstream independent PC9 payload pin')
            parts[row['rank']] = a
            inputs.append(dict(PC=9, rank=row['rank'], version=source_version,
                generation=row['generation'], payload_sha256=row['payload_sha256'],
                file_sha256=row['file_sha256'], path=str(path)))
        result = assemble(parts)
        np.save(out / 'golden_z.npy', result, allow_pickle=False)
        payload = hashlib.sha256(result.tobytes()).hexdigest()
        write = op['writes'][0]
        expectations = []
        for rank in ranks:
            indices = [i for i in write['home_indices'] if rank in homes[i]['rank_group']]
            if not indices or any(homes[i]['version'] != write['version'] for i in indices):
                raise ValueError('actual PC10 destination home/version binding')
            expectations.append(dict(PC=10, version=write['version'], rank=rank,
                generation=reference['expectations'][0]['generation'], field='data',
                shape=[8192], dtype='<f4', home_indices=indices,
                payload_sha256=payload, path='golden_z.npy', file_sha256=sha(out / 'golden_z.npy')))
        source_pins = {str(Path(p).resolve()): sha(p) for p in
                       [__file__, V.__file__, Path(V.__file__).with_name('hdc_golden.py')]}
        contract = dict(status='INDEPENDENT_PC10_EXPECTED_OUTPUTS_COMMITTED',
            PCs=[10], expectations=expectations, output_count=96,
            parent_reference_sha256=REFERENCE, parent_reference_path=str(reference_path),
            native_program_sha256=NATIVE, original_homes_sha256=sha(homes_path),
            R41_binding_proof_sha256=sha(binding_proof_path),
            R41_effective_native_content_sha256=proof['effective_native_content_sha256'],
            input_manifest_sha256=reference['input_manifest_sha256'],
            checkpoint_revision=reference['checkpoint_revision'],
            checkpoint_index_sha256=reference['checkpoint_index_sha256'],
            checkpoint_config_sha256=reference['checkpoint_config_sha256'],
            token_history_sha256=reference['token_history_sha256'],
            entering_window_payload_sha256=reference['entering_window_payload_sha256'],
            independently_derived_PC9_inputs=inputs, reference_source_sha256=source_pins,
            original_tree='((0+1)+(2+3))+((4+5)+(6+7)); j0..7 from ranks8*group+j',
            final_rounding='single original BF16 RNE after FP32 group tree; output remains F32 storing BF16 values',
            flatten='group-major eight1024-word groups; replicated8192words to each96rank',
            post_PC10_state=dict(version=write['version'], future_readers=[o['pc'] for o in native['instructions'][11:] if write['version'] in [r['version'] for r in o['reads']]],
                source_parts_release_only_after_all_PC10_rank_consumers_and_reverse_retirement=True),
            comparison_rule='all96(PC,version,rank,generation,field) source-bound identities; exact shape,dtype,home and payload-byte SHA; missing or duplicate output FAIL',
            observes_only=True, native_arithmetic_imported=False,
            actual_provider_execution_compared=False, hardware_qualified=False,
            full_token_qualified=False)
        (out / 'expected_outputs.json').write_text(json.dumps(contract, sort_keys=True, indent=2) + '\n')
        record.update(status='PASS_INDEPENDENT_PC10_GOLDEN_GENERATED_NOT_YET_COMPARED',
            source_parts=64, output_count=96, output_words_per_rank=8192,
            output_payload_sha256=payload, expected_outputs_sha256=sha(out / 'expected_outputs.json'))
    except Exception as error:
        record.update(status='FAIL_INDEPENDENT_PC10_GOLDEN_PRESERVED', reason=str(error), exception_type=type(error).__name__)
        raise
    finally:
        record['end_ns'] = time.time_ns()
        save()
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('reference', 'native', 'homes', 'binding_proof', 'out'):
        p.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(generate(a.reference, a.native, a.homes, a.binding_proof, a.out), sort_keys=True))
