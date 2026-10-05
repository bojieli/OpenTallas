#!/usr/bin/env python3
"""Replay frozen fea phase bytes using its exact sources and hash-checked inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PIN = 'fea811df454fcc7aaa1609a42c3ee4eb58c9672a'


def blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


with tempfile.TemporaryDirectory(prefix='w16-fea-phase-replay-') as directory:
    dest = Path(directory)
    for path in ('tools/w10_q_phase_reservations.py', 'tools/w10_q_power_envelope.py',
                 'tools/w10_liberty_event_energy.py'):
        out = dest / path
        out.parent.mkdir(exist_ok=True)
        out.write_bytes(blob(PIN, path))
    (dest / 'tools/__init__.py').write_text('')
    sys.path.insert(0, directory)
    from tools.w10_q_phase_reservations import build

    raw = blob(PIN, 'results/uarch/w10_q_existing_icg_r1/phases.json')
    original = json.loads(raw)
    inputs = {}
    for name, item in original['input_files'].items():
        path = item['path'].split('/OpenTallas/')[-1] if '/OpenTallas/' in item['path'] else item['path']
        commit = 'e61a5a1ee' if name == 'geometry' else PIN
        source = blob(commit, path)
        if hashlib.sha256(source).hexdigest() != item['sha256']:
            raise ValueError('input hash mismatch: ' + name)
        inputs[name] = json.loads(source)
    for path, expected in original['additional_library_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('library hash mismatch: ' + path)
    replay = build(**inputs,
        libs=Path('/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1'),
        macros=Path('/home/ubuntu/w10-w18-recovery/baseline_wake/physical_src_r2/physical/asap7_memory_macros/ot_rom_4096x274_m8'))
    replay['input_files'] = original['input_files']
    if (json.dumps(replay, indent=2, sort_keys=True) + '\n').encode() != raw:
        raise ValueError('phase output differs from frozen source record')
    print('PASS exact fea phase bytes; conditional reservation only; no actual power or admission')
