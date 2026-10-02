#!/usr/bin/env python3
"""Replay historical pure models with committed archival inputs. Never builds/launches."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'results/uarch/w17_owner_progress_archival_closure_20261002'
def manifest():
    m=json.loads((ARCHIVE/'manifest.json').read_text())
    for origin,item in m['files'].items():
        p=(ROOT/item['archival_path']).resolve()
        if not p.is_relative_to(ARCHIVE.resolve()):raise ValueError('archive path escape')
        if not p.is_file() or p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('archival byte mismatch '+origin)
    return m

def bind(module,kind):
    pins=manifest()['files']
    module.ROOT=ARCHIVE/'failed_root';module.OWNER=ARCHIVE/'owner'
    if kind=='d1':
        module.MODEL=module.OWNER/'tools/w17_window_epoch9_timing_model.py'
        module.PRED=module.OWNER/'results/uarch/w17_window_epoch9_reproducible_prediction_20261001/run1/prediction.json'
        module.EVENTS=module.PRED.parent/'credit1_events.jsonl'
        def exact_git_bytes(command,**kwargs):
            if len(command)!=3 or command[:2]!=['git','show']:raise ValueError('unapproved external command in archival replay')
            key='git:'+command[2]
            if key not in pins:raise ValueError('unarchived original source '+key)
            return (ROOT/pins[key]['archival_path']).read_bytes()
        module.subprocess=SimpleNamespace(check_output=exact_git_bytes)
    elif kind=='r2':
        module.PROFILE=ARCHIVE/'profile/frontend_profile.json'
        module.TRANSFER=ARCHIVE/'baseline/binary_transfer.json'
        module.PRED=module.OWNER/'results/uarch/w17_window_epoch9_producer_prediction_20261001_attempt3/prediction.json'
        module.JOURNAL=module.PRED.parent/'L0_no_retain_events.jsonl'
        oldcone=module.cone
        def archival_cone(paths):
            mapped=[]
            for p in paths:
                if str(p) in pins:mapped.append(ROOT/pins[str(p)]['archival_path'])
                elif p.is_relative_to(ROOT):mapped.append(p)
                else:raise ValueError('unarchived external source '+str(p))
            return oldcone(mapped)
        module.cone=archival_cone
    else:raise ValueError('unknown historical model')
    return module

def load(kind):
    file={'d1':'w17_D1_PC24_inputs.py','r2':'w17_owner_progress_resource_r2.py'}[kind]
    spec=importlib.util.spec_from_file_location('archival_'+kind,ROOT/'tools'/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return bind(mod,kind)

def replay():
    results={}
    original={'d1':ROOT/'results/uarch/w17_D1_PC24_inputs_20261002/record.json','r2':ROOT/'results/uarch/w17_owner_progress_resource_r2_20261002/model.json'}
    origins={str(ROOT/v['archival_path']):k for k,v in manifest()['files'].items()}
    for kind in ['d1','r2']:
        got=load(kind).build()
        if kind=='r2':got['profile_pins']={origins.get(k,k):v for k,v in got['profile_pins'].items()}
        expected=json.loads(original[kind].read_text())
        if got!=expected:raise ValueError('historical '+kind+' record mismatch; no adjustment')
        results[kind]={'all_fields_identical':True,'record_sha256':hashlib.sha256(original[kind].read_bytes()).hexdigest()}
    return {'verdict':'PASS_COMMITTED_ARCHIVAL_INPUT_CLOSURE_ALL_HISTORICAL_FIELDS_IDENTICAL','archival_files':len(manifest()['files']),'records':results,'old_files_edited':False,'private_worktree_reads':False,'tmp_profile_reads':False,'compile_or_runtime_launched':False}
if __name__=='__main__':print(json.dumps(replay(),indent=2))
