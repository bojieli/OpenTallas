#!/usr/bin/env python3
"""Added-only r2 preparation; reuse pinned namespaces and explicitly select r2 bench."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'results/rtl/dsrom_actual_element_prepare_r2_20261001/model.json'

def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def verify_pins():
    model=json.loads(MODEL.read_text())
    for path,pin in model['preserved_files_sha256'].items():
        data=git('show',model['preserved_commit']+':'+path)
        if sha(data)!=pin or (ROOT/path).read_bytes()!=data:raise ValueError('preserved file changed: '+path)
    for path,pin in model['new_artifact_pins'].items():
        if sha((ROOT/path).read_bytes())!=pin:raise ValueError('r2 artifact changed: '+path)
    for path,pin in model['source_pins'].items():
        if sha(git('show',model['source_commit']+':'+path))!=pin['sha256']:raise ValueError('source changed: '+path)
    for pin in model['authority_records']+[model['source_case_driver']]:
        if sha(git('show',pin['commit']+':'+pin['path']))!=pin['sha256']:raise ValueError('authority changed: '+pin['path'])
    return model

def prepare(out):
    if out.exists():raise FileExistsError(out)
    model=verify_pins()
    spec=importlib.util.spec_from_file_location('legacy_prepare',ROOT/'tools/prepare_dsrom_actual_element_gate.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    # Original helper-body substitution and namespace algorithm are reused byte-for-byte.
    files=legacy.generate(legacy.load_sources())
    files[Path(model['bench_path']).name]=(ROOT/model['bench_path']).read_text()
    files['dsrom_actual_element_rom.cpp']=(ROOT/'rtl/test/dsrom_actual_element_rom.cpp').read_text()
    pins={n:sha(t.encode()) for n,t in files.items()}
    if pins!=model['generated_files_sha256']:raise ValueError('r2 generated package mismatch')
    if 'tb_dsrom_actual_element_gate.sv' in files:raise ValueError('old bench must not enter r2 compile package')
    out.mkdir(parents=True,exist_ok=False)
    for name,text in files.items():
        with (out/name).open('x') as f:f.write(text)
    record=dict(status='R2_PREPARED_NOT_EXECUTED',bench_revision='r2',selected_bench=model['bench_path'],model_sha256=sha(MODEL.read_bytes()),files_sha256=pins,execution_gate=model['execution_gate'],preserved_files_verified=len(model['preserved_files_sha256']),compile_plan_proposed_only=model['compile_plan_proposed_only'],simulate_plan_proposed_only=model['simulate_plan_proposed_only'])
    with (out/'preparation.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
