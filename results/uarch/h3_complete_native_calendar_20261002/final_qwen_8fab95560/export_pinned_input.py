#!/usr/bin/env python3
"""Restore the bulk input from the immutable producer commit, without checkout."""
import hashlib
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = 'results/uarch/h3_qwen_complete_native_20261002/Qwen_native.json.gz'
EXPECTED = '75a3997b07b492c4c1f8eeec55488c8ef754a49987aa297e1cc16648e49c3674'
raw = subprocess.check_output(['git', 'show', '8fab95560:' + SOURCE], cwd=ROOT)
if hashlib.sha256(raw).hexdigest() != EXPECTED:
    raise ValueError('committed producer input hash mismatch')
dest = HERE / 'Qwen_native.json.gz'
if dest.exists() and dest.read_bytes() != raw:
    raise ValueError('refusing to replace a different producer input')
if not dest.exists():
    dest.write_bytes(raw)
print('PASS_COMMITTED_QWEN_INPUT', len(raw), EXPECTED)
