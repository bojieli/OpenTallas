#!/usr/bin/env python3
"""Prepare source copies only; no compiler, simulator, runner or previous GO reuse."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'results/rtl/dsrom_actual_element_rowfix_prepare_20261002/model.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def legacy():
    spec=importlib.util.spec_from_file_location('pinned_prepare',ROOT/'tools/prepare_dsrom_actual_element_gate.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def verify():
    m=json.loads(MODEL.read_text())
    for p,h in m['preserved_files_sha256'].items():
        original=subprocess.check_output(['git','show',m['preserved_commit']+':'+p],cwd=ROOT)
        if sha(original)!=h or (ROOT/p).read_bytes()!=original: raise ValueError('preserved artifact changed: '+p)
    for p,h in m['new_artifact_pins'].items():
        if sha((ROOT/p).read_bytes())!=h: raise ValueError('new artifact changed: '+p)
    for record in m['authority_records']+[m['source_case_driver'],m['model_binding']]:
        commit=record.get('commit',record.get('source_commit'))
        if sha(subprocess.check_output(['git','show',commit+':'+record['path']],cwd=ROOT))!=record['sha256']: raise ValueError('authority pin changed')
    return m

def files():
    m=json.loads(MODEL.read_text());g=legacy();sources=g.load_sources()
    for original,copy in m['source_copies'].items(): sources[original]=(ROOT/copy).read_text()
    # Original source keys intentionally retained: generated compile names unchanged,
    # same corrected copy on both sides, candidate delta only common helper bodies.
    package=g.generate(sources)
    for p in (m['bench_path'],'rtl/test/dsrom_actual_element_rom.cpp'): package[Path(p).name]=(ROOT/p).read_text()
    return package

def prepare(out):
    if out.exists(): raise FileExistsError(out)
    m=verify();package=files();pins={p:sha(t.encode()) for p,t in package.items()}
    if pins!=m['generated_files_sha256']:raise ValueError('generated pins changed')
    out.mkdir(parents=True,exist_ok=False)
    for p,t in package.items():
        with (out/p).open('x') as f:f.write(t)
    receipt=dict(status='ROWFIX_PREPARED_NOT_BUILT',selected_bench=m['bench_path'],model_sha256=sha(MODEL.read_bytes()),files_sha256=pins,preserved_count=len(m['preserved_files_sha256']),execution_gate=m['execution_gate'],compile_authorized=False,simulate_authorized=False)
    with (out/'preparation.json').open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n')
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
