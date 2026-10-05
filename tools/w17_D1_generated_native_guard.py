#!/usr/bin/env python3
"""Read-only generated ABI enrollment. Never compiles, links or runs a model."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def review(root, contract, source_root):
    root, source_root = Path(root), Path(source_root)
    receipt_path = root / 'verdict.json'
    require(not receipt_path.is_symlink(), 'receipt symlink')
    require(sha(receipt_path) == contract['receipt_sha256'], 'terminal receipt hash')
    r = json.loads(receipt_path.read_text())
    require(r['verdict'] == 'PASS_FRONTEND_ONLY' and type(r['exit_code']) is int
            and r['exit_code'] == 0 and r['termination_reason'] is None, 'frontend not PASS')
    for k in ('source_commit', 'plan_sha256', 'GO_sha256'):
        require(r[k] == contract[k], 'wrong ' + k)
    for k in ('native_credit', 'runtime_credit', 'token_credit', 'physical_credit'):
        require(r[k] is False, 'unexpected qualification: ' + k)
    files = r['generated_files']
    seen, total = set(), 0
    for entry in files:
        rel = Path(entry['path'])
        require(not rel.is_absolute() and '..' not in rel.parts and rel.parts
                and entry['path'] not in seen, 'unsafe or duplicate inventory path')
        seen.add(entry['path'])
        p = root / rel
        require(not any((root / Path(*rel.parts[:i])).is_symlink()
                        for i in range(1, len(rel.parts) + 1)), 'inventory symlink')
        require(type(entry['bytes']) is int and entry['bytes'] >= 0, 'invalid size')
        require(p.is_file() and p.stat().st_size == entry['bytes']
                and sha(p) == entry['sha256'], 'generated file changed: ' + str(rel))
        total += entry['bytes']
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    require(actual == seen | {'start.json', 'verdict.json'}, 'unenrolled or missing output')
    require(sha(root / 'frontend.log') == r['log_sha256'], 'log hash')
    for rel, digest in contract['source_files'].items():
        p = Path(rel)
        require(not p.is_absolute() and '..' not in p.parts, 'unsafe source path')
        require(sha(source_root / p) == digest, 'source input changed: ' + rel)
    prefix = 'Vtb_D1_scope_core'
    names = [prefix + s for s in ('.h', '__Dpi.h', '.mk', '_classes.mk', '__verFiles.dat')]
    for name in names:
        require('obj/' + name in seen, 'missing ABI metadata: ' + name)
    header = (root / 'obj' / names[0]).read_text()
    for pattern in (r'VL_OUT\(&observed_cycle,31,0\)', r'void eval\(\)',
                    r'void final\(\)', r'bool eventsPending\(\)', r'uint64_t nextTimeSlot\(\)'):
        require(re.search(pattern, header), 'native API mismatch: ' + pattern)
    tiles = len(re.findall(r'const __PVT__tb_D1_scope_core__DOT__endpoint__DOT__g_t__BRA__', header))
    require(tiles == 64, 'full attention geometry mismatch')
    dpi = (root / 'obj' / names[1]).read_text()
    require('extern void v41rt_die_register(int rank);' in dpi
            and 'extern int v41rt_vm_word(int a);' in dpi, 'DPI signature mismatch')
    mk = (root / 'obj' / names[2]).read_text()
    classes = (root / 'obj' / names[3]).read_text()
    require(re.search(r'^VM_PREFIX = Vtb_D1_scope_core$', mk, re.M), 'make prefix')
    for key, value in [('VM_TIMING', 1), ('VM_PARALLEL_BUILDS', 1), ('VM_TRACE', 0)]:
        require(re.search(r'^' + key + ' = ' + str(value) + '$', classes, re.M), 'make ABI ' + key)
    dat = (root / 'obj' / names[4]).read_text()
    require('--timing --threads 1 --top-module tb_D1_scope_core --prefix Vtb_D1_scope_core' in dat,
            'frontend command ABI')
    remaining = contract['retained_output_cap_bytes'] - total
    return dict(schema='opentallas.D1.generated-native-review.v1',
                interface='GENERATED_ABI_ENROLLED', native_execution_authorized=False,
                runtime_authorized=False, generated_files=len(files), generated_bytes=total,
                cpp_files=sum(x['path'].endswith('.cpp') for x in files), attention_tiles=tiles,
                retained_output_remaining_bytes=remaining,
                compile_admission='BLOCKED_PENDING_FRESH_GO_AND_OBJECT_DISK_MODEL',
                causal_service_bound='BOUND_MISSING', original_cause='UNOBSERVED')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(review(a.output, json.loads(a.contract.read_text()), a.source_root), indent=2, sort_keys=True))
