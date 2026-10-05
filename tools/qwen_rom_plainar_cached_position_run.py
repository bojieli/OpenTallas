#!/usr/bin/env python3
"""Run one existing plain-AR STREAM4 binary on an owned, retained position.

No compilation, inference, input construction or arithmetic producer. The legacy
input book's baseline verdict is historical; this run uses its pinned payloads
with the separately selected current STREAM4 binary and 37-stage source list.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str) + '\n')


def words(path):
    return [int(x, 16) for x in Path(path).read_text().split()]


def compare(a, b):
    return dict(words=len(a), expected_words=len(b), mismatches=
                sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('executable', 'stages', 'inputs', 'source_root', 'output'):
        p.add_argument('--' + key.replace('_', '-'), type=Path, required=True)
    for key in ('executable_sha256', 'stages_sha256', 'inputs_sha256'):
        p.add_argument('--' + key.replace('_', '-'), required=True)
    a = p.parse_args()
    assert not a.output.exists(), 'fresh immutable run directory required'
    for key in ('executable', 'stages', 'inputs'):
        assert sha(getattr(a, key)) == getattr(a, key + '_sha256'), key + ' changed'
    stages = [x.split() for x in a.stages.read_text().splitlines()]
    assert [x[0] for x in stages] == [f'L{i}' for i in range(36)] + ['head']
    assert all(len(x) == 6 and x[5] == '0' for x in stages)
    assert all(Path(d).is_dir() for x in stages for d in x[1:5])
    book = json.loads(a.inputs.read_text())
    position, token = book['position'], book['token']
    assert 0 <= position < 4095, 'this owner selects a distinct short-context position'
    oracle = Path(book['oracle']['root']); reference = oracle / f'P{position}'
    assert sha(oracle / 'oracle.json') == book['oracle']['sha256']
    original = json.loads((oracle / 'oracle.json').read_text())
    assert original['layers'] == 36 and original['head'] and original['tp'] == 4
    expected_head = original['per_position'][str(position)]['head']
    assert set(book['history']) == {f'L{l}_die{d}' for l in range(36) for d in range(4)}
    history = Path(book['history_directory'])
    for key, pin in book['history'].items():
        raw = history / (key + '.bin')
        assert raw.stat().st_size == pin['bytes'] == 16777216
        assert sha(raw) == pin['raw_sha256'], key + ' history changed'
    preload = Path(book['preload']['path'])
    assert sha(preload) == book['preload']['sha256']
    for l in range(36):
        for d in range(4):
            assert (reference / f'L{l:02d}_die{d}_x.hex').is_file()
            assert (reference / 'kv_at_P' / f'L{l}_die{d}.json').is_file()
    assert all((reference / f'head_die{d}_xnorm.hex').is_file() for d in range(4))
    sys.path.insert(0, str(a.source_root / 'tools'))
    from qwen_rom_rt_token_w12_rm import e4m3  # existing exact comparator conversion only
    a.output.mkdir()
    lock = (a.output / 'sole.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    run = a.output / 'run'
    cmd = [str(a.executable), '--stages', str(a.stages), str(run), str(preload),
           '--pos', str(position), '--token', str(token), '--kv-dir', str(history),
           '--kv-ideal', '0', '--early-go', '1', '--posted-wb', '1']
    write(a.output / 'runtime.command.json', cmd)
    write(a.output / 'source_inputs.json', dict(arguments=vars(a) | {'output': str(a.output)},
          comparator_sha256=sha(a.source_root / 'tools/qwen_rom_rt_token_w12_rm.py')))
    env = os.environ | {'RT_THREADS': '16', 'RT_PROGRESS': '4096'}
    checks = {}
    with (a.output / 'runtime.log').open('x') as log:
        child = subprocess.Popen(['/srv/opentallas-scratch/admit.sh', '48', '--',
                                  '/usr/bin/time', '-v', *cmd], stdout=log,
                                 stderr=subprocess.STDOUT, env=env)
        write(a.output / 'state.json', dict(owner_pid=os.getpid(), gate_pid=child.pid,
                                          phase='admission_or_runtime', position=position))
        print('GATE_PID', child.pid, flush=True)
        while child.poll() is None:
            time.sleep(30)
            text = (a.output / 'runtime.log').read_text()
            for l in range(36):
                if str(l) in checks or not re.search(r'^STAGE L' + str(l) + r' done ', text, re.M):
                    continue
                paths = [run / f'L{l}_die{d}_x.hex' for d in range(4)]
                if not all(x.exists() for x in paths):
                    continue
                checks[str(l)] = [compare(words(paths[d]), words(reference / f'L{l:02d}_die{d}_x.hex')) for d in range(4)]
                write(a.output / 'completed_layer_comparison.json', checks)
                print('LAYER', l, 'MISMATCHES', sum(x['mismatches'] for x in checks[str(l)]), flush=True)
        rc = child.wait()
    (a.output / 'runtime.exit').write_text(str(rc) + '\n')
    assert rc == 0, 'runtime failure preserved'
    text = (a.output / 'runtime.log').read_text()
    completed = re.findall(r'^STAGE (\S+) done .*$', text, re.M)
    marker = re.search(r'QWEN_ROM_STREAM4_PLAIN_AR_FULLTOKEN DONE stages=37 cycles=(\d+)', text)
    assert completed == [x[0] for x in stages] and marker and 'WRITEBACK drained=1' in text
    layers, kv, heads, norms = {}, {}, {}, {}
    for l in range(36):
        for d in range(4):
            key = f'L{l}_die{d}'
            layers[key] = compare(words(run / (key + '_x.hex')), words(reference / f'L{l:02d}_die{d}_x.hex'))
            want = json.loads((reference / 'kv_at_P' / (key + '.json')).read_text())
            rows = [x.split() for x in (run / (key + '_kvP.hex')).read_text().splitlines()]
            kv[key] = {kind: compare([int(x[3], 16) for x in rows if x[0] == kind],
                        [e4m3(int(x, 16)) for x in want[field]])
                       for kind, field in [('K', 'k_bits'), ('V', 'v_bits')]}
    for d in range(4):
        heads[str(d)] = compare(words(run / f'head_die{d}_result.hex'),
                               [expected_head['next_token'], int(expected_head['next_logit_bits'], 16)])
        norms[str(d)] = compare(words(run / f'head_die{d}_xnorm.hex'), words(reference / f'head_die{d}_xnorm.hex'))
    good = all(x['mismatches'] == 0 for group in [layers, heads, norms] for x in group.values()) and all(x['mismatches'] == 0 for group in kv.values() for x in group.values())
    write(a.output / 'full_numerical_comparison.json', dict(status='PASS' if good else 'FAIL',
          position=position, token=token, cycles=int(marker[1]), process_exit=rc,
          layer_x=layers, kv=kv, head=heads, head_xnorm=norms,
          actual_writeback_drained=True, physical_qualification=False))
    print('FINAL', 'PASS' if good else 'FAIL', flush=True)
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
