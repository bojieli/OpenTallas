#!/usr/bin/env python3
"""Preserve the six original06 projection traces without touching its live run."""
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

REMOTE = r'''
import hashlib,json
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/s81-hwin-early-source-1019/run_four_state_fullshape_06/four_state')
files={}
for seed in [1,19,313]:
    for role in ['original','projected']:
        for suffix in ['trace','log']:
            name=f'equiv_{role}_seed{seed}.{suffix}'
            raw=(p/name).read_bytes()
            files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
print(json.dumps(files))
'''
out = Path(__file__).resolve().parent / 'projection_traces'
result = subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',
    'ot-epyc8','python3 -c '+shlex.quote(REMOTE)],capture_output=True,text=True,
    check=True,timeout=120)
files = json.loads(result.stdout)
out.mkdir(exist_ok=True)
hashes = {}
for name, item in files.items():
    raw=item['text'].encode()
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    target=out/name
    if target.exists():
        assert target.read_bytes()==raw, f'Changed receipt: {name}'
    else:
        with target.open('xb') as stream: stream.write(raw)
    hashes[name]=item['sha256']
for seed in [1,19,313]:
    assert files[f'equiv_original_seed{seed}.trace']['text']==files[f'equiv_projected_seed{seed}.trace']['text'], f'Projection mismatch: {seed}'
manifest={'sha256':hashes,'byte_equal_trace_seeds':[1,19,313],
    'scope':'Original06 actual trace pairs; no namespace-package substitution or live-run modification.'}
raw=(json.dumps(manifest,indent=2)+'\n').encode()
target=out/'manifest.json'
if target.exists(): assert target.read_bytes()==raw
else:
    with target.open('xb') as stream: stream.write(raw)
print(json.dumps({'files':len(hashes),'byte_equal_trace_seeds':[1,19,313]}))
