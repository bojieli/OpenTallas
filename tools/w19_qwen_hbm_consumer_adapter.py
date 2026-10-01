#!/usr/bin/env python3
"""Opt-in bit-preserving fixture export and accepted-output trace checker.

No numerical DUT implementation, host epilogue, or physical KV allocator.
JSONL observations must come from accepted DUT outputs, not oracle replay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = 'results/uarch/w19_qwen_hbm_consumer_adapter_preflight.json'
FIXTURES = 'results/rtl/w19_qwen_hbm_vector_kv_fixtures'
INPUTS = dict(raw_qkv_bits=(32, (3072,)),
              qn_bits=(32, (128,)), kn_bits=(32, (128,)),
              cos_bits=(32, (64,)), sin_bits=(32, (64,)))
EXPECTED = dict(raw_qkv_bits=(32, (3072,)), rstd_bits=(32, ()), post_norm_bits=(32, (3072,)),
                q_rstd_bits=(32, (16,)), k_rstd_bits=(32, (4,)),
                q_norm_bits=(32, (16, 128)), k_norm_bits=(32, (4, 128)),
                q_rope_bits=(32, (16, 128)), k_rope_bits=(32, (4, 128)),
                q_bf16_bits=(16, (16, 128)), k_fp8_bits=(8, (4, 128)),
                v_fp8_bits=(8, (4, 128)), k_fp8_fp32_bits=(32, (4, 128)),
                v_fp8_fp32_bits=(32, (4, 128)))
FAULTS = ('none', 'bitflip', 'drop', 'duplicate', 'stale-die')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def validate_pins():
    pre = json.loads((ROOT / PREFLIGHT).read_text())
    for path, digest in pre['source_sha256'].items():
        if sha(ROOT / path) != digest:
            raise ValueError('fixture source drift: ' + path)
    for path, digest in pre['consumer_source_sha256'].items():
        source = subprocess.check_output(['git', 'show', pre['consumer_model_revision'] + ':' + path], cwd=ROOT)
        if hashlib.sha256(source).hexdigest() != digest:
            raise ValueError('consumer model drift: ' + path)
    return pre


def row_identity(row):
    if type(row) is not int or not 0 <= row < 3072:
        raise ValueError('die-local QKV row outside full shape')
    sm, local = divmod(row, 96)
    return dict(global_row=row, sm=sm, slice=sm // 8, bank=sm % 8,
                partition_base=96 * sm, local_row=local)


def head_read_map(die=0):
    # These are numerical projection heads, not physical KV addresses.
    if type(die) is not int or die not in (0, 1):
        raise ValueError('unknown TP die')
    for projection, base, heads in [('q', 0, 16), ('k', 2048, 4), ('v', 2560, 4)]:
        for head in range(heads):
            for dimension in range(128):
                global_index = (die * heads + head) * 128 + dimension
                yield dict(die=die, projection=projection, head=head, dimension=dimension,
                           global_head=die * heads + head, projection_global_index=global_index,
                           global_qkv_index={'q': 0, 'k': 4096, 'v': 5120}[projection] + global_index,
                           **row_identity(base + head * 128 + dimension))


def export(bundle, enabled=False):
    if not enabled:
        raise ValueError('adapter disabled; explicitly enable fixture export')
    pre = validate_pins()
    bundle = Path(bundle)
    bundle.mkdir(exist_ok=False)
    artifacts = []
    for die in (0, 1):
        with np.load(ROOT / FIXTURES / f'd{die}_vector_kv.npz', allow_pickle=False) as data:
            if set(data.files) != set(INPUTS) | set(EXPECTED):
                raise ValueError('unknown or missing fixture field')
            for role, fields in [('inputs', INPUTS), ('expected_only', EXPECTED)]:
                folder = bundle / role
                folder.mkdir(exist_ok=True)
                for name, (width, shape) in fields.items():
                    array = data[name]
                    if array.shape != shape or array.dtype != np.dtype(f'uint{width}'):
                        raise ValueError('fixture shape/type mismatch: ' + name)
                    path = folder / f'd{die}_{name}.hex'
                    with path.open('x') as f:
                        for bits in array.reshape(-1):
                            f.write(f'{int(bits):0{width//4}x}\n')
                    artifacts.append(dict(die=die, boundary=name, role=role,
                        width=width, shape=list(shape), words=array.size,
                        path=str(path.relative_to(bundle)), sha256=sha(path)))
    mapping = bundle / 'head_reads.jsonl'
    with mapping.open('x') as f:
        for die in (0, 1):
            for item in head_read_map(die):
                f.write(json.dumps(item, sort_keys=True) + '\n')
    result = dict(schema='opentallas.w19-qwen-consumer-export.v1',
        status='fixture_export_only', full_token=False, adoption=False,
        fixture_inputs='inputs/ contains raw RTL outputs and checkpoint constants only',
        expected_only='Never feed expected_only/ intermediates into a successor DUT',
        rstd_contract='Actual RTL norm producer owns rstd; fixture scalar is expected-only, never a DUT input',
        physical_KV_addresses=False, token=0, layer=0, position=0,
        preflight_sha256=sha(ROOT / PREFLIGHT), source_sha256=sha(__file__),
        consumer_model_revision=pre['consumer_model_revision'], artifacts=artifacts,
        head_reads=dict(path=mapping.name, sha256=sha(mapping), entries=6144),
        strict_explicit_child_RC=False, missing_explicit_child_RC_cases=61)
    save(bundle / 'manifest.json', result)
    return result


def load_expected(bundle):
    bundle = Path(bundle)
    manifest = json.loads((bundle / 'manifest.json').read_text())
    validate_pins()
    if (manifest['schema'] != 'opentallas.w19-qwen-consumer-export.v1' or
            manifest['preflight_sha256'] != sha(ROOT / PREFLIGHT) or
            manifest['source_sha256'] != sha(__file__)):
        raise ValueError('adapter preflight drift')
    expected = {}
    census = set()
    for a in manifest['artifacts']:
        key = (a['role'], a['die'], a['boundary'])
        if key in census:
            raise ValueError('duplicate artifact')
        census.add(key)
        fields = INPUTS if a['role'] == 'inputs' else EXPECTED if a['role'] == 'expected_only' else {}
        if a['die'] not in (0, 1) or a['boundary'] not in fields:
            raise ValueError('unknown artifact identity')
        width, shape = fields[a['boundary']]
        path = bundle / a['role'] / f"d{a['die']}_{a['boundary']}.hex"
        if (a['path'] != str(path.relative_to(bundle)) or a['width'] != width or
                a['shape'] != list(shape) or a['words'] != int(np.prod(shape)) or sha(path) != a['sha256']):
            raise ValueError('artifact provenance or geometry mismatch')
        words = path.read_text().splitlines()
        if len(words) != a['words'] or any(len(w) != width // 4 for w in words):
            raise ValueError('invalid hex stream length/width')
        values = [int(w, 16) for w in words]
        with np.load(ROOT / FIXTURES / f"d{a['die']}_vector_kv.npz", allow_pickle=False) as original:
            if values != original[a['boundary']].reshape(-1).tolist():
                raise ValueError('export differs from pinned NPZ bits')
        if a['role'] == 'expected_only':
            expected[(a['die'], a['boundary'])] = (width, values)
    required = {(role, d, n) for role, fields in [('inputs', INPUTS), ('expected_only', EXPECTED)]
                for d in (0, 1) for n in fields}
    if census != required:
        raise ValueError('incomplete artifact census')
    canonical_mapping = ''.join(json.dumps(item, sort_keys=True) + '\n'
                               for die in (0, 1) for item in head_read_map(die))
    if (sha(bundle / 'head_reads.jsonl') != manifest['head_reads']['sha256'] or
            (bundle / 'head_reads.jsonl').read_text() != canonical_mapping):
        raise ValueError('head read mapping drift')
    return expected


def observations(records, fault='none'):
    if fault not in FAULTS:
        raise ValueError('unknown fault control')
    for i, original in enumerate(records):
        record = dict(original)
        if i == 0:
            if fault == 'drop':
                continue
            if fault == 'bitflip':
                record['bits'] ^= 1
            if fault == 'stale-die':
                record['die'] = 2
            if fault == 'duplicate':
                yield record
        yield record


def check_records(expected, records, fault='none'):
    offsets = {key: 0 for key in expected}
    last_cycle = {key: -1 for key in expected}
    count = 0
    for record in observations(records, fault):
        required = {'die', 'boundary', 'index', 'bits', 'cycle', 'fault'}
        if set(record) != required or any(type(record[k]) is not int for k in required - {'boundary'}):
            raise ValueError('invalid accepted-output record')
        if not isinstance(record['boundary'], str):
            raise ValueError('invalid boundary identity')
        key = (record['die'], record['boundary'])
        if key not in expected or record['fault'] != 0:
            raise ValueError('unknown boundary/die or DUT fault')
        width, words = expected[key]
        index = record['index']
        if index != offsets[key] or index >= len(words):
            raise ValueError('duplicate, missing, or reordered boundary element')
        if not 0 <= record['bits'] < 1 << width or record['cycle'] < last_cycle[key] or record['cycle'] < 0:
            raise ValueError('width overflow or cycle order fault')
        if record['bits'] != words[index]:
            raise ValueError(f'bit mismatch {key} index{index}')
        offsets[key] += 1
        last_cycle[key] = record['cycle']
        count += 1
    if any(offsets[key] != len(words) for key, (_, words) in expected.items()):
        raise ValueError('incomplete full-head boundary census')
    return dict(status='observed_boundary_bits_exact', elements=count,
                fault_control=fault, full_token=False, runtime_admission=False,
                claim='Checker proves trace bits only; actual RTL origin, shared service, RC and timing require owner receipts')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    ex = sub.add_parser('export'); ex.add_argument('--bundle', type=Path, required=True)
    ex.add_argument('--enable', action='store_true')
    ck = sub.add_parser('check'); ck.add_argument('--bundle', type=Path, required=True)
    ck.add_argument('--trace', type=Path, required=True); ck.add_argument('--out', type=Path, required=True)
    ck.add_argument('--fault', choices=FAULTS, default='none')
    a = ap.parse_args()
    if a.command == 'export':
        result = export(a.bundle, a.enable)
    else:
        try:
            expected = load_expected(a.bundle)
            with a.trace.open() as f:
                result = check_records(expected, (json.loads(line) for line in f), a.fault)
        except (ValueError, KeyError, TypeError) as error:
            save(a.out, dict(status='fail', error=str(error), trace_sha256=sha(a.trace),
                            fault_control=a.fault, full_token=False, runtime_admission=False))
            raise SystemExit(1)
        result.update(trace_sha256=sha(a.trace), manifest_sha256=sha(a.bundle / 'manifest.json'))
        save(a.out, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'artifacts'}, sort_keys=True))


if __name__ == '__main__':
    main()
