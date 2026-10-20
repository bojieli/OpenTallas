#!/usr/bin/env python3
"""Validate an explicitly selected compute die/table pair; this is identity, not qualification."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re


def validate(manifest):
    path = Path(manifest).resolve()
    doc = json.loads(path.read_text())
    if doc.get('schema') != 'opentallas.kv_compute_pair.v1':
        raise ValueError('compute pair manifest schema')
    commit = doc.get('source_commit', '')
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('compute pair needs full source commit')
    selected = {}
    for key in ('die_v', 'relay_stages'):
        entry = doc[key]
        item = Path(entry['path'])
        item = (path.parent / item).resolve() if not item.is_absolute() else item.resolve()
        if '\n' in str(item) or '\r' in str(item):
            raise ValueError('newline in selected path')
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        if digest != entry['sha256']:
            raise ValueError(f'{key} SHA256 mismatch')
        selected[key] = dict(path=str(item), sha256=digest)
    table_path = Path(selected['relay_stages']['path'])
    opener = gzip.open if table_path.suffix == '.gz' else open
    with opener(table_path, 'rt') as f:
        table = json.load(f)
    plan = table.get('plan', {})
    tc = plan.get('commit', '')
    if not re.fullmatch('[0-9a-f]{9,40}', tc) or not commit.startswith(tc):
        raise ValueError('compute table source commit mismatch')
    if (table.get('design') != 'qwen_compute' or table.get('role') != 'die_plan'
            or table.get('coverage') != 'complete' or table.get('problem_count') != 0
            or table.get('problems') or plan.get('generator') != 'tools/qwen_layerbench/netlist_relay_stages.py'):
        raise ValueError('need complete problem-free compute netlist-walk table')
    if not plan.get('sources') or plan['sources'][0] != doc['table_die_origin']:
        raise ValueError('compute table die origin mismatch')
    if doc.get('scope') not in ('diagnostic', 'release_candidate'):
        raise ValueError('explicit diagnostic/release_candidate scope required')
    return dict(schema=doc['schema'], scope=doc['scope'], source_commit=commit,
                files=selected, plan_id=plan['id'], table_digest=table['digest'],
                qualification='IDENTITY_ONLY; source/view/native/physical/age qualification remains separate')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--diagnostic', action='store_true')
    a = ap.parse_args()
    try:
        receipt = validate(a.manifest)
        if receipt['scope'] == 'diagnostic' and not a.diagnostic:
            raise ValueError('diagnostic compute pair requires OT_BIND_DIAGNOSTIC=1')
        Path(a.out).write_text(json.dumps(receipt, indent=2) + '\n')
        for value in (receipt['files']['die_v']['path'], receipt['files']['relay_stages']['path'], receipt['source_commit']):
            print(value)
    except (ValueError, KeyError, OSError) as exc:
        ap.exit(1, f'COMPUTE_PAIR FAIL {exc}\n')


if __name__ == '__main__':
    main()
