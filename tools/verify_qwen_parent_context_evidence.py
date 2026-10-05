#!/usr/bin/env python3
"""Verify final additive QROM interface evidence and immutable source pins."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_rom_parent_context_service_20261002'

def verify():
    def obj(name):return json.loads((OUT/name).read_text())
    def check(path,digest):
        actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        if actual!=digest:raise ValueError('pin mismatch: '+path)
    for path,digest in obj('artifact-sha256-r2.json').items():check(path,digest)
    for path,digest in obj('implementation-pins-r2.json').items():check(path,digest)
    m=obj('model-r7.json')
    for path,digest in m['source_sha256'].items():
        check(path,digest)
        blob=subprocess.check_output(['git','show',m['parent']+':'+path],cwd=ROOT)
        if hashlib.sha256(blob).hexdigest()!=digest:raise ValueError('parent mismatch: '+path)
    p=obj('preservation-r1.json')
    for path,digest in p['pinned_original_sha256'].items():check(path,digest)
    c=p['numerical_capture'];check(c['capture_path'],c['capture_sha256'])
    return dict(verdict='PASS_PIN_PRESERVATION_ONLY',source_pins=len(m['source_sha256']),
                originals=len(p['pinned_original_sha256']),actual_production_qualified=False,
                physical_admission=False)

if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
