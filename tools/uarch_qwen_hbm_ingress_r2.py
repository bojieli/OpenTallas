#!/usr/bin/env python3
"""Additive current-generator replay; preserves all original model receipts."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
import uarch_qwen_l2_injector as L
import uarch_qwen_hbm_ingress as I

ROOT=Path(__file__).resolve().parents[1]
RECORDS=ROOT/'results/uarch/qwen_hbm_connected_20261001'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def replay(revision):
    revision=subprocess.check_output(['git','rev-parse',revision],cwd=ROOT,text=True).strip()
    source=subprocess.check_output(['git','show',revision+':tools/uarch_model.py'],cwd=ROOT)
    spec=importlib.util.spec_from_loader('current_qwen_uarch_replay',loader=None)
    module=importlib.util.module_from_spec(spec)
    module.__file__=str(ROOT/'tools/uarch_model.py')
    import sys
    sys.modules[spec.name]=module
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    L.U=module;I.U=module
    outputs={}
    for name,composer in [('L2_injector',L.compose),('HBM_ingress',I.compose)]:
        historical=RECORDS/(name+'_before_RTL.json')
        old=json.loads(historical.read_text())
        fresh=composer()
        old_numbers=[];new_numbers=[]
        def numbers(x,path,out):
            if isinstance(x,dict):
                for k,v in x.items():
                    if k!='source_sha256':numbers(v,path+'/'+k,out)
            elif isinstance(x,list):
                for k,v in enumerate(x):numbers(v,path+'/'+str(k),out)
            elif isinstance(x,(int,float)) and not isinstance(x,bool):out.append((path,x))
        numbers(old,'',old_numbers);numbers(fresh,'',new_numbers)
        assert old_numbers==new_numbers, 'current generator changed numerical model'
        fresh['source_sha256']['tools/uarch_model.py']=sha(source)
        for path,digest in fresh['source_sha256'].items():
            actual=sha(source) if path=='tools/uarch_model.py' else sha((ROOT/path).read_bytes())
            assert actual==digest,path
        fresh['current_generator_replay']={
            'revision':revision,'source_sha256':sha(source),
            'historical_record':str(historical.relative_to(ROOT)),
            'historical_record_sha256':sha(historical.read_bytes()),
            'historical_generator_sha256':old['source_sha256']['tools/uarch_model.py'],
            'numeric_paths_checked':len(old_numbers),'numeric_values_identical':True,
            'generator_path_resolution':'git show at immutable revision; imported with retained model input root',
            'historical_inputs_retained':True,
            'replay_tool_sha256':sha(Path(__file__).read_bytes())}
        fresh['adoption']=False;fresh['physical_build_ready']=False
        fresh['fit_admission']={'analytical_die_area_within_budget':fresh['area']['composed_die_mm2']<fresh['area']['core_available_mm2'],
            'SM_slot_fit':False,'real_full_32SM_LEF_fit_qualified':False,
            'contextual_SS_FF_qualified':False,'no_adoption':True}
        outputs[name]=fresh
    l2_bytes=(json.dumps(outputs['L2_injector'],indent=2)+'\n').encode()
    outputs['HBM_ingress']['current_L2_dependency']={
        'path':'results/uarch/qwen_hbm_connected_20261001/L2_injector_before_RTL_r2.json',
        'sha256':sha(l2_bytes),'numeric_values_identical':True,
        'fit_ready_for_physical_build':False}
    for name,value in outputs.items():
        with (RECORDS/(name+'_before_RTL_r2.json')).open('x') as f:
            json.dump(value,f,indent=2);f.write('\n')
    return {name:value['current_generator_replay']['numeric_paths_checked'] for name,value in outputs.items()}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True)
    print(json.dumps(replay(parser.parse_args().revision)))
