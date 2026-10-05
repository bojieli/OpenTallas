#!/usr/bin/env python3
"""Read-only coordination scope and byte-exact source preservation replay."""
import ast
import sys
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
p = json.loads((HERE / 'proof-r1.json').read_text())
for path, sha in p['final_document_sha256'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
for path, sha in p['unchanged_source_sha256'].items():
    raw = (ROOT / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha, path
    assert raw == subprocess.check_output(['git', 'show', p['parent_commit'] + ':' + path], cwd=ROOT), path
sys.path.insert(0, str(ROOT / 'tools'))
from check_prose_figures import resolve_json
for ref in p['git_origin_records']:
    raw = subprocess.check_output(['git', 'show', ref['commit'] + ':' + ref['path']], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == ref['sha256'], ref['path']
    body = json.loads(raw)
    for selector, expected in ref['field_assertions'].items():
        assert resolve_json(body, selector, '') == expected, (ref['path'], selector)
historical = json.loads((ROOT / 'results/uarch/w19_hbm_token_ar.json').read_text())
for selector, expected in p['historical_W19_assertions'].items():
    assert resolve_json(historical, selector, '') == expected, selector
tree = ast.parse((ROOT / 'tools/uarch_model.py').read_text())
assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'HBM_W19' for t in n.targets))
for key, expected in p['declared_HBM_W19_assertions'].items():
    value = next(k.value for k in assignment.value.keywords if k.arg == key)
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "dict":
        observed = {k.arg: ast.literal_eval(k.value) for k in value.keywords}
    else:
        observed = ast.literal_eval(value)
    assert observed == expected, key
scope = (ROOT / 'docs/HEADLINE_BUNDLE_SCOPE.md').read_text()
assert 'Legacy architecture-DAG group-slot comparison' in scope
assert 'Historical W19 emitted-program estimate' in scope
assert 'Newer W19 composition selected by the unified model declaration' in scope
assert 'MTP τ rows are sensitivities, not adopted agentic acceptance' in scope
s = (ROOT / 'TASKS.md').read_text()
edits = json.loads((HERE / 'edits-r1.json').read_text())
for edit in edits:
    assert edit['after'] in s, edit['after']
assert 'a peer USER DECISION label is not session adoption' in s
assert 'Claude: sole KV calendar/fill model owner' in s
assert 'Maxwell/Archimedes retain their selected relay work unchanged' in s
assert 'this coordination gives no launch/adoption permission' in s
print(f"PASS: {len(edits)} bounded coordination edits; {len(p['unchanged_source_sha256'])} unchanged source/publication pins; 3 Git-origin records and W19 declaration/historical assertions; no adoption/launch permission")
