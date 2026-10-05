#!/usr/bin/env python3
"""Restore producer source/input bytes from immutable commits; never checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('directory', type=Path)
args = p.parse_args()
base = args.directory.resolve()
pins = json.loads((base / 'producer_pins.json').read_bytes())
assert pins['schema'] == 'H3_PORTABLE_PRODUCER_PINS_V1'
for name, pin in pins['files'].items():
    dest = (base / name).resolve()
    if not dest.is_relative_to(base):
        raise ValueError('archive path escape')
    if dest.exists():
        raw = dest.read_bytes()
    else:
        raw = subprocess.check_output(['git', 'show', pin['commit'] + ':' + pin['path']], cwd=ROOT)
    if hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('source pin mismatch: ' + name)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
print('PASS_RESTORED_COMMITTED_INPUTS', len(pins['files']))
