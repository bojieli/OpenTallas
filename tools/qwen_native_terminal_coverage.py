#!/usr/bin/env python3
"""Offline coverage gate for the pinned trained native job; never executes arithmetic.

39 independent comparisons qualify layer/head boundaries, not all 1737 PCs.
Missing observed KV journals or KV payload comparisons remain explicit open gates.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import numpy as np

SOURCE = '870c5fe581b768df28dd2998b2d0aecc24510c23'
GO = '026847e37d735d7dcdc1d0bda8bb332d9dfd233d'
ARTIFACT = 'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz'
LOCK = 'compiler/models/qwen3-8b/checkpoint_source.json'
QUALIFIED_IMAGES_SHA256 = 'b055a2e9674c5903fa28b8cfe3d38e2e0c5c664624253b644f539bcd96067fdb'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(directory, name):
    return json.loads((Path(directory) / name).read_bytes())


def pinned(repo, commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=repo)


def boundaries(native):
    h = native['source_program']['config']['hidden_size']
    v = native['source_program']['config']['vocab_size'] // 2
    return {**{f'L{i}.X': h for i in range(36)}, 'head.norm': h,
            'head.d0.scaled': v, 'head.d1.scaled': v}


def verify_trace(native, rows, position=0):
    ops = native['operations']
    require(len(ops) == len(rows) == 1737, 'complete 1737 PC trace')
    values = {v['version']: v for v in native['operands']}
    previous = dict(transactions=0, bytes=0, byte_ranges=0)
    elapsed = 0
    done = set()
    for op, row in zip(ops, rows):
        require(row['pc'] == op['pc'] == len(done) and row['opcode'] == op['opcode'], 'source ordered PC/opcode')
        require(set(op['dependencies']) <= done, 'source dependency precedence')
        require(np.isfinite(row['elapsed_s']) and row['elapsed_s'] >= elapsed, 'finite monotonic elapsed')
        elapsed = row['elapsed_s']
        require([o['version'] for o in row['outputs']] == op['writes'], 'exact output versions')
        for output in row['outputs']:
            shape = [position+1 if n == 'position+1' else n for n in values[output['version']]['shape']]
            require(output['shape'] == shape, 'source output shape')
            require(re.fullmatch('[0-9a-f]{64}', output['sha256']) is not None, 'output SHA256')
        provider = row['provider']
        require(provider['read_lease_outstanding'] is False, 'checkpoint reader drained')
        for key in previous:
            require(type(provider[key]) is int and provider[key] >= previous[key], 'monotonic provider counters')
            if op['opcode'] in ('KV_WRITE', 'KV_FENCE', 'KV_READ'):
                require(provider[key] == previous[key], 'mutable KV checkpoint transaction')
        previous = {key: provider[key] for key in previous}
        done.add(op['pc'])
    return previous


def verify_captures(native, rows, directory, comparisons, next_token):
    expected = boundaries(native)
    require(len(comparisons) == len(expected) and {c['register'] for c in comparisons} == set(expected), '39 unique comparison boundaries')
    for c in comparisons:
        require(c['values'] == expected[c['register']], 'per-register comparison extent')
        require(all(c[k] == 0 for k in ('bit_mismatches', 'actual_nonfinite', 'reference_nonfinite')), 'comparison mismatch/nonfinite')
    names = {v['version']: v['name'] for v in native['operands']}
    outputs = {names[o['version']]: o for r in rows for o in r['outputs']}
    heads = []
    for name, size in expected.items():
        a = np.load(Path(directory) / (name + '.npy'), allow_pickle=False)
        require(a.dtype == np.float32 and a.shape == (size,) and np.isfinite(a).all(), 'captured shape/dtype/finite ' + name)
        require(digest(a.tobytes()) == outputs[name]['sha256'], 'capture output hash ' + name)
        if name.startswith('head.d'):
            heads.append(a)
    require(int(np.argmax(np.concatenate(heads))) == next_token, 'captured global head argmax')
    require(outputs['next_token']['sha256'] == digest(np.array([next_token], dtype=np.uint32).tobytes()), 'retired next-token output hash')


def tensor_shapes(native):
    c = native['source_program']['config']; h = c['hidden_size']; hd = c['head_dim']; ff = c['intermediate_size']; v = c['vocab_size']
    shapes = {'model.embed_tokens.weight': [v, h], 'lm_head.weight': [v, h], 'model.norm.weight': [h]}
    for layer in range(36):
        p = f'model.layers.{layer}'
        for name in ('input_layernorm', 'post_attention_layernorm'):
            shapes[p + '.' + name + '.weight'] = [h]
        for name in ('q', 'k'):
            shapes[p + f'.self_attn.{name}_norm.weight'] = [hd]
        for name, count in [('q', c['num_attention_heads']*hd), ('k', c['num_key_value_heads']*hd), ('v', c['num_key_value_heads']*hd), ('o', h)]:
            shapes[p + f'.self_attn.{name}_proj.weight'] = [count, h]
        for name in ('gate', 'up'):
            shapes[p + f'.mlp.{name}_proj.weight'] = [ff, h]
        shapes[p + '.mlp.down_proj.weight'] = [h, ff]
    return shapes


def verify_reader(reader, native, lock, token, index=None):
    expected = {x['path']: x['sha256'] for x in lock['expected_files'] if x['path'].endswith('.safetensors')}
    require(reader['verified_shards'] == expected and reader['checkpoint_revision'] == lock['revision'], 'released checkpoint reader identity')
    require(reader['max_source_rows_per_read'] == 256 and not any(reader[k] for k in ('images_written', 'downloads', 'actual_hardware_memory_provider')), 'reference reader boundary')
    shapes = tensor_shapes(native)
    if index is not None:
        require(set(index['weight_map']) == set(shapes), 'checkpoint index tensor set')
    intervals = {}
    for r in reader['reads']:
        key = r['tensor']; shape = r['shape']; lo = r['row_start']; hi = r['row_stop']
        require(key in shapes and shape == shapes[key] and r['shard'] in expected, 'reader tensor/shape/shard')
        if index is not None:
            require(r['shard'] == index['weight_map'][key], 'checkpoint index shard binding')
        require(re.fullmatch('[0-9a-f]{64}', r['sha256']) is not None, 'reader slice SHA')
        if lo is None:
            require(hi is None and len(shape) == 1 and r['bytes'] == shape[0]*2, 'vector source read')
            lo, hi = 0, shape[0]
        else:
            require(len(shape) == 2 and 0 <= lo < hi <= shape[0] and hi-lo <= 256 and r['bytes'] == (hi-lo)*shape[1]*2, 'matrix source read')
        intervals.setdefault(key, []).append((lo, hi))
    require(set(intervals) == set(shapes), 'all released tensors read')
    for key, spans in intervals.items():
        if key == 'model.embed_tokens.weight':
            require(set(spans) == {(token, token+1)}, 'actual embedding row')
            continue
        cursor = 0
        for lo, hi in sorted(spans):
            require(lo <= cursor, 'checkpoint source row gap')
            cursor = max(cursor, hi)
        require(cursor == shapes[key][0], 'complete checkpoint tensor rows')
    return len(intervals)


def verify_kv_journal(native, events, position=0):
    """Validate actual event records only; absent events must never be synthesized."""
    names = {v['version']: v['name'] for v in native['operands']}
    expected = []
    for op in native['operations']:
        code = op['opcode']
        if code in ('KV_WRITE', 'KV_FENCE', 'KV_READ'):
            a = op['attributes']; key = [a['layer'], a['die'], position]
            expected.append((op['pc'], {'KV_WRITE': 'write_accept', 'KV_FENCE': 'commit_publish', 'KV_READ': 'acquire'}[code], key, None))
        elif code in ('SCORES', 'PV'):
            # The producer version carries the actual layer/die identity.
            prefix = names[op['reads'][1]].split('.')[:2]
            key = [int(prefix[0][1:]), int(prefix[1][1:]), position]
            expected.append((op['pc'], 'consumer_done', key, code))
            if code == 'PV':
                expected.append((op['pc'], 'release', key, None))
    require(len(events) == len(expected) == 432, '432 actual ordered KV events')
    pending = {}; published = {}; active = {}; identities = set()
    for e, (pc, kind, key, stage) in zip(events, expected):
        require(e['pc'] == pc and e['event'] == kind and e.get('cycles') is None, 'KV observed event order/PC')
        k = tuple(key)
        if kind == 'write_accept':
            tag = e['tag']; require(e['key'] == key and tag not in identities and k not in published, 'KV writer identity')
            identities.add(tag); pending[tag] = k
        elif kind == 'commit_publish':
            require(e['key'] == key and pending.get(e['tag']) == k, 'KV publication identity')
            published[k] = pending.pop(e['tag'])
        elif kind == 'acquire':
            lease = e['lease']; require(e['key'] == key and k in published and lease not in identities, 'KV acquisition identity')
            identities.add(lease); active[lease] = (k, [])
        elif kind == 'consumer_done':
            state = active.get(e['lease']); require(state is not None and state[0] == k and e['stage'] == stage, 'KV consumer identity')
            require(state[1] == ([] if stage == 'SCORES' else ['SCORES']), 'KV consumer precedence')
            state[1].append(stage)
        else:
            state = active.pop(e['lease'], None); require(state == (k, ['SCORES', 'PV']), 'KV release identity')
    require(not pending and not active and len(published) == 72, 'KV lifecycle drain')
    return len(events)


def verify(directory, repo, qualified_images):
    directory = Path(directory); nt = read(directory, 'native/terminal.json'); t = read(directory, 'terminal.json'); a = read(directory, 'GO.json')
    require(a == json.loads(pinned(repo, GO, a['admission_record_path'])) and (directory/'GO.commit').read_text().strip() == GO, 'committed GO identity')
    require(t['source_commit'] == a['source_commit'] == SOURCE and t['GO_commit'] == GO, 'pinned worker identity')
    for name, h in a['source_sha256'].items():
        if Path(name).is_absolute():
            require(Path(name).parent == Path('/home/ubuntu/otjobs/qwen-trained-native-token-pve1-20261002-r1') and Path(name).name in ('launcher.py', 'qualified_images.json'), 'admitted external source inventory')
            data = (directory/Path(name).name).read_bytes()
        else:
            data = pinned(repo, SOURCE, name)
        require(digest(data) == h, 'admitted source pin ' + name)
    require(t['actual_native_log_sha256'] == digest((directory/'actual_native.log').read_bytes()), 'actual native log identity')
    require(t['native_terminal_sha256'] == digest((directory/'native/terminal.json').read_bytes()) and t['native_terminal'] == nt, 'raw terminal identity')
    require(t['exit_code'] == 0 and t['verdict'] == nt['verdict'] == 'PASS_TRAINED_NATIVE_TOKEN_POSTCHECKED', 'actual terminal success')
    require(t['termination_reason'] is None, 'supervisor protective termination')
    log = (directory/'actual_native.log').read_text()
    require(json.loads(log.strip().splitlines()[-1]) == nt, 'actual stdout terminal marker')
    require(nt['full_checkpoint_native'] is True and nt['layers'] == 36 and nt['input_token'] == 9707 and nt['position'] == 0 and nt['oracle_callbacks'] == 0, 'full trained single token boundary')
    require(not any(nt[k] for k in ('actual_RTL', 'physical_credit', 'token_rate_credit')), 'software qualification boundary')
    native = json.loads(gzip.decompress(pinned(repo, SOURCE, ARTIFACT)))
    rows = [json.loads(line) for line in (directory/'native/native_progress.jsonl').read_text().splitlines()]
    counters = verify_trace(native, rows)
    result = nt['native']
    require(result['status'] == 'PASS_BOUNDED_TILED_SOFTWARE' and result['PCs'] == 1737 and result['temporary_HBM_bytes'] == 0, 'native retirement')
    require(all(nt['provider'][k] == counters[k] for k in counters) and not nt['provider']['read_lease_outstanding'], 'terminal provider counter binding')
    comparisons = read(directory, 'native/post_execution_comparisons.json')
    require(comparisons == nt['post_execution_comparisons'], 'raw comparison identity')
    verify_captures(native, rows, directory/'native', comparisons, result['next_token'])
    lock_bytes = pinned(repo, SOURCE, LOCK); lock = json.loads(lock_bytes)
    q = read(Path(qualified_images).parent, Path(qualified_images).name); identity = q['identity']
    require(digest(Path(qualified_images).read_bytes()) == QUALIFIED_IMAGES_SHA256, 'independently qualified image receipt bytes')
    require(q['PASS'] is True and q['all_page_hashes_verified'] is True and q['runtime_source_commit'] == SOURCE, 'qualified image receipt')
    require(a['qualified_images']['qualification_sha256'] == QUALIFIED_IMAGES_SHA256 and a['qualified_images']['manifest_sha256'] == q['manifest_sha256'], 'admitted qualified image join')
    require(identity['checkpoint_lock_sha256'] == digest(lock_bytes) and identity['checkpoint_revision'] == lock['revision'], 'image released checkpoint lock')
    shards = {x['path']: x['sha256'] for x in lock['expected_files'] if x['path'].endswith('.safetensors')}
    require(identity['checkpoint_files_sha256'] == shards and identity['native_sha256'] == digest((json.dumps(native,sort_keys=True,indent=2)+'\n').encode()), 'image checkpoint/native binding')
    require(read(directory, 'native/image_manifest_identity.json')['sha256'] == q['manifest_sha256'], 'executed image manifest identity')
    reader = read(directory, 'native/reference_source_provenance.json')
    gaps = ['1737 output hashes are observations; independent comparisons cover39 layer/head boundaries only', 'independent FP8 KV payload comparison not emitted by pinned driver']
    index = None
    index_path = directory/'checkpoint_index.json'
    if index_path.exists():
        expected_index = next(x['sha256'] for x in lock['expected_files'] if x['path'] == 'model.safetensors.index.json')
        require(digest(index_path.read_bytes()) == expected_index, 'released checkpoint index bytes')
        index = json.loads(index_path.read_bytes())
    else:
        gaps.append('locked checkpoint index not archived: per-tensor source-shard mapping remains unverified')
    tensors = verify_reader(reader, native, lock, nt['input_token'], index)
    journal = directory/'native/kv_journal.jsonl'
    journal_status = 'MISSING_NOT_EMITTED_BY_PINNED_DRIVER'
    if journal.exists():
        verify_kv_journal(native, [json.loads(x) for x in journal.read_text().splitlines()])
        # The pinned driver cannot produce this file. Structural validity alone
        # cannot turn an added/synthesized journal into an observed job receipt.
        journal_status = 'STRUCTURE_VALID_ORIGIN_UNQUALIFIED_FOR_PINNED_DRIVER'
        gaps.append('supplied KV journal structurally valid but no emitting source/observation provenance in pinned job')
    else:
        gaps.append('actual ordered KV lifecycle journal not emitted by pinned driver')
    return dict(verdict='PASS_LAYER_HEAD_BOUNDARIES_WITH_OPEN_KV_COVERAGE', source_commit=SOURCE,
                PCs=1737, independent_comparison_boundaries=39, compared_values=303488,
                source_tensors=tensors, ordered_KV_journal=journal_status, open_coverage=gaps,
                checkpoint_tensor_shard_mapping_verified=index is not None,
                fulltoken_KV_comparison_qualified=False, actual_RTL=False, physical_credit=False,
                rate_credit=False, qualified_images_sha256=digest(Path(qualified_images).read_bytes()))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--qualified-images', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(args.archive, args.repo, args.qualified_images), indent=2))
