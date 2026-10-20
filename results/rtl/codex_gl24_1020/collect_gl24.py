#!/usr/bin/env python3
"""Require all sixteen owner views of every measured GL24 layer."""
import hashlib
import json
import re
from pathlib import Path

root=Path('/srv/opentallas-scratch/claude/codex-gl24-1020')
def digest(path):
    sha=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):sha.update(chunk)
    return sha.hexdigest()
def fields(line):return dict(re.findall(r'(\w+)=(\S+)',line))
exe=digest(root/'Vtb_toksim_gath')
assert exe=='72b85d0205302141e4909d455e7e5d272a81d9cb407f581e77c479e60446f9fb'
layers={}
for layer in ['L24','L28','L32','L36']:
    views={}
    for die in range(4):
        for stack in range(4):
            name=f'{layer}_v{die}{stack}'
            case=root/'cases'/name/'case.json'
            meta=json.loads(case.read_text())
            assert meta['layer']==layer and meta['view']==dict(die=die,stack=stack)
            assert meta['n_sel']==512 and meta['T']==640 and all(meta['anchors'].values())
            for image,sha in meta['images'].items():assert digest(case.parent/image)==sha,(name,image)
            log=root/'out'/f'run_{name}_g0.log'
            if die or stack:
                wrapper=(root/'out'/f'owner_{layer}_{die}{stack}.log').read_text()
                assert f'GL24_DONE {layer} {die}{stack}' in wrapper,name
            lines=log.read_text().splitlines()
            g=fields(next(line for line in lines if line.startswith('GATH_T ')))
            s=fields(next(line for line in lines if line.startswith('SVCRS ')))
            assert s['verdict']=='PASS',name
            for key in ['sc_errors','se_errors','order_errors','se_bad_slices','sm_rows_bad','pv_errors','pv_bad_slices','jd_fault','root_fault','slice_faults','cred_err']:
                assert int(s[key])==0,(name,key,s[key])
            assert int(s['first_fault_code'],16)==0
            assert int(s['pv_checked'])==2048 and int(s['root_beats'])==160 and int(s['done'])==2
            assert int(s['sc_checked'])>0 and int(s['se_checked'])>0
            assert int(g['static_io'])==1 and int(g['sel_gap'])==0 and int(g['lat'])==40
            span=int(g['gather_span'])
            assert span==int(g['own_done_last'])-int(g['t_sel'])+1
            views[f'{die},{stack}']=dict(span=span,own_reads=int(g['own_reads']),own_beats=int(g['own_beats']),
                sc_checked=int(s['sc_checked']),se_checked=int(s['se_checked']),pv_checked=int(s['pv_checked']),
                case_sha256=digest(case),log_sha256=digest(log),case=str(case.relative_to(root)),log=str(log.relative_to(root)))
    worst=max(views,key=lambda view:views[view]['span'])
    layers[layer]=dict(views=views,worst_view=worst,worst_span=views[worst]['span'],all16_PASS=True)
result=dict(scope='Exact four measured layers; all16owner views; existing GATH binary and released fixture anchors',
            exe_sha256=exe,layers=layers,per_layer={layer:rec['worst_span'] for layer,rec in layers.items()},
            all64_PASS=True,full_layer_token_qualification=False)
(root/'gl24_collection.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key!='layers'},indent=2))
