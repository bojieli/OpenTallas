#!/usr/bin/env python3
"""Read completed HWIN receipts; never modify or restart the running job."""
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

REMOTE = r'''
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
base=Path('/srv/opentallas-scratch/claude/s81-hwin-early-source-1019')
run=base/'run_four_state_fullshape_06'/'four_state'
scope=subprocess.run(['systemctl','--user','show','oth-ubuntu-2036610-1792446395.scope','--property=ActiveState,SubState'],capture_output=True,text=True)
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'scope_stdout':scope.stdout,'scope_stderr':scope.stderr,'scope_returncode':scope.returncode,'phases':[],'source_hashes':{},'compiled_input_hashes':{},'static_receipts':{}}
for p in sorted(run.glob('run_phase*.log')):
    raw=p.read_bytes(); text=raw.decode(errors='replace')
    failed=any(token in text for token in ['FATAL:','ERROR:','MUWIN FAIL','EARLY_MITER FAIL'])
    complete='MUWIN PASS' in text and 'EARLY_MITER edges' in text and not failed
    result['phases'].append({'name':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'complete_pass':complete,'failed':failed,'text':text if complete or failed else None})
for p in sorted((base/'src_rx06').rglob('*')):
    if p.is_file() and p.suffix in ['.sv','.v','.sh','.py']:
        result['source_hashes'][str(p.relative_to(base/'src_rx06'))]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in sorted(run.iterdir()):
    if p.is_file() and (p.suffix in ['.sv','.diff','.json'] or p.name in ['iverilog_version.txt','tb.vvp','primitive_probe.log']):
        raw=p.read_bytes()
        result['compiled_input_hashes'][p.name]=hashlib.sha256(raw).hexdigest()
        if p.name!='tb.vvp': result['static_receipts'][p.name]=raw.decode()
print(json.dumps(result))
'''

out = Path(__file__).resolve().parent
result = subprocess.run(
    ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'ot-epyc8',
     'python3 -c ' + shlex.quote(REMOTE)],
    capture_output=True, text=True, check=True, timeout=120,
)
data = json.loads(result.stdout)
for previous in sorted((out / 'observations').glob('*.json')):
    old = json.loads(previous.read_text())
    assert old['source_hashes'] == data['source_hashes'], 'Staged source changed'
    if 'compiled_input_hashes' in old:
        assert old['compiled_input_hashes'] == data['compiled_input_hashes'], 'Compiled input changed'
for name, value in data.pop('static_receipts').items():
    path = out / 'static_receipts' / name
    raw = value.encode()
    assert hashlib.sha256(raw).hexdigest() == data['compiled_input_hashes'][name]
    if path.exists():
        assert path.read_bytes() == raw, f'Changed static receipt: {path}'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
for phase in data['phases']:
    text = phase.pop('text')
    if text is None:
        continue
    path = out / 'completed' / phase['name']
    raw = text.encode()
    assert hashlib.sha256(raw).hexdigest() == phase['sha256']
    if path.exists():
        assert path.read_bytes() == raw, f'Changed completed receipt: {path}'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
snapshot = out / 'observations' / (data['observed_utc'].replace(':', '_') + '.json')
snapshot.parent.mkdir(parents=True, exist_ok=True)
with snapshot.open('x') as stream:
    json.dump(data, stream, indent=2)
    stream.write('\n')
print(json.dumps({'observation': str(snapshot), 'scope': data['scope_stdout'],
                  'phases': data['phases'], 'source_files': len(data['source_hashes'])}, indent=2))
