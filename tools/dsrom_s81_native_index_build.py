#!/usr/bin/env python3
"""Build only owner-selected existing S81 native index/selector leaves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--selection', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--jobs', type=int, required=True)
p.add_argument('--unit', choices=('scorer','selector'))
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
s = json.loads(a.selection.read_text())
if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
    raise RuntimeError('build requires clean pinned worktree')
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
verilator = '/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
a.out.mkdir(parents=True, exist_ok=False)
(a.out/'selection.json').write_text(json.dumps(s, indent=2)+'\n')
ready = []
for key, top, required in (
    ('scorer', 'ot_hdc_v41x_idx_pool_adapt',
     ['AW','NW','W','G','IL','MP','IH','NPC','HAW','HLENW','HTAGW','HBEATW',
      'SHARDED','SLICE_SECTORS','RING','RING_RSB','RING_RTAIL','RING_WB','RING_GA']),
    ('selector', 'ot_hdc_v41x_xu_adapt',
     ['AW','NW','K','IKW','SK_STEP','X_SEL','X_EG','SQ','SW','SK','SLAW'])):
    if a.unit and key != a.unit:
        continue
    unit = s[key]
    params = unit['parameters']
    if set(params) != set(required):
        raise RuntimeError(f'{key}: explicit complete selected parameters required')
    if key == 'scorer' and (params['AW'],params['NW']) != (30,21):
        raise RuntimeError('scorer AW30/NW21 required')
    if key == 'selector' and any(params[k] != v for k,v in
                               dict(X_SEL=1,SQ=4,SW=16).items()):
        raise RuntimeError('selector selected geometry mismatch')
    if key == 'selector' and params['SK'] not in (512,2048):
        raise RuntimeError('selector capacity must match selected S81 source')
    sources = unit['sources']
    if not sources or any('/test/' in x or not (root/x).is_file() for x in sources):
        raise RuntimeError('existing production source closure required')
    prefix = unit['prefix']
    obj = a.out/key/'obj'; obj.mkdir(parents=True)
    cmd = [verilator,'--cc','-Wno-fatal','--output-split','20000',
           '--output-split-cfuncs','200','-CFLAGS','-O0 -fPIC',
           '--top-module',top,'--prefix',prefix,'--Mdir',str(obj)]
    cmd += ['-D'+x for x in s.get('defines', []) + unit.get('defines', [])]
    cmd += [f'-G{k}={v}' for k,v in params.items()]
    cmd += [str(root/x) for x in sources]
    entry = dict(unit=key,source_commit=sha,parameters=params,history_binding=s['history_binding'],
                 command=cmd,pid=os.getpid(),
                 sources={x:hashlib.sha256((root/x).read_bytes()).hexdigest() for x in sources})
    (a.out/key/'build.json').write_text(json.dumps(entry,indent=2)+'\n')
    with (a.out/key/'frontend.log').open('w') as log:
        subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    header = obj/(prefix+'.h')
    entry['header'] = str(header)
    entry['header_sha256'] = hashlib.sha256(header.read_bytes()).hexdigest()
    (a.out/key/'headers_ready.json').write_text(json.dumps(entry,indent=2)+'\n')
    print(json.dumps(dict(state='headers_ready',unit=key,header=str(header))),flush=True)
    ready.append(entry)
for entry in ready:
    key = entry['unit']
    prefix = s[key]['prefix']
    obj = a.out/key/'obj'
    cmd = ['make','-C',str(obj),'-f',prefix+'.mk',f'-j{a.jobs}',
           'OPT_FAST=-O0','OPT_SLOW=-O0',prefix+'__ALL.a']
    with (a.out/key/'compile.log').open('w') as log:
        subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    archive = obj/(prefix+'__ALL.a')
    entry.update(archive=str(archive),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (a.out/key/'ready.json').write_text(json.dumps(entry,indent=2)+'\n')
    print(json.dumps(dict(state='archive_ready',unit=key,archive=str(archive))),flush=True)
(a.out/'ready.json').write_text(json.dumps(ready,indent=2)+'\n')
