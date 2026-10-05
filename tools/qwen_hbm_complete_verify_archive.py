#!/usr/bin/env python3
"""Verify immutable token-0 software archive without rerunning arithmetic."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
import numpy as np

def verify(directory,repo=None):
    directory=Path(directory);r=json.loads((directory/'receipt.json').read_text())
    for name,digest in r['artifacts_sha256'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:raise ValueError('archive byte hash '+name)
    execution=json.loads((directory/'token0_execution.json').read_text())
    if execution['status']!='SOFTWARE_PROGRAM_COMPLETED' or not execution['fullshape'] or not execution['complete_program_executed']:raise ValueError('missing positive software completion')
    if execution['instructions_retired']!=1737 or len(execution['trace'])!=1737:raise ValueError('incomplete instruction retirement')
    done=set()
    for index,op in enumerate(execution['trace']):
        if op['id']!=index or not set(op['dependencies'])<=done:raise ValueError('instruction dependency retirement')
        if op['cycles'] is not None:raise ValueError('software trace assigned hardware cycles')
        done.add(index)
    comparisons=json.loads((directory/'independent_comparisons.json').read_text())
    if comparisons!=execution['post_execution_comparisons'] or len(comparisons)!=39:raise ValueError('independent comparison boundaries')
    names={c['register'] for c in comparisons}
    if names!={f'L{layer}.X' for layer in range(36)}|{'head.norm','head.d0.scaled','head.d1.scaled'}:raise ValueError('missing layer/head comparison')
    if any(c['bit_mismatches'] or c['actual_nonfinite'] or c['reference_nonfinite'] for c in comparisons):raise ValueError('numeric comparison failed')
    hashes=json.loads((directory/'layer_source_npy_sha256.json').read_text())
    with zipfile.ZipFile(directory/'token0_layer_outputs.npz') as archive:
        if set(archive.namelist())!=set(hashes):raise ValueError('layer archive members')
        for name,digest in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:raise ValueError('original layer bytes '+name)
    with np.load(directory/'token0_layer_outputs.npz',allow_pickle=False) as arrays:
        if len(arrays.files)!=36 or any(arrays[key].shape!=(4096,) or not np.isfinite(arrays[key]).all() for key in arrays.files):raise ValueError('full-shape layer payload')
    head=[]
    for die in range(2):
        a=np.load(directory/f'token0_head.d{die}.scaled.npy',allow_pickle=False)
        if a.shape!=(75968,) or not np.isfinite(a).all():raise ValueError('full-shape head payload')
        head.append(a)
    next_token=int(np.argmax(np.concatenate(head)))
    if next_token!=execution['next_token'] or next_token!=r['next_token']:raise ValueError('independent global argmax')
    if r['actual_process_returncode'] is not None or not r['whole_two_token_job_live']:raise ValueError('archive scope changed; token0 captured with whole job live')
    if execution['actual_RTL_executed'] or r['actual_RTL_executed'] or r['token_cycles'] is not None or r['token_rate'] is not None:raise ValueError('software qualification boundary')
    if repo is not None:
        for name,digest in r['source_sha256'].items():
            data=subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=repo)
            if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('immutable source pin '+name)
    return dict(token0_software_archive='PASS',layers=36,head_rows=151936,next_token=next_token,
                comparison_boundaries=39,bit_mismatches=0,actual_RTL_executed=False,
                whole_job_returncode_at_capture=None,token_cycles=None,token_rate=None)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--repo',type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.archive,args.repo)))
