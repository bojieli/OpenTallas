#!/usr/bin/env python3
"""Catalogue immutable DSROM safetensors headers, never read tensor payloads.

The stored dtype/shape is not a logical FP4 shape or a physical ROM image.
Raw-header SHA hashes JSON bytes (including padding). Framed-header SHA hashes
LE64(header length) followed by those same bytes; neither hashes tensor data.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess

REVISION = 'dba1be0a40aa45a94ad051997016db3960a90277'
INDEX_SHA = '74b0686a3d2891980d5e303251b075a3bccae2c2ff650747db2620a649b98fa8'
CACHE_COMMIT = '8c44707ebe238ecd3d7e8cfe29920e79c33a7cf7'
CACHE_ROOT = 'results/quality/w16_w19_nonsm_residency_20261001'
DEFAULT_OUT = 'results/quality/w16_w17_checkpoint_header_catalogue_20261001'
EXPERT = re.compile(r'^layers\.(\d+)\.ffn\.experts\.(\d+)\.(w[123])\.(weight|scale)$')
DTYPE_BYTES = {'BOOL': 1, 'U8': 1, 'I8': 1, 'F8_E4M3': 1, 'F8_E5M2': 1,
               'F8_E8M0': 1, 'I16': 2, 'U16': 2, 'F16': 2, 'BF16': 2,
               'I32': 4, 'U32': 4, 'F32': 4, 'I64': 8, 'U64': 8, 'F64': 8}
ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'duplicate JSON key: ' + key)
        out[key] = value
    return out


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique_object)


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + '\n')


def read_header(path):
    """Use exact pread ranges; a BufferedReader could prefetch payload bytes."""
    fd = os.open(path, os.O_RDONLY)
    try:
        before = os.fstat(fd)
        prefix = os.pread(fd, 8, 0)
        require(len(prefix) == 8, 'short header length: ' + str(path))
        length = struct.unpack('<Q', prefix)[0]
        require(2 <= length <= 16 * 1024**2, 'unbounded/invalid header length')
        require(8 + length <= before.st_size, 'header extends outside file')
        raw = os.pread(fd, length, 8)
        require(len(raw) == length, 'short raw header')
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                'checkpoint changed during header read')
        return prefix, raw, {
            'file_bytes': after.st_size, 'mtime_ns': after.st_mtime_ns,
            'resolved_blob_path': str(path.resolve()),
            'blob_id_from_cache_path_not_rehashed': path.resolve().name,
            'checkpoint_bytes_read': 8 + length,
        }
    finally:
        os.close(fd)


def validate_header(header, shard, index, data_base, file_bytes):
    require(isinstance(header, dict), 'header is not an object')
    intervals = []
    for key, entry in header.items():
        if key == '__metadata__':
            continue
        require(index.get(key) == shard, 'index/header mapping mismatch: ' + key)
        require(isinstance(entry, dict), 'invalid tensor entry: ' + key)
        dtype, shape, offsets = entry.get('dtype'), entry.get('shape'), entry.get('data_offsets')
        require(dtype in DTYPE_BYTES, 'unsupported stored dtype: ' + str(dtype))
        require(isinstance(shape, list) and all(type(n) is int and n >= 0 for n in shape),
                'invalid stored shape: ' + key)
        require(isinstance(offsets, list) and len(offsets) == 2
                and all(type(n) is int for n in offsets), 'invalid data offsets: ' + key)
        low, high = offsets
        require(0 <= low <= high <= file_bytes - data_base, 'offset outside payload: ' + key)
        require(high - low == math.prod(shape) * DTYPE_BYTES[dtype],
                'stored dtype/shape/span disagreement: ' + key)
        intervals.append((low, high, key))
    position = 0
    for low, high, key in sorted(intervals):
        require(low == position, 'overlap/gap in payload spans: ' + key)
        position = high
    require(position == file_bytes - data_base, 'unaccounted file payload extent: ' + shard)
    return {'tensor_count': len(intervals), 'index_mapping_exact': True,
            'stored_dtype_shape_span_valid': True, 'offsets_in_file': True,
            'payload_spans_nonoverlapping_and_contiguous': True,
            'payload_extent_bytes_from_stat_and_offsets': position}


def stored_record(shard, entry, data_base):
    low, high = entry['data_offsets']
    return {'shard': shard, 'dtype': entry['dtype'], 'stored_shape': entry['shape'],
            'data_offsets': entry['data_offsets'], 'stored_bytes': high - low,
            'data_base': data_base, 'absolute_file_offsets': [data_base + low, data_base + high]}


def coverage(index, headers, bindings):
    expected = {f'layers.{layer}.ffn.experts.{expert}.{matrix}.{part}'
                for layer in range(40) for expert in range(384)
                for matrix in ('w1', 'w3', 'w2') for part in ('weight', 'scale')}
    actual = {key for key in index if EXPERT.fullmatch(key)}
    require(actual == expected,
            f'expert coverage mismatch: missing={len(expected - actual)}, extra={len(actual - expected)}')
    tensors = {}
    for key in sorted(expected):
        shard = index[key]
        require(key in headers[shard], 'expert absent from actual header: ' + key)
        tensors[key] = stored_record(shard, headers[shard][key], bindings[shard]['data_base'])
    pairs = {key: key[:-len('weight')] + 'scale' for key in sorted(expected) if key.endswith('.weight')}
    require(len(pairs) == 46080 and len(set(pairs.values())) == 46080,
            'weight/scale pairing not bijective')
    require(set(pairs.values()) == {key for key in expected if key.endswith('.scale')},
            'unpaired scale entry')
    per_layer = []
    signatures = Counter()
    for layer in range(40):
        prefix = f'layers.{layer}.ffn.experts.'
        weights = [key for key in pairs if key.startswith(prefix)]
        require(len(weights) == 384 * 3, 'incomplete layer: ' + str(layer))
        per_layer.append({'layer': layer, 'experts': 384, 'weight_count': len(weights),
                          'scale_count': len(weights)})
    for key, scale_key in pairs.items():
        matrix = EXPERT.fullmatch(key).group(3)
        w, s = tensors[key], tensors[scale_key]
        signatures[(matrix, w['dtype'], tuple(w['stored_shape']), s['dtype'], tuple(s['stored_shape']))] += 1
    observed = [{'matrix': k[0], 'weight_stored_dtype': k[1], 'weight_stored_shape': list(k[2]),
                 'scale_stored_dtype': k[3], 'scale_stored_shape': list(k[4]), 'pair_count': v}
                for k, v in sorted(signatures.items())]
    return tensors, pairs, {
        'layers': 40, 'experts_per_layer': 384, 'matrices_per_expert': ['w1', 'w3', 'w2'],
        'weight_count': len(pairs), 'scale_count': len(pairs), 'tensor_count': len(tensors),
        'missing_keys': [], 'extra_routed_expert_keys': [], 'unique_keys': True,
        'scale_pairing_bijective': True, 'per_layer': per_layer,
        'weight_stored_bytes_from_offsets': sum(tensors[key]['stored_bytes'] for key in pairs),
        'scale_stored_bytes_from_offsets': sum(tensors[key]['stored_bytes'] for key in pairs.values()),
        'observed_stored_signatures': observed,
    }


def git_blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def reuse_cache(index_sha, headers, bindings):
    paths = [CACHE_ROOT + '/non_SM_source_inventory.json', CACHE_ROOT + '/selected_headers.json']
    raw = {path: git_blob(CACHE_COMMIT, path) for path in paths}
    inv, selected = [parse(raw[path]) for path in paths]
    require(inv['checkpoint_revision'] == REVISION and inv['checkpoint_index_sha256'] == index_sha
            and selected['index_sha256'] == index_sha, 'existing immutable cache checkpoint drift')
    for shard, h in inv['header_bindings'].items():
        b = bindings[shard]
        require(h['sha256'] == b['framed_header_sha256'] and h['header_bytes'] == b['header_bytes'],
                'existing framed header pin drift: ' + shard)
        require(inv['shards'][shard]['bytes'] == b['file_bytes']
                and inv['shards'][shard]['blob'] == b['blob_id_from_cache_path_not_rehashed'],
                'existing shard identity drift: ' + shard)
    for shard, h in selected['headers'].items():
        b = bindings[shard]
        require(h['header_sha256'] == b['raw_header_sha256'] and h['header_bytes'] == b['header_bytes'],
                'existing raw header pin drift: ' + shard)
    for item in inv['items']:
        e = headers[item['shard']][item['tensor']]
        require((e['dtype'], e['shape'], e['data_offsets'], e['data_offsets'][1] - e['data_offsets'][0])
                == (item['dtype'], item['shape'], item['data_offsets'], item['stored_bytes']),
                'existing selected tensor drift: ' + item['tensor'])
    for key, item in selected['selected_tensors'].items():
        e = headers[item['shard']][key]
        require(e['dtype'] == item['dtype'] and e['shape'] == item['shape']
                and e['data_offsets'] == item['data_offsets'], 'selected header drift: ' + key)
    return {'commit': CACHE_COMMIT, 'inputs': {path: sha(data) for path, data in raw.items()},
            'index_sha256_matched': True, 'framed_header_pins_matched': len(inv['header_bindings']),
            'raw_header_pins_matched': len(selected['headers']),
            'non_SM_items_matched': len(inv['items']), 'selected_tensors_matched': len(selected['selected_tensors']),
            'full_raw_header_cache_available': False,
            'reuse': 'Reuse immutable cached identities/selected metadata as crosschecks; read missing complete header bytes only.'}


def build(snapshot, out):
    require(snapshot.name == REVISION, 'wrong immutable checkpoint revision')
    config_raw = (snapshot / 'config.json').read_bytes()
    index_raw = (snapshot / 'model.safetensors.index.json').read_bytes()
    config, index_doc = parse(config_raw), parse(index_raw)
    index = index_doc['weight_map']
    require(sha(index_raw) == INDEX_SHA, 'checkpoint index SHA mismatch')
    require(config['text_config']['num_hidden_layers'] == 40
            and config['text_config']['n_routed_experts'] == 384, 'config coverage disagreement')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'headers').mkdir()
    (out / 'config.json').write_bytes(config_raw)
    (out / 'model.safetensors.index.json').write_bytes(index_raw)
    headers, bindings, seen = {}, {}, set()
    for shard in sorted(set(index.values())):
        require(isinstance(shard, str) and Path(shard).name == shard and shard.endswith('.safetensors'),
                'invalid shard name')
        prefix, raw, identity = read_header(snapshot / shard)
        header = parse(raw)
        data_base = len(prefix) + len(raw)
        valid = validate_header(header, shard, index, data_base, identity['file_bytes'])
        keys = set(header) - {'__metadata__'}
        require(not keys & seen, 'tensor appears in multiple shard headers')
        seen |= keys
        name = 'headers/' + shard + '.header.json'
        (out / name).write_bytes(raw)
        headers[shard] = header
        bindings[shard] = dict(identity, raw_header_path=name, header_bytes=len(raw),
                               length_prefix_encoding='uint64_little_endian', data_base=data_base,
                               raw_header_sha256=sha(raw), framed_header_sha256=sha(prefix + raw),
                               validation=valid, full_blob_rehashed=False)
    require(seen == set(index), 'complete index/header key set disagreement')
    tensors, pairs, complete = coverage(index, headers, bindings)
    reused = reuse_cache(sha(index_raw), headers, bindings)
    save_json(out / 'reused_cache_provenance.json', reused)
    save_json(out / 'coverage.json', complete)
    questions = {
        'scope': 'Stored metadata evidence only; packing semantics remain unqualified.',
        'observed_stored_signatures': complete['observed_stored_signatures'],
        'checkpoint_quantization_config_verbatim': config['quantization_config'],
        'questions_for_Ram_and_Godel': [
            'Which source-pinned packing generator reinterprets stored I8 byte bit patterns, and what is the exact FP4 nibble order? No U8 reinterpretation is certified by the header.',
            'How does the generator bind stored-shape axes and F8_E8M0 scale keys to logical expert operands and scale application order? Config expert_dtype=fp4 is not a packing proof.',
            'Which immutable packing-generator and segment-order refs bind byte order, physical word boundaries, padding, replication and resident placement?',
            'Where is the exact generator replay/equivalence evidence that permits changing the existing full physical-word accounting?',
        ],
        'packing_generator_bound': False, 'segment_order_bound': False,
        'logical_tensor_shape_inferred': False, 'physical_ROM_words_inferred': False,
        'retain_existing_full_physical_words_until_packing_generator_bound': True,
    }
    save_json(out / 'dtype_packing_questions.json', questions)
    catalogue = {
        'schema': 'opentallas.dsrom.actual-checkpoint-header-catalogue.v1',
        'status': 'PASS_AT_HEADER_METADATA_SCOPE', 'snapshot': str(snapshot),
        'checkpoint_revision': REVISION, 'source_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'generator_path': 'tools/dsrom_checkpoint_header_catalogue.py',
        'generator_sha256': sha(Path(__file__).read_bytes()),
        'config_path': 'config.json', 'config_sha256': sha(config_raw),
        'index_path': 'model.safetensors.index.json', 'index_sha256': sha(index_raw),
        'index_tensor_count': len(index), 'index_shard_count': len(bindings),
        'hash_domains': {'raw_header_sha256': 'SHA256(exact JSON header bytes including padding)',
                        'framed_header_sha256': 'SHA256(LE64(header_bytes) || exact JSON header bytes)',
                        'config_and_index_sha256': 'SHA256(exact metadata file bytes)'},
        'data_offsets_convention': 'Relative to data_base=8+header_bytes; absolute_file_offsets are file positions, never ROM addresses.',
        'shards': bindings, 'coverage': complete, 'tensors': tensors, 'weight_scale_pairs': pairs,
        'reused_cache_provenance': reused,
        'metadata_IO': {'safetensors_bytes_read': sum(b['checkpoint_bytes_read'] for b in bindings.values()),
                        'tensor_payload_bytes_requested': 0, 'numeric_tensor_payload_loaded': False,
                        'full_weight_sha_performed': False, 'config_and_index_bytes_read': len(config_raw) + len(index_raw)},
        'packing_generator_bound': False, 'segment_order_bound': False,
        'logical_tensor_shape_inferred': False, 'physical_ROM_words_inferred': False,
        'physical_capacity_credit': False, 'admission_claim': False, 'adopt': False,
        'retain_existing_full_physical_words_until_packing_generator_bound': True,
    }
    save_json(out / 'catalogue.json', catalogue)
    verify_output(out)
    files = sorted(p for p in out.rglob('*') if p.is_file())
    (out / 'SHA256SUMS').write_text(''.join(sha(p.read_bytes()) + '  ' + str(p.relative_to(out)) + '\n' for p in files))
    return catalogue


def verify_output(out):
    c = parse((out / 'catalogue.json').read_bytes())
    config_raw, index_raw = [(out / c[k]).read_bytes() for k in ('config_path', 'index_path')]
    require(sha(config_raw) == c['config_sha256'] and sha(index_raw) == c['index_sha256'] == INDEX_SHA,
            'copied metadata drift')
    index = parse(index_raw)['weight_map']
    headers, seen = {}, set()
    for shard, b in c['shards'].items():
        raw = (out / b['raw_header_path']).read_bytes()
        require(len(raw) == b['header_bytes'] and b['data_base'] == len(raw) + 8,
                'raw header length/data base drift')
        require(sha(raw) == b['raw_header_sha256']
                and sha(struct.pack('<Q', len(raw)) + raw) == b['framed_header_sha256'], 'header hash domain drift')
        header = parse(raw)
        require(validate_header(header, shard, index, b['data_base'], b['file_bytes']) == b['validation'],
                'recorded offset validation drift')
        keys = set(header) - {'__metadata__'}
        require(not keys & seen, 'duplicate archived header keys')
        seen |= keys
        headers[shard] = header
    require(seen == set(index) and len(seen) == c['index_tensor_count'], 'archived index/header coverage drift')
    tensors, pairs, complete = coverage(index, headers, c['shards'])
    require(tensors == c['tensors'] and pairs == c['weight_scale_pairs'] and complete == c['coverage'],
            'catalogue not derived exactly from archived actual headers')
    return {'status': 'PASS_AT_HEADER_METADATA_SCOPE', 'weights': len(pairs), 'scales': len(pairs),
            'shards': len(headers), 'indexed_tensors': len(seen), 'payload_read': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots') / REVISION)
    parser.add_argument('--output', type=Path, default=ROOT / DEFAULT_OUT)
    parser.add_argument('--verify-output', action='store_true')
    args = parser.parse_args()
    if args.verify_output:
        print(json.dumps(verify_output(args.output), sort_keys=True))
    else:
        c = build(args.snapshot, args.output)
        print(json.dumps({'status': c['status'], 'coverage': c['coverage'], 'metadata_IO': c['metadata_IO']}, sort_keys=True))


if __name__ == '__main__':
    main()
