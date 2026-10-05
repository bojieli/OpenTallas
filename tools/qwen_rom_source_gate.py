#!/usr/bin/env python3
"""Read-only capture/replay of the existing connected Qwen ROM runtime.

No build, simulation, P&R, parameter adoption or model-rate publication. Capture
uses the existing collector's PID/boot binding, snapshots completed checkpoints,
and retains raw terminal failures. Replay independently compares all four ranks.
"""
import argparse
import base64
import datetime
import hashlib
import inspect
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL_STAGES = [f'L{i}' for i in range(36)] + ['head']
FAULTS = ('seq_fault', 'core_fault', 'coll_fault')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_stages(log):
    rows = []
    for name, tail in re.findall(r'^STAGE (\S+) done (.*)$', log, re.M):
        fields = dict(item.split('=', 1) for item in tail.split() if '=' in item)
        if any(int(fields.get(k, '-1')) != 0 for k in FAULTS):
            raise ValueError(f'{name}: missing or nonzero fault mask')
        if int(fields['cycles']) <= 0 or int(fields['end_cyc']) - int(fields['start_cyc']) != int(fields['cycles']):
            raise ValueError(f'{name}: inconsistent cycle span')
        if rows and int(fields['start_cyc']) != int(rows[-1]['end_cyc']) + 1:
            raise ValueError(f'{name}: discontinuous stage span')
        rows.append(dict(name=name, **fields))
    names = [r['name'] for r in rows]
    if names != FULL_STAGES[:len(names)]:
        raise ValueError('Completed stages must be the unique ordered full-token prefix')
    return rows


def worker_capture(binding):
    import sys
    source = Path('/home/ubuntu/w12/wt4')
    out = Path('/home/ubuntu/w12/rt_tp4d')
    oracle = Path('/home/ubuntu/w12/oracle_tp4')
    job = dict(roots=binding['roots'], scopes=[str(out)])
    before = capture(job, binding['processes'])
    identity = evaluate(binding, before)
    if identity['state'] == 'identity_changed':
        raise RuntimeError('Original process/host identity changed')
    sys.path.insert(0, str(source / 'tools'))
    import qwen_rom_rt_token as runtime
    pins = {str(p.relative_to(source)): sha(p.read_bytes()) for p in runtime.SOURCES}
    files = {}
    def save(name, path):
        data = path.read_bytes()
        files[name] = dict(sha256=sha(data), base64=base64.b64encode(data).decode())
    for source_path in runtime.SOURCES:
        save('source/' + str(source_path.relative_to(source)), source_path)
    save('generated/ot_qwen_rom_core.sv', out / 'gen/ot_qwen_rom_core.sv')
    save('generated/ot_hdc_vstream_rt.sv', out / 'gen/ot_hdc_vstream_rt.sv')
    save('token.log', out / 'token.log')
    rows = parse_stages(base64.b64decode(files['token.log']['base64']).decode())
    save('build_params.json', out / 'build_params.json')
    save('oracle.json', oracle / 'oracle.json')
    save('stages.txt', Path('/home/ubuntu/w12/st_tp4_sw64/stages.txt'))
    for row in rows:
        if row['name'] == 'head':
            continue
        for d in range(4):
            name = row['name']
            save(f'actual/{name}_die{d}_x.hex', out / f'{name}_die{d}_x.hex')
            save(f'expected/{name}_die{d}_x.hex', oracle / f'L{int(name[1:]):02d}_die{d}_x.hex')
    terminal = Path('/home/ubuntu/w12/rt_tp4d_token.json')
    if terminal.exists() and identity['state'] == 'eligible_for_intake':
        save('terminal.json', terminal)
    # Verify source bytes and completed vectors did not change while reading.
    if pins != {str(p.relative_to(source)): sha(p.read_bytes()) for p in runtime.SOURCES}:
        raise RuntimeError('Source changed during capture')
    for row in rows:
        if row['name'] == 'head':
            continue
        for d in range(4):
            name = row['name']
            for prefix, path in [('actual', out / f'{name}_die{d}_x.hex'),
                                 ('expected', oracle / f'L{int(name[1:]):02d}_die{d}_x.hex')]:
                if sha(path.read_bytes()) != files[f'{prefix}/{name}_die{d}_x.hex']['sha256']:
                    raise RuntimeError('Checkpoint changed during capture')
    after = capture(job, binding['processes'])
    end_identity = evaluate(binding, after)
    if end_identity['state'] == 'identity_changed':
        raise RuntimeError('Process identity changed during capture')
    if 'terminal.json' in files and end_identity['state'] != 'eligible_for_intake':
        raise RuntimeError('Live child prevents terminal intake')
    return dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), identity=identity,
                end_identity=end_identity, source_root=str(source), source_sha256_at_capture=pins,
                binary_sha256=sha((out / 'qwen_rom_rt').read_bytes()),
                generated_core_sha256=sha((out / 'gen/ot_qwen_rom_core.sv').read_bytes()),
                source_unchanged_during_capture=True, files=files)


def capture_existing(binding):
    import w12_terminal_collect as collector
    preamble = 'import base64,datetime,hashlib,json,os,re,socket\nfrom pathlib import Path\n'
    code = preamble + 'FULL_STAGES=' + repr(FULL_STAGES) + '\nFAULTS=' + repr(FAULTS) + '\n'
    for f in (collector.read_process, collector.capture, collector.evaluate, sha, parse_stages, worker_capture):
        code += inspect.getsource(f) + '\n'
    code += 'print(json.dumps(worker_capture(' + repr(binding) + ')))\n'
    proc = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                           binding['endpoint'], 'python3', '-'], input=code, text=True,
                          capture_output=True, timeout=60)
    if proc.returncode:
        raise RuntimeError(proc.stderr[-2000:])
    return json.loads(proc.stdout)


def replay(package, source_root=ROOT):
    files = {}
    for name, item in package['files'].items():
        data = base64.b64decode(item['base64'], validate=True)
        if sha(data) != item['sha256']:
            raise ValueError(f'{name}: archive hash mismatch')
        files[name] = data
    rows = parse_stages(files['token.log'].decode())
    params = json.loads(files['build_params.json'])
    required = {'die': ['-GG=6144', '-GD=4', '-GSW=64', '-GSMIN=7', '-GTCUT=7'],
                'tile': ['-GGT=6144', '-GCODE_BANKS=5', '-GSMIN=7', '-GKV_LOCAL=0'],
                'coll': ['-GN=4', '-GLAT=339', '-GDEPTH=1024']}
    for block, flags in required.items():
        actual = params[block]
        keys = [f.split('=', 1)[0] for f in actual]
        if len(keys) != len(set(keys)) or not set(flags) <= set(actual):
            raise ValueError(f'{block}: missing, duplicate or different connected-runtime parameters')
    planned = [line.split()[0] for line in files['stages.txt'].decode().splitlines() if line.strip()]
    if planned != FULL_STAGES:
        raise ValueError('Stage manifest is not the full 36-layer plus head target')
    checks = {}
    for row in rows:
        if row['name'] == 'head':
            continue
        for d in range(4):
            key = f"{row['name']}_die{d}_x.hex"
            a = [int(x, 16) for x in files[f'actual/{key}'].split()]
            b = [int(x, 16) for x in files[f'expected/{key}'].split()]
            if len(a) != 4096 or len(b) != 4096 or any(x < 0 or x > 0xffffffff for x in a + b):
                raise ValueError(f'{key}: requires exactly 4096 FP32 bit words on each side')
            mm = sum(x != y for x, y in zip(a, b))
            checks[key] = dict(words=4096, mismatches=mm, actual_sha256=sha(files[f'actual/{key}']),
                               expected_sha256=sha(files[f'expected/{key}']))
    if any(c['mismatches'] for c in checks.values()):
        raise ValueError('Connected checkpoint mismatches')
    source_join = {}
    for name, digest in package['source_sha256_at_capture'].items():
        if 'source/' + name in files and sha(files['source/' + name]) != digest:
            raise ValueError(f'{name}: archived source differs from capture pin')
        path = source_root / name
        source_join[name] = dict(capture_sha256=digest, current_sha256=sha(path.read_bytes()) if path.is_file() else None)
    terminal = json.loads(files['terminal.json']) if 'terminal.json' in files else None
    full_exact = False
    terminal_errors = []
    if terminal is not None:
        oracle = json.loads(files['oracle.json'])
        if [r['name'] for r in rows] != FULL_STAGES or terminal.get('stages_run') != FULL_STAGES:
            terminal_errors.append('missing full stage coverage')
        if terminal.get('status') != 'pass' or terminal.get('source_stable') is not True:
            terminal_errors.append('original terminal FAIL or source instability')
        if not package['source_sha256_at_capture']:
            terminal_errors.append('empty source pin set')
        dp = terminal.get('design_point', {})
        for key, expected in [('tp', 4), ('groups_per_die', 6144), ('tiles_per_die', 1536),
                              ('su_width', 64), ('smin', 7), ('tree_cut', 7), ('collective_lat_cycles', 339)]:
            if dp.get(key) != expected:
                terminal_errors.append('design_point.' + key + ' mismatch')
        original_checks = terminal.get('layer_x_checks', {})
        if len(original_checks) != 144:
            terminal_errors.append('original terminal checkpoint count mismatch')
        for name, measured in checks.items():
            original = original_checks.get(name[:-4], {})
            if any(original.get(k) != measured[k] for k in ('words', 'mismatches', 'actual_sha256', 'expected_sha256')):
                terminal_errors.append(name + ' original checkpoint mismatch')
        if terminal.get('source_sha256') != package['source_sha256_at_capture']:
            terminal_errors.append('launch-to-capture source mismatch')
        for key, expected in [('binary_sha256', package['binary_sha256']),
                              ('generated_core_sha256', package['generated_core_sha256']),
                              ('oracle_sha256', sha(files['oracle.json'])),
                              ('rtl_token', oracle.get('next_token')),
                              ('rtl_logit_bits', oracle.get('next_logit_bits'))]:
            if expected is None or terminal.get(key) != expected:
                terminal_errors.append(key + ' mismatch')
        m = re.search(r'^QWEN_ROM_TOKEN_TP2 PASS stages=(\d+) token=(\d+) val=([0-9a-f]+) die1_token=(\d+) cycles=(\d+)',
                      files['token.log'].decode(), re.M)
        if not m or int(m[1]) != 37 or int(m[2]) != oracle.get('next_token') or int(m[4]) != int(m[2]) or m[3] != oracle.get('next_logit_bits'):
            terminal_errors.append('missing or inconsistent original simulator PASS line')
        elif int(m[5]) != terminal.get('total_cycles') or not rows or int(m[5]) != int(rows[-1]['end_cyc']):
            terminal_errors.append('terminal cycles mismatch')
        if package['end_identity']['state'] != 'eligible_for_intake':
            terminal_errors.append('original processes still live')
        full_exact = not terminal_errors
    return dict(schema='opentallas.qwen-rom-source-gate.v1',
                status='fail' if terminal_errors else ('pass' if full_exact else 'pending'),
                checkpoint_status='bit_exact' if checks else 'pending', checks=checks,
                completed_stages=[r['name'] for r in rows], stage_cycles={r['name']: int(r['cycles']) for r in rows},
                full_token_exact_at_runtime_scope=full_exact, terminal_errors=terminal_errors,
                source_join=source_join, current_source_joined=bool(source_join) and all(
                    s['capture_sha256'] == s['current_sha256'] for s in source_join.values()),
                params=params, identity=package['end_identity'], adoption=False,
                claim_boundary='Connected TP4 SU64 position-zero runtime checkpoints only until original full terminal joins. '
                'Host stage loading, embedding preload and zero KV reset remain bench services. '
                'No SU1024, contextual SS/FF, macro-local KV, power, product-rate or adoption credit.')


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture-binding', type=Path, help='existing collector bindings.json; reads only tp4_su64_token')
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--result', type=Path, required=True)
    ap.add_argument('--source-root', type=Path, default=ROOT)
    args = ap.parse_args()
    if args.result.exists() or (args.capture_binding and args.package.exists()):
        ap.error('Refusing to overwrite evidence')
    if args.capture_binding:
        binding = json.loads(args.capture_binding.read_text())['tp4_su64_token']
        write_new(args.package, capture_existing(binding))
    package = json.loads(args.package.read_text())
    try:
        result = replay(package, args.source_root)
    except Exception as exc:
        result = dict(schema='opentallas.qwen-rom-source-gate.v1', status='fail', error=str(exc), adoption=False)
    result['package_sha256'] = sha(args.package.read_bytes())
    result['verifier_sha256'] = sha(Path(__file__).read_bytes())
    write_new(args.result, result)
    print(json.dumps({k:result.get(k) for k in ['status', 'checkpoint_status', 'completed_stages',
                                             'current_source_joined', 'full_token_exact_at_runtime_scope', 'error']}))
    if result['status'] == 'fail':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
