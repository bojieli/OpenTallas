#!/usr/bin/env python3
"""Bind the pruned parent to its own complete-word and bitmapped receipts."""
from pathlib import Path
import hashlib
import json
import random

root = Path(__file__).resolve().parents[2]
receipt = root / 'results/rtl/qwen_compute_native_glue_1014/parent_pruned_1015'

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

rng = random.Random(198)
masks = {}
for bank in range(5):
    for col in range(2):
        payload = ''.join(f'{rng.getrandbits(2128):0532x}\n' for _ in range(512))
        masks[f'masks/qtile_t0_b{bank}_c{col}.viamap.hex'] = hashlib.sha256(payload.encode()).hexdigest()
for path, expected in json.loads((receipt / 'source_hashes.json').read_text()).items():
    actual = masks[path] if path.startswith('masks/') else hashlib.sha256((root / path).read_bytes()).hexdigest()
    require(actual == expected, f'pruned parent source/mask changed: {path}')
for name in ['m0', 'm1', 'm2', 'm3', 'boot16', 'allbanks']:
    text = (receipt / f'run_{name}.log').read_text()
    build = (receipt / f'build_{name}.log').read_text()
    require('Verilator: Built from' in build, f'missing actual build: {name}')
    require(('FAIL parent tile complete word' if name in ['m1', 'm2', 'm3'] else 'PASS actual full old-parent') in text,
            f'missing numerical/negative result: {name}')
require('checks3499' in (receipt / 'run_m0.log').read_text(), 'main oracle coverage changed')
require('checks3559' in (receipt / 'run_boot16.log').read_text(), 'boot16 coverage changed')
allbanks = (receipt / 'run_allbanks.log').read_text()
require('ACTUAL_BANK_READS 64 120 96 104 64' in allbanks, 'all-bank reads changed')
require('checks5959 output448 node745 nonzero448' in allbanks, 'all-bank word coverage changed')
measure = json.loads((receipt / 'measurement.json').read_text())
require(measure['actual_bitmapped_FF_count'] == 943 and measure['reduction'] == 1335, 'measured residual count changed')
deps = json.loads((receipt / 'pin_dependency_audit.json').read_text())
require(deps['status'] == 'PASS' and deps['pairs'] == 31504 and deps['unmatched_count'] == 0, 'native dependency audit changed')
jobs = json.loads((receipt / 'jobs.json').read_text())
require(all(x['harness_exit_code'] == 0 for x in jobs.values()), 'one or more actual jobs did not finish successfully')
native = json.loads((receipt / 'native_synthesis/comparison.json').read_text())
require(native['exit'] == 0 and native['baseline']['handoff_odb_dff'] == native['candidate']['handoff_odb_dff'] == 954, 'native mapped FF comparison changed')
print('PASS exact pruned-parent receipt: 943 pre-ABC FF,954 mapped handoff FF unchanged,3499 words,3 mutants,3559 boot16,5959 allbank,31504 pin pairs; physicalqualificationOPEN')
