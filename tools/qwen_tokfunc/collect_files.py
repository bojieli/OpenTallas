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
        logical = Path(match)
        candidate = logical.resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            names.add(str(candidate.relative_to(root)))
        elif (logical.is_relative_to(root / 'fx') and candidate.is_file()
              and candidate.is_relative_to(root.parent)):
            # STG3 deliberately links its fixtures to the original stage.
            # Fetch their bytes at the logical path, never a parent escape.
            names.add(str(logical.relative_to(root)))

for value in result.get('logs', []):
    add(value)
for value in (result.get('ages') or {}).values():
    add(value)
for cfg in result.get('configs', {}).values():
    for key in ('vec_ages', 'stn_ages', 'slice_ages'):
        add(cfg.get(key))
if str(result.get('stage', '')).startswith('stg'):
    for cfg in ('rel', 'pos', 'mut'):
        for path in ('vtb.sha256', 'vflags.txt', 'build/slice_calibrate.out',
                     'build/calibrate.out', 'cal_mat/calibrate.out',
                     'cal_mat/cal.ev', 'cal_mat/cal.log'):
            add(f'{cfg}/{path}')
    add('fx/L*_fixture.json')
    add('fx/L*.log')
    # build receipts (STEWARD-TOKb-QW 10-21): the source/binary identity chain normalize_collected_stg.py verifies
    add('overlay.sha256')
    for cfg in ('rel', 'pos', 'mut'):
        for path in (f'{cfg}.build_source.json', f'{cfg}.identity.log', f'{cfg}/build/obj_n12/build_identity.json'):
            add(path)
for name in sorted(names):
    sys.stdout.buffer.write(name.encode() + b'\0')
