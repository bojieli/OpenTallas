#!/usr/bin/env python3
"""Reuse pinned full-stack leaf exactness for a pin-plan-only physical variant."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = {
    'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles.sv': '95559c7061ece09e720b661b865823cfaa56387cb6a632130f93b33d71ed8db8',
    'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles_top.sv': '73c0c21ea4e8727b5674b351108051d9cf261a6a8b326b5090fda71404b921aa',
}
for path, sha in LOCK.items():
    if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != sha:
        raise RuntimeError(f'pinned exact vehicle changed: {path}')
j = json.loads((ROOT/'results/closure_loop/qkd_kvwq_leaf_a-5b265f2b7-tc-hm10/verdict.json').read_text())
assert j['source_commit'] == '5b265f2b7cb1225b5c4dc1b70e6edea5f0e3d861'
assert j['status'] == 'CLOSED'
if sys.argv[1] == 'pos':
    b = j['benches']['bench_kvwq_dist_pos']
    assert b['ok'] and b['rc'] == 0 and 'KVWQ_DIST_PASS' in b['tail']
    print('KVWQ_LEAF_PINNED_EXACT_PASS: unchanged full32PC leaf mechanism, 24 and144 rows')
else:
    b = j['benches']['bench_kvwq_dist_neg']
    assert b['ok'] and b['rc'] == 1 and 'KVWQ_DIST_NEG_DETECTED' in b['tail']
    print('KVWQ_LEAF_PINNED_NEG_DETECTED: unchanged full32PC mutants1/2/3')
    sys.exit(1)
