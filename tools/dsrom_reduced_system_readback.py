#!/usr/bin/env python3
"""Read-only qualification of the retained five-node DS ROM system checker.

No preparation, inference, simulation, or operand publication occurs here.
PASS describes the pinned bench's comparisons, not independent raw readback,
full shape, accepted-write fencing, hardware signoff, or a global drain proof.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from dsrom_reduced_token_binding import CachedReducedTokenBinding, words

TB = 'rtl/test/dsrom_sys/tb_dsrom_system.sv'
TB_SHA = '947a723e0f217cad9646d5cd3f7a681d5383681e06b579fdb3393264efe1ccd0'
NAME = 'sys_b5_p3g2'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def records(text, prefix):
    return [dict(re.findall(r'(\w+)=([^\s]+)', line))
            for line in text.splitlines() if line.startswith(prefix + ' ')]


def single(text, prefix):
    r = records(text, prefix)
    require(len(r) == 1, f'{prefix}: missing or duplicate terminal record')
    return r[0]


def integer(r, key):
    v = r.get(key, '')
    require(bool(re.fullmatch(r'[0-9]+', v)), f'missing/unknown {key}')
    return int(v)


def user_accepted_three_tokens(text, binding):
    """Explicit owner stop scope; no fourth-position or final-state assertion."""
    require(binding.users == 1 and binding.steps == 4, 'unsupported accepted prefix')
    observed = {}
    for label in ('TOK', 'CPL TOKEN'):
        rows = records(text, label)
        require(len(rows) == 3, f'{label}: accepted scope requires exactly three records')
        found = {}
        for row in rows:
            key = integer(row, 'user'), integer(row, 'pos')
            require(key in {(0, 0), (0, 1), (0, 2)} and key not in found,
                    f'{label}: duplicate or out-of-scope token')
            require(integer(row, 'token') == binding.expected_output(*key),
                    f'{label}: cached token mismatch')
            if label == 'CPL TOKEN':
                require(row.get('tag') == '5a', 'foreign completion job tag')
            found[key] = row
        observed[label] = found
    tokens = [{'user': 0, 'position': p,
               'token': integer(observed['TOK'][(0, p)], 'token'),
               'device_cycle': integer(observed['TOK'][(0, p)], 'cycle'),
               'completion_stamp': integer(observed['CPL TOKEN'][(0, p)], 'stamp')}
              for p in range(3)]
    diagnostics = [line for line in text.splitlines() if re.match(
        r'^(FAIL|MISMATCH|CPL_MISMATCH|LOGIT|KV|VM|FAULT|SYS_FAULT|WATCHDOG|TIMEOUT)(\s|$)', line)]
    return {'schema': 'opentallas.dsrom.reduced_system_readback.v1',
            'status': 'INTENTIONAL_USER_STOP_ACCEPTED_THREE_TOKENS',
            'tokens': tokens, 'token_comparison_pass': True,
            'runtime_diagnostics': diagnostics,
            'numerical_qualified': False, 'full_four_position_pass': False,
            'final_logit_summary_available': bool(records(text, 'HDC41_ARRAY')),
            'final_state_checks_available': bool(records(text, 'NODE')),
            'raw_field_export': False, 'accepted_write_visibility_qualified': False,
            'global_drain_qualified': False,
            'scope': 'user-accepted three actual device tokens and matching host completions only',
            'log_sha256': hashlib.sha256(text.encode()).hexdigest()}


def check_log(text, binding, terminal):
    """Check terminal evidence; without a terminal receipt return progress only."""
    tok, cpl = records(text, 'TOK'), records(text, 'CPL TOKEN')
    progress = {'device_tokens': len(tok), 'completion_tokens': len(cpl)}
    if terminal is None:
        return {'status': 'PENDING_TERMINAL', 'progress': progress,
                'numerical_qualified': False}
    require(type(terminal.get('returncode')) is int and terminal['returncode'] == 0,
            'authoritative simulator returncode is not zero')
    require(terminal.get('log_sha256') == hashlib.sha256(text.encode()).hexdigest(),
            'terminal log hash mismatch')
    require(terminal.get('config_name') == NAME
            and terminal.get('config') == binding.prep['config'], 'terminal configuration mismatch')
    require(terminal.get('input_sha256') == binding.prep['input_sha256'],
            'compiled source pins differ from cached preparation')
    require(text.splitlines().count('PASS') == 1, 'missing or duplicate exact PASS line')
    forbidden = r'^(FAIL|MISMATCH|CPL_MISMATCH|LOGIT|KV|VM|FAULT|SYS_FAULT|STUCK|WATCHDOG|TIMEOUT|HOSTCQ_FAIL|QSTREAM_FAIL|KVHBM_FAIL|IDXHBM_FAIL|IDXHBM_USER_FAIL)(\s|$)'
    require(not re.search(forbidden, text, re.M), 'runtime mismatch/fault/timeout evidence')
    require(not re.search(r'readmem\w*.*(error|warning|cannot|not found)', text, re.I),
            'source image load failure')
    keys = {(u, p) for u in range(binding.users) for p in range(binding.steps)}
    for label, rows in [('TOK', tok), ('CPL TOKEN', cpl)]:
        seen = set()
        for row in rows:
            if label == 'CPL TOKEN':
                require(row.get('tag') == '5a', 'foreign completion job tag')
            key = integer(row, 'user'), integer(row, 'pos')
            require(key in keys and key not in seen, f'{label}: foreign/duplicate identity')
            require(integer(row, 'token') == binding.expected_output(*key), f'{label}: token mismatch')
            seen.add(key)
        require(seen == keys, f'{label}: incomplete positions')
    a = single(text, 'HDC41_ARRAY')
    for key, value in {'nodes': 5, 'users': 1, 'generated': 2, 'mismatches': 0,
                       'logit_mismatch': 0, 'lm_head_checks': 8, 'state_mismatch': 0}.items():
        require(integer(a, key) == value, f'array coverage/value mismatch: {key}')
    require(integer(a, 'total_cycles') > 0, 'empty runtime')
    nodes = records(text, 'NODE')
    require(len(nodes) == 5 and {integer(n, 'node') for n in nodes} == set(range(5)),
            'incomplete/duplicate node state checks')
    for n in nodes:
        require(integer(n, 'jobs') == 4 and integer(n, 'state_mismatch') == 0,
                'node job/state coverage mismatch')
    hcq = single(text, 'HOSTCQ')
    for k, v in {'tokens_dev': 4, 'tokens_cpl': 4, 'done_cpl': 1, 'err_cpl': 0,
                 'cpl_mismatch': 0, 'fault': 0, 'code': 0, 'wdog': 0}.items():
        require(integer(hcq, k) == v, f'host completion mismatch: {k}')
    kv = single(text, 'KVHBM')
    require(all(integer(kv, k) > 0 for k in ('ops', 'words', 'writes')),
            'empty physical KV activity')
    require(integer(kv, 'state_bad') == 0 and set(kv.get('fault', '')) == {'0'},
            'physical KV state/fault mismatch')
    hbm = records(text, 'HBM_NODE')
    require(len(hbm) == 5 and {integer(n, 'node') for n in hbm} == set(range(5)),
            'missing HBM node coverage')
    for n in hbm:
        require(integer(n, 'q_bad') == 0 and integer(n, 'q_fault') == 0,
                'physical weight stream mismatch')
    for k in ('q_words', 'q_reads', 'idx_records'):
        require(sum(integer(n, k) for n in hbm) > 0, f'empty {k}')
    require(sum(integer(n, 'idx_writes') for n in hbm)
            == 12 * sum(integer(n, 'idx_records') for n in hbm), 'index record coverage mismatch')
    links = records(text, 'LINK')
    require(len(links) == 5 and {integer(n, 'link') for n in links} == set(range(5)),
            'missing link coverage')
    require(all(integer(n, 'fault') == 0 and integer(n, 'code') == 0 for n in links),
            'link fault')
    ix = single(text, 'IDXHBM_USERS')
    require(all(re.fullmatch('[01]+', ix.get(k, '')) and int(ix[k], 2) & 1
                for k in ('read', 'wrote')), 'missing user index activity')
    require(re.findall(r'^USERS_DONE (\d+)$', text, re.M) == ['1'], 'missing user completion')
    return {'status': 'PASS_PINNED_REDUCED_BENCH_COMPARISONS', 'progress': progress,
            'numerical_qualified': True, 'compared_logit_words': 16160,
            'compared_native_kv_shadow_words': 2621440,
            'compared_persistent_vector_words': 81920,
            'raw_field_export': False, 'full_shape_qualified': False,
            'released_checkpoint_image_provenance_qualified': False,
            'accepted_write_visibility_qualified': False, 'global_drain_qualified': False}


def qualify(scratch, source_root, log, terminal=None):
    scratch, source_root, log = map(Path, (scratch, source_root, log))
    b = CachedReducedTokenBinding(scratch, NAME)
    require(b.prep['config'] == {'body': 3, 'hp': 2, 'pkg': [0, 0, 1, 1, 2],
                                'users': 1, 'stall': 5, 'plen': 3, 'ngen': 2},
            'unsupported selected reduced configuration')
    pins = b.prep['input_sha256']
    require(pins.get(TB) == TB_SHA, 'unsupported numerical checker source')
    for relative, sha in pins.items():
        p = Path(relative)
        require(not p.is_absolute() and '..' not in p.parts, 'invalid source pin path')
        require(digest(source_root / p) == sha, f'source pin mismatch: {relative}')
    # The selected snapshot defines two contiguous 2020-row head partitions.
    for fun, values in [('C_HEAD', [0, 0, 0, 1, 1]),
                        ('C_PROWS', [0, 0, 0, 2020, 2020]),
                        ('C_ROW0', [0, 0, 0, 0, 2020])]:
        found = re.findall(r'(\d+):\s*' + fun + r'\s*=\s*(\d+);', b.svh)
        require(found == [(str(i), str(v)) for i, v in enumerate(values)],
                f'unsupported head partition: {fun}')
    require(re.search(r'\bVOCAB\s*=\s*4040\b', b.svh), 'unsupported vocabulary')
    gold = scratch / 'gold_p3g2.json'
    g = json.loads(gold.read_text())
    logits = words(b.img / 'expect_logits.hex', 32)
    require(len(g) == b.npr and len(logits) == b.npr * b.SMAX * 4040,
            'cached golden extent mismatch')
    for u, trajectory in enumerate(g):
        require(trajectory['prompt'] == b.prompts[u]
                and trajectory['generated'] == b.generated[u]
                and len(trajectory['steps']) == b.steps, 'golden trajectory mismatch')
        for pos, step in enumerate(trajectory['steps']):
            require(step['pos'] == pos and step['argmax'] == b.expect_words[u*b.SMAX + pos],
                    'golden token mismatch')
            start = (u * b.SMAX + pos) * 4040
            require(list(logits[start:start+4040]) == step['logits'], 'cached golden logits mismatch')
    paths = [scratch / f'prep_{NAME}.json', scratch / f'svh_{NAME}.svh', gold,
             *sorted(b.img.glob('*.hex'))]
    obj = scratch / f'obj_{NAME}'
    compiled_svh = obj / 'v41_array_cfg.svh'
    require(compiled_svh.read_text() == b.svh, 'compiled array schedule differs from cached source')
    for node in range(5):
        for prompt in range(2):
            for stem, count in [('kv', 524288), ('vm', 16384)]:
                path = b.img / f'expect_{stem}{node:02d}_{prompt}.hex'
                require(len(words(path, 32)) == count, f'incomplete state comparison image: {path}')
    cmd_path = obj / 'build_cmd.json'
    cmd = json.loads(cmd_path.read_text())
    require(isinstance(cmd, list), 'missing actual build command')
    flags = ('-GUSERS=1', '-GSTALL=5', '-GMBAW_P=18', '+define+HDC_W_HBM=1',
             '+define+HDC_KV_HBM=1', '+define+HDC_X_IDX=2', '+define+HDC_SW=8',
             *[f'+define+HDC_X_{unit}=1' for unit in ('HE', 'ME', 'ATT', 'SEL', 'EG', 'SU')])
    for flag in flags:
        require(flag in cmd, f'unsupported build: {flag}')
    require({s for s in cmd if s.startswith('-G')} == {s for s in flags if s.startswith('-G')},
            'unsupported parameter overrides')
    require(str(source_root / TB) in cmd, 'actual build does not name selected bench')
    exe = obj / 'Vtb_dsrom_system'
    if terminal is not None:
        execution = terminal.get('execution_command', [])
        for arg in (str(exe), f'+DIR={b.img}', f'+ROMS={scratch / "roms"}',
                    '+NUSERS=1', '+NPROMPT=3', '+NGEN=2'):
            require(arg in execution, f'terminal execution binding mismatch: {arg}')
        require(not terminal.get('gparams'), 'terminal has unsupported parameter overrides')
    paths.extend([cmd_path, compiled_svh, exe])
    # Inspect existing files only. These hashes bind comparison inputs; they do
    # not certify those payloads as DUT inputs or as an independent full model.
    text = log.read_text()
    record = check_log(text, b, terminal)
    record['schema'] = 'opentallas.dsrom.reduced_system_readback.v1'
    record['source_pins'] = pins
    record['cached_artifacts'] = {str(p): digest(p) for p in paths}
    record['log_sha256'] = hashlib.sha256(text.encode()).hexdigest()
    record['scope'] = 'five-node cached sys_b5_p3g2; source-pinned internal RTL checker'
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scratch', required=True)
    p.add_argument('--source-root', required=True)
    p.add_argument('--log', required=True)
    p.add_argument('--terminal', help='owner gate JSON written after simulator return')
    p.add_argument('--user-accepted-three-tokens', action='store_true',
                   help='explicit intentional-user-stop scope; never asserts full numerical PASS')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    terminal = json.loads(Path(a.terminal).read_text()) if a.terminal else None
    if a.user_accepted_three_tokens:
        require(terminal is None, 'user-stop scope does not reinterpret a full terminal verdict')
        b = CachedReducedTokenBinding(a.scratch, NAME)
        require(b.prep['input_sha256'].get(TB) == TB_SHA
                and digest(Path(a.source_root) / TB) == TB_SHA, 'unsupported checker source')
        result = user_accepted_three_tokens(Path(a.log).read_text(), b)
        result['source_pins'] = b.prep['input_sha256']
        result['cached_token_image_sha256'] = digest(b.img / 'expect_tokens.hex')
    else:
        result = qualify(a.scratch, a.source_root, a.log, terminal)
    Path(a.out).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
