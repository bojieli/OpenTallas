#!/usr/bin/env python3
"""Verify the cold OpenDB manifest and immutable files before admitting a PRD seed."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def verify(source, output, manifest, tool):
    source, output, manifest, tool = map(Path, (source, output, manifest, tool))
    if len({p.resolve() for p in (source, output, manifest, tool)}) != 4:
        raise ValueError('input/output/manifest/tool alias')
    m = json.loads(manifest.read_text())
    if (m.get('schema') != 'opentallas.prd_filler_preclean.v1'
            or m.get('status') != 'DERIVED_FINAL_SEED_READY_NOT_ADOPTED'
            or m.get('preservation_match') is not True):
        raise ValueError('missing successful preservation manifest')
    for key, path in [('source_sha256', source), ('output_sha256', output), ('tool_sha256', tool)]:
        if m.get(key) != sha_file(path):
            raise ValueError(f'{key} does not match immutable file')
    before, after, removed = (m.get(k) for k in ('instances_before', 'instances_after', 'removed'))
    if any(type(n) is not int or n < 0 for n in (before, after, removed)) or before - after != removed:
        raise ValueError('inconsistent typed filler counts')
    if removed == 0 and m.get('allow_empty') is not True:
        raise ValueError('empty preclean was not explicitly allowed')
    if m.get('output_bytes') != output.stat().st_size or output.stat().st_size == 0:
        raise ValueError('output size mismatch')
    p = m.get('preserved') or {}
    if p.get('nonfiller_instances') != after:
        raise ValueError('remaining instances are not the preserved nonfiller set')
    for key in ('nonfiller_placement_sha256', 'ports_sha256',
                'nonpg_net_connectivity_and_exact_wire_sha256', 'clock_connectivity_and_exact_wire_sha256'):
        if not isinstance(p.get(key), str) or not re.fullmatch('[0-9a-f]{64}', p[key]):
            raise ValueError(f'missing preserved fingerprint {key}')
    for key in ('ports', 'nonpg_nets', 'clock_nets', 'wire_ops'):
        if type(p.get(key)) is not int or p[key] < 0:
            raise ValueError(f'invalid preserved count {key}')
    if p['clock_nets'] > p['nonpg_nets']:
        raise ValueError('clock count exceeds non-PG count')
    return {'status': 'VERIFIED_FINAL_SEED', 'source': str(source), 'output': str(output),
            'manifest': str(manifest), 'manifest_sha256': sha_file(manifest),
            'source_sha256': m['source_sha256'], 'output_sha256': m['output_sha256'],
            'tool_sha256': m['tool_sha256'], 'removed': removed, 'preserved': p}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source'); ap.add_argument('output'); ap.add_argument('manifest')
    ap.add_argument('--tool', required=True); ap.add_argument('--receipt')
    a = ap.parse_args()
    try:
        if a.receipt and Path(a.receipt).resolve() in {Path(p).resolve() for p in (a.source, a.output, a.manifest, a.tool)}:
            raise ValueError("receipt aliases a proof input or seed")
        result = verify(a.source, a.output, a.manifest, a.tool)
        if a.receipt:
            Path(a.receipt).write_text(json.dumps(result, indent=2) + '\n')
    except (OSError, ValueError, TypeError) as exc:
        raise SystemExit(f'PRD_PRECLEAN_REFUSE: {exc}') from exc
    print(json.dumps(result))


if __name__ == '__main__':
    main()
