#!/usr/bin/env python3
"""Read final original06 logs only after every required receipt is present.

This checks log contents; it does not invent the outer OT_RUN_EXIT status.
"""
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

REMOTE = r'''
import json
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/s81-hwin-early-source-1019/run_four_state_fullshape_06/four_state')
names=['build.log','build_equiv_original.log','build_equiv_projected.log','primitive_probe_build.log']
names += ['run_phase'+str(n)+'.log' for n in [0,1,2,3,4,5,6,7,8,90,93]]
names += [prefix+m+'.log' for m in ['PAYLOAD','CONTROL'] for prefix in ['build_mutant_','run_mutant_']]
missing=[n for n in names if not (p/n).is_file()]
if missing: raise SystemExit('PENDING final receipts: '+','.join(missing))
print(json.dumps({n:(p/n).read_text() for n in names}))
'''
result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',
    'ot-epyc8','python3 -c '+shlex.quote(REMOTE)],capture_output=True,text=True,
    check=True,timeout=120)
files=json.loads(result.stdout)
for phase in [0,1,2,3,4,5,6,7,8,90,93]:
    text=files[f'run_phase{phase}.log']
    assert 'MUWIN PASS' in text and 'EARLY_MITER edges' in text
    assert not any(x in text for x in ['FATAL:','ERROR:','MUWIN FAIL','EARLY_MITER FAIL'])
for mutant in ['PAYLOAD','CONTROL']:
    text=files[f'run_mutant_{mutant}.log']
    assert 'EARLY_X_CAUSAL' in text and 'EARLY_X' in text and 'FATAL:' in text
out=Path(__file__).resolve().parent/'final_receipts'
out.mkdir(exist_ok=True)
hashes={}
for name,text in files.items():
    raw=text.encode(); target=out/name
    if target.exists(): assert target.read_bytes()==raw, f'Changed final receipt: {name}'
    else:
        with target.open('xb') as stream: stream.write(raw)
    hashes[name]=hashlib.sha256(raw).hexdigest()
manifest={'sha256':hashes,'all_eleven_phase_logs':'PASS',
    'qualified_payload_control_X_causal_logs':'expected fatal witnesses present',
    'outer_OT_RUN_EXIT':'NOT_INFERRED: requires original client receipt',
    'scope':'Exact original06 logs; no source, schedule, reset, namespace or runtime changes.'}
raw=(json.dumps(manifest,indent=2)+'\n').encode(); target=out/'manifest.json'
if target.exists(): assert target.read_bytes()==raw
else:
    with target.open('xb') as stream: stream.write(raw)
print(json.dumps({'files':len(hashes),'phase_logs':'all eleven PASS','outer_OT_RUN_EXIT':'NOT_INFERRED'}))
