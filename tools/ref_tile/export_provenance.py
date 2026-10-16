"""Transactional provenance for NEW view exports; never repair historical bundles."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from collections import Counter


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def check_invariants(raw, transformed, parse_lef):
    """Require identical macro identity/outline and pin ABI; original rects are a multiset subset."""
    def geometry(text):
        names = re.findall(r'(?m)^\s*MACRO\s+(\S+)\s*$', text)
        if len(names) != 1:
            raise ValueError('expected exactly one MACRO')
        macro = parse_lef(text)
        origins = re.findall(r'\bORIGIN\s+([^;]+);', text)
        return macro, [tuple(float(v) for v in origin.split()) for origin in origins]
    a, ao = geometry(raw)
    b, bo = geometry(transformed)
    for key in ('name', 'W', 'H'):
        if a[key] != b[key]:
            raise ValueError(f'changed macro {key}')
    if ao != bo or a['pins'].keys() != b['pins'].keys():
        raise ValueError('changed macro origin or pin names')
    for name, pin in a['pins'].items():
        after = b['pins'][name]
        if any(pin[key] != after[key] for key in ('direction', 'use')):
            raise ValueError(f'changed pin ABI: {name}')
        if Counter(pin['rects']) - Counter(after['rects']):
            raise ValueError(f'original pin rectangles removed/changed: {name}')
    return {'macro_outline': 'PASS', 'pin_names_directions_uses': 'PASS', 'original_pin_rectangles_retained': 'PASS'}


def finalize(out, top, helper, lint_module, lint_kwargs=None, transform=True):
    """Preserve raw exporter record, validate candidate, then publish final LEF/hash atomically.

    On any failure abstract.json is marked !ok, the raw LEF remains untouched, and
    a failure receipt is retained. The caller must already check view_export's exit.
    """
    out, helper = Path(out), Path(helper)
    manifest_path = out / 'abstract.json'
    manifest = json.loads(manifest_path.read_text())
    provenance = out / 'provenance'
    receipt = {'schema': 1, 'kind': 'abstract_pin_stub' if transform else 'identity', 'status': 'FAIL'}
    try:
        if provenance.exists():
            raise ValueError('existing provenance: use a fresh export directory')
        provenance.mkdir()
        raw_manifest = provenance / 'view_export.abstract.json'
        raw_manifest.write_bytes(manifest_path.read_bytes())
        manifest['ok'] = False
        write_json(manifest_path, manifest)
        if not json.loads(raw_manifest.read_text()).get('ok'):
            raise ValueError('raw exporter manifest not ok')
        lef = out / f'{top}.lef'
        expected = manifest['files'][lef.name]
        if sha(lef) != expected:
            raise ValueError('raw LEF hash differs from exporter manifest')
        raw_dir = provenance / 'raw'
        raw_dir.mkdir()
        raw = raw_dir / lef.name
        raw.write_bytes(lef.read_bytes())
        candidate = provenance / (top + '.candidate.lef')
        receipt.update(input={'path': str(raw.relative_to(out)), 'sha256': expected},
                       environment={key: os.environ.get(key) for key in ('OT_OBS_CLOSE', 'OT_OBS_CLOSE_UM')})
        if transform:
            helper_hash = sha(helper)
            receipt['helper'] = {'path': str(helper), 'sha256': helper_hash}
            command = [sys.executable, str(helper), str(raw), str(candidate)]
            run = subprocess.run(command, capture_output=True, text=True)
            receipt.update(command=command, returncode=run.returncode, stdout=run.stdout, stderr=run.stderr)
            if run.returncode:
                raise ValueError(f'abstract_pin_stub exit {run.returncode}')
            if sha(helper) != helper_hash or sha(raw) != expected:
                raise ValueError('helper or raw input changed during transformation')
        else:
            candidate.write_bytes(raw.read_bytes())
        receipt['invariants'] = check_invariants(raw.read_text(), candidate.read_text(), lint_module.parse_lef)
        lint = lint_module.lint(str(candidate), str(out), **(lint_kwargs or {}))
        write_json(out / 'child_lint.json', lint)
        receipt['child_lint'] = lint
        if lint['verdict'] != 'PASS':
            raise ValueError('child_lint FAIL')
        final_hash = sha(candidate)
        receipt.update(status='PASS', output={'path': lef.name, 'sha256': final_hash})
        receipt_path = provenance / 'abstract_pin_stub.json'
        write_json(receipt_path, receipt)
        manifest['files'][lef.name] = final_hash
        manifest['export_provenance'] = dict(schema=1, raw_manifest=str(raw_manifest.relative_to(out)),
            raw_manifest_sha256=sha(raw_manifest), transformation=str(receipt_path.relative_to(out)),
            transformation_sha256=sha(receipt_path))
        manifest['ok'] = True
        candidate.replace(lef)
        write_json(manifest_path, manifest)
        return lint
    except Exception as exc:
        manifest['ok'] = False
        manifest['export_failure'] = str(exc)
        write_json(manifest_path, manifest)
        receipt['error'] = str(exc)
        # Existing records are evidence, never overwrite them on a retry.
        if provenance.exists() and not (provenance / 'abstract_pin_stub.json').exists():
            write_json(provenance / 'abstract_pin_stub.json', receipt)
        return {'verdict': 'FAIL', 'fails': [str(exc)]}
