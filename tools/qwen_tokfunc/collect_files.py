#!/usr/bin/env python3
"""List stage receipts and referenced evidence, relative to the stage, as NUL paths.

Accept old collectors' stage-prefixed paths and <name> placeholders. Build
objects and fixtures are left on the host; only explicit evidence is fetched.
"""
import glob
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
result = json.loads((root / 'result.json').read_text())
names = {'result.json'}

def add(value):
    if not isinstance(value, str):
        return
    path = value.removeprefix(root.name + '/').replace('<name>', '*')
    for match in glob.glob(str(root / path)):
        candidate = Path(match).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            names.add(str(candidate.relative_to(root)))

for value in result.get('logs', []):
    add(value)
for value in (result.get('ages') or {}).values():
    add(value)
for cfg in result.get('configs', {}).values():
    for key in ('vec_ages', 'stn_ages', 'slice_ages'):
        add(cfg.get(key))
for name in sorted(names):
    sys.stdout.buffer.write(name.encode() + b'\0')
