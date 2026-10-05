#!/usr/bin/env python3
"""Read-only replay: exact record basis, historical scope and unchanged source pins."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from check_prose_figures import resolve_json

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check():
    manifest = json.loads((HERE / 'proof-r1.json').read_text())
    for path, sha in manifest['unchanged_source_sha256'].items():
        data = (ROOT / path).read_bytes()
        assert digest(data) == sha, ('source changed', path)
        original = subprocess.check_output(['git', 'show', manifest['base_commit'] + ':' + path], cwd=ROOT)
        assert original == data, ('baseline source changed', path)
    for path, sha in manifest['final_document_sha256'].items():
        assert digest((ROOT / path).read_bytes()) == sha, ('document changed', path)
    for record in manifest['record_assertions']:
        data = json.loads((ROOT / record['path']).read_text())
        assert resolve_json(data, record['selector'], '') == record['expected'], record
    edits = json.loads((HERE / 'edits-r1.json').read_text())
    for edit in edits:
        assert edit['after'] in (ROOT / edit['path']).read_text(), ('edit absent', edit['after'])
    micro = (ROOT / 'docs/MICROARCH_MODEL.md').read_text()
    atlas = (ROOT / 'docs/ARCHITECTURE_ATLAS.html').read_text()
    scope = (ROOT / 'docs/HEADLINE_BUNDLE_SCOPE.md').read_text()
    assert '| 0.5–0.668 µs | 2,785 | 2,920 |' in micro, 'independent fabric row overwritten'
    assert 'No current product-rate headline is adopted.' in atlas
    assert 'Historical TP-2/DFlash model, nonadopted for the current TP-4 AR target.' in atlas
    assert 'actual_sustained_PHY_Bps=null' in scope
    assert 'adoption` is false' in scope
    assert 'QWEN_ROM_PRODUCT = dict(k=4, G=6144, link="board", packages=2, stacks_per_die=4)' in (ROOT / 'tools/uarch_model.py').read_text()
    print(f"PASS: {len(manifest['record_assertions'])} exact record assertions; {len(manifest['unchanged_source_sha256'])} byte-exact baseline sources; {len(edits)} scoped edits; historical/publication scope")

if __name__ == '__main__':
    check()
